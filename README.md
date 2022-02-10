# trilium-py

Python client for ETAPI of Trilium Note.

# Installation

```
python3 -m pip install trilium-py --user
```

# Usage

```
from trilium_py.client import ETAPI

server_url = 'YOUR_HOST'
token = 'YOUR_TOKEN'
ea = ETAPI(server_url, token)
```

# Develop

```
python -m pip install --user -e .
```

# Original OpenAPI Documentation

The original OpenAPI document is [here](https://github.com/zadam/trilium/blob/master/src/etapi/etapi.openapi.yaml). You
can open it with [swagger editor](https://editor.swagger.io/).
