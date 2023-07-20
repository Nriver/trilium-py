import os
import json
import base64

output = './out'
resource_sub_folder_name = '_resources'

counter = 1


def make_dir(p):
    if not os.path.exists(p):
        os.makedirs(p)


def decode(s):
    return base64.b64decode(s)


make_dir(output)

with open('turtl-backup.json', 'r', encoding='utf-8') as f:
    d = json.loads(f.read())

spaces = {}
for x in d['spaces']:
    folder_name = x['title']
    spaces[x['id']] = folder_name
    path = f'{output}/{folder_name}'
    make_dir(path)

boards = {}
for x in d['boards']:
    # print(x)
    space_id = x['space_id']
    path = f"{output}/{spaces[space_id]}/{x['title']}"
    boards[x['id']] = path
    make_dir(path)

files = {}
for x in d['files']:
    files[x['id']] = x['data']

notes = {}
for x in d['notes']:
    board_id = x['board_id']
    content = x['text']
    title = x['title']
    note_type = x['type']

    if not title:
        # give a default name if no title exists
        title = f'No title {counter}'
        counter += 1

    if not board_id:
        # root folder if not belong to board
        file_path = f'{output}/{title}.md'
    else:
        # put it under sub board folder
        file_path = f'{boards[board_id]}/{title}.md'

    print(file_path)

    if note_type == 'text':
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    elif note_type == 'password':
        content = f"{x['username']}\n{x['password']}\n\n{content}"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    elif note_type == 'link':
        content = f"[{x['url']}]({x['url']})\n\n{content}"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    elif note_type == 'image':
        print(x)
        print(x['id'])
        # extract image file
        image_name = x['file']['name']
        if not board_id:
            image_folder = f'{output}/{resource_sub_folder_name}/{title}'
        else:
            image_folder = f'{boards[board_id]}/{resource_sub_folder_name}/{title}'
        make_dir(image_folder)

        image_path = f'{image_folder}/{image_name}'
        with open(image_path, 'wb') as f:
            f.write(base64.b64decode(files[x['id']]))
        # add image to note
        content = f"![{image_name}]({resource_sub_folder_name}/{title}/{image_name})\n\n{content}"

        print(content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    elif note_type == 'file':
        print(x['id'])
        # extract file
        attachment_name = x['file']['name']
        print(title)
        if not board_id:
            attachment_folder = f'{output}/{resource_sub_folder_name}/{title}'
        else:
            attachment_folder = f'{boards[board_id]}/{resource_sub_folder_name}/{title}'
        make_dir(attachment_folder)
        attachment_path = f'{attachment_folder}/{attachment_name}'
        with open(attachment_path, 'wb') as f:
            f.write(base64.b64decode(files[x['id']]))
        # add file to note
        content = (
            f"[{attachment_name}]({resource_sub_folder_name}/{title}/{attachment_name})"
            f"\n\n{content}"
        )
        print(content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(x)
