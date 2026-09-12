"""Tests for front matter tag import (`importTags`).

Runs fully offline with requests_mock — no Trilium server needed.
"""
import json
import os
import tempfile
import unittest

import requests_mock

from trilium_py.client import ETAPI, _parse_front_matter_tags


class TestParseFrontMatterTags(unittest.TestCase):
    def test_joplin_shape(self):
        fm = (
            'title: My note\n'
            'updated: 2025-09-08 12:34:56Z\n'
            'created: 2025-09-01 08:00:00Z\n'
            'tags:\n'
            '  - nix\n'
            '  - state-management\n'
        )
        self.assertEqual(
            _parse_front_matter_tags(fm), ['nix', 'state-management'])

    def test_missing_or_empty(self):
        self.assertEqual(_parse_front_matter_tags('title: x\n'), [])
        self.assertEqual(_parse_front_matter_tags('tags:\n'), [])
        self.assertEqual(_parse_front_matter_tags('tags: []\n'), [])

    def test_quoted_and_duplicates(self):
        fm = "tags:\n  - 'it''s'\n  - plain\n  - plain\n"
        self.assertEqual(_parse_front_matter_tags(fm), ["it's", 'plain'])

    def test_tags_key_must_be_top_level(self):
        # indented `- ` lines without a `tags:` key are not tags
        self.assertEqual(
            _parse_front_matter_tags('title: x\nbody:\n  - nope\n'), [])

    def test_stops_at_block_end(self):
        fm = 'tags:\n  - a\nnot a list\n  - b\n'
        self.assertEqual(_parse_front_matter_tags(fm), ['a'])


class TestUploadMdFileTags(unittest.TestCase):
    NOTE = (
        '---\n'
        'title: Tagged note\n'
        'updated: 2025-09-08 12:34:56Z\n'
        'created: 2025-09-01 08:00:00Z\n'
        'tags:\n'
        '  - nix\n'
        '  - dph\n'
        '---\n'
        '\n'
        'Body text.\n'
    )

    def _write_note(self):
        tmp = tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8')
        tmp.write(self.NOTE)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_labels_created(self):
        ea = ETAPI('http://bogus:8080', 'bogus')
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note',
                      json={'note': {'noteId': 'n1'}})
            attrs = mock.post('http://bogus:8080/etapi/attributes/',
                              json={'attributeId': 'a1'})
            ea.upload_md_file(file=self._write_note(), parentNoteId='root',
                              parse_math=False, hasFrontMatter=True,
                              importTags=True)
            sent = [json.loads(req.text) for req in attrs.request_history]
            # NB: clean_param() strips the empty value / False inheritable
            # defaults on the wire; the server applies the same defaults.
            self.assertEqual(
                [(s['noteId'], s['type'], s['name']) for s in sent],
                [('n1', 'label', 'nix'), ('n1', 'label', 'dph')])

    def test_opt_in_default_off(self):
        ea = ETAPI('http://bogus:8080', 'bogus')
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note',
                      json={'note': {'noteId': 'n1'}})
            attrs = mock.post('http://bogus:8080/etapi/attributes/',
                              json={'attributeId': 'a1'})
            ea.upload_md_file(file=self._write_note(), parentNoteId='root',
                              parse_math=False, hasFrontMatter=True)
            self.assertEqual(attrs.call_count, 0)


if __name__ == '__main__':
    unittest.main()
