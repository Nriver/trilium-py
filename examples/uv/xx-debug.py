'''debug script for trilium-py'''
# /// script
# dependencies = [
#   "trilium-py",
#   "python-dotenv",
# ]
# ///

from trilium_py.client import ETAPI
import sys

server_url = 'http://localhost:8080'
token = 'GgS8B5YHT2ij_xUg/aXm2luCzUyf5Xofq89hc5TCXqfVzV4cvAikZmqo='
ea = ETAPI(server_url, token)

import_root = 'import-from-tpy'

res = ea.search_note(f"note.title = '{import_root}'")
# print(res)
if res['results']:
    noteId = res['results'][0]['noteId']
    print(noteId)
else:
    res = ea.create_note(
        parentNoteId="root",
        title=import_root,
        type="text",
        content=f"Import root for {sys.argv[0]}",
    )
    noteId = res['note']['noteId']


if noteId:
    res = ea.upload_md_file(
        parentNoteId=noteId,
        file="./sample/sample-2.md",
    )
    print(res)
else:
    print(f'NoteId {noteId} not found')
# res = ea.upload_md_folder(
#     parentNoteId="import-test",
#     mdFolder="./sample",
# )