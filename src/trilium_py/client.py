import os
import re
import urllib.parse

import magic
import markdown2
import requests
from bs4 import BeautifulSoup
from natsort import natsort

from .utils.param_util import format_query_string, clean_param
from .utils.time_util import get_yesterday, get_today
from .utils.markdown_math import sanitizeInput, reconstructMath

class ETAPI:

    def __init__(self, server_url: str, token: str = None):
        self.server_url = server_url
        self.token = token

    def get_header(self) -> dict:
        return {
            'Authorization': self.token,
        }

    def login(self, password: str) -> str:
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
            print(res.json()['message'])
            return None

    def logout(self, token_to_destroy: str = None) -> bool:
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
            print('logout successfully')
            return True
        return False

    def app_info(self) -> dict:
        """

        :return:
        """
        result = []

        url = f'{self.server_url}/etapi/app-info'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def search_note(self, search: str, **params) -> dict:
        """

        :param search:
        :param params:
        :return:
        """
        result = []

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

    def create_note(self, parentNoteId: str, title: str, type: str, mime: str = None, content=None,
                    notePosition: int = None, prefix: str = None,
                    isExpanded: str = None, noteId: str = None,
                    branchId: str = None) -> dict:
        """
        Actually it's create or update, if noteId already exists, the corresponding note will be updated
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
            "branchId": branchId
        }
        res = requests.post(url, json=clean_param(params), headers=self.get_header())

        return res.json()
    
    def create_file_note(self, parentNoteId: str, title: str, file_data: str, content_file: str,
                         type: str = 'file', mime: str = None,
                         content=None, notePosition: int = None, prefix: str = None,
                         isExpanded: str = None, noteId: str = None,
                         branchId: str = None):
        '''
        Create a note
        set file name attribute
        Update its content with image binary content
        :param parentNoteId:
        :param title:
        :param file_data: file object from buffer.
        :param content_file: file path in file system.
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

        url = f'{self.server_url}/etapi/create-note'

        if not mime:
            # if mime not specified, get mime info by python-magic package
            if file_data:
                mime = magic.from_buffer(file_data, mime=True)
            elif content_file:
                mime = magic.from_file(file_data, mime=True)

        if not mime:
            # just in case python-magic not working, give a default mime
            mime = "image/png"

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
            "branchId": branchId
        }

        res_file = requests.post(url, json=clean_param(params),
                                 headers={'content-type': 'application/json', 'Authorization': self.token, })
        res_file_json = res_file.json()
        new_noteId = res_file_json['note']['noteId']

        # set file name
        content_file_name = os.path.basename(content_file)
        self.create_attribute(attributeId=None, noteId=new_noteId, type='label', name='originalFileName',
                              value=content_file_name, isInheritable=False)

        # upload file, set note content
        url = f'{self.server_url}/etapi/notes/{new_noteId}/content'
        # content-type here will affect the result
        # not working, encoding issue? automated force encoding to utf-8 and lost data
        if not file_data:
            file_data = open(content_file, 'rb').read()
        res = requests.put(url, data=file_data,
                           # headers={'content-type': 'text/plain', 'Authorization': self.token, })
                           headers={
                               'content-type': 'application/octet-stream',
                               'Content-Transfer-Encoding': 'binary',
                               'Authorization': self.token,
                           })
        if res.status_code == 204:
            return res_file_json
        return

    def create_image_note(self, parentNoteId: str, title: str, image_file: str, type: str = 'image', mime: str = None,
                          content=None,
                          notePosition: int = None, prefix: str = None,
                          isExpanded: str = None, noteId: str = None,
                          branchId: str = None):

        '''
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

        url = f'{self.server_url}/etapi/create-note'

        if not mime:
            # if mime not specified, get mime info by python-magic package
            mime = magic.from_file(image_file, mime=True)

        if not mime:
            # just in case python-magic not working, give a default mime
            mime = "image/png"

        params = {
            "parentNoteId": parentNoteId,
            "title": title,
            "type": type,
            "mime": mime,
            "content": "image",
            "notePosition": notePosition,
            "prefix": prefix,
            "isExpanded": isExpanded,
            "noteId": noteId,
            "branchId": branchId
        }
        res_image = requests.post(url, json=clean_param(params),
                                  headers={'content-type': 'application/json', 'Authorization': self.token, })
        res_image_json = res_image.json()
        new_noteId = res_image_json['note']['noteId']

        # set file name
        image_file_name = os.path.basename(image_file)
        self.create_attribute(attributeId=None, noteId=new_noteId, type='label', name='originalFileName',
                              value=image_file_name, isInheritable=False)

        # upload image, set note content
        url = f'{self.server_url}/etapi/notes/{new_noteId}/content'
        image_data = open(image_file, 'rb').read()
        # content-type here will affect the result
        # not working, encoding issue? automated force encoding to utf-8 and lost data
        res = requests.put(url, data=image_data,
                           # headers={'content-type': 'text/plain', 'Authorization': self.token, })
                           headers={
                               'content-type': 'application/octet-stream',
                               'Content-Transfer-Encoding': 'binary',
                               'Authorization': self.token,
                           })
        if res.status_code == 204:
            return res_image_json
        return

    def patch_note(self, noteId: str, title: str = None, type: str = None, mime: str = None) -> dict:
        url = f'{self.server_url}/etapi/notes/{noteId}'
        params = {
            "title": title,
            "type": type,
            "mime": mime,
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
        res = requests.put(url, data=content.encode('utf-8'),
                           headers={'content-type': 'text/plain', 'Authorization': self.token})
        if res.status_code == 204:
            return True
        return False

    def get_branch(self, branchId: str) -> dict:
        url = f'{self.server_url}/etapi/branches/{branchId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_branch(self, branchId: str, noteId: str, parentNoteId: str, prefix: str, notePosition: int,
                      isExpanded: bool, utcDateModified) -> dict:
        # url = f'{self.server_url}/etapi/branches/{branchId}'
        url = f'{self.server_url}/etapi/branches/'
        params = {
            "branchId": branchId,
            "noteId": noteId,
            "parentNoteId": parentNoteId,
            "prefix": prefix,
            "notePosition": notePosition,
            "isExpanded": isExpanded,
            "utcDateModified": utcDateModified
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

    def create_attribute(self, attributeId: str, noteId: str, type: str, name: str, value: str,
                         isInheritable: bool) -> dict:
        url = f'{self.server_url}/etapi/attributes/'
        params = {
            "attributeId": attributeId,
            "noteId": noteId,
            "type": type,
            "name": name,
            "value": value,
            "isInheritable": isInheritable,
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

    def export_note(self, noteId: str, format: str, savePath: str, chunk_size=128):
        """
        Export note by id. Please note that protected notes are not allowed to be exported by ETAPI.

        :param noteId: note id
        :param format: format should be "html" or "markdown" or "md" for short
        :savePath: path for exported file
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
        print(r.status_code)
        with open(savePath, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)
        return True

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
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        noteId = res.json()['noteId']
        return self.update_note_content(noteId, content)

    def get_todo(self):
        """get today's todo list"""

        content = self.get_today_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        todo_list = []
        for x in todo_labels:
            description = x.text.strip()
            checked = x.find("input").get("checked")
            if checked:
                status = True
            else:
                status = False
            todo_list.append([status, description])
        # free mem
        soup.decompose()
        del soup
        return todo_list

    def todo_check(self, todo_index, check=True):
        """check/uncheck a todo"""
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
            # free mem
            soup.decompose()
            del soup

            return self.set_today_note_content(new_content)
        except IndexError:
            # free mem
            soup.decompose()
            del soup
            return False

    def todo_uncheck(self, todo_index):
        """uncheck a todo"""
        return self.todo_check(todo_index, check=False)

    def add_todo(self, todo_description):
        """append item to todo list"""
        todo_description = todo_description.strip()
        try:
            content = self.get_today_note_content()
            soup = BeautifulSoup(content, 'html.parser')
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            # append todo item after last todo item
            # special case 1: no todo available, add it to the beginning of document
            # special case 2: if last todo item is empty, update it

            if "todo-list__label" in todo_description:
                todo_item_html = f'''<li>{todo_description}</li>'''
            else:
                todo_item_html = f'''<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/ > <span class = "todo-list__label__description">{todo_description}</span></label></li>'''

            if not todo_labels:
                print('new empty page')
                todo_item_html = f'''<p>TODO:</p><ul class="todo-list">{todo_item_html}</ul>'''
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
            # free mem
            soup.decompose()
            del soup

            return self.set_today_note_content(new_content)

        except Exception as e:
            print(e)
            return False

    def update_todo(self, todo_index, todo_description):
        """update a todo item description"""
        todo_description = todo_description.strip()
        content = self.get_today_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        try:
            todo_label = todo_labels[todo_index]
            target_span = todo_label.find_next("span", {"class": "todo-list__label__description"})
            target_span.string = todo_description
            new_content = str(soup)
            # free mem
            soup.decompose()
            del soup
            return self.set_today_note_content(new_content)

        except IndexError:
            # free mem
            soup.decompose()
            del soup
            return False

    def delete_todo(self, todo_index):
        """delete a todo item"""
        date = get_today()
        self.delete_date_todo(date, todo_index)

    def delete_yesterday_todo(self, todo_index):
        date = get_yesterday()
        self.delete_date_todo(date, todo_index)

    def delete_date_todo(self, date, todo_index):
        content = self.get_day_note(date)
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})

        try:
            todo_label = todo_labels[todo_index]
            # decompose parent <li> tag
            todo_label.parent.decompose()
            new_content = str(soup)

            # free mem
            soup.decompose()
            del soup
            return self.set_day_note(date, new_content)

        except IndexError:
            # free mem
            soup.decompose()
            del soup
            return False

    def get_yesterday_unfinished_todo(self):
        content = self.get_yesterday_note_content()
        soup = BeautifulSoup(content, 'html.parser')
        todo_labels = soup.find_all("label", {"class": "todo-list__label"})
        unfinished_todo_list = []
        for x in todo_labels:
            checked = x.find("input").get("checked")
            if not checked:
                description = x.text.strip()
                unfinished_todo_list.append([False, description])
        # free mem
        soup.decompose()
        del soup
        return unfinished_todo_list

    def move_yesterday_unfinished_todo_to_today(self):
        content = self.get_yesterday_note_content()
        soup = BeautifulSoup(content, 'html.parser')
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

    def upload_md_file(self, file: str, parentNoteId: str):
        md_file = os.path.abspath(file).replace('\\', '/').replace('//', '/')
        md_full_name = os.path.basename(md_file)
        md_name = md_full_name[:-3]
        md_folder = os.path.dirname(md_file)
        print(md_file)
        # print(md_name)
        # print(md_folder)

        # convert md to html
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # fix logseq image size format
            logseq_image_pat = r'(\!\[.*\]\(.*\))\{.*?:height.*width.*}'
            content = re.sub(logseq_image_pat, r'\1', content)
            
            if not re.search(re.escape("$"),content):
                # extra format support
                # https://github.com/trentm/python-markdown2/wiki/Extras
                html = markdown2.markdown(content, extras=['fenced-code-blocks', 'strike', 'tables', 'task_list'])
                # print(html)
            else:
                no_latex_part, latex_code_part = sanitizeInput(content)
                html = reconstructMath(markdown2.markdown(no_latex_part, 
                                                          extras=['fenced-code-blocks', 'strike', 'tables', 'task_list']),
                                      latex_code_part)

        # detect images
        pat = '<img (.*?) />'
        images = re.findall(pat, html)

        if not images:
            res = self.create_note(
                parentNoteId=parentNoteId,
                title=md_name,
                type="text",
                content=html,
            )

        else:
            # images require manually upload and url need to be replaced
            print('found images:')
            print(images)

            # create empty note, replace it later
            res = self.create_note(
                parentNoteId=parentNoteId,
                title=md_name,
                type="text",
                content='importing...',
            )
            # print(res)

            note_id = res['note']['noteId']
            # print(note_id)

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
                # unquote path, incase the url is quoted
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

                res = self.create_image_note(
                    parentNoteId=note_id,
                    title=image_name,
                    image_file=image_file_path,
                )
                # print(res)
                image_note_id = res['note']['noteId']
                # fix path with `/` in it, the param should be quoted. e.g. relative url from obsidian
                image_url = f"api/images/{image_note_id}/{urllib.parse.quote(res['note']['title'], safe='')}"
                print(image_url)

                html = html.replace(image_path, image_url)

                # add relation for image
                self.create_attribute(attributeId=None, noteId=note_id, type='relation', name='imageLink',
                                      value=image_note_id, isInheritable=False)

            # replace note content
            res = self.update_note_content(note_id, html)
            # print(res)

            return res

    def upload_md_folder(self, parentNoteId: str, mdFolder: str, includePattern=[],
                         ignoreFolder=[], ignoreFile=[]):
        if not includePattern:
            includePattern = ['.md', ]

        # note tree
        # record for noteId
        note_tree = {'.': parentNoteId}
        print(mdFolder)

        mdFolder = os.path.expandvars(os.path.expanduser(mdFolder))

        for root, dirs, files in os.walk(mdFolder, topdown=True):
            root_folder_name = os.path.basename(root)

            rel_path = os.path.relpath(root, start=mdFolder)
            if any(x in rel_path for x in ignoreFolder):
                continue

            print('==============')
            print(f'root {root}')
            print(f'root_folder_name {root_folder_name}')
            print(f'rel_path {rel_path}')

            current_parent_note_id = note_tree[rel_path]

            print(f'files')
            for name in natsort.natsorted(files):
                # only include markdown files
                if any(x == name for x in ignoreFile):
                    continue

                if any(x in name for x in includePattern):
                    file_path = os.path.join(root, name)
                    print(file_path)
                    self.upload_md_file(file=file_path, parentNoteId=current_parent_note_id)

            print(f'dirs')
            for name in natsort.natsorted(dirs):
                if all(x not in name for x in ignoreFolder):
                    dir_path = os.path.join(root, name)
                    print(dir_path)
                    rel_path = os.path.relpath(dir_path, start=mdFolder)
                    print(rel_path)
                    res = self.create_note(
                        parentNoteId=current_parent_note_id,
                        title=name,
                        type="text",
                        content=name,
                    )
                    res['note']['noteId']
                    note_tree[rel_path] = res['note']['noteId']

        return True
