# trilium-py

Python client for ETAPI of Trilium Note.

# Installation

```
python3 -m pip install trilium-py --user
```

# Usage

Down below are some simple example code to use this package.

## initialize

If you have a ETAPI token, change the `server_url` and `token` to yours.

```
from trilium_py.client import ETAPI

server_url = 'http://localhost:8080'
token = 'YOUR_TOKEN'
ea = ETAPI(server_url, token)
```

If you haven't created ETAPI token, you can create one with your password. Please note, you can only see this token
once, please save it if you want to reuse the token.

```
from trilium_py.client import ETAPI

server_url = 'http://localhost:8080'
password = '1234'
ea = ETAPI(server_url)
token = ea.login(password)
print(token)
```

After initialization, you can use Trilium ETAPI with python now. The following are some examples.

## Search note

Search note with keyword.

```
res = ea.search_note(
    search="python",
)

for x in res['results']:
    print(x['noteId'], x['title'])
```

## Create Note

You can create a simple note like this.

```
res = ea.create_note(
    parentNoteId="root",
    title="Simple note 1",
    type="text",
    content="Simple note example",
    noteId="note1"
)
```

The `noteId` is not mandatory, if not provided, Trilium will generate a random one. You can retrieve it in the return.

```
noteId = res['note']['noteId']
```

## Get note

To retrieve the note's content.

```
ea.get_note_content("note1")
```

You can get a note metadata by its id.

```
ea.get_note(note_id)
```

## Update note

Update note content

```
ea.update_note_content("note1", "updated by python")
```

Modify note title

```
ea.patch_note(
    noteId="note1",
    title="Python client moded",
)
```

## Delete note

Simply delete a note by id.

```
ea.delete_note("note1")
```

# TODO List

## Add TODO item

You can use `add_todo` to add a TODO item, param is the TODO description

```
ea.add_todo("买暖宝宝")
```

## Check/Uncheck a TODO item

param is the index of the TODO item

```
ea.todo_check(0)
ea.todo_uncheck(1)
```

## Update a TODO item

Use `update_todo` to update a TODO item description at certain index.

```
ea.update_todo(0, "去码头整点薯条")
```

# Delete a TDOO item

Remove a TODO item by its index.

```
ea.delete_todo(1)
```

# Develop

Install with pip egg link to make package change without reinstall.

```
python -m pip install --user -e .
```

# Original OpenAPI Documentation

The original OpenAPI document is [here](https://github.com/zadam/trilium/blob/master/src/etapi/etapi.openapi.yaml). You
can open it with [swagger editor](https://editor.swagger.io/).
