import re

import minify_html


def beautify_content(content):
    """
    beautify note content, add new lines and remove redundant lines

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
