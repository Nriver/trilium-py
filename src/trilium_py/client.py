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

    def search_notes(self, search, **params):
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

    def get_note(self, note_id):
        """
        get note by note id
        root note's id is just "root"

        :param note_id:
        :return:
        """
        url = f'{self.server_url}/etapi/notes/{note_id}'
        res = requests.get(url, headers=self.get_header())
        return res.json()

    def create_note(self, parent_note_id, title, type, mime, content, note_position, prefix, is_expanded, note_id,
                    branch_id):
        """
        If note_id already exists, the corresponding note will be updated
        :param parent_note_id:
        :param title:
        :param type:
        :param mime:
        :param content:
        :param note_position:
        :param prefix:
        :param is_expanded:
        :param note_id:
        :param branch_id:
        :return:
        """
        url = f'{self.server_url}/etapi/create-note'
        params = {
            "parentNoteId": parent_note_id,
            "title": title,
            "type": type,
            # "mime": "application/json",
            "content": content,
            # "notePosition": note_position,
            # "prefix": prefix,
            # "isExpanded": is_expanded,
            "noteId": note_id,
            "branchId": branch_id
        }
        res = requests.post(url, data=format_query_string(params), headers=self.get_header())
        print(res.json())
