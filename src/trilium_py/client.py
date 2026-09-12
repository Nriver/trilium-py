import mimetypes
import json
import os
import re
import string
import sys
import urllib.parse
from collections import deque
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional, Union

import markdown2
import requests
from bs4 import BeautifulSoup
from dateutil.tz import tzlocal
from loguru import logger
from natsort import natsort
from tqdm import tqdm

from .utils.file_util import replace_extension
from .utils.html_util import add_internal_links
from .utils.image_util import compress_image_bytes, get_extension_from_image_mime
from .utils.markdown_math import reconstructMath, sanitizeInput
from .utils.note_util import beautify_content, sort_note_by_headings, preprocess_note_title_list
from .utils.param_util import clean_param, format_query_string
from .utils.time_util import (
    get_today,
    get_yesterday,
    format_dates_for_api,
)
from .version import __version__


def _parse_front_matter_tags(frontmatter: str) -> list[str]:
    """Extract a `tags:` string list from a Markdown front matter block.

    Handles the Joplin "Markdown + Front Matter" shape:

        tags:
          - nix
          - 'quoted ''tag'''

    Only a block-style list directly under a top-level `tags:` key is read;
    anything else (inline `tags: []`, missing key, ...) yields [].
    Single/double-quoted scalars are unquoted. Order is preserved,
    duplicates are removed.
    """
    tags: list[str] = []
    lines = frontmatter.split('\n')
    i = 0
    while i < len(lines):
        if re.match(r'^tags:\s*$', lines[i]):
            i += 1
            while i < len(lines) and re.match(r'^\s+-\s+', lines[i]):
                item = re.sub(r'^\s+-\s+', '', lines[i]).strip()
                if len(item) >= 2 and item.startswith("'") and item.endswith("'"):
                    item = item[1:-1].replace("''", "'")
                elif len(item) >= 2 and item.startswith('"') and item.endswith('"'):
                    item = item[1:-1].replace('\\"', '"').replace('\\\\', '\\')
                if item:
                    tags.append(item)
                i += 1
            break
        i += 1
    return list(dict.fromkeys(tags))


