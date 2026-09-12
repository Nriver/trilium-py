"""Tests for folder-level note-to-note link resolving (`resolveMdLinks`).

Runs fully offline with requests_mock — no Trilium server needed.
"""
import json
import os
import shutil
import tempfile
import unittest

import requests_mock

from trilium_py.client import ETAPI


def note_md(title, updated, created, body):
    return (
        '---\n'
        f'title: {title}\n'
        f'updated: {updated}\n'
        f'created: {created}\n'
        '---\n\n'
        f'{body}\n'
    )


def puts_to(mock, note_id):
    return [r for r in mock.request_history
            if r.method == 'PUT' and r.url.endswith(f'/etapi/notes/{note_id}/content')]


def patches_to(mock, note_id):
    return [r for r in mock.request_history
            if r.method == 'PATCH' and r.url.endswith(f'/etapi/notes/{note_id}')]


class TestResolveMdLinks(unittest.TestCase):
    A_UPDATED = '2025-09-08 12:34:56Z'
    B_UPDATED = '2024-05-06 10:11:12Z'

    def _write(self, tmpdir, rel, text):
        path = os.path.join(tmpdir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path

    def _cycle_tree(self):
        """a.md <-> sub/b.md: a circular note-to-note linkage."""
        tmpdir = tempfile.mkdtemp()
        self._write(tmpdir, 'a.md', note_md(
            'a', self.A_UPDATED, '2025-09-01 08:00:00Z', '[B](sub/b.md)'))
        self._write(tmpdir, 'sub/b.md', note_md(
            'b', self.B_UPDATED, '2024-01-01 08:00:00Z', '[A](../a.md)'))
        return tmpdir

    def _upload(self, mock, folder, **kwargs):
        ea = ETAPI('http://bogus:8080', 'bogus')
        ea.upload_md_folder(parentNoteId='root', mdFolder=folder,
                            parse_math=False, hasFrontMatter=True, **kwargs)

    def test_circular_links_resolve_both_ways(self):
        tmpdir = self._cycle_tree()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note', [
                {'json': {'note': {'noteId': 'nA'}}},
                {'json': {'note': {'noteId': 'nB'}}},
            ])
            mock.post('http://bogus:8080/etapi/attachments',
                      json={'attachmentId': 'a1', 'title': 'x'})
            mock.get('http://bogus:8080/etapi/notes/nA/content',
                     text='<p><a href="sub/b.md">B</a></p>')
            mock.get('http://bogus:8080/etapi/notes/nB/content',
                     text='<p><a href="../a.md">A</a></p>')
            mock.put(requests_mock.ANY, status_code=204)
            mock.patch('http://bogus:8080/etapi/notes/nA', json={})
            mock.patch('http://bogus:8080/etapi/notes/nB', json={})
            self._upload(mock, tmpdir, importModified=True, resolveMdLinks=True)

            # No note source is ever snapshotted as a file attachment.
            attached = [r for r in mock.request_history
                        if r.method == 'POST' and r.url.endswith('/etapi/attachments')]
            self.assertEqual(attached, [])

            put_a = puts_to(mock, 'nA')
            put_b = puts_to(mock, 'nB')
            self.assertEqual(len(put_a), 1)
            self.assertEqual(len(put_b), 1)
            self.assertIn('#root/nB', put_a[0].text)
            self.assertNotIn('b.md', put_a[0].text)
            self.assertIn('#root/nA', put_b[0].text)
            self.assertNotIn('a.md', put_b[0].text)

            # Dates are restored after each rewrite.
            patch_a = patches_to(mock, 'nA')
            patch_b = patches_to(mock, 'nB')
            self.assertEqual(len(patch_a), 1)
            self.assertEqual(len(patch_b), 1)
            self.assertEqual(json.loads(patch_a[0].text)['utcDateModified'],
                             '2025-09-08 12:34:56.000Z')
            self.assertEqual(json.loads(patch_b[0].text)['utcDateModified'],
                             '2024-05-06 10:11:12.000Z')

    def test_disabled_by_default_keeps_old_attach_behavior(self):
        tmpdir = self._cycle_tree()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note', [
                {'json': {'note': {'noteId': 'nA'}}},
                {'json': {'note': {'noteId': 'nB'}}},
            ])
            mock.post('http://bogus:8080/etapi/attachments',
                      json={'attachmentId': 'a1', 'title': 'x'})
            mock.put(requests_mock.ANY, status_code=204)
            self._upload(mock, tmpdir, importModified=True)

            attached = [r for r in mock.request_history
                        if r.method == 'POST' and r.url.endswith('/etapi/attachments')]
            self.assertEqual(len(attached), 2)
            # No second pass: notes are never read back.
            gets = [r for r in mock.request_history if r.method == 'GET']
            self.assertEqual(gets, [])

    def test_missing_target_is_left_alone(self):
        tmpdir = tempfile.mkdtemp()
        self._write(tmpdir, 'c.md', note_md(
            'c', self.A_UPDATED, '2025-09-01 08:00:00Z', '[Ghost](ghost.md)'))
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note',
                      json={'note': {'noteId': 'nC'}})
            mock.post('http://bogus:8080/etapi/attachments',
                      json={'attachmentId': 'a1', 'title': 'x'})
            mock.get('http://bogus:8080/etapi/notes/nC/content',
                     text='<p><a href="ghost.md">Ghost</a></p>')
            mock.put(requests_mock.ANY, status_code=204)
            mock.patch(requests_mock.ANY, json={})
            self._upload(mock, tmpdir, importModified=True, resolveMdLinks=True)

            self.assertEqual(puts_to(mock, 'nC'), [])
            self.assertEqual(patches_to(mock, 'nC'), [])
            attached = [r for r in mock.request_history
                        if r.method == 'POST' and r.url.endswith('/etapi/attachments')]
            self.assertEqual(attached, [])


    def test_md_mention_without_link_skips_server_roundtrip(self):
        tmpdir = tempfile.mkdtemp()
        self._write(tmpdir, 'd.md', note_md(
            'd', self.A_UPDATED, '2025-09-01 08:00:00Z',
            'I keep my notes like Agents.md in Joplin.'))
        self.addCleanup(shutil.rmtree, tmpdir, True)
        with requests_mock.Mocker() as mock:
            mock.post('http://bogus:8080/etapi/create-note',
                      json={'note': {'noteId': 'nD'}})
            mock.put(requests_mock.ANY, status_code=204)
            self._upload(mock, tmpdir, importModified=True, resolveMdLinks=True)

            gets = [r for r in mock.request_history if r.method == 'GET']
            self.assertEqual(gets, [])
            self.assertEqual(
                [r for r in mock.request_history if r.method == 'PUT'], [])


if __name__ == '__main__':
    unittest.main()
