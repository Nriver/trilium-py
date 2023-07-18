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
