"""Verify trilium-py ToDo processing.

"""
import re
import unittest

import requests_mock

from trilium_py.client import ETAPI, ItemTemplate, ListTemplate


class TestToDo(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.maxDiff = None

    def setUp(self):
        self.etapi = ETAPI('mock://bogus:8080')
        self.day_url = re.compile(
            r'mock://bogus:8080/etapi/calendar/days/[0-9]{4}-[0-9]{2}-[0-9]{2}'
        )
        self.content_url = re.compile(r'mock://bogus:8080/etapi/notes/[0-9a-f]{8}/content')
        self.body = '<p></p>'

        todo_item = ItemTemplate()
        todo_item_checked = ItemTemplate(checked=True)

        self.task_list = {
            'checked': ListTemplate().substitute(
                items=todo_item.substitute(description='item_1')
                + todo_item_checked.substitute(description='item_2')
            )
            + self.body,
            'unchecked': ListTemplate().substitute(
                items=todo_item.substitute(description='item_1')
                + todo_item.substitute(description='item_2')
            )
            + self.body,
            'updated': ListTemplate().substitute(
                items=todo_item.substitute(description='item_3')
                + todo_item_checked.substitute(description='item_2')
            )
            + self.body,
            'deleted': ListTemplate().substitute(items=todo_item.substitute(description='item_1'))
            + self.body,
        }

    @requests_mock.Mocker()
    def test_todo_add(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.body)
        put = mock.put(self.content_url, status_code=204)

        self.assertTrue(self.etapi.add_todo('item_1'))
        self.assertEqual(
            put.last_request.text,
            ListTemplate().substitute(items=ItemTemplate('item_1').substitute()) + self.body,
        )

    @requests_mock.Mocker()
    def test_todo_add_h3(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.body)
        put = mock.put(self.content_url, status_code=204)

        self.assertTrue(self.etapi.add_todo('item_1', todo_caption='<h3>Tasks</h3>'), True)
        self.assertEqual(
            put.last_request.text,
            ListTemplate('<h3>Tasks</h3>').substitute(items=ItemTemplate('item_1').substitute())
            + self.body,
        )

    def test_get_todo_checker(self):
        with requests_mock.Mocker() as mock:
            mock.get(self.day_url, json={"noteId": "deadbeef"})
            mock.get(self.content_url, text=self.task_list['checked'])

            result = self.etapi.get_todo()
            self.assertListEqual(result[0], [False, 'item_1'])
            self.assertListEqual(result[1], [True, 'item_2'])

            put = mock.put(self.content_url, status_code=204)
            self.assertTrue(self.etapi.todo_uncheck(1), True)
            self.assertEqual(put.last_request.text, self.task_list['unchecked'])

        with requests_mock.Mocker() as mock:
            mock.get(self.day_url, json={"noteId": "deadbeef"})
            mock.get(self.content_url, text=self.task_list['unchecked'])

            result = self.etapi.get_todo()
            self.assertListEqual(result[0], [False, 'item_1'])
            self.assertListEqual(result[1], [False, 'item_2'])

            put = mock.put(self.content_url, status_code=204)
            self.assertTrue(self.etapi.todo_check(1))
            self.assertEqual(put.last_request.text, self.task_list['checked'])

    @requests_mock.Mocker()
    def test_update_todo(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.task_list['checked'])

        put = mock.put(self.content_url, status_code=204)
        self.assertTrue(self.etapi.update_todo(0, 'item_3'))
        self.assertEqual(put.last_request.text, self.task_list['updated'])

    @requests_mock.Mocker()
    def test_delete_todo(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.task_list['checked'])

        put = mock.put(self.content_url, status_code=204)
        self.assertTrue(self.etapi.delete_todo(1))
        self.assertEqual(put.last_request.text, self.task_list['deleted'])

        self.assertFalse(self.etapi.delete_todo(99))

    @requests_mock.Mocker()
    def test_delete_yesterday_todo(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.task_list['checked'])

        put = mock.put(self.content_url, status_code=204)
        self.assertTrue(self.etapi.delete_yesterday_todo(1))
        self.assertEqual(put.last_request.text, self.task_list['deleted'])

    @requests_mock.Mocker()
    def test_get_yesterday_unfinished_todo(self, mock):
        mock.get(self.day_url, json={"noteId": "deadbeef"})
        mock.get(self.content_url, text=self.task_list['checked'])

        results = self.etapi.get_yesterday_unfinished_todo()
        self.assertEqual(len(results), 1)
        self.assertListEqual(results[0], [False, 'item_1'])

    @requests_mock.Mocker()
    def test_move_yesterday_unfinished_todo(self, mock):
        """A little more complicated than the others.

        deadbeef is the noteId of the day note containing the todo list. (yesterday's note)
        c0ffee is the noteId of the current day note. (today's note)
        """
        mock.register_uri(
            'GET',
            self.day_url,
            [{'json': {"noteId": "deadbeef"}}, {'json': {"noteId": "c0ffee"}}],
        )
        mock.get('mock://bogus:8080/etapi/notes/deadbeef/content', text=self.task_list['checked'])
        mock.get('mock://bogus:8080/etapi/notes/c0ffee/content', text=self.body)

        put_c0ffee = mock.put('mock://bogus:8080/etapi/notes/c0ffee/content', status_code=204)

        self.assertIsNone(self.etapi.move_yesterday_unfinished_todo_to_today())
        self.assertEqual(put_c0ffee.call_count, 1)
        self.assertEqual(put_c0ffee.last_request.text, self.task_list['deleted'])
