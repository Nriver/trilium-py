import re
import html
from bs4 import BeautifulSoup

from .html_util import sort_h_tags_with_hierarchy


def beautify_content(content):
    """
    Beautify note content  (excluding <pre> blocks except trimming inside <code>):
    - Normalize heading levels so the highest becomes h2
    - Clean redundant empty lines
    - Add new line before headings (idempotent, no duplication)

    :param content: The HTML content to be beautified.
    :return: Beautified HTML content.
    """

    # Extract <pre> blocks and store them in a dictionary
    pre_blocks = {}
    def _extract_pre(m):
        block = m.group(0)
        key = f"__PRE_BLOCK_{len(pre_blocks)}__"

        # trim empty lines in <pre><code>
        block = re.sub(
            r'(<pre.*?><code.*?>)\n*([\s\S]*?)\n*(</code></pre>)',
            lambda mm: mm.group(1) + mm.group(2) + mm.group(3),
            block
        )

        pre_blocks[key] = block
        return key
    # Beautify content
    content = re.sub(r"<pre.*?>.*?</pre>", _extract_pre, content, flags=re.DOTALL)


    # Use html module to unescape HTML entities (like &nbsp;)
    content = html.unescape(content)

    # Normalize heading levels
    headings = re.findall(r'<h([2-6])', content)
    if headings:
        min_heading = min(int(h) for h in headings)
        if min_heading > 2:
            shift = min_heading - 2

            def replace_heading(m):
                level = int(m.group(2))
                new_level = max(2, level - shift)
                return f"{m.group(1)}h{new_level}{m.group(3)}"

            content = re.sub(r'(<\/?)h([2-6])(>)', replace_heading, content)

    # Remove redundant <p> before headings
    for heading_level in range(2, 6):
        content = re.sub(
            fr'(?:<p>\s*</p>\s*)+(<h{heading_level}>)',
            r'\1',
            content
        )

    # Ensure one empty <p></p> before headings (but no duplicates)
    for heading_level in range(2, 6):
        content = re.sub(
            fr'(?<!<p></p>)(<h{heading_level}>)',
            r'<p></p>\1',
            content
        )

    # remove redundant new line in code block
    content = content.replace('\n</code></pre>', '</code></pre>')

    # add new line to image
    content = content.replace(' <img', '</p><p><img')

    # remove redundant empty line
    content = content.replace('<p> </p><p>&nbsp;</p>', '<p>&nbsp;</p>')
    content = content.replace('<p>&nbsp;</p><p>&nbsp;</p>', '<p>&nbsp;</p>')

    # remove redundant beginning
    content = re.sub('^<p></p><h2>', '<h2>', content)
    content = re.sub('^<div><div><p></p><h2>', '<h2>', content)

    # Assemble pre blocks
    for key, block in pre_blocks.items():
        content = content.replace(key, block)

    return content


def sort_note_by_headings(html_content, locale_str='zh_CN.UTF-8'):
    """
    Sorts note content order by the name of headings, following the rules of the input language.

    :param html_content: The HTML content to be sorted.
    :param locale_str: Should be something like 'zh_CN.UTF-8', which is the Chinese Pinyin order.
    :return: The sorted HTML content as a string.
    """

    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all h tags
    h_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

    # Split the content by h tags
    result_list = []
    for i, h_tag in enumerate(h_tags):
        current_h = str(h_tag)

        # The next h tag (if it exists)
        next_h_tag = h_tags[i + 1] if i + 1 < len(h_tags) else None

        # The position of the next h tag in the HTML content
        next_h_index = html_content.find(str(next_h_tag)) if next_h_tag else None

        # Extract the h tag and the content after it
        if next_h_index:
            content_after_h = html_content[html_content.find(str(h_tag)): next_h_index]
        else:
            # If there is no next h tag, extract the h tag and all content after it
            content_after_h = html_content[html_content.find(str(h_tag)):]

        # result_list.append([current_h, content_after_h])
        result_list.append(content_after_h)

    # Extract the content before the first h tag
    first_h_index = html_content.find(str(h_tags[0]))
    content_before_first_h = html_content[:first_h_index]

    # Sort the h tags
    sorted_html = sort_h_tags_with_hierarchy(result_list, locale_str)

    # Assemble the parts
    sorted_html_string = content_before_first_h + sorted_html

    return sorted_html_string


def preprocess_note_title_list(data):
    """
    Optimized version of the function to preprocess the list of [title, note_id].
    Cleans titles, removes duplicates and previous matching entries, and sorts by title length.
    """

    def clean_title(title):
        return title.strip()

    # Use an ordered dictionary to maintain insertion order while ensuring uniqueness
    from collections import OrderedDict

    cleaned_data = OrderedDict()

    # Traverse the data and process each title
    for title, note_id in data:
        cleaned_title = clean_title(title)
        if cleaned_title in cleaned_data:
            # If the title already exists, remove it
            del cleaned_data[cleaned_title]
        else:
            # Otherwise, add it to the dictionary
            cleaned_data[cleaned_title] = note_id

    # Convert the dictionary back to a list and sort by title length (descending)
    return sorted(cleaned_data.items(), key=lambda x: len(x[0]), reverse=True)
