import re

import minify_html
from bs4 import BeautifulSoup

from .html_util import sort_h_tags_with_hierarchy


def beautify_content(content):
    """
    Beautify note content, add new lines and remove redundant lines

    :param content:
    :return:
    """

    # minify html, it's slightly different from ckeditor's minify, but works fine.
    content = minify_html.minify(content, keep_closing_tags=True)

    # fix redundant empty p tag
    # logger.info('<p> <p></p><h2>' in content)
    for heading_level in range(2, 6):
        content = content.replace(f'<p> </p><p></p><h{heading_level}>', f'<h{heading_level}>')
        content = content.replace(f'<p> <p></p><h{heading_level}>', f'<h{heading_level}>')
        content = content.replace(f'<p> <h{heading_level}>', f'<h{heading_level}>')

    # logger.info(content)

    # add new line before headings
    for heading_level in range(2, 6):
        pat = f'<h{heading_level}>'
        res = re.finditer(pat, content)
        if res:
            for x in reversed(list(res)):
                pos = x.span()[0]
                key1 = '<p>&nbsp;</p>'
                back_pos1 = pos - len(key1)
                key2 = '<p></p>'
                back_pos2 = pos - len(key2)

                # logger.info(f'pos1 {content[back_pos1:pos]}')
                # logger.info(f'pos2 {content[back_pos2:pos]}')

                if not (
                    (back_pos1 >= 0 and content[back_pos1:pos] == key1)
                    or (back_pos2 >= 0 and content[back_pos2:pos] == key2)
                ):
                    content = content[:pos] + '<p></p>' + content[pos:]

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
            content_after_h = html_content[html_content.find(str(h_tag)) : next_h_index]
        else:
            # If there is no next h tag, extract the h tag and all content after it
            content_after_h = html_content[html_content.find(str(h_tag)) :]

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
