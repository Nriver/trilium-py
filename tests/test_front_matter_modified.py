"""Tests for front matter last-modified import (`importModified`).

Runs fully offline with requests_mock — no Trilium server needed.
"""
import json
import os
import shutil
import tempfile
import unittest

import requests_mock

from trilium_py.client import ETAPI, _format_front_matter_date, _parse_front_matter_title


class TestParseFrontMatterTitle(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_parse_front_matter_title('title: plain title\n'), 'plain title')

    def test_single_quoted(self):
        self.assertEqual(
            _parse_front_matter_title("title: 'What/Why?'\n"), 'What/Why?')
        self.assertEqual(
            _parse_front_matter_title("title: 'it''s'\n"), "it's")

    def test_double_quoted(self):
        self.assertEqual(
            _parse_front_matter_title('title: "say \\"hi\\""\n'), 'say "hi"')

    def test_missing_or_empty(self):
        self.assertIsNone(_parse_front_matter_title('created: x\n'))
        self.assertIsNone(_parse_front_matter_title('title: \n'))
        self.assertIsNone(_parse_front_matter_title(''))


class TestFormatFrontMatterDate(unittest.TestCase):
    def test_with_millis(self):
        local, utc = _format_front_matter_date('2025-09-08 12:34:56.789Z')
        self.assertEqual(utc, '2025-09-08 12:34:56.789Z')
        # Same instant, rendered in local time with offset.
        self.assertRegex(local, r'^2025-09-08 \d{2}:34:56\.789[+-]\d{4}$')

    def test_without_millis(self):
        local, utc = _format_front_matter_date('2025-09-01 08:00:00Z')
        self.assertEqual(utc, '2025-09-01 08:00:00.000Z')
        self.assertIn('.000', local)

    def test_rejects_bad_shapes(self):
        self.assertEqual(_format_front_matter_date('yesterday'), (None, None))
        self.assertEqual(_format_front_matter_date('2025-09-08'), (None, None))
        self.assertEqual(_format_front_matter_date(''), (None, None))


