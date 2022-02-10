import requests


class ETAPI:

    def __init__(self, server_url, token=None):
        self.server_url = server_url
        self.token = token

    def login(self, password):
        """
        generate token with password
        """
        url = f'{self.server_url}/etapi/auth/login'

        data = {'password': password}

        res = requests.post(url, data=data)
        if res.status_code == 201:
            return res.json()['authToken']
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
            print('logout successfull')
            return True
        return False
