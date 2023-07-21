"""Verify trilium-py ETAPI methods.

These tests are an example of how to use standard library unittest to test the trilium-py
"""
import unittest

import requests_mock

from trilium_py.client import ETAPI


class TestETAPI(unittest.TestCase):
    def test_etapi(self):
        ETAPI('http://bogus:8080')

    def test_etapi_login(self):
        etapi = ETAPI('http://bogus:8080')

        with requests_mock.Mocker() as mock:
            adapter = mock.post(
                'http://bogus:8080/etapi/auth/login',
                json={"authToken": "Token bogus"},
                status_code=201,
            )
            self.assertEqual(etapi.login('123'), 'Token bogus')
            self.assertEqual(adapter.last_request.text, 'password=123')

            # Test that the token is cached
            mock.post(
                'http://bogus:8080/etapi/auth/logout',
                status_code=204,
                request_headers={
                    'Authorization': 'Token bogus',
                },
            )
            self.assertTrue(etapi.logout())

    def test_etapi_logout(self):
        etapi = ETAPI('http://bogus:8080')

        with requests_mock.Mocker() as mock:
            mock.post(
                'http://bogus:8080/etapi/auth/logout',
                status_code=204,
                request_headers={
                    'Authorization': 'Token bogus',
                },
            )
            self.assertTrue(etapi.logout('Token bogus'))

            # Test that the token is not cached
            self.assertFalse(etapi.logout())

    def test_etapi_close(self):
        etapi = ETAPI('http://bogus:8080')

        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/sync/now')
            self.assertIsNone(etapi.close())

    def test_etapi_login_fail(self):
        etapi = ETAPI('http://bogus:8080')

        with requests_mock.Mocker() as mock:
            adapter = mock.post(
                'http://bogus:8080/etapi/auth/login',
                json={"message": "failed test_etapi_login_fail"},
                status_code=500,
            )
            self.assertIsNone(etapi.login('123'))
            self.assertEqual(adapter.last_request.text, 'password=123')


if __name__ == '__main__':
    unittest.main()
