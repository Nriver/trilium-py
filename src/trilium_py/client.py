import requests

from .utils.url_util import format_query_string


class ETAPI:

    def __init__(self, server_url, token=None):
        self.server_url = server_url
        self.token = token

    def get_header(self):
        return {
            'Authorization': self.token,
        }

    def login(self, password):
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

    def logout(self, token_to_destroy=None):
        """
        destroy token
        """

        if not token_to_destroy:
            token_to_destroy = self.token

        if not token_to_destroy:
            return

        url = f'{self.server_url}/etapi/auth/logout'
        headers = {
            'Authorization': token_to_destroy,
        }
        res = requests.post(url, headers=headers)
        if res.status_code == 204:
            print('logout successfully')
            return True
        return False

    def search_note(self, search, **params):
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

    def get_note(self, noteId):
        """
        get note by note id
        root note's id is just "root"

        :param noteId:
        :return:
        """
        url = f'{self.server_url}/etapi/notes/{noteId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_note(self, parentNoteId, title, type, mime, content, notePosition, prefix, isExpanded, noteId,
                    branchId):
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
            # "mime": "application/json",
            "content": content,
            # "notePosition": notePosition,
            # "prefix": prefix,
            # "isExpanded": isExpanded,
            "noteId": noteId,
            "branchId": branchId
        }
        res = requests.post(url, data=format_query_string(params), headers=self.get_header())
        return res.json()

    def patch_note(self, noteId: str, title: str, type: str, mime: str):
        url = f'{self.server_url}/etapi/notes/{noteId}'
        params = {
            "title": title,
            "type": type,
            "mime": mime,
        }
        res = requests.patch(url, data=format_query_string(params), headers=self.get_header())
        return res.json()

    def delete_note(self, noteId: str):
        url = f'{self.server_url}/etapi/notes/{noteId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def get_branch(self, branchId):
        url = f'{self.server_url}/etapi/branches/{branchId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_branch(self, branchId, noteId, parentNoteId, prefix, notePosition, isExpanded, utcDateModified):
        # url = f'{self.server_url}/etapi/branches/{branchId}'
        url = f'{self.server_url}/etapi/branches/'
        params = {
            "branchId": branchId,
            "noteId": noteId,
            "parentNoteId": parentNoteId,
            "prefix": prefix,
            # "notePosition": notePosition,
            # "isExpanded": isExpanded,
            "utcDateModified": utcDateModified
        }
        res = requests.post(url, data=format_query_string(params), headers=self.get_header())
        print(res.status_code)
        return res.json()

    def patch_branch(self, branchId, notePosition, prefix, isExpanded):
        url = f'{self.server_url}/etapi/branches/{branchId}'
        params = {
            # "notePosition": notePosition,
            "prefix": prefix,
            # "isExpanded": isExpanded,
        }
        res = requests.patch(url, data=format_query_string(params), headers=self.get_header())
        return res.json()

    def delete_branch(self, branchId: str):
        url = f'{self.server_url}/etapi/branches/{branchId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def get_attribute(self, attributeId):
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_attribute(self, attributeId, noteId, type, name, value, isInheritable):
        # url = f'{self.server_url}/etapi/attributes/{attributeId}'
        url = f'{self.server_url}/etapi/attributes/'
        params = {
            "attributeId": attributeId,
            "noteId": noteId,
            "type": type,
            "name": name,
            "value": value,
            # "isInheritable": isInheritable,
        }
        res = requests.post(url, data=format_query_string(params), headers=self.get_header())
        print(res.status_code)
        return res.json()

    def patch_attribute(self, attributeId, value):
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        params = {
            "value": value,
        }
        res = requests.patch(url, data=format_query_string(params), headers=self.get_header())
        return res.json()

    def delete_attribute(self, attributeId: str):
        url = f'{self.server_url}/etapi/attributes/{attributeId}'
        res = requests.delete(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def refresh_note_ordering(self, parentNoteId):
        url = f'{self.server_url}/etapi/refresh-note-ordering/{parentNoteId}'
        res = requests.post(url, headers=self.get_header())
        if res.status_code == 204:
            return True
        return False

    def inbox(self, date):
        url = f'{self.server_url}/etapi/inbox/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_days(self, date):
        url = f'{self.server_url}/etapi/calendar/days/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_weeks(self, date):
        url = f'{self.server_url}/etapi/calendar/weeks/{date}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_months(self, month):
        url = f'{self.server_url}/etapi/calendar/months/{month}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def get_calendar_years(self, year):
        url = f'{self.server_url}/etapi/calendar/years/{year}'
        res = requests.get(url, headers=self.get_header())
        return res.json()
