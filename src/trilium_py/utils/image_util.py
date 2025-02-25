from io import BytesIO

from PIL import Image, ImageOps


def compress_image_bytes(image_bytes, extension, quality=90):
    """
    Compress image binary data

    Args:
    image_bytes: Binary data of the image

    Returns:
    Compressed binary data of the image
    """
    try:
        with BytesIO(image_bytes) as img_buffer:
            with Image.open(img_buffer) as img:
                # Correct image orientation based on EXIF data, if available
                # This ensures the image is properly oriented after conversion
                img = ImageOps.exif_transpose(img)

                output_buffer = BytesIO()
                # PIL/pillow can only recognize JPEG, it does not know JPG...
                if extension == 'jpg':
                    extension = 'jpeg'
                img.save(output_buffer, format=extension, optimize=True, quality=quality)
                compressed_image_bytes = output_buffer.getvalue()
                return compressed_image_bytes
    except Exception as e:
        print("Error compressing image binary data:", str(e))
        return None


def get_extension_from_image_mime(mime):
    """
    reverse process of
    https://github.com/zadam/trilium/blob/25b49e1ca28323f1a468968c8d918dcd8330d5c7/src/services/image.js#L60
    :param mime:
    :return:
    """
    mime = mime.lower()

    if mime == 'image/svg+xml':
        return 'svg'
    else:
        return mime.split('/')[1]


if __name__ == "__main__":
    image_file = '/home/nate/data/1/1.jpg'
    output_file = '/home/nate/data/1/1.webp'
    with open(image_file, 'rb') as f:
        image_bytes = f.read()
    compressed_image_bytes = compress_image_bytes(image_bytes, 'webp', 90)
    with open(output_file, 'wb') as f:
        f.write(compressed_image_bytes)
