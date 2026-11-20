# 역할: 사진 형식·크기를 검사하고 회전을 보정해 SAM 입력용 JPEG로 축소합니다.
from io import BytesIO
import math

from PIL import Image, ImageOps

MAX_SOURCE_PIXELS = 64_000_000
MAX_SAM_PIXELS = 16_000_000


def prepare_photo(data):
    with Image.open(BytesIO(data)) as source:
        if source.format not in {'JPEG', 'PNG'} or source.width * source.height > MAX_SOURCE_PIXELS:
            raise ValueError('Expected JPEG/PNG up to 64 megapixels')
        source.verify()
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        pixels = image.width * image.height
        if pixels > MAX_SAM_PIXELS:
            scale = math.sqrt(MAX_SAM_PIXELS / pixels)
            image.thumbnail((max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                            Image.Resampling.LANCZOS)
        if image.mode in {'RGBA', 'LA'} or 'transparency' in image.info:
            rgba = image.convert('RGBA')
            background = Image.new('RGB', image.size, 'white')
            background.paste(rgba, mask=rgba.getchannel('A'))
            image = background
        else:
            image = image.convert('RGB')
        output = BytesIO()
        image.save(output, format='JPEG', quality=95)
        return output.getvalue()
