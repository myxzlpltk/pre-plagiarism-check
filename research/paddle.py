import numpy as np
import collections
import string
from paddleocr import PaddleOCR
from tqdm import tqdm
from PIL import Image, ImageColor, ImageDraw, ImageFont


def draw_square_char(char, font, size=128, fontsize=128):
    # Set canvas size
    W, H = size, size
    # Set font
    font = ImageFont.truetype('../inputs/times.ttf', fontsize)
    # Make empty image
    img = Image.new('RGB', (W, H), color='white')
    # Draw text to image
    draw = ImageDraw.Draw(img)
    _, _, w, h = font.getbbox(char)
    draw.text(((W - w) / 2, ((H - h) / 2) - size / 10), char, 0, font=font)

    return np.asarray(img)


print("Loading OCR...")
ocr = PaddleOCR(lang='en', use_gpu=False)
print("OCR loaded!")

# Get list possible character
chars = list(string.digits + string.ascii_letters)

# Setup problematic font map
hashmap = dict()

for char in tqdm(chars):
    img = draw_square_char(char, '../inputs/times.ttf')
    result = ocr.ocr(img, cls=True)

    if len(result) > 0:
        most_char, total = collections.Counter(result[0][1][0]).most_common(1)[0]
        if most_char != char:
            # Add to hash map
            hashmap[char] = most_char
    else:
        raise Exception(f"{char} not detected")

print(hashmap)
