import locale
import re

from bs4 import BeautifulSoup

TAG_LEVELS = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4, 'h5': 5, 'h6': 6}


def sort_h_tags_with_hierarchy(data, locale_str='zh_CN.UTF-8'):
    """
    sort HTML content based on the names of its headings (h1, h2, h3, etc.) in hierarchical order
    following the rules of the input language (specified by locale_str)

    :param data:
    :param locale_str:
    :return:
    """

    def add_node(parent, node):
        if 'children' not in parent:
            parent['children'] = []
        parent['children'].append(node)

    def sort_node_by_name(node, locale_str):
        # sort with respect to local language
        locale.setlocale(locale.LC_COLLATE, locale_str)
        if 'children' in node:
            node['children'] = sorted(node['children'], key=lambda x: locale.strxfrm(x['name']))
            for child in node['children']:
                sort_node_by_name(child, locale_str)

    def dfs_concat_data(node):
        result = ""
        if 'data' in node:
            result += node['data']
        if 'children' in node:
            for child in node['children']:
                result += dfs_concat_data(child)
        return result

    def convert_to_tree(data):
        root = {'name': 'root', 'children': []}
        current_tags = {1: root}
        for item in data:
            soup = BeautifulSoup(item, 'html.parser')
            tag_name = soup.find(re.compile(r'^h[1-6]$'))

            if not tag_name:
                continue

            tag_level = TAG_LEVELS[tag_name.name]
            node = {'name': tag_name.text, 'data': item, 'children': []}

            parent_tag_level = tag_level - 1
            parent = current_tags.get(parent_tag_level)
            if not parent:
                # If parent doesn't exist, add the node to the root
                add_node(root, node)
            else:
                add_node(parent, node)

            # Update current_tags with the new node
            current_tags[tag_level] = node

        return root

    # Convert data to tree
    tree = convert_to_tree(data)

    # Sort nodes by name
    sort_node_by_name(tree, locale_str)

    # Concatenate data in a depth-first search manner
    html_string = dfs_concat_data(tree)
    return html_string