def _parse_front_matter_title(frontmatter: str) -> Optional[str]:
    """Extract the `title:` value from a Markdown front matter block.

    Handles the Joplin "Markdown + Front Matter" shapes ``title: plain``,
    ``title: 'single ''quoted'''`` and ``title: "double \\"quoted\\""``.
    Returns ``None`` when absent or empty so callers can fall back to the
    file name (which is filesystem-sanitised and truncated).
    """
    match = re.search(r'^title:[ \t]*(.+)$', frontmatter, re.MULTILINE)
    if not match:
        return None
    item = match.group(1).strip()
    if len(item) >= 2 and item.startswith("'") and item.endswith("'"):
        item = item[1:-1].replace("''", "'")
    elif len(item) >= 2 and item.startswith('"') and item.endswith('"'):
        item = item[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    item = item.strip()
    return item or None


def _format_front_matter_date(raw: str) -> tuple[Optional[str], Optional[str]]:
    """Normalise a front matter timestamp to Trilium's (local, UTC) pair.

    Accepts the Joplin "Markdown + Front Matter" shape
    ``YYYY-MM-DD HH:MM:SS[.mmm][Z]``. Returns ``(None, None)`` for anything
    else so callers can omit the field (preserving Trilium's "now" default).
    """
    ts_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(\.\d+)?(Z?)$', raw.strip())
    if not ts_match:
        return None, None
    base, millis, _tz = ts_match.groups()
    millis = (millis or '.000')[:4].ljust(4, '0')  # ensure exactly .mmm
    utc_date = f"{base}{millis}Z"

    # Convert to local timezone
    dt_utc = datetime.strptime(f"{base}{millis}", "%Y-%m-%d %H:%M:%S.%f").replace(
        tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(tzlocal())
    local_date = dt_local.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt_local.microsecond // 1000:03d}{dt_local.strftime('%z')}"
    return local_date, utc_date


def _read_front_matter_modified(md_file: str) -> tuple[Optional[str], Optional[str]]:
    """(dateModified, utcDateModified) from a Markdown front matter `updated:` key.

    Returns ``(None, None)`` when the file cannot be read or holds no
    parseable value, so callers can skip the date restore.
    """
    try:
        with open(md_file, encoding='utf-8') as fh:
            content = fh.read()
    except OSError:
        return None, None
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not frontmatter_match:
        return None, None
    updated_match = re.search(r'^updated:\s*(.+)$', frontmatter_match.group(1), re.MULTILINE)
    if not updated_match:
        return None, None
    return _format_front_matter_date(updated_match.group(1))


class ETAPI:
    __version__ = __version__

    def __init__(self, server_url: str, token: Optional[str] = None):
        if sys.version_info < (3, 9):
            print(
                (
                    f'You are using Python {sys.version_info.major}.{sys.version_info.minor}'
                    ', 3.9+ is required.'
                ),
                file=sys.stderr,
            )

        self.server_url = server_url
        self.token: str = token  # type: ignore

    def get_header(self) -> dict:
        return {
            'Authorization': self.token,
        }

    def login(self, password: str) -> Optional[str]:
        """
        generate token with password
        """
        url = f'{self.server_url}/etapi/auth/login'

        data = {'password': password}

        res = requests.post(url, data=data)
        if res.status_code == 201:
            self.token = res.json()['authToken']
            return self.token
        else:
            logger.info(res.json()['message'])
            return None

    def logout(self, token_to_destroy: Optional[str] = None) -> bool:
        """
        destroy token
        """

        if not token_to_destroy:
            token_to_destroy = self.token

        if not token_to_destroy:
            return False

        url = f'{self.server_url}/etapi/auth/logout'
        headers = {
            'Authorization': token_to_destroy,
        }
        res = requests.post(url, headers=headers)
        if res.status_code == 204:
            logger.info('logout successfully')
            return True
        return False

    def app_info(self) -> dict:
        """
        basic info about running Trilium version.

        :return:
        """
        url = f'{self.server_url}/etapi/app-info'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def search_note(self, search: str, **params) -> dict:
        """

        :param search:
        :param params:
        :return:
        """
        url = f'{self.server_url}/etapi/notes'
        params['search'] = search
        res = requests.get(url, params=format_query_string(params), headers=self.get_header())
        return res.json()

    def get_note(self, noteId: str) -> dict:
        """
        get note by note id
        root note's id is just "root"

        :param noteId:
        :return:
        """
        url = f'{self.server_url}/etapi/notes/{noteId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_note(
            self,
            parentNoteId: str,
            title: str,
            type: str,
            mime: Optional[str] = None,
            content=None,
            notePosition: Optional[int] = None,
            prefix: Optional[str] = None,
            isExpanded: Optional[str] = None,
            noteId: Optional[str] = None,
            branchId: Optional[str] = None,
            dateCreated: Optional[str] = None,
            utcDateCreated: Optional[str] = None,
            dateModified: Optional[str] = None,
            utcDateModified: Optional[str] = None
    ) -> dict:
        """
        Actually it's create or update,
        if noteId already exists, the corresponding note will be updated

        :param parentNoteId:
        :param title:
        :param type:
        :param mime:
        :param content:
        :param notePosition:
        :param prefix:
        :param isExpanded:
        :param noteId:
        :param branchId:
        :param dateCreated: local-time creation override, already in ETAPI
            local format (e.g. from _format_front_matter_date)
        :param utcDateCreated: UTC creation override, already in ETAPI UTC
            format. The server derives one from the other when only one is
            given; omit both for the default (current datetime).
        :param dateModified: local-time last-modified override (needs a Trilium
            server with ETAPI dateModified support; omitted when None)
        :param utcDateModified: UTC last-modified override (needs a Trilium
            server with ETAPI utcDateModified support; omitted when None)
        :return:
        """
        url = f'{self.server_url}/etapi/create-note'

        params = {
            "parentNoteId": parentNoteId,
            "title": title,
            "type": type,
            "mime": mime,
            "content": content,
            "notePosition": notePosition,
            "prefix": prefix,
            "isExpanded": isExpanded,
            "noteId": noteId,
            "branchId": branchId,
            "dateCreated": dateCreated,
            "utcDateCreated": utcDateCreated,
            "dateModified": dateModified,
            "utcDateModified": utcDateModified,
        }

        res = requests.post(url, json=clean_param(params), headers=self.get_header())

        return res.json()

    def _create_binary_note(
            self,
            parentNoteId: str,
            title: str,
            file_path: str,
            type: str,
            mime: str,
            content: str,
            notePosition: Optional[int] = None,
            prefix: Optional[str] = None,
            isExpanded: Optional[str] = None,
            noteId: Optional[str] = None,
            branchId: Optional[str] = None,
    ):
        '''
        Helper method to create a note with binary content (file or image)

        :param parentNoteId: ID of the parent note
        :param title: Title of the note
        :param file_path: Path to the file in the file system
        :param type: Type of the note ('file' or 'image')
        :param mime: MIME type of the file
        :param content: Initial content for the note
        :param notePosition: Position of the note (optional)
        :param prefix: Prefix for the note (optional)
        :param isExpanded: Whether the note is expanded (optional)
        :param noteId: ID for the note (optional)
        :param branchId: ID for the branch (optional)
        :return: Response JSON or None if failed
        '''
        url = f'{self.server_url}/etapi/create-note'

        params = {
            "parentNoteId": parentNoteId,
            "title": title,
            "type": type,
            "mime": mime,
            "content": content,
            "notePosition": notePosition,
            "prefix": prefix,
            "isExpanded": isExpanded,
            "noteId": noteId,
            "branchId": branchId,
        }

        res_note = requests.post(
            url,
            json=clean_param(params),
            headers={
                'content-type': 'application/json',
                'Authorization': self.token,
            },
        )
        res_note_json = res_note.json()
        new_noteId = res_note_json['note']['noteId']

        # set file name
        file_path_name = os.path.basename(file_path)
        self.create_attribute(
            attributeId=None,
            noteId=new_noteId,
            type='label',
            name='originalFileName',
            value=file_path_name,
            isInheritable=False,
        )

        # upload file, set note content
        url = f'{self.server_url}/etapi/notes/{new_noteId}/content'
        file_data = open(file_path, 'rb').read()
        res = requests.put(
            url,
            data=file_data,
            headers={
                'content-type': 'application/octet-stream',
                'Content-Transfer-Encoding': 'binary',
                'Authorization': self.token,
            },
        )
        if res.status_code == 204:
            return res_note_json
        return None

    def create_file_note(
            self,
            parentNoteId: str,
            title: str,
            file_path: str,
            type: str = 'file',
            mime: str = "application/octet-stream",
            content='<p></p>',
            notePosition: Optional[int] = None,
            prefix: Optional[str] = None,
            isExpanded: Optional[str] = None,
            noteId: Optional[str] = None,
            branchId: Optional[str] = None,
    ):
        '''
        Upload ordinary file as a sub-note

        Create a note
        set file name attribute
        Update its content with raw file binary content
        :param parentNoteId:
        :param title:
        :param file_path: file path in file system.
        :param type:
        :param mime:
        :param content:
        :param notePosition:
        :param prefix:
        :param isExpanded:
        :param noteId:
        :param branchId:
        :return:
        '''
        return self._create_binary_note(
            parentNoteId=parentNoteId,
            title=title,
            file_path=file_path,
            type=type,
            mime=mime,
            content=content,
            notePosition=notePosition,
            prefix=prefix,
            isExpanded=isExpanded,
            noteId=noteId,
            branchId=branchId
        )

    def create_image_note(
            self,
            parentNoteId: str,
            title: str,
            image_file: str,
            type: str = 'image',
            mime: Optional[str] = None,
            content: str = "image",
            notePosition: Optional[int] = None,
            prefix: Optional[str] = None,
            isExpanded: Optional[str] = None,
            noteId: Optional[str] = None,
            branchId: Optional[str] = None,
    ):
        '''
        Upload image as a sub-note

        Create a note
        set file name attribute
        Update its content with image binary content

        :param parentNoteId:
        :param title:
        :param image_file:
        :param type:
        :param mime:
        :param content:
        :param notePosition:
        :param prefix:
        :param isExpanded:
        :param noteId:
        :param branchId:
        :return:
        '''
        if not mime:
            # if mime not specified, get mime info by python-magic package
            mime, _ = mimetypes.guess_type(image_file)

        if not mime:
            # just in case python-magic not working, give a default mime
            mime = "image/png"

        return self._create_binary_note(
            parentNoteId=parentNoteId,
            title=title,
            file_path=image_file,
            type=type,
            mime=mime,
            content=content,
            notePosition=notePosition,
            prefix=prefix,
            isExpanded=isExpanded,
            noteId=noteId,
            branchId=branchId
        )

    def patch_note(
            self,
            noteId: str,
            title: Optional[str] = None,
            type: Optional[str] = None,
            mime: Optional[str] = None,
            dateCreated: Optional[datetime] = None,
            utcDateCreated: Optional[datetime] = None,
            dateModified: Optional[str] = None,
            utcDateModified: Optional[str] = None,
    ) -> dict:
        """
        Update note properties.

        Args:
            noteId (str): ID of the note to update
            title (str, optional): New title for the note
            type (str, optional): New type for the note
            mime (str, optional): New MIME type for the note
            dateCreated (datetime, optional): New creation date (local time)
            utcDateCreated (datetime, optional): New creation date (UTC time)
            dateModified (str, optional): New last-modified date, already in
                ETAPI local format (e.g. from _format_front_matter_date).
                Needs a Trilium server with ETAPI dateModified PATCH support.
            utcDateModified (str, optional): New last-modified date, already in
                ETAPI UTC format. Takes precedence over dateModified.

        Returns:
            dict: Response from the API
        """
        url = f'{self.server_url}/etapi/notes/{noteId}'

        # Format dates for API if provided
        formatted_date_created, formatted_utc_date_created = None, None
        if dateCreated or utcDateCreated:
            formatted_date_created, formatted_utc_date_created = format_dates_for_api(
                local_date=dateCreated,
                utc_date=utcDateCreated
            )

        params = {
            "title": title,
            "type": type,
            "mime": mime,
            "dateCreated": formatted_date_created,
            "utcDateCreated": formatted_utc_date_created,
            "dateModified": dateModified,
            "utcDateModified": utcDateModified,
        }
        res = requests.patch(url, json=clean_param(params), headers=self.get_header())
        return res.json()

    def delete_note(self, noteId: str) -> bool:
        url = f'{self.server_url}/etapi/notes/{noteId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def get_note_content(self, noteId: str) -> str:
        url = f'{self.server_url}/etapi/notes/{noteId}/content'
        res = requests.get(url, headers=self.get_header())
        return res.content.decode('utf-8')

    def update_note_content(self, noteId: str, content: str) -> bool:
        """update note content"""
        url = f'{self.server_url}/etapi/notes/{noteId}/content'
        res = requests.put(
            url,
            data=content.encode('utf-8'),
            headers={'content-type': 'text/plain', 'Authorization': self.token},
        )
        if res.status_code == 204:
            return True
        return False

    def get_branch(self, branchId: str) -> dict:
        url = f'{self.server_url}/etapi/branches/{branchId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_branch(
            self,
            noteId: str,
            parentNoteId: str,
            prefix: str = "",
            notePosition: int = 0,
            isExpanded: bool = False,
            utcDateModified=None
    ) -> dict:
        """
         In Trilium, a *clone* (internally called a "branch") links a note to a parent note,
        allowing the same note to appear in multiple places within the note tree.
        This method creates such a clone or updates an existing one if it already exists
        between the specified parent and child.

        :param noteId:
        :param parentNoteId:
        :param prefix:
        :param notePosition:
        :param isExpanded:
        :param utcDateModified:
        :return:
        """
        url = f'{self.server_url}/etapi/branches/'
        params = {
            "noteId": noteId,
            "parentNoteId": parentNoteId,
            "prefix": prefix,
            "notePosition": notePosition,
            "isExpanded": isExpanded,
            "utcDateModified": utcDateModified,
        }
        res = requests.post(url, json=clean_param(params), headers=self.get_header())
        return res.json()

    def patch_branch(self, branchId: str, notePosition: int, prefix: str, isExpanded: bool) -> dict:
        url = f'{self.server_url}/etapi/branches/{branchId}'
        params = {
            "notePosition": notePosition,
            "prefix": prefix,
            "isExpanded": isExpanded,
        }
        res = requests.patch(url, json=clean_param(params), headers=self.get_header())
        return res.json()

    def delete_branch(self, branchId: str) -> bool:
        url = f'{self.server_url}/etapi/branches/{branchId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def get_attribute(self, attributeId: str) -> dict:
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_attribute(
            self,
            noteId: str,
            type: str,
            name: str,
            value: str,
            isInheritable: bool,
            attributeId: Optional[str] = None,
    ) -> dict:
        url = f'{self.server_url}/etapi/attributes/'
        params = {
            "noteId": noteId,
            "type": type,
            "name": name,
            "value": value,
            "isInheritable": isInheritable,
            "attributeId": attributeId,
        }
        res = requests.post(url, json=clean_param(params), headers=self.get_header())
        return res.json()

    def patch_attribute(self, attributeId: str, value: str) -> dict:
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        params = {
            "value": value,
        }
        res = requests.patch(url, json=clean_param(params), headers=self.get_header())
        return res.json()

    def delete_attribute(self, attributeId: str) -> bool:
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def refresh_note_ordering(self, parentNoteId: str) -> bool:
        url = f'{self.server_url}/etapi/refresh-note-ordering/{parentNoteId}'
        res = requests.post(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def inbox(self, date: str) -> dict:
        url = f'{self.server_url}/etapi/inbox/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_days(self, date: str) -> dict:
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_weeks(self, date: str):
        url = f'{self.server_url}/etapi/calendar/weeks/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_months(self, month: str) -> dict:
        url = f'{self.server_url}/etapi/calendar/months/{month}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_years(self, year: str) -> dict:
        url = f'{self.server_url}/etapi/calendar/years/{year}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def export_note(self, noteId: str, format: str, save_path: str, chunk_size=128):
        """
        Export note by id. Please note that protected notes are not allowed to be exported by ETAPI.

        :param noteId: note id
        :param format: format should be "html" or "markdown" or "md" for short
        :save_path: path for exported file
        :chunk_size: download chunk size, default to 128
        :return:
        """
        url = f'{self.server_url}/etapi/notes/{noteId}/export'
        if format in ['md', 'markdown']:
            format = 'markdown'
        else:
            format = 'html'
        params = {
            "format": format,
        }
        r = requests.get(url, params=clean_param(params), headers=self.get_header())
        logger.info(r.status_code)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)
        return True

    def import_note(self, noteId: str, file_path: str):
        """
        import zip format note
        """
        url = f'{self.server_url}/etapi/notes/{noteId}/import'
        file_data = open(file_path, 'rb').read()
        res = requests.post(
            url,
            data=file_data,
            headers={
                'content-type': 'application/octet-stream',
                'Content-Transfer-Encoding': 'binary',
                'Authorization': self.token,
            },
        )
        logger.info(res)
        if res.status_code == 201:
            return True
        else:
            return False

    def save_revision(self, noteId: str):
        """
        force save note revision
        :param noteId:
        :return:
        """

        url = f'{self.server_url}/etapi/notes/{noteId}/revision'
        res = requests.post(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def get_today_note_content(self):
        date = get_today()
        return self.get_day_note(date)

    def set_today_note_content(self, content):
        date = get_today()
        return self.set_day_note(date, content)

    def get_yesterday_note_content(self):
        date = get_yesterday()
        return self.get_day_note(date)

    def set_yesterday_note_content(self, content):
        date = get_yesterday()
        return self.set_day_note(date, content)

    def get_day_note(self, date):
        """
        get note content by date
        :param date: date string in format of "%Y-%m-%d", e.g. "2022-02-25"
        :return:
        """
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        noteId = res.json()['noteId']
        content = self.get_note_content(noteId)
        return content

    def set_day_note(self, date, content):
        """
        set note content by date
        :param date: date string in format of "%Y-%m-%d", e.g. "2022-02-25"
        :param content: note content
        :return:
        """
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        noteId = res.json()['noteId']
        return self.update_note_content(noteId, content)

    def get_todo(self) -> list[list[Union[bool, str]]]:
        """get today's todo list.

        :return: list of todo items, each item is a list of [status, description]
        """
        content = self.get_today_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        try:
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            todo_list: list[list[Union[bool, str]]] = []
            for x in todo_labels:
                description = x.text.strip()
                checked = x.find("input").get("checked")
                if checked:
                    status = True
                else:
                    status = False
                todo_list.append([status, description])
        finally:
            # free mem
            soup.decompose()
            del soup
        return todo_list

    def todo_check(self, todo_index: int, check: bool = True) -> bool:
        """check/uncheck a todo item by index.

        :param todo_index: index starts from 0
        :param check: True to check, False to uncheck
        :return: True if success, False if failed
        """
        content = self.get_today_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        try:
            label = todo_labels[todo_index]
            check_input = label.find("input")
            if check:
                check_input['checked'] = 'checked'
            else:
                del check_input['checked']

            new_content = str(soup)
            return self.set_today_note_content(new_content)
        except IndexError:
            return False
        finally:
            # free mem
            soup.decompose()
            del soup

    def todo_uncheck(self, todo_index: int) -> bool:
        """uncheck a todo item by index.

        :param todo_index: index starts from 0
        :return: True if success, False if failed
        """
        return self.todo_check(todo_index, check=False)

    def add_todo(
            self, todo_description: str, todo_caption: str = r'<p>TODO:</p>', date: str = None
    ) -> bool:
        """append item to todo list.

        :param todo_description: todo item
        :param todo_caption: caption added to new todo lists, default to '<p>TODO:</p>'
        :param date: date string in format of "%Y-%m-%d", e.g. "2022-02-25"
        :return: True if success, False if failed
        """
        todo_description = todo_description.strip()
        soup: Optional[BeautifulSoup] = None
        try:
            if not date:
                date = get_today()
            content = self.get_day_note(date)
            soup = BeautifulSoup(content, 'html.parser')
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            # append todo item after last todo item
            # special case 1: no todo available, add it to the beginning of document
            # special case 2: if last todo item is empty, update it

            if "todo-list__label" in todo_description:
                todo_item_html = f'''<li>{todo_description}</li>'''
            else:
                todo_item_html = ItemTemplate(todo_description).substitute()

            if not todo_labels:
                logger.info('new empty page')
                todo_item_html = ListTemplate(todo_caption).substitute(items=todo_item_html)
                todo_item = BeautifulSoup(todo_item_html, 'html.parser')
                soup.insert(0, todo_item)
            else:
                last_todo_label = todo_labels[-1]
                if not last_todo_label.text.strip():
                    # replace last empty todo item
                    todo_item = BeautifulSoup(todo_item_html, 'html.parser')
                    todo_list_label = soup.find_all("ul", {"class": "todo-list"})[0]
                    empty_li = todo_list_label.find_all("li")[-1]
                    empty_li.replace_with(todo_item)
                else:
                    # if todo item list exists, append to the end
                    todo_item = BeautifulSoup(todo_item_html, 'html.parser')
                    todo_list_label = soup.find_all("ul", {"class": "todo-list"})[0]
                    todo_list_label.append(todo_item)
            new_content = str(soup)
            return self.set_day_note(date, new_content)
        except Exception as e:
            logger.info(e)
            return False
        finally:
            # free mem
            if soup:
                soup.decompose()
                del soup

    def update_todo(self, todo_index: int, todo_description: str) -> bool:
        """update a todo item by index.

        :param todo_index: index starts from 0
        :param todo_description: new todo item
        :return: True if success, False if failed"""
        todo_description = todo_description.strip()

        content = self.get_today_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        try:
            todo_label = todo_labels[todo_index]
            target_span = todo_label.find_next("span", {"class": "todo-list__label__description"})
            target_span.string = todo_description
            new_content = str(soup)
            return self.set_today_note_content(new_content)
        except IndexError:
            return False
        finally:
            # free mem
            soup.decompose()
            del soup

    def delete_todo(self, todo_index: int) -> bool:
        """delete a todo item by index.

        :param todo_index: index starts from 0
        :return: True if success, False if failed
        """
        date = get_today()
        return self.delete_date_todo(date, todo_index)

    def delete_yesterday_todo(self, todo_index: int) -> bool:
        """delete todo item by index from yesterday's note.

        :param todo_index: index starts from 0
        :return: True if success, False if failed
        """
        date = get_yesterday()
        return self.delete_date_todo(date, todo_index)

    def delete_date_todo(self, date: str, todo_index: int) -> bool:
        """delete todo item by index from a specific date's note.

        :param date: date in format of "%Y-%m-%d", e.g. "2022-02-25"
        :param todo_index: index starts from 0
        :return: True if success, False if failed
        """
        content = self.get_day_note(date)

        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        try:
            todo_label = todo_labels[todo_index]
            # decompose parent <li> tag
            todo_label.parent.decompose()

            new_content = str(soup)
            return self.set_day_note(date, new_content)
        except IndexError:
            return False
        finally:
            # free mem
            soup.decompose()
            del soup

    def get_yesterday_unfinished_todo(self) -> list[list[Union[bool, str]]]:
        """get yesterday's unfinished todo list.

        :return: list of todo items, each item is a list of [status, description]
        """
        content = self.get_yesterday_note_content()

        unfinished_todo_list = []
        soup = BeautifulSoup(content, 'html.parser')
        try:
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            for x in todo_labels:
                checked = x.find("input").get("checked")
                if not checked:
                    description = x.text.strip()
                    unfinished_todo_list.append([False, description])
        finally:
            # free mem
            soup.decompose()
            del soup
        return unfinished_todo_list

    def move_yesterday_unfinished_todo_to_today(self) -> None:
        """move yesterday's unfinished todo list to today's note."""
        content = self.get_yesterday_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        try:
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            todo_indexes = []
            todo_descriptions = []
            for i, x in enumerate(todo_labels):
                checked = x.find("input").get("checked")
                if not checked:
                    description = x.text.strip()
                    if not description:
                        # skip empty todos
                        continue
                    todo_indexes.append(i)
                    # keep the internal link, text format or what so ever, avoid lost valuable info
                    todo_descriptions.append(str(x))

            if not todo_descriptions:
                return

            # add todos to today
            for description in todo_descriptions:
                self.add_todo(description)

            # remove todos from yesterday
            for i in reversed(sorted(todo_indexes)):
                self.delete_yesterday_todo(i)
        finally:
            soup.decompose()
            del soup

    def sort_todo(self, noteId: Optional[str] = None, date: Optional[str] = None,
                  append_new_done: bool = False) -> bool:
        """Sort todo list items for a specific date.

        :param noteId: target note ID. If provided, the date parameter will be ignored.
        :param date: date string in format of "%Y-%m-%d", default to today
        :param append_new_done:
            False: Unfinished tasks first, finished tasks last. Keep original order within each group.
            True: Unfinished tasks first, finished tasks last. Newly finished tasks will be appended after previously finished tasks.
        :return: True if success, False if failed
        """
        soup = None
        try:
            if noteId:
                content = self.get_note_content(noteId)
            else:
                if not date:
                    date = get_today()
                content = self.get_day_note(date)

            soup = BeautifulSoup(content, 'html.parser')
            todo_lists = soup.find_all("ul", {"class": "todo-list"})
            if not todo_lists:
                return True

            for todo_list_ul in todo_lists:
                todo_labels = todo_list_ul.find_all("label", {"class": "todo-list__label"})
                if not todo_labels:
                    continue

                items = []
                for label in todo_labels:
                    checked = label.find("input").get("checked")
                    is_done = True if checked else False
                    li_tag = label.parent
                    items.append({
                        'is_done': is_done,
                        'li': li_tag
                    })

                if not append_new_done:
                    sorted_items = sorted(items, key=lambda x: x['is_done'])
                    final_lis = [item['li'] for item in sorted_items]
                else:
                    # Push newly checked items to the absolute bottom.
                    still_todo = [x for x in items if not x['is_done']]
                    old_done = []
                    idx = len(items) - 1
                    while idx >= 0 and items[idx]['is_done']:
                        old_done.insert(0, items[idx])
                        idx -= 1
                    new_done = [x for x in items[:idx + 1] if x['is_done']]
                    # Recombine: remaining todos -> old completed -> newly completed
                    final_lis = (
                            [x['li'] for x in still_todo] +
                            [x['li'] for x in old_done] +
                            [x['li'] for x in new_done]
                    )

                # Extract <li> nodes safely from DOM tree to prevent them from being destroyed by clear()
                for li in final_lis:
                    li.extract()
                # Clear container and re-append elements with the new order
                todo_list_ul.clear()
                for li in final_lis:
                    todo_list_ul.append(li)

            new_content = str(soup)
            if noteId:
                return self.update_note_content(noteId, new_content)
            else:
                return self.set_day_note(date, new_content)

        except Exception as e:
            logger.info(f"Sort todo failed: {e}")
            return False
        finally:
            if soup:
                soup.decompose()
                del soup

    def add_periodic_todos(self, periodic_todos):
        today = datetime.today().date()
        weekday = today.isoweekday()  # Monday=1, Sunday=7
        day = today.day
        month = today.month
        year = today.year

        # last day of month
        next_month = month % 12 + 1
        next_month_year = year + (1 if next_month == 1 else 0)
        last_day_of_month = (datetime(next_month_year, next_month, 1).date() - timedelta(days=1)).day

        today_todos = self.get_todo()

        for task in periodic_todos:
            task_content = task["content"]
            add_task = False

            # Daily task
            if task.get("type") == "daily":
                add_task = True

            # Weekly task
            elif task.get("type") == "weekly" and task.get("weekday") == weekday:
                add_task = True

            # Monthly task
            elif task.get("type") == "monthly":
                task_day = task.get("day")
                if isinstance(task_day, int):
                    if task_day > 0:
                        # Positive day → fixed day of month (e.g. 1 = first day)
                        if day == task_day:
                            add_task = True
                    elif task_day < 0:
                        # Negative day → count from the end of month (e.g. -1 = last day, -2 = second last day)
                        target_day = last_day_of_month + 1 + task_day
                        if day == target_day:
                            add_task = True

            # Yearly task
            elif task.get("type") == "yearly":
                if task.get("month") == month and task.get("day") == day:
                    add_task = True

            # Custom date range (string to date)
            start_date = task.get("start_date")
            end_date = task.get("end_date")
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                if today < start_date:
                    add_task = False
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                if today > end_date:
                    add_task = False

            # Add todo if not already present
            if add_task and task_content not in today_todos:
                self.add_todo(task_content)

        return

    def upload_md_file(
            self, file: str,
            parentNoteId: str,
            parse_math: bool = True,
            image_and_file_as_attachments: bool = True,
            hasFrontMatter: bool = False,
            cleanText: bool = False,
            importTags: bool = False,
            importModified: bool = False,
            skipMdFileLinks: bool = False
    ):
        md_file = os.path.abspath(file).replace('\\', '/').replace('//', '/')
        md_full_name = os.path.basename(md_file)
        md_name = md_full_name[:-3]
        md_folder = os.path.dirname(md_file)
        logger.info(md_file)
        # logger.info(md_name)
        # logger.info(md_folder)

        # convert md to html
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

            utcDateCreated = None
            dateCreated = None
            dateModified = None
            utcDateModified = None
            front_matter_tags: list[str] = []

            if hasFrontMatter:

                # Extract and strip FrontMatter (delimited by leading ---)
                frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if frontmatter_match:
                    frontmatter = frontmatter_match.group(1)
                    content = content[frontmatter_match.end():]

                    # Extract the 'created' key from FrontMatter
                    created_match = re.search(r'^created:\s*(.+)$', frontmatter, re.MULTILINE)
                    if created_match:
                        dateCreated, utcDateCreated = _format_front_matter_date(created_match.group(1))

                    # Extract the 'updated' key as the note's last-modified
                    # date (opt-in: needs a Trilium server with ETAPI
                    # dateModified/utcDateModified support).
                    if importModified:
                        updated_match = re.search(r'^updated:\s*(.+)$', frontmatter, re.MULTILINE)
                        if updated_match:
                            dateModified, utcDateModified = _format_front_matter_date(updated_match.group(1))

                    # Extract the 'tags' list from FrontMatter (e.g. Joplin
                    # "Markdown + Front Matter" exports) for label import.
                    if importTags:
                        front_matter_tags = _parse_front_matter_tags(frontmatter)

                    # The file name is filesystem-sanitised (`/` `?` -> `_`,
                    # truncated), so prefer the real title when present.
                    front_matter_title = _parse_front_matter_title(frontmatter)
                    if front_matter_title:
                        md_name = front_matter_title

            # fix logseq image size format
            logseq_image_pat = r'(\!\[.*\]\(.*\))\{.*?:height.*width.*}'
            content = re.sub(logseq_image_pat, r'\1', content)

            # Check if we should parse math formulas
            if not parse_math or not re.search(re.escape("$"), content):
                # extra format support
                # https://github.com/trentm/python-markdown2/wiki/Extras
                html = markdown2.markdown(
                    content,
                    extras=['fenced-code-blocks', 'strike', 'tables', 'task_list', 'code-friendly'],
                )

                if cleanText:
                    html = beautify_content(html)

                # logger.info(html)
            else:
                # Parse math formulas
                no_latex_part, latex_code_part = sanitizeInput(content)
                html = reconstructMath(
                    markdown2.markdown(
                        no_latex_part,
                        extras=['fenced-code-blocks', 'strike', 'tables', 'task_list'],
                    ),
                    list(
                        map(
                            lambda x: x.replace("<", " \\lt ").replace(">", " \\gt "),
                            latex_code_part,
                        )
                    ),
                )
        note_id = ''

        # detect images
        # https://github.com/Nriver/trilium-py/issues/36
        pat = '<img (.*?)>'
        images = re.findall(pat, html)

        current_note_res = self.create_note(
            parentNoteId=parentNoteId,
            title=md_name,
            type="text",
            content=html,
            dateCreated=dateCreated,
            utcDateCreated=utcDateCreated,
            dateModified=dateModified,
            utcDateModified=utcDateModified
        )
        note_id = current_note_res['note']['noteId']
        # logger.info(note_id)

        # Import front matter tags (e.g. from Joplin) as Trilium labels.
        for tag in front_matter_tags:
            try:
                res = self.create_attribute(
                    noteId=note_id, type='label', name=tag, value='', isInheritable=False)
            except Exception as e:
                logger.warning(f'Failed to create label {tag!r} on note {note_id}: {e}')
                continue
            if not isinstance(res, dict) or 'attributeId' not in res:
                # trilium-py returns the JSON error body instead of raising.
                logger.warning(f'Failed to create label {tag!r} on note {note_id}: {res}')

        # Whether the HTML was rewritten to point at uploaded attachments.
        # Any PUT /content re-stamps dateModified to now on the server, so
        # these flags decide both whether a rewrite PUT is needed at all and
        # whether importModified dates must be restored afterwards via PATCH.
        images_rewritten = False
        files_rewritten = False

        if images:
            # images require manually upload and url need to be replaced
            logger.info('found images:')
            logger.info(images)

            # process images
            for match in images:
                # extract image url and name
                image_names = re.findall('alt="(.*?)"', match)
                image_paths = re.findall('src="(.*?)"', match)

                if not image_paths:
                    continue
                image_path = image_paths[0]
                if not image_names:
                    image_name = ''
                else:
                    image_name = image_names[0]

                # absolute path
                if image_path.startswith('http'):
                    # skip online images
                    continue

                # fix vnote image with special size format
                if ' ' in image_path and image_path.endswith('x'):
                    image_path = image_path.split(' ')[0]

                image_file_path = os.path.join(md_folder, image_path).replace('\\', '/')
                # unquote path, in case the url is quoted
                image_file_path_unquote = urllib.parse.unquote(image_file_path)

                # skip if path does not point to a valid file
                if os.path.isdir(image_file_path) or os.path.isdir(image_file_path_unquote):
                    continue

                # try both raw path and unquoted path
                if not os.path.exists(image_file_path):
                    if not os.path.exists(image_file_path_unquote):
                        # image file not exist, ignore it
                        continue
                    image_file_path = image_file_path_unquote

                if not image_name:
                    # if image name is not specified, use file name
                    image_name = os.path.basename(image_path)

                if image_and_file_as_attachments:
                    res = self.create_attachment(
                        ownerId=note_id,
                        file_path=image_file_path,
                        title=image_name,
                        role='image',
                    )
                    image_note_id = res['attachmentId']
                    image_url = f"api/attachments/{image_note_id}/image/{urllib.parse.quote(res['title'], safe='')}"
                    logger.info(image_url)
                else:
                    res = self.create_image_note(
                        parentNoteId=note_id,
                        title=image_name,
                        image_file=image_file_path,
                    )
                    # logger.info(res)
                    image_note_id = res['note']['noteId']
                    # fix path with `/` in it, the param should be quoted.
                    # e.g. relative url from obsidian
                    image_url = (
                        f"api/images/{image_note_id}/"
                        f"{urllib.parse.quote(res['note']['title'], safe='')}"
                    )
                    logger.info(image_url)

                html = html.replace(image_path, image_url)
                images_rewritten = True

                # add relation for image
                self.create_attribute(
                    attributeId=None,
                    noteId=note_id,
                    type='relation',
                    name='imageLink',
                    value=image_note_id,
                    isInheritable=False,
                )

            # Only rewrite the note when an attachment URL actually replaced a
            # local path. An unconditional PUT re-stamps dateModified to now on
            # the server, wiping the dateModified/utcDateModified sent on
            # create-note (e.g. notes with only external http(s) images).
            if images_rewritten:
                res = self.update_note_content(note_id, html)
            # logger.info(res)

        # detect files
        pat = '<a href="(.*?)">(.*)</a>'
        a_links = re.findall(pat, html)
        logger.info(a_links)
        for link, link_name in a_links:
            # fix file path
            file_path = ''
            if link.startswith(('http:', 'https:')):
                # skip online link
                continue
            if skipMdFileLinks and urllib.parse.unquote(link.split('#', 1)[0]).lower().endswith('.md'):
                # Note-to-note link: the folder-level second pass resolves
                # these to internal links once every note exists. Never
                # snapshot a note's source as a file attachment.
                continue
            if os.path.exists(link):
                # absolute file path
                file_path = link
            else:
                file_path = os.path.join(md_folder, link).replace('\\', '/')
                # unquote path, in case the url is quoted
                file_path_unquote = urllib.parse.unquote(file_path)

                # skip if path does not point to a valid file
                if os.path.isdir(file_path) or os.path.isdir(file_path_unquote):
                    continue

                # try both raw path and unquoted path
                if os.path.exists(file_path_unquote):
                    file_path = file_path_unquote

            # upload file
            if os.path.exists(file_path):
                logger.info(file_path)

                if image_and_file_as_attachments:
                    res = self.create_attachment(
                        ownerId=note_id,
                        file_path=file_path,
                        title=link_name,
                        role='file',
                    )
                    file_attachment_id = res['attachmentId']
                    file_url = f"#root/{note_id}?viewMode=attachments&amp;attachmentId={file_attachment_id}"
                    logger.info(file_url)
                else:
                    res = self.create_file_note(
                        parentNoteId=note_id,
                        title=link_name,
                        file_path=file_path,
                    )

                    # update file link
                    file_note_id = res['note']['noteId']
                    # fix path with `/` in it, the param should be quoted.
                    # e.g. relative url from obsidian
                    file_url = f"#root/{note_id}/{file_note_id}"

                html = html.replace(link, file_url)
                files_rewritten = True

        # A necessary content rewrite (local attachments replaced) re-stamps
        # dateModified to now on the server. Restore the front matter dates
        # afterwards when importModified requested them; older servers without
        # PATCH dateModified support 400 and the note keeps import-time dates.
        if files_rewritten:
            res = self.update_note_content(note_id, html)

        if (dateModified or utcDateModified) and (images_rewritten or files_rewritten):
            try:
                restore = self.patch_note(
                    noteId=note_id,
                    dateModified=dateModified,
                    utcDateModified=utcDateModified,
                )
                if not isinstance(restore, dict) or restore.get('code'):
                    logger.warning(f'Failed to restore last-modified on note {note_id}: {restore}')
            except Exception as e:
                logger.warning(f'Failed to restore last-modified on note {note_id}: {e}')

        return current_note_res

    def upload_md_folder(
            self,
            parentNoteId: str,
            mdFolder: str,
            includePattern: Optional[list[str]] = None,
            ignoreFolder: Optional[list[str]] = None,
            ignoreFile: Optional[list[str]] = None,
            parse_math: bool = True,
            hasFrontMatter: Optional[bool] = False,
            cleanText: Optional[bool] = False,
            importTags: bool = False,
            importModified: bool = False,
            resolveMdLinks: bool = False
    ):
        includePattern = includePattern or ['.md']
        ignoreFolder = ignoreFolder or []
        ignoreFile = ignoreFile or []

        # note tree
        # record for noteId
        note_tree = {'.': parentNoteId}
        logger.info(mdFolder)

        mdFolder = os.path.expandvars(os.path.expanduser(mdFolder))

        # Folder dates exported by our Joplin exporter (_folders.json): plain
        # directories carry no timestamps, so without this every folder note
        # stamps import time. A missing/invalid manifest keeps that default.
        folder_dates: dict = {}
        try:
            with open(os.path.join(mdFolder, '_folders.json'), encoding='utf-8') as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    folder_dates = loaded
        except (OSError, ValueError):
            folder_dates = {}

        error_files = {}
        # Source-md relpath -> created Trilium noteId, for the second pass
        # that resolves note-to-note links once every target exists.
        note_map: dict[str, str] = {}
        for root, dirs, files in os.walk(mdFolder, topdown=True):
            root_folder_name = os.path.basename(root)

            rel_path = os.path.relpath(root, start=mdFolder)
            if any(x in rel_path for x in ignoreFolder):
                continue

            logger.info('==============')
            logger.info(f'root {root}')
            logger.info(f'root_folder_name {root_folder_name}')
            logger.info(f'rel_path {rel_path}')

            current_parent_note_id = note_tree[rel_path]

            logger.info('files')
            for name in natsort.natsorted(files):
                # only include markdown files
                if any(x == name for x in ignoreFile):
                    continue

                if any(x in name for x in includePattern):
                    file_path = os.path.join(root, name)
                    logger.info(file_path)
                    try:
                        up_res = self.upload_md_file(file=file_path, parentNoteId=current_parent_note_id, parse_math=parse_math,
                                                     hasFrontMatter=hasFrontMatter, cleanText=cleanText,
                                                     importTags=importTags, importModified=importModified,
                                                     skipMdFileLinks=resolveMdLinks)
                        if resolveMdLinks and isinstance(up_res, dict):
                            created_id = up_res.get('note', {}).get('noteId') if isinstance(up_res.get('note'), dict) else None
                            if created_id:
                                note_map[os.path.normpath(os.path.relpath(file_path, start=mdFolder))] = created_id
                    except Exception as e:
                        error_files[os.path.abspath(file_path)] = e

            logger.info('dirs')
            for name in natsort.natsorted(dirs):
                if all(x not in name for x in ignoreFolder):
                    dir_path = os.path.join(root, name)
                    logger.info(dir_path)
                    rel_path = os.path.relpath(dir_path, start=mdFolder)
                    logger.info(rel_path)
                    # Directory names are filesystem-sanitised; prefer the
                    # real notebook title (and its Joplin emoji, appended so
                    # title sort order is unaffected).
                    title = name
                    entry = folder_dates.get(rel_path)
                    if isinstance(entry, dict):
                        if entry.get('title'):
                            title = entry['title']
                        if entry.get('icon'):
                            title = f"{title} {entry['icon']}"
                    folder_kwargs: dict = dict(
                        parentNoteId=current_parent_note_id,
                        title=title,
                        type="text",
                        content=name,
                    )
                    if isinstance(entry, dict):
                        if entry.get('created'):
                            folder_kwargs['dateCreated'], folder_kwargs['utcDateCreated'] = \
                                _format_front_matter_date(entry['created'])
                        if importModified and entry.get('updated'):
                            folder_kwargs['dateModified'], folder_kwargs['utcDateModified'] = \
                                _format_front_matter_date(entry['updated'])
                    res = self.create_note(**folder_kwargs)
                    res['note']['noteId']
                    note_tree[rel_path] = res['note']['noteId']

        if resolveMdLinks and note_map:
            # Second pass: every target now exists, so `.md` hrefs left alone
            # above can become internal links. Cycles need no special casing:
            # nothing is resolved until the map is complete.
            href_re = re.compile(r'<a href="(.*?)">(.*?)</a>')
            md_link_re = re.compile(r'(\]\(|href="|\]:)\s*\S*\.md', re.IGNORECASE)
            for md_rel, note_id in note_map.items():
                src_file = os.path.join(mdFolder, md_rel)
                try:
                    with open(src_file, encoding='utf-8') as fh:
                        if not md_link_re.search(fh.read()):
                            continue
                except OSError:
                    continue
                try:
                    html = self.get_note_content(note_id)
                except Exception as e:
                    logger.warning(f'Failed to read note {note_id} for link resolving: {e}')
                    continue
                new_html = html
                for href, _text in href_re.findall(html):
                    if href.startswith(('http:', 'https:', '#', 'api/', 'data:')):
                        continue
                    target = urllib.parse.unquote(href.split('#', 1)[0])
                    if not target.lower().endswith('.md'):
                        continue
                    resolved = os.path.normpath(os.path.join(os.path.dirname(md_rel), target))
                    target_id = note_map.get(resolved)
                    if not target_id:
                        continue
                    new_html = new_html.replace(href, f'#root/{target_id}')
                if new_html == html:
                    continue
                if not self.update_note_content(note_id, new_html):
                    logger.warning(f'Failed to rewrite note links on note {note_id}')
                    continue
                if importModified:
                    dateModified, utcDateModified = _read_front_matter_modified(src_file)
                    if dateModified or utcDateModified:
                        try:
                            restore = self.patch_note(
                                noteId=note_id,
                                dateModified=dateModified,
                                utcDateModified=utcDateModified,
                            )
                            if not isinstance(restore, dict) or restore.get('code'):
                                logger.warning(f'Failed to restore last-modified on note {note_id}: {restore}')
                        except Exception as e:
                            logger.warning(f'Failed to restore last-modified on note {note_id}: {e}')

        # count how many errors
        if error_files:
            count = len(error_files)
            logger.error(f"There are {count} errors.")
            for i, (file, e) in enumerate(error_files.items()):
                logger.error(f"{i} | {file}: {e}")
            # return False
        return True

    def backup(self, backup_name):
        url = f'{self.server_url}/etapi/backup/{backup_name}'

        res = requests.put(url, headers=self.get_header())
        if res.status_code == 204:
            logger.info('backup successfully')
            return True
        return False

    def beautify_note(self, noteId: str) -> bool:
        """
        beautify note content, add new lines and remove redundant lines, etc.

        :param noteId:
        :return:
        """
        content = self.get_note_content(noteId)
        new_content = beautify_content(content)
        res = self.update_note_content(noteId, new_content)
        return res

    def beautify_sub_notes(self, noteId: str):
        """
        beautify note and its child notes

        :param noteId:
        :return:
        """
        note = self.get_note(noteId)
        logger.info(f"{noteId} {note['type']} {note['title']}")

        if note['type'] == 'text':
            self.beautify_note(noteId)

        for x in note['childNoteIds']:
            # logger.info(x)
            self.beautify_sub_notes(x)

    def close(self):
        """
        Force sync from server

        .. Code:: python

        with closing(client.get_note(noteId)) as note:
            pass

        :return:
        """
        url = f"{self.server_url}/etapi/sync/now"
        res = requests.post(url, headers=self.get_header())
        if res.status_code == 200:
            logger.info("sync successfully")

    def get_attachments(self, noteId: str):
        """
        get attachment list of a note
        :param noteId:
        :return:
        """
        url = f'{self.server_url}/etapi/notes/{noteId}/attachments'

        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_attachment(self, attachmentId: str) -> dict:
        """
        get attachment by id

        :param attachmentId:
        :return:
        """
        url = f'{self.server_url}/etapi/attachments/{attachmentId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_attachment(
            self,
            ownerId: str,
            file_path: str,
            title: str = None,
            role: str = None,
            mime: str = None,
            position: int = 0,
    ) -> dict:
        """
        create or update a attachment

        the meta data and the content are uploaded with separate requests
        due to:
        1. tried to directly upload `content` with `/etapi/attachments` endpoint without luck.
        tried json, ordinary form, base64 encoding, string conversion, etc. But only results in broken images :(
        2. there is a size limit if the content is too large which will throw `PayloadTooLargeError`

        update_attachment_content work fine with file uploads.

        :param ownerId:
        :param file_path:
        :param title:
        :param role: should be 'image' or 'file'
        :param mime: e.g. 'image/png'
        :param position:
        :return:
        """
        url = f'{self.server_url}/etapi/attachments'

        if not title:
            title = os.path.basename(file_path)

        if not mime:
            # if mime not specified, get mime info by python-magic package
            mime, _ = mimetypes.guess_type(file_path)

        if not mime:
            # just in case python-magic not working, give a default mime
            mime = 'image/png'

        if not role:
            if 'image' in mime:
                role = 'image'
            else:
                role = 'file'

        params = {
            "ownerId": ownerId,
            "role": role,
            "mime": mime,
            "title": title,
            "position": position,
            "content": '',
        }
        res = requests.post(url, data=clean_param(params), headers=self.get_header()).json()

        self.update_attachment_content(res['attachmentId'], file_path)

        return res

    def update_attachment(
            self,
            attachmentId: str,
            title: str,
            role: str,
            mime: str,
            position: int = 0,
    ) -> dict:
        """
        update a attachment

        :param role: should be 'image' or 'file'
        :param mime: e.g. 'image/png'
        :param title:
        :param position:
        :return:
        """
        url = f'{self.server_url}/etapi/attachments/{attachmentId}'

        params = {
            "role": role,
            "mime": mime,
            "title": title,
            "position": position,
        }
        res = requests.patch(url, json=clean_param(params), headers=self.get_header())

        return res.json()

    def get_attachment_content(self, attachmentId: str) -> bytes:
        url = f'{self.server_url}/etapi/attachments/{attachmentId}/content'
        res = requests.get(url, headers=self.get_header())
        return res.content

    def update_attachment_content(
            self, attachmentId: str, data_source: str, is_file: bool = True
    ) -> bool:
        # upload file, set content
        url = f'{self.server_url}/etapi/attachments/{attachmentId}/content'
        if is_file:
            file_data = open(data_source, 'rb').read()
        else:
            file_data = data_source
        res = requests.put(
            url,
            data=file_data,
            headers={
                'content-type': 'application/octet-stream',
                'Content-Transfer-Encoding': 'binary',
                'Authorization': self.token,
            },
        )
        if res.status_code == 204:
            return True
        return False

    def delete_attachment(self, attachmentId: str) -> bool:
        url = f'{self.server_url}/etapi/attachments/{attachmentId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def optimize_image_attachments(self, noteId: str, quality: int = 90):
        """
        comporess image attachments, this keeps the original format
        :param noteId:
        :param quality:
        :return:
        """

        attachments = self.get_attachments(noteId)
        for attachment in attachments:
            try:
                logger.info(attachment)
                if not attachment['role'] == 'image' and attachment['contentLength'] > 0:
                    continue
                image_data = self.get_attachment_content(attachment['attachmentId'])
                extension = get_extension_from_image_mime(attachment['mime'])
                compressed_data = compress_image_bytes(image_data, extension, quality)
                size_before = len(image_data)
                size_after = len(compressed_data)
                logger.info(f"Size before compression: {size_before} bytes")
                logger.info(f"Size after compression: {size_after} bytes")
                if size_after < size_before:
                    logger.info('replace image')
                    self.update_attachment_content(
                        attachment['attachmentId'], compressed_data, is_file=False
                    )
                else:
                    logger.info('skip image')
            except:
                pass

    def optimize_image_attachments_to_webp(self, noteId: str, quality: int = 90, skip_webp=True):
        """
        comporess image attachments, this tries to convert the original image to webp
        :param noteId:
        :param quality:
        :return:
        """

        attachments = self.get_attachments(noteId)
        for attachment in attachments:
            try:
                logger.info(attachment)
                if not attachment['role'] == 'image' and attachment['contentLength'] > 0:
                    continue
                # skip webp conversion if it's already webp
                if skip_webp and attachment['mime'] == 'image/webp':
                    continue
                image_data = self.get_attachment_content(attachment['attachmentId'])
                # try to convert to webp
                extension = 'webp'
                compressed_data = compress_image_bytes(image_data, extension, quality)
                size_before = len(image_data)
                size_after = len(compressed_data)
                logger.info(f"Size before compression: {size_before} bytes")
                logger.info(f"Size after compression: {size_after} bytes")
                if size_after < size_before:
                    logger.info('replace image')
                    # update image content data
                    res = self.update_attachment_content(
                        attachment['attachmentId'], compressed_data, is_file=False
                    )
                    logger.info(res)
                    # update image file name and mime
                    res = self.update_attachment(
                        attachmentId=attachment['attachmentId'],
                        title=replace_extension(attachment['title'], 'webp'),
                        role='image',
                        mime='image/webp',
                    )
                    logger.info(res)
                else:
                    logger.info('skip image')
            except Exception as e:
                logger.error(e)

    def sort_note_content(self, noteId: str, locale_str: str = 'zh_CN.UTF-8'):
        """
        Sort note content by headings
        You can set locale to sort with respect to your local language.

        :param noteId:
        :param locale_str:  should be something like 'zh_CN.UTF-8'
        """
        html_content = self.get_note_content(noteId)
        sorted_html_content = sort_note_by_headings(html_content, locale_str)
        self.update_note_content(noteId, sorted_html_content)

    def delete_empty_note(self, note_title=None, verbose=False):
        """
        delete empty `new note` which are created accidentally
        :return:
        """
        if not note_title:
            note_title = 'new note'
        res = self.search_note(
            search=f'note.title = "{note_title}"',
        )
        logger.info(f'found {len(res["results"])} notes with title "{note_title}"')
        for x in res['results']:
            content = self.get_note_content(x['noteId'])
            if not content:
                logger.info(f'delete note {x["noteId"]}')
                self.delete_note(x["noteId"])
            else:
                logger.warning(f'note {x["noteId"]} is not empty')
                if verbose:
                    logger.info(content)

    def auto_create_internal_link(
            self,
            target_note_id=None,
            target_notes=None,
            process_all_notes=False,
            skip_clipped_notes=True,
            skip_day_notes=True,
            verbose=True,
    ):
        """
        Create internal link for notes
        """

        # Prepare note title and note id list
        # Get all note titles and note ids
        all_notes = self.search_note(search="note.title %= '.*' #!ignoreAutoInternalLink")
        all_note_title_list = []
        for x in all_notes['results']:
            if x['isProtected']:
                # Remove protected notes, they are not editable via ETAPI
                continue
            title = x['title']
            note_id = x['noteId']
            all_note_title_list.append([title, note_id])

        # Process the note titles, handling duplicates and sorting
        processed_note_title_list = preprocess_note_title_list(all_note_title_list)

        # prepare target note id
        if target_note_id:
            target_notes = [
                target_note_id,
            ]
        elif target_notes:
            pass
        elif process_all_notes:
            # process all notes if not provided a note id list
            target_notes = [
                x['noteId']
                for x in self.search_note(search="note.title %= '.*'")['results']
                if not x['isProtected']
            ]

        # Add internal link

        def get_child_note_title_note_id_list(note_id):
            res = self.get_note(note_id)
            result = []
            for child_note_id in res['childNoteIds']:
                x = self.get_note(child_note_id)
                result.append([x['title'], x['noteId']])
            return preprocess_note_title_list(result)

        for note_id in tqdm(target_notes):

            # only process text note here
            current_note = self.get_note(note_id)

            if verbose:
                logger.info(f'current note id: {note_id} title: {current_note["title"]}')

            if not current_note['type'] == 'text':
                if verbose:
                    logger.info('skip: not text note')
                continue

            if skip_clipped_notes and any(
                    [x['name'] == 'pageUrl' for x in current_note['attributes']]
            ):
                if verbose:
                    logger.info('skip: clipped note')
                continue

            if skip_day_notes and any(
                    [x['name'] == 'dateNote' for x in current_note['attributes']]
            ):
                if verbose:
                    logger.info('skip: day note')
                continue

            # add child note, we can handle sub notes with same name from different parent notes
            processed_child_note_title_list = get_child_note_title_note_id_list(note_id)
            tmp_list_for_current_note = processed_child_note_title_list + processed_note_title_list

            content = self.get_note_content(note_id)
            updated_content, replaced = add_internal_links(
                content, tmp_list_for_current_note, current_note_id=note_id
            )
            # If content has changed, update the note
            if replaced:
                self.update_note_content(note_id, updated_content)
                if verbose:
                    logger.info(f"Added internal link to note {note_id}.")

    def traverse_note_tree(self, noteId: str, depth: int = 3, limit: int = 100, method: Literal['dfs', 'bfs'] = 'dfs'):
        """
        Traverse the note tree using either DFS or BFS and collect information from notes and their descendants.
        Args:
            noteId: Starting note ID
            depth: Maximum traversal depth
            limit: Maximum number of notes to collect before stopping (default: 100)
            method: Traversal method, either 'dfs' (depth-first) or 'bfs' (breadth-first) (default: 'dfs')
        Returns:
            list: List containing information of all found notes in the tree, up to limit
        """
        search_result = []

        if method.lower() not in ['dfs', 'bfs']:
            raise ValueError("Method must be either 'dfs' or 'bfs'")

        # DFS Implementation
        if method.lower() == 'dfs':
            def dfs_helper(current_note_id: str, current_depth: int) -> None:
                if current_depth > depth or len(search_result) >= limit:
                    return

                try:
                    note = self.get_note(noteId=current_note_id)
                    note_content = self.get_note_content(current_note_id)

                    search_result.append({
                        "noteId": current_note_id,
                        "title": note.get("title", ""),
                        "content": note_content,
                        "depth": current_depth
                    })

                    child_note_ids = note.get('childNoteIds', [])
                    for sub_note_id in child_note_ids:
                        if len(search_result) < limit:
                            dfs_helper(sub_note_id, current_depth + 1)
                except Exception as e:
                    logger.error(f"Error processing note {current_note_id}: {str(e)}")

            dfs_helper(noteId, 1)

        # BFS Implementation
        elif method.lower() == 'bfs':
            queue = deque([(noteId, 1)])  # (note_id, depth)

            while queue and len(search_result) < limit:
                current_note_id, current_depth = queue.popleft()

                if current_depth > depth:
                    continue

                try:
                    note = self.get_note(noteId=current_note_id)
                    note_content = self.get_note_content(current_note_id)

                    search_result.append({
                        "noteId": current_note_id,
                        "title": note.get("title", ""),
                        "content": note_content,
                        "depth": current_depth
                    })

                    child_note_ids = note.get('childNoteIds', [])
                    for sub_note_id in child_note_ids:
                        if current_depth < depth:
                            queue.append((sub_note_id, current_depth + 1))
                except Exception as e:
                    logger.error(f"Error processing note {current_note_id}: {str(e)}")

        if len(search_result) >= limit:
            logger.info(f"Reached limit of {limit} notes using {method} method, stopping traversal")

        return search_result


