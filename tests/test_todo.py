import re
import unittest

import requests_mock

from trilium_py.client import ETAPI


class TestToDo(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.etapi = ETAPI('mock://bogus:8080')
        self.day_url = re.compile(
            r'mock://bogus:8080/etapi/calendar/days/[0-9]{4}-[0-9]{2}-[0-9]{2}'
        )
        self.content_url = 'mock://bogus:8080/etapi/notes/deadbeef/content'

    def test_todo_add(self):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', self.day_url, json={"noteId": "deadbeef"})
            mock.get(self.content_url, text="<p></p>")
            adapter = mock.put(self.content_url, status_code=204)

            result = self.etapi.add_todo('item_1')
            text = '<p>TODO:</p><ul class="todo-list"><li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/><span class="todo-list__label__description">item_1</span></label></li></ul><p></p>'
            self.assertEqual(adapter.last_request.text, text)
            self.assertTrue(result)

    def test_todo_add_h3(self):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', self.day_url, json={"noteId": "deadbeef"})
            mock.get(self.content_url, text="<p></p>")
            adapter = mock.put(self.content_url, status_code=204)

            result = self.etapi.add_todo('item_1', todo_caption='<h3>To Do</h3>')
            text = '<h3>To Do</h3><ul class="todo-list"><li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/><span class="todo-list__label__description">item_1</span></label></li></ul><p></p>'
            self.assertEqual(adapter.last_request.text, text)
            self.assertTrue(result)
