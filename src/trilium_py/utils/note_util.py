import re


def beautify_content(content):
    """
    beautify note content, add new lines and remove redundant lines

    :param content:
    :return:
    """

    # add new line before headings
    for heading_level in range(2, 6):
        pat = f'</p><h{heading_level}>'
        res = re.finditer(pat, content)
        if res:
            for x in reversed(list(res)):
                pos = x.span()[0]
                key = '<p>&nbsp;'
                back_pos = pos - len(key)
                if back_pos < 0:
                    continue
                # print(content[back_pos:pos])
                if content[back_pos:pos] != key:
                    content = content[:pos] + '</p><p>&nbsp;' + content[pos:]

    # remove redundant new line in code block
    content = content.replace('\n</code></pre>', '</code></pre>')

    # add new line to image
    content = content.replace(' <img', '/p><p><img')

    return content
