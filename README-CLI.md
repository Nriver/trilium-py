# Trilium-py CLI

An experimental command line interface wrapper for trilium-py, a python library for Trilium Notes.

I prototyped this as a standalone package first, [trilium-py-cli][tpy]. That seemed promising, so I created this branch in my trilium-py fork to see if it could be merged into the main repository.

uv managed install works, regular pip install doesn't. I don't know why.

I use `uv` from Astral.sh to manage python environments and packages, which uses the newer `pyproject.toml` format, while trilium-py uses the older `setup.py` format. I don't understand setup.py well, and I haven't been able to get the cli script installed using the standard `pip install .` method with setup.py


## User Installation

```bash
uv tool install git+https://github.com/maphew/trilium-py/tree/CLI
```

This will make the `tpy` command available in your shell. 

(On Windows or systems where git is not in PATH, download the repo archive, unpack it, and run `uv tool install .` from the root directory of the repo.)

## Developer Installation

```bash
git clone https://github.com/maphew/trilium-py.git
cd trilium-py
uv sync
source .venv/bin/activate
```

## Usage

```
❯ tpy
Usage: tpy [OPTIONS] COMMAND [ARGS]...

  Trilium-py CLI - Command line interface for trilium-py.

Options:
  --version        Show the version and exit.
  --env-file FILE  Path to .env file to load
  --debug          Enable debug output
  --help           Show this message and exit.

Commands:
  config  Manage tpy-cli configuration.
  info    Display information about the Trilium server.
  notes   Manage Trilium notes.
```

Get and save token to .env file:

```
tpy config get-token
```

```
❯ tpy config get-token --server https://www.example.org
Enter your Trilium password: 
Connecting to Trilium server at https://www.example.org...
╭─────────────────── Server Information ───────────────────╮
│ Trilium: 0.93.0                                          │
│ Build Date: 2025-04-17T19:25:28Z                         │
│ Build Revision: 8211fd36af3149c60014737eee2407abb5516974 │
╰──────────────────────────────────────────────────────────╯
╭───── Authentication Token ─────╮
│ Server: https://www.example.org│
│ Token: Oo919mXP...TdI=         │
╰────────────────────────────────╯

✓ Token saved to: .env

✓ Successfully connected to Trilium v0.93.0
```

Show configured server info

```
❯ tpy info server
```

```
Fetching server information...
╭──────────────────── Trilium Server Information ────────────────────╮
│ Server                  : https://www.example.org                  │
│ Token                   : OYE=..............nLNz                   │
│ App Version             : 0.93.0                                   │
│ Db Version              : 229                                      │
│ Node Version            : v22.14.0                                 │
│ Sync Version            : 34                                       │
│ Build Date              : 2025-04-17T19:25:28Z                     │
│ Build Revision          : 8211fd36af3149c60014737eee2407abb5516974 │
│ Data Directory          : /home/node/trilium-data                  │
│ Clipper Protocol Version: 1.0                                      │
│ Utc Date Time           : 2025-04-27T01:06:03.891Z                 │
╰────────────────────────────────────────────────────────────────────╯
```


[tpy]: https://github.com/maphew/trilium-py-cli