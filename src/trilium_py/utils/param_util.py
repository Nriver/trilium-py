import json


def format_query_string(params):
    """

    convert
    {"search": "root", "fastSearch": False}
    to
    {"search": "root", "fastSearch": "false"}

    cause trilium takes "false" and "true" instead of "False" and "True"
    :param params:
    :return:
    """
    json_str = (
        str(json.dumps(params, ensure_ascii=False))
        .replace(': false', ': "false"')
        .replace(': true', ': "true"')
    )
    params = json.loads(json_str)
    return params


def clean_param(params):
    clean_list = []
    for k, v in params.items():
        if not v:
            clean_list.append(k)
    for x in clean_list:
        params.pop(x)
    return params
