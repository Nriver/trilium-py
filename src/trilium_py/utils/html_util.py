import locale
import re
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# Disable MarkupResemblesLocatorWarning globally
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)

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


def add_internal_links(
    html_content, keyword_note_id_list, current_note_id=None, exclude_headings=True
):
    """
    Adds internal links to the HTML content by replacing keywords with anchor tags.

    Args:
        html_content (str): The HTML content to process.
        keyword_note_id_list (list of tuples): List of (keyword, note_id).
        exclude_headings (bool): Whether to exclude heading tags from processing.
        current_note_id (str): The ID of the current note to prevent self-referencing.

    Returns:
        tuple: A tuple containing the updated HTML content and a boolean indicating if replacements were made.
    """
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")
    replaced = False  # Flag to check if any replacement happens

    # Precompile the keywords and links into a dictionary, excluding self-referencing notes
    keyword_to_link = {
        keyword: f'<a class="reference-link" href="#root/{note_id}">{keyword}</a>'
        for keyword, note_id in keyword_note_id_list
        if note_id != current_note_id  # Exclude the current note's ID
    }

    # Create a regex pattern to match any keyword
    if not keyword_to_link:
        return str(soup), replaced  # No keywords to process

    keyword_pattern = re.compile(
        r'\b(' + '|'.join(re.escape(k) for k in keyword_to_link.keys()) + r')\b'
    )

    # Tags to exclude from replacement
    exclude_tags = ['a']
    if exclude_headings:
        exclude_tags.extend(['h2', 'h3', 'h4', 'h5', 'h6'])

    # Traverse all text nodes once
    for text_node in soup.find_all(string=True):
        # Skip nodes inside tags that shouldn't contain links
        if text_node.parent.name in exclude_tags:
            continue

        # Replace keywords in the text
        def replace_keyword(match):
            replaced_keyword = match.group(0)
            return keyword_to_link[replaced_keyword]

        new_text = keyword_pattern.sub(replace_keyword, text_node)
        if new_text != text_node:  # If the text has actually changed
            text_node.replace_with(BeautifulSoup(new_text, "html.parser"))
            replaced = True  # Mark that replacement has occurred

    return str(soup), replaced


if __name__ == '__main__':
    # Example input HTML content
    html_content = """
    <p> Only root can see this. <a href="#root/python_programming">Python</a> is a widely used programming language. Python has a simple syntax and supports multiple paradigms.</p>
    """
    # List of keywords and their corresponding note ids
    data = [
        ["Python", "python_programming"],
        ["programming language", "programming_language"],
        ["simple syntax", "simple_syntax"],
        ["root", "root"],
    ]
    updated_html, updated = add_internal_links(html_content, data)
    print(f'content updated {updated}')
    if updated:
        # Output the modified HTML
        print(updated_html)
