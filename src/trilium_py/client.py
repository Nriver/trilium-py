from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .utils.param_util import format_query_string, clean_param


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

    # def create_image_note(self, parentNoteId: str, title: str, type: str, image_file: str, mime: str = None,
    #                       content=None,
    #                       notePosition: int = None, prefix: str = None,
    #                       isExpanded: str = None, noteId: str = None,
    #                       branchId: str = None):
    #     # Not working
    #
    #     # Create a note
    #     # set file name attribute
    #     # Update its content
    #
    #     url = f'{self.server_url}/etapi/create-note'
    #     print(image_file)
    #     params = {
    #         "parentNoteId": parentNoteId,
    #         "title": title,
    #         "type": type,
    #         "mime": mime,
    #         "content": "image",
    #         "notePosition": notePosition,
    #         "prefix": prefix,
    #         "isExpanded": isExpanded,
    #         "noteId": noteId,
    #         "branchId": branchId
    #     }
    #     res = requests.post(url, json=clean_param(params), headers=self.get_header())
    #     print(res)
    #     new_noteId = res.json()['note']['noteId']
    #
    #     # set file name
    #     image_file_name = os.path.basename(image_file)
    #     self.create_attribute(attributeId=None, noteId=new_noteId, type='label', name='originalFileName',
    #                           value=image_file_name, isInheritable=False)
    #
    #     # upload image, set note content
    #     url = f'{self.server_url}/etapi/notes/{new_noteId}/content'
    #     image_data = open(image_file, 'rb').read()
    #     # content-type here will effect the result
    #     # not working, encoding issue? automated force encoding to utf-8 and lost data
    #     res = requests.put(url, data=image_data,
    #                        headers={'content-type': 'text/plain', 'Authorization': self.token, })
    #     if res.status_code == 204:
    #         return True
    #     return False

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

    def get_today_note_content(self):
        date = datetime.now().strftime("%Y-%m-%d")
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        noteId = res.json()['noteId']
        content = self.get_note_content(noteId)
        return content

    def set_today_note_content(self, content):
        date = datetime.now().strftime("%Y-%m-%d")
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
        try:
            content = self.get_today_note_content()
            print(content)
            soup = BeautifulSoup(content, 'html.parser')
            todo_labels = soup.find_all("label", {"class": "todo-list__label"})
            # append todo item after last todo item
            # special case 1: no todo available, add it to the beginning of document
            # special case 2: if last todo item is empty, update it

            todo_item_html = f'''<li><label class="todo-list__label"><input type="checkbox"/><span class="todo-list__label__description">{todo_description}</span></label></li>'''

            if not todo_labels:
                todo_item_html = f'''<p>TODO:</p><ul class="todo-list">{todo_item_html}</ul>'''
                todo_item = BeautifulSoup(todo_item_html, 'html.parser')
                soup.insert(0, todo_item)
            else:
                last_todo = todo_labels[-1]
                if not last_todo.text.strip():
                    target_span = last_todo.find_next("span", {"class": "todo-list__label__description"})
                    target_span.string = todo_description
                else:
                    todo_item = BeautifulSoup(todo_item_html, 'html.parser')
                    last_todo.append(todo_item)

            new_content = str(soup)
            # free mem
            soup.decompose()
            del soup

            return self.set_today_note_content(new_content)

        except Exception as e:
            print(e)
            return False
