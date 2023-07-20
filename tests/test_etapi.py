import unittest
import requests_mock

from trilium_py.client import ETAPI


class TestETAPI(unittest.TestCase):
    def test_etapi(self):
        ETAPI('http://bogus:8080')

    def test_etapi_login(self):
        etapi = ETAPI('http://bogus:8080')

        with requests_mock.Mocker() as mock:
            mock.post(
                'http://bogus:8080/etapi/auth/login', json={"authToken": "bogus"}, status_code=201
            )
            self.assertEqual(etapi.login('admin'), 'bogus')

        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/sync/now')
            self.assertIsNone(etapi.close())


if __name__ == '__main__':
    unittest.main()