class ListTemplate(string.Template):
    """Encapsulate To Do List HTML details

    :param caption: Text to be presented as the To Do list caption. Default: <p>TODO:</p>
    """

    def __init__(self, caption: str = '<p>TODO:</p>') -> None:
        self._defaults: dict[str, object] = {
            'caption': caption,
        }
        super().__init__('${caption}<ul class="todo-list">${items}</ul>')

    def substitute(self, mapping: Optional[Mapping[str, object]] = None, **kwds: object) -> str:
        d = self._defaults.copy()
        d.update(mapping or {})
        return super().substitute(d, **kwds)


class ItemTemplate(string.Template):
    """Encapsulate To Do Item HTML details

    :param description: Optional text to be presented as the To Do item
    :param checked: If True To Do item is presented will filled in check box. Default is False.
    """

    def __init__(self, description: Optional[str] = None, checked: bool = False) -> None:
        super().__init__(
            '<li><label class="todo-list__label">'
            '<input${checked} disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">$description</span></label></li>'
        )
        self._defaults: dict[str, object] = {
            'description': description,
            'checked': ' checked="checked"' if checked else '',
        }

    def substitute(self, mapping: Optional[Mapping[str, object]] = None, **kwds: object) -> str:
        d = self._defaults.copy()
        d.update(mapping or {})
        return super().substitute(d, **kwds)
