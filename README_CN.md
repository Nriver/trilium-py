# 🐍 trilium-py

<p align="center">
<a href="README.md">English</a> | 简体中文
</p>

> [!IMPORTANT]
> 中文文档可能落后于英文文档，如果有问题请先查看英文文档。

Trilium Note的ETAPI的Python客户端。

[![Downloads](https://static.pepy.tech/badge/trilium-py)](https://pepy.tech/project/trilium-py)
[![Supported Versions](https://img.shields.io/pypi/pyversions/trilium-py.svg)](https://pypi.org/project/trilium-py)
[![Supported Versions](https://img.shields.io/pypi/v/trilium-py?color=%2334D058&label=pypi%20package)](https://pypi.org/project/trilium-py)
[![PyPI license](https://img.shields.io/pypi/l/trilium-py.svg)](https://pypi.python.org/pypi/trilium-py/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)

## 🦮 目录

<!--ts-->
* [🐍 trilium-py](#-trilium-py)
   * [🦮 目录](#-目录)
   * [🔧 安装](#-安装)
   * [📖 (基本) 用法](#-基本-用法)
      * [🚀 初始化](#-初始化)
      * [📊 应用信息](#-应用信息)
      * [🔍 搜索笔记](#-搜索笔记)
      * [🏭 创建笔记](#-创建笔记)
         * [🖼️ 创建图片笔记](#️-创建图片笔记)
      * [👀 获取笔记](#-获取笔记)
      * [🔄 更新笔记](#-更新笔记)
      * [🗑️ 删除笔记](#️-删除笔记)
      * [📅 日记](#-日记)
      * [📤 导出笔记](#-导出笔记)
      * [💾 创建数据备份](#-创建数据备份)
      * [获取附件信息](#获取附件信息)
      * [更新附件信息](#更新附件信息)
      * [获取附件内容](#获取附件内容)
      * [更新附件内容](#更新附件内容)
      * [创建附件](#创建附件)
   * [(高级用法) ✅ TODO 列表](#高级用法--todo-列表)
      * [添加TODO项](#添加todo项)
      * [检查/取消检查TODO项](#检查取消检查todo项)
      * [更新TODO项](#更新todo项)
      * [删除TODO项](#删除todo项)
      * [将昨天未完成的待办事项移到今天](#将昨天未完成的待办事项移到今天)
   * [(高级用法) 🚚 上传Markdown文件](#高级用法--上传markdown文件)
      * [上传单个带图片的Markdown文件](#上传单个带图片的markdown文件)
      * [批量上传文件夹中的Markdown文件](#批量上传文件夹中的markdown文件)
         * [从VNote导入](#从vnote导入)
         * [从Joplin导入](#从joplin导入)
         * [从Logseq导入](#从logseq导入)
         * [从Obsidian导入](#从obsidian导入)
         * [从有道云笔记导入](#从有道云笔记导入)
         * [从Turtl导入](#从turtl导入)
         * [从其他Markdown软件导入](#从其他markdown软件导入)
   * [(高级用法) 🎨 美化笔记](#高级用法--美化笔记)
      * [美化笔记](#美化笔记)
      * [美化笔记及其子笔记](#美化笔记及其子笔记)
   * [(高级用法) 🧹 排序笔记内容](#高级用法--排序笔记内容)
   * [🛠️ 开发](#️-开发)
   * [🔗 原始OpenAPI文档](#-原始openapi文档)
<!--te-->

## 🔧 安装

```bash
python3 -m pip install trilium-py --user
```

## 📖 (基本) 用法

以下是Trilium的ETAPI提供的基本功能。下面是一些使用这个包的简单示例代码。

### 🚀 初始化

如果你有一个ETAPI令牌，请将 `server_url` 和 `token` 更改为你自己的。

```python
from trilium_py.client import ETAPI

server_url = 'http://localhost:8080'
token = 'YOUR_TOKEN'
ea = ETAPI(server_url, token)
```

如果你还没有创建ETAPI令牌，你可以使用密码创建一个。请注意，你只能看到这个令牌一次，请保存它以便重用。

```python
from trilium_py.client import ETAPI

server_url = 'http://localhost:8080'
password = '1234'
ea = ETAPI(server_url)
token = ea.login(password)
print(token)
```

初始化后，就可以使用Python使用Trilium的ETAPI了。以下是一些示例。

### 📊 应用信息

首先，你可以获取应用程序的信息。

```python
print(ea.app_info())
```

可以输出服务器应用程序的版本等信息。

### 🔍 搜索笔记

使用关键字搜索笔记。

```python
res = ea.search_note(
    search="python",
)

for x in res['results']:
    print(x['noteId'], x['title'])
```

使用正则表达式进行搜索。例如，搜索并获取特定笔记下的所有子笔记：

```python
res = ea.search_note(
    # 通过笔记标题进行正则表达式搜索
    search="note.title %= '.*'",
    ancestorNoteId="父笔记ID",
    fastSearch=False,
    limit=1000,
)
```

### 🏭 创建笔记

你可以像这样创建一个简单的笔记。

```python
res = ea.create_note(
    parentNoteId="root",
    title="笔记标题",
    type="text",
    content="笔记内容",
    noteId="note1"
)
```

`noteId` 不是必需的，如果没有提供，Trilium会生成一个随机的。返回信息里可以看到这个noteId的值。

```python
noteId = res['note']['noteId']
```

#### 🖼️ 创建图片笔记

图像笔记是一种特殊类型的笔记。你可以使用最少的信息创建一个图像笔记，如下所示。`image_file` 是图片的路径。

```python
res = ea.create_image_note(
    parentNoteId="root",
    title="Image note 1",
    image_file="shield.png",
)
```
### 👀 获取笔记

检索笔记的内容。

```python
ea.get_note_content("noteid")
```

你可以通过笔记的ID获取笔记的元数据。

```python
ea.get_note(note_id)
```

### 🔄 更新笔记

更新笔记内容

```python
ea.update_note_content("noteid", "由Python更新")
```

修改笔记标题

```python
ea.patch_note(
    noteId="noteid",
    title="Python客户端修改",
)
```

### 🗑️ 删除笔记

通过笔记ID删除一个笔记。

```python
ea.delete_note("noteid")
```

### 📅 日记

你可以使用 `get_day_note` 获取特定日期的内容。日期字符串应该采用"%Y-%m-%d"的格式，例如 "2022-02-25"。

```python
ea.get_day_note("2022-02-25")
```

然后使用 `set_day_note` 设置/更新一个日记。内容应该是一个（HTML）字符串。

```python
ea.set_day_note(date, new_content)
```

### 📤 导出笔记

导出笔记有两种格式 `html` 或 `markdown`/`md`。

```python
res = ea.export_note(
    noteId='sK5fn4T6yZRI',
    format='md',
    savePath='/home/nate/data/1/test.zip',
)
```

### 💾 创建数据备份

这个例子将创建一个数据库备份文件，类似于 `trilium-data/backup/backup-test.db`。

```python
res = ea.backup("test")
```

你可以使用Linux中的cron实用程序来安排定期自动备份。例如，要在每天上午3:00进行一次备份，你可以使用以下cron表达式：

```bash
0 3 * * * python /path/to/backup-script.py
```

### 获取附件信息

获取图片标题等。

```python
res = ea.get_attachment('Y5V6pYq6nwXo')
```

### 更新附件信息

更改图片标题等。

```python
res = ea.update_attachment(
    attachmentId='2b7pPzqocS1s', title='你好ETAPI', role='image', mime='image/png'
)
```

### 获取附件内容

获取真实的图片文件。

```python
res = ea.get_attachment_content('icpDE4orQxlI')
with open('1.png', 'wb') as f:
    f.write(res)
```

### 更新附件内容

用新的图片替换旧的。

```python
res = ea.update_attachment_content('icWqV6zFtE0V', '/home/nate/data/1.png')
```

### 创建附件

上传一个图片文件作为笔记的附件。

```python
res = ea.create_attachment(
    ownerId='8m8luXym5LxT',
    file_path='/home/nate/data/ksnip_20230630-103509.png',
)
```

## (高级用法) ✅ TODO 列表

借助Python的强大功能，我已经扩展了ETAPI的基本用法。现在你可以对待办事项列表做一些事情了。

### 添加TODO项

你可以使用 `add_todo` 来添加一个TODO项，参数是TODO的描述。

```python
ea.add_todo("买暖宝宝")
```

### 检查/取消检查TODO项

参数是TODO项的索引。

```python
ea.todo_check(0)
ea.todo_uncheck(1)
```
### 更新TODO项

使用 `update_todo` 来更新某个索引处的TODO项描述。

```python
ea.update_todo(0, "去码头整点薯条")
```

### 删除TODO项

通过索引删除TODO项。

```python
ea.delete_todo(1)
```

### 将昨天未完成的待办事项移到今天

如标题所示，你可以将昨天未完成的事情移到今天。未完成的待办事项将从昨天的笔记中删除。

```python
ea.move_yesterday_unfinished_todo_to_today()
```

## (高级用法) 🚚 上传Markdown文件

### 上传单个带图片的Markdown文件

现在你可以将带有图片的Markdown文件导入Trilium了！trilium-py将帮助你上传图片并为你修复链接！

```python
res = ea.upload_md_file(
    parentNoteId="root",
    file="./md-demo/manjaro 修改caps lock.md",
)
```

### 批量上传文件夹中的Markdown文件

你可以上传一个包含许多Markdown文件的文件夹到Trilium并保留文件夹结构！

#### 从VNote导入

比如，上传所有来自[VNote](https://github.com/vnotex/vnote)的笔记，只需执行以下操作：

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="~/data/vnotebook/",
    ignoreFolder=['vx_notebook', 'vx_recycle_bin', 'vx_images', '_v_images'],
)
```

#### 从Joplin导入

Joplin可以轻松导入。

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="/home/nate/data/joplin_data/",
    ignoreFolder=['_resources', ],
)
```

#### 从Logseq导入

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="/home/nate/data/logseq_data/",
    ignoreFolder=['assets', 'logseq'],
)
```

#### 从Obsidian导入

Obsidian有一个非常独特的文件链接系统。你应该使用[obsidian-export](https://github.com/zoni/obsidian-export)将Obsidian vault转换为常规的Markdown文件。然后再使用trilium-py将笔记导入Trilium。

首先进行转换。

```bash
obsidian-export /path/to/your/vault /out
```

然后像导入普通markdown一样导入，trilium-py会为你处理图片。

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="E:/data/out",
)
```

#### 从有道云笔记导入

有道云笔记不再提供导出功能。不过好在你可以使用<https://github.com/DeppWang/youdaonote-pull>下载你的笔记并将其转换为Markdown文件。之后，trilium-py应该能够帮助你导入它们。

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="/home/nate/gitRepo/youdaonote-pull/out/",
)
```

#### 从Turtl导入

你需要首先将Turtl从json转换为markdown。
详见 [turtl-to-markdown](https://github.com/Nriver/trilium-py/tree/main/examples/turtl-to-markdown)。

然后你可以像这样使用trilium-py导入：

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="/home/nate/gitRepo/turtl-to-markdown/out/",
    ignoreFolder=['_resources'],
)
```

#### 从其他Markdown软件导入

一般来说，markdown文件有各种标准。你可以尝试使用以下方法导入它们

```python
res = ea.upload_md_folder(
    parentNoteId="root",
    mdFolder="/home/nate/data/your_markdown_files/",
)
```

如果有任何问题，请随时创建一个[issue](https://github.com/Nriver/trilium-py/issues/new)。

## (高级用法) 🎨 美化笔记

由于Trilium使用的库的限制，导入的笔记可能会遇到轻微的格式问题。这些问题包括代码块末尾出现额外的一行，图像与笔记内容融为一体，标题之间缺少换行符，导致笔记内容显得拥挤。

以下是你可以用来美化你的笔记的方法。

### 美化笔记

指定笔记ID以美化笔记内容。

```python
ea.beautify_note('krm8B9JthNfi')
```

### 美化笔记及其子笔记

```python
ea.beautify_sub_notes('tlPuzU2szLJh')
```

## (高级用法) 🧹 排序笔记内容

按照标题名称对笔记进行排序。这个功能对包含大量列表的笔记非常有价值，比如按各种流派排序的书名列表。它同样适用于管理浏览器书签或收集链接。

此外，你还可以为排序指定一个语言代码，以根据你的本地语言进行排序。这可以增强排序过程并使其适应你的语言偏好。

```python
res = ea.sort_note_content('lPxtkknjR2bJ')
res = ea.sort_note_content('y6hROhWjNmHQ', 'zh_CN.UTF-8')
```

##（高级用法）🧹 删除空的“新笔记”

有时，我无意中创建了大量的“新笔记”，而这些笔记在我的笔记树中仍未被删除。这些“新笔记”使我的工作区杂乱不堪，散落在各个地方。我开发了这个批量删除空的“新笔记”的功能。此外，它会为包含内容的“新笔记”生成警告消息，也许我们应该为这些笔记更改标题。

```python
ea.delete_empty_note()
```

## 🛠️ 开发

使用pip egg link进行安装，以便在不重新安装的情况下进行包更改。

```python
python -m pip install --user -e .
```

## 🔗 原始OpenAPI文档

原始OpenAPI文档在[这里](https://github.com/zadam/trilium/blob/master/src/etapi/etapi.openapi.yaml)。你可以使用[swagger editor](https://editor.swagger.io/)打开它。
