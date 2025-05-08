import re
import sys
from typing import Optional

import requests
from loguru import logger

from .version import __version__


class WEBAPI:
    __version__ = __version__

    def __init__(self, server_url: str, sid: Optional[str] = None, _csrf: Optional[str] = None,
                 csrf_token: Optional[str] = None):
        if sys.version_info < (3, 9):
            print(
                (
                    f'You are using Python {sys.version_info.major}.{sys.version_info.minor}'
                    ', 3.9+ is required.'
                ),
                file=sys.stderr,
            )

        self.server_url = server_url
        self.sid: str = sid
        self._csrf = _csrf
        self.csrf_token = csrf_token

    def get_cookie(self) -> dict:
        return {
            '_csrf': self._csrf,
            'trilium.sid': self.sid,
            'trilium-device': 'desktop'
        }

    def get_headers(self) -> dict:
        return {
            'x-csrf-token': self.csrf_token,
        }

    def refresh_csrf_token(self) -> str:
        url = f'{self.server_url}/'
        res = requests.get(url, cookies=self.get_cookie())
        csrf_token_match = re.search(r"csrfToken:\s*'([^']+)'", res.text)

        if csrf_token_match:
            csrf_token = csrf_token_match.group(1)
            logger.info(f"Extracted csrfToken: {csrf_token}")
            self.csrf_token = csrf_token
            return csrf_token
        else:
            logger.info("csrfToken not found.")
            return ''

    def login(self, password: str) -> Optional[str]:
        """
        mimic web login
        """
        url = f'{self.server_url}/login'

        data = {'password': password}

        # login process is in 2-step
        # 1. 302 set-cookie trilium.sid
        # 2. 200 set-cookie _csrf
        # single requests will not work, need to use session
        session = requests.Session()
        res = session.post(url, data=data, allow_redirects=True)
        for cookie in session.cookies:
            logger.info(f"{cookie.name}: {cookie.value}")

        if res.status_code == 200:
            self.sid = session.cookies.get('trilium.sid')
            self._csrf = session.cookies.get('_csrf')
            self.refresh_csrf_token()
            return self.sid
        else:
            logger.info(res.text)
            return ''

    def logout(self, sid: Optional[str] = None) -> bool:
        """
        mimic web logout
        """

        if not sid:
            sid = self.sid

        if not sid:
            return False

        url = f'{self.server_url}/logout'
        res = requests.post(url, headers=self.get_headers(), cookies=self.get_cookie())

        if res.status_code == 200:
            logger.info('logout successfully')
            return True
        return False

    def get_note_content(self, note_id):
        url = f'{self.server_url}/api/notes/{note_id}/blob'
        res = requests.get(url, cookies=self.get_cookie())
        return res.json()['content']

    def share_note(self, note_id: str):
        url = f'{self.server_url}/api/notes/{note_id}/clone-to-note/_share'

        res = requests.put(url, headers=self.get_headers(), cookies=self.get_cookie())
        logger.info(res.json())
        if res.json():
            return True
        return False

    def cancel_share_note(self, note_id: str):
        url = f'{self.server_url}/api/branches/_share_{note_id}?taskId=no-progress-reporting'

        res = requests.delete(url, headers=self.get_headers(), cookies=self.get_cookie())
        logger.info(res.json())

        if res.status_code == 200:  # DELETE 请求通常返回 200 表示成功
            return True
        return False