# Using Trilium Py with UV

Examples of Trilium-py scripts that can be run using [**`uv`** from Astral](https://github.com/astral-sh/uv)
without having to install anything other than _uv_ ahead of time, not even python.

1. Install uv,
2. run a script.

```
uv run <scipt-name> <parameters>
```

## Development

Write standalone scripts with dependencies declared using (inline metadata)[https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata] (PEP 723) and execute with `uv run`. For example:

```python
'''demo: hello world from Trilium-py'''
# /// script
# dependencies = [
#   "click",
#   "rich",
#   "trilium-py",
# ]
# ///
import rich
rich.print("hello world from Trilium-py :)")
```

Then execute :

    uv run hello-world.py

Script names follow function names, for example `ea_app_info.py` for `ea.app_info()`.


## Examples

### Get Trilium Token
Implementation of README.md#etapi-initialization

```shell
❯ uv run get_etapi_token.py --help
Usage: get_etapi_token.py [OPTIONS] SERVER_URL PASSWORD

  Get and save Trilium ETAPI token

Options:
  -e, --env-file FILE  Path to .env file to save token
  --global             Save token to global ~/.trilium-py/.env file
  --help               Show this message and exit.

❯ uv run get_etapi_token.py http://localhost:8080 tttt
Connecting to Trilium server at http://localhost:8080...
╭────────────────── Trilium Authentication Successful ──────────────────╮
│ ✓ Successfully obtained token from Trilium 0.92.3-beta                │
│                                                                       │
│ Token saved to: /var/home/me/dev/trilium-py/examples/uv/.env          │
│                                                                       │
│ You can now use Trilium-py tools that require Trilium authentication. │
╰───────────────────────────────────────────────────────────────────────╯
```

### Show Trilium App Info

Implementation of README.md#-basic-etapi-usage

```shell
❯ uv run ea_app_info.py --help
Usage: ea_app_info.py [OPTIONS]

  Display Trilium server information

Options:
  -e, --env-file FILE  Path to .env file with token
  --global             Use global ~/.trilium-py/.env file
  --help               Show this message and exit.

❯ uv run ea_app_info.py 
╭─────────────────────── Connection Information ───────────────────────╮
│ Configuration Source: /var/home/matt/dev/trilium-py/examples/uv/.env │
│ Server URL: http://localhost:8080                                    │
│ Token: ********...mqo=                                               │
╰──────────────────────────────────────────────────────────────────────╯
Connecting to Trilium server...
                     Trilium Server Information                      
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property               ┃ Value                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ appVersion             │ 0.92.3-beta                              │
│ dbVersion              │ 228                                      │
│ nodeVersion            │ v23.9.0                                  │
│ syncVersion            │ 34                                       │
│ buildDate              │ 2025-03-07T21:59:10Z                     │
│ buildRevision          │ e76601cd21c0fe0d50745affe582f61bcd752fec │
│ dataDirectory          │ /var/home/matt/dev/trilium/data          │
│ clipperProtocolVersion │ 1.0                                      │
│ utcDateTime            │ 2025-03-14T03:01:34.341Z                 │
└────────────────────────┴──────────────────────────────────────────┘
```
