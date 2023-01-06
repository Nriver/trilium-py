# trilium-py

Python client for ETAPI of Trilium Note.

# Toc

<!--ts-->

* [trilium-py](#trilium-py)
* [Toc](#toc)
* [Installation](#installation)
* [(Basic) Usage](#basic-usage)
    * [Initialization](#initialization)
    * [Application Information](#application-information)
    * [Search note](#search-note)
    * [Create Note](#create-note)
        * [Create Image note](#create-image-note)
    * [Get note](#get-note)
    * [Update note](#update-note)
    * [Delete note](#delete-note)
    * [Day note](#day-note)
* [(Advanced Usage) TODO List](#advanced-usage-todo-list)
    * [Add TODO item](#add-todo-item)
    * [Check/Uncheck a TODO item](#checkuncheck-a-todo-item)
    * [Update a TODO item](#update-a-todo-item)
    * [Delete a TDOO item](#delete-a-tdoo-item)
    * [Move yesterday's unfinished todo to today](#move-yesterdays-unfinished-todo-to-today)
* [(Advanced Usage) Upload Markdown files](#advanced-usage-upload-markdown-files)
    * [Upload single Markdown file with images](#upload-single-markdown-file-with-images)
    * [Bulk upload Markdown files in a folder!](#bulk-upload-markdown-files-in-a-folder)
* [Develop](#develop)
* [Original OpenAPI Documentation](#original-openapi-documentation)

<!--te-->

# Installation

```
python3 -m pip install trilium-py --user
```

# (Basic) Usage

These are basic function that Trilium's ETAPI provides. Down below are some simple example code to use this package.

## Initialization

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

## Application Information

To start with, you can get the application information like this.

```
print(ea.app_info())
```

It should give you the version of your server application and some extra information.

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

### Create Image note

Image note is a special kind of note. You can create an image note with minimal information like this. The `image_file`
refers to the path of image.

```
res = ea.create_image_note(
    parentNoteId="root",
    title="Image note 1",
    image_file="shield.png",
)
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

## Day note

You can get the content of a certain date with `get_day_note`. The date string should be in format of "%Y-%m-%d", e.g. "
2022-02-25".

```
es.get_day_note("2022-02-25")
```

Then set/update a day note with `set_day_note`. The content should be a (html) string.

```
self.set_day_note(date, new_content)
```

# (Advanced Usage) TODO List

With the power of Python, I have expanded the basic usage of ETAPI. You can do something with todo list now.

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

## Delete a TDOO item

Remove a TODO item by its index.

```
ea.delete_todo(1)
```

## Move yesterday's unfinished todo to today

As the title suggests, you can move yesterday's unfinished things to today. Unfinished todos will be deleted from
yesterday's note.

```
ea.move_yesterday_unfinished_todo_to_today()
```

# (Advanced Usage) Upload Markdown files

## Upload single Markdown file with images

You can import Markdown file with images into Trilium now! Trilium-py will help you to upload the images and fix the
links for you!

```
res = ea.upload_md_file(
    parentNoteId="root",
    file="./md-demo/manjaro 修改caps lock.md",
)
```

## Bulk upload Markdown files in a folder!

You can upload a folder with lots of Markdown files to Trilium and preserve the folder structure!

Say, upload all the notes from [VNote](https://github.com/vnotex/vnote), simply do this:

```
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="~/data/vnotebook/",
    ignoreFolder=['vx_notebook', 'vx_recycle_bin', 'vx_images', '_v_images'],
)
```

# Develop

Install with pip egg link to make package change without reinstall.

```
python -m pip install --user -e .
```

# Original OpenAPI Documentation

The original OpenAPI document is [here](https://github.com/zadam/trilium/blob/master/src/etapi/etapi.openapi.yaml). You
can open it with [swagger editor](https://editor.swagger.io/).
