"""Tests for folder-note dates via the `_folders.json` manifest.

Runs fully offline with requests_mock — no Trilium server needed.
"""
import json
import os
import shutil
import tempfile
import unittest

import requests_mock

from trilium_py.client import ETAPI

NOTE = (
    '---\n'
    'title: note\n'
    'updated: 2025-09-08 12:34:56Z\n'
    'created: 2025-09-01 08:00:00Z\n'
    '---\n'
    '\n'
    'Body text.\n'
)


def make_tree(manifest=None):
    """Build tmpdir/sub/note.md, with an optional _folders.json manifest."""
    tmpdir = tempfile.mkdtemp()
    os.mkdir(os.path.join(tmpdir, 'sub'))
    with open(os.path.join(tmpdir, 'sub', 'note.md'), 'w', encoding='utf-8') as fh:
        fh.write(NOTE)
    if manifest is not None:
        with open(os.path.join(tmpdir, '_folders.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh)
    return tmpdir


def creates(mock):
    """All create-note payloads, in the order they were sent."""
    return [json.loads(r.text) for r in mock.request_history
            if r.method == 'POST' and r.url.endswith('/etapi/create-note')]


class TestUploadMdFolderDates(unittest.TestCase):
    MANIFEST = {'sub': {'created': '2020-03-13 19:05:04Z',
                        'updated': '2022-07-05 02:35:39Z'}}

    def _upload(self, mock, folder, **kwargs):
        mock.post('http://bogus:8080/etapi/create-note',
                  json={'note': {'noteId': 'n1'}})
        ea = ETAPI('http://bogus:8080', 'bogus')
        ea.upload_md_folder(parentNoteId='root', mdFolder=folder,
                            parse_math=False, hasFrontMatter=True, **kwargs)

    def test_folder_dates_sent_with_import_modified(self):
        tmpdir = make_tree(self.MANIFEST)
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir, importModified=True)
        folder = next(p for p in creates(mock) if p['title'] == 'sub')
        self.assertEqual(folder['utcDateCreated'], '2020-03-13 19:05:04.000Z')
        self.assertIn('dateCreated', folder)
        self.assertEqual(folder['utcDateModified'], '2022-07-05 02:35:39.000Z')
        self.assertIn('dateModified', folder)

    def test_folder_modified_omitted_by_default(self):
        tmpdir = make_tree(self.MANIFEST)
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir)
        folder = next(p for p in creates(mock) if p['title'] == 'sub')
        self.assertEqual(folder['utcDateCreated'], '2020-03-13 19:05:04.000Z')
        self.assertNotIn('dateModified', folder)
        self.assertNotIn('utcDateModified', folder)

    def test_missing_manifest_keeps_import_time(self):
        tmpdir = make_tree(None)
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir, importModified=True)
        folder = next(p for p in creates(mock) if p['title'] == 'sub')
        for key in ('dateCreated', 'utcDateCreated',
                    'dateModified', 'utcDateModified'):
            self.assertNotIn(key, folder)

    def test_folder_icon_appended_to_title(self):
        manifest = {'sub': {'created': '2020-03-13 19:05:04Z',
                            'updated': '2022-07-05 02:35:39Z',
                            'icon': '🤖'}}
        tmpdir = make_tree(manifest)
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir, importModified=True)
        titles = [p['title'] for p in creates(mock)]
        self.assertIn('sub 🤖', titles)

    def test_folder_without_icon_keeps_plain_title(self):
        tmpdir = make_tree(self.MANIFEST)
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir, importModified=True)
        titles = [p['title'] for p in creates(mock)]
        self.assertIn('sub', titles)
        self.assertNotIn('sub ', titles)

    def test_folder_real_title_beats_sanitised_dirname(self):
        manifest = {'LLM _ ML _ AI': {'title': 'LLM / ML / AI',
                                      'created': '2023-05-31 14:25:40Z',
                                      'updated': '2023-05-31 14:25:40Z',
                                      'icon': '🧠'}}
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        os.mkdir(os.path.join(tmpdir, 'LLM _ ML _ AI'))
        with open(os.path.join(tmpdir, 'LLM _ ML _ AI', 'note.md'),
                  'w', encoding='utf-8') as fh:
            fh.write(NOTE)
        with open(os.path.join(tmpdir, '_folders.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh)
        with requests_mock.Mocker() as mock:
            self._upload(mock, tmpdir, importModified=True)
        titles = [p['title'] for p in creates(mock)]
        self.assertIn('LLM / ML / AI 🧠', titles)


if __name__ == '__main__':
    unittest.main()
