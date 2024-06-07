import os


def replace_extension(filename: str, new_extension: str) -> str:
    """
    Replaces the extension of a given filename with a new extension.

    :param filename: Original filename
    :param new_extension: New extension to replace the old one (e.g., '.webp')
    :return: Filename with the new extension
    """
    if not new_extension.startswith('.'):
        new_extension = '.' + new_extension

    base = os.path.splitext(filename)[0]
    return base + new_extension
