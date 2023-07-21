"""Verify trilium-py ToDo processing.

These tests are an example of how to use pytest to test the trilium-py
"""
import re

import pytest
import requests_mock

from trilium_py.client import ETAPI


@pytest.fixture()
def etapi():
    return ETAPI('mock://bogus:8080')


@pytest.fixture()
def day_url():
    return re.compile(r'mock://bogus:8080/etapi/calendar/days/[0-9]{4}-[0-9]{2}-[0-9]{2}')


@pytest.fixture()
def content_url():
    return 'mock://bogus:8080/etapi/notes/deadbeef/content'


@pytest.fixture()
def task_list():
    return {
        'checked': (
            '<p>TODO:</p>'
            '<ul class="todo-list">'
            '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_1</span></label></li>'
            '<li><label class="todo-list__label">'
            '<input checked="checked" disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_2</span></label></li>'
            '</ul><p></p>'
        ),
        'unchecked': (
            '<p>TODO:</p>'
            '<ul class="todo-list">'
            '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_1</span></label></li>'
            '<li><label class="todo-list__label">'
            '<input disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_2</span></label></li>'
            '</ul><p></p>'
        ),
        'updated': (
            '<p>TODO:</p>'
            '<ul class="todo-list">'
            '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_3</span></label></li>'
            '<li><label class="todo-list__label">'
            '<input checked="checked" disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_2</span></label></li>'
            '</ul><p></p>'
        ),
        'deleted': (
            '<p>TODO:</p>'
            '<ul class="todo-list">'
            '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
            '<span class="todo-list__label__description">item_1</span></label></li>'
            '</ul><p></p>'
        ),
    }


class TestToDoPytest:
    def test_todo_add(self, etapi, day_url, content_url):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text="<p></p>")
            adapter = mock.put(content_url, status_code=204)

            result = etapi.add_todo('item_1')
            text = (
                '<p>TODO:</p><ul class="todo-list">'
                '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
                '<span class="todo-list__label__description">item_1</span>'
                '</label></li></ul><p></p>'
            )
            assert adapter.last_request.text == text
            assert result == True

    def test_todo_add_h3(self, etapi, day_url, content_url):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text="<p></p>")
            adapter = mock.put(content_url, status_code=204)

            result = etapi.add_todo('item_1', todo_caption='<h3>To Do</h3>')
            text = (
                '<h3>To Do</h3><ul class="todo-list">'
                '<li><label class="todo-list__label"><input disabled="disabled" type="checkbox"/>'
                '<span class="todo-list__label__description">item_1</span>'
                '</label></li></ul><p></p>'
            )
            assert adapter.last_request.text == text
            assert result == True

    def test_get_todo_checker(self, etapi, day_url, content_url, task_list):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['checked'])

            result = etapi.get_todo()
            assert result[0] == [False, 'item_1']
            assert result[1] == [True, 'item_2']

            adapter = mock.put(content_url, status_code=204)
            result = etapi.todo_uncheck(1)
            assert adapter.last_request.text == task_list['unchecked']
            assert result == True

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['unchecked'])

            result = etapi.get_todo()
            assert result[0] == [False, 'item_1']
            assert result[1] == [False, 'item_2']

            adapter = mock.put(content_url, status_code=204)
            result = etapi.todo_check(1)
            assert adapter.last_request.text == task_list['checked']
            assert result == True

    def test_update_todo(self, etapi, day_url, content_url, task_list):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['checked'])

            adapter = mock.put(content_url, status_code=204)
            result = etapi.update_todo(0, 'item_3')
            assert adapter.last_request.text == task_list['updated']
            assert result == True

    def test_delete_todo(self, etapi, day_url, content_url, task_list):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['checked'])

            adapter = mock.put(content_url, status_code=204)
            result = etapi.delete_todo(1)
            assert adapter.last_request.text == task_list['deleted']
            assert result == True

            assert etapi.delete_todo(99) == False

    def test_delete_yesterday_todo(self, etapi, day_url, content_url, task_list):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['checked'])

            adapter = mock.put(content_url, status_code=204)
            result = etapi.delete_yesterday_todo(1)
            assert adapter.last_request.text == task_list['deleted']
            assert result == True

    def test_get_yesterday_unfinished_todo(self, etapi, day_url, content_url, task_list):
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', day_url, json={"noteId": "deadbeef"})
            mock.get(content_url, text=task_list['checked'])

            result = etapi.get_yesterday_unfinished_todo()
            assert len(result) == 1
            assert result[0] == [False, 'item_1']

    def test_move_yesterday_unfinished_todo(self, etapi, day_url, content_url, task_list):
        """A little more complicated than the others, so we'll test it separately.

        deadbeef is the noteId of the day note containing the todo list. (yesterday's note)
        c0ffee is the noteId of the current day note. (today's note)
        """
        with requests_mock.Mocker() as mock:
            mock.register_uri(
                'GET', day_url, [{'json': {"noteId": "deadbeef"}}, {'json': {"noteId": "c0ffee"}}]
            )
            mock.get(content_url, text=task_list['checked'])
            mock.get('mock://bogus:8080/etapi/notes/c0ffee/content', text='<p></p>')

            put_c0ffee = mock.put('mock://bogus:8080/etapi/notes/c0ffee/content', status_code=204)

            assert etapi.move_yesterday_unfinished_todo_to_today() == None
            assert put_c0ffee.call_count == 1
            assert put_c0ffee.last_request.text == task_list['deleted']