class TestUploadMdFileTitle(unittest.TestCase):
    def _write_named(self, dirname, filename, body):
        path = os.path.join(dirname, filename)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(body)
        return path

    def _create_payload(self, mock, path, **kwargs):
        mock.post('http://bogus:8080/etapi/create-note',
                  json={'note': {'noteId': 'n1'}})
        ea = ETAPI('http://bogus:8080', 'bogus')
        ea.upload_md_file(file=path, parentNoteId='root',
                          parse_math=False, hasFrontMatter=True, **kwargs)
        return json.loads(mock.request_history[0].text)

    def test_front_matter_title_beats_sanitised_filename(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        path = self._write_named(
            tmpdir, 'What_Why_.md',
            '---\ntitle: \'What/Why?\'\ncreated: 2025-09-01 08:00:00Z\n---\n\nBody.\n')
        with requests_mock.Mocker() as mock:
            sent = self._create_payload(mock, path)
        self.assertEqual(sent['title'], 'What/Why?')

    def test_missing_title_falls_back_to_filename(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        path = self._write_named(
            tmpdir, 'plain.md',
            '---\ncreated: 2025-09-01 08:00:00Z\n---\n\nBody.\n')
        with requests_mock.Mocker() as mock:
            sent = self._create_payload(mock, path)
        self.assertEqual(sent['title'], 'plain')


class TestUploadMdFileModified(unittest.TestCase):
    NOTE = (
        '---\n'
        'title: Modified note\n'
        'updated: 2025-09-08 12:34:56Z\n'
        'created: 2025-09-01 08:00:00Z\n'
        '---\n'
        '\n'
        'Body text.\n'
    )

    def _write_note(self, body=None):
        tmp = tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8')
        tmp.write(body or self.NOTE)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def _upload(self, mock, path, **kwargs):
        created = mock.post('http://bogus:8080/etapi/create-note',
                            json={'note': {'noteId': 'n1'}})
        ea = ETAPI('http://bogus:8080', 'bogus')
        ea.upload_md_file(file=path, parentNoteId='root',
                          parse_math=False, hasFrontMatter=True, **kwargs)
        return json.loads(created.last_request.text)

    def test_modified_sent_when_opted_in(self):
        with requests_mock.Mocker() as mock:
            sent = self._upload(mock, self._write_note(), importModified=True)
        self.assertEqual(sent['utcDateModified'], '2025-09-08 12:34:56.000Z')
        self.assertRegex(sent['dateModified'], r'\.000[+-]\d{4}$')
        # created still flows as before, as a local/UTC pair
        self.assertIn('dateCreated', sent)
        self.assertEqual(sent['utcDateCreated'], '2025-09-01 08:00:00.000Z')

    def test_modified_omitted_by_default(self):
        with requests_mock.Mocker() as mock:
            sent = self._upload(mock, self._write_note())
        self.assertNotIn('dateModified', sent)
        self.assertNotIn('utcDateModified', sent)
        self.assertIn('dateCreated', sent)
        self.assertIn('utcDateCreated', sent)

    def test_unparseable_updated_is_omitted(self):
        bad = self.NOTE.replace('updated: 2025-09-08 12:34:56Z', 'updated: someday')
        with requests_mock.Mocker() as mock:
            sent = self._upload(mock, self._write_note(bad), importModified=True)
        self.assertNotIn('dateModified', sent)
        self.assertNotIn('utcDateModified', sent)

    def test_missing_updated_is_omitted(self):
        bare = '---\ntitle: x\ncreated: 2025-09-01 08:00:00Z\n---\n\nBody.\n'
        with requests_mock.Mocker() as mock:
            sent = self._upload(mock, self._write_note(bare), importModified=True)
        self.assertNotIn('dateModified', sent)
        self.assertNotIn('utcDateModified', sent)


class TestUploadMdFileContentRewrite(unittest.TestCase):
    """Attachment rewrites must not silently drop importModified dates.

    Regression tests for notes like "Mech Warrior Hanger Art" (external-only
    <img>) and "TTGO T-Display Sensors" (external markdown image): both used to
    issue an unconditional PUT /content after create-note, re-stamping
    dateModified to import time. Notes with real local attachments (e.g. "PS5
    NixOS") still need the rewrite PUT, but must restore the dates via PATCH.
    """

    FRONT = (
        '---\n'
        'title: x\n'
        'updated: 2025-09-08 12:34:56Z\n'
        'created: 2025-09-01 08:00:00Z\n'
        '---\n\n'
    )

    def _write_tree(self, md_body, image_bytes=None, image_name='pic.png'):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(tmpdir, ignore_errors=True))
        md_path = os.path.join(tmpdir, 'note.md')
        with open(md_path, 'w', encoding='utf-8') as fh:
            fh.write(self.FRONT + md_body)
        if image_bytes is not None:
            with open(os.path.join(tmpdir, image_name), 'wb') as fh:
                fh.write(image_bytes)
        return md_path

    def _mocks(self, mock):
        mock.post('http://bogus:8080/etapi/create-note',
                  json={'note': {'noteId': 'n1'}})
        mock.put('http://bogus:8080/etapi/notes/n1/content', status_code=204)
        mock.post('http://bogus:8080/etapi/attachments',
                  json={'attachmentId': 'a1', 'title': 'pic.png'})
        mock.put('http://bogus:8080/etapi/attachments/a1/content', status_code=204)
        mock.post('http://bogus:8080/etapi/attributes/',
                  json={'attributeId': 'attr1'})
        patched = mock.patch('http://bogus:8080/etapi/notes/n1',
                             json={'noteId': 'n1'})
        return patched

    def _puts(self, mock):
        return [r for r in mock.request_history
                if r.method == 'PUT' and '/notes/n1/content' in r.url]

    def test_external_img_skips_rewrite(self):
        md = ('<img src="http://example.com/repair_facility.gif" width="80%">\n'
              '\nBody.\n')
        path = self._write_tree(md)
        with requests_mock.Mocker() as mock:
            self._mocks(mock)
            ea = ETAPI('http://bogus:8080', 'bogus')
            ea.upload_md_file(file=path, parentNoteId='root',
                              parse_math=False, hasFrontMatter=True,
                              importModified=True)
            self.assertEqual(self._puts(mock), [])
            self.assertEqual(
                [r for r in mock.request_history if r.method == 'PATCH'], [])

    def test_external_markdown_image_skips_rewrite(self):
        md = '![pinmap.jpg](https://example.com/pinmap.jpg?raw=true)\n\nBody.\n'
        path = self._write_tree(md)
        with requests_mock.Mocker() as mock:
            self._mocks(mock)
            ea = ETAPI('http://bogus:8080', 'bogus')
            ea.upload_md_file(file=path, parentNoteId='root',
                              parse_math=False, hasFrontMatter=True,
                              importModified=True)
            self.assertEqual(self._puts(mock), [])
            self.assertEqual(
                [r for r in mock.request_history if r.method == 'PATCH'], [])

    def test_local_image_rewrites_then_restores_dates(self):
        md = '![pic.png](pic.png)\n\nBody.\n'
        # Minimal valid PNG header bytes; content is never decoded in the test.
        path = self._write_tree(md, image_bytes=b'\x89PNG\r\n\x1a\n' + b'\x00' * 32)
        with requests_mock.Mocker() as mock:
            patched = self._mocks(mock)
            ea = ETAPI('http://bogus:8080', 'bogus')
            ea.upload_md_file(file=path, parentNoteId='root',
                              parse_math=False, hasFrontMatter=True,
                              importModified=True)
            self.assertEqual(len(self._puts(mock)), 1)
            self.assertEqual(len(patched.request_history), 1)
            sent = json.loads(patched.last_request.text)
            self.assertEqual(sent['utcDateModified'], '2025-09-08 12:34:56.000Z')
            self.assertIn('dateModified', sent)

    def test_local_image_without_import_modified_does_not_patch(self):
        md = '![pic.png](pic.png)\n\nBody.\n'
        path = self._write_tree(md, image_bytes=b'\x89PNG\r\n\x1a\n' + b'\x00' * 32)
        with requests_mock.Mocker() as mock:
            self._mocks(mock)
            ea = ETAPI('http://bogus:8080', 'bogus')
            ea.upload_md_file(file=path, parentNoteId='root',
                              parse_math=False, hasFrontMatter=True)
            self.assertEqual(len(self._puts(mock)), 1)
            self.assertEqual(
                [r for r in mock.request_history if r.method == 'PATCH'], [])


if __name__ == '__main__':
    unittest.main()
