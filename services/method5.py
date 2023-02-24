import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import collections
import easyocr
import fitz
import hashlib
import numpy as np
import string
import time
import redis
import json
from minio import Minio
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

# Define system variable
print("Loading OCR model...", end=' ')
reader = easyocr.Reader([], gpu=True)  # OCR tool
chars = list(string.digits + string.ascii_letters)  # Get list possible character
print("[Completed]")

client = Minio(
    endpoint="host.docker.internal:9000",
    secure=False,
    access_key="p8bBrkOUX3JXTDus",
    secret_key="rimJyqs5zNrNhj55nmU6wEVga6SUUkRD",
)
print("Minio connected,", "bucket found" if client.bucket_exists("documents") else "bucket not found")


# Define reusable function
def char_in_font(unicode_char, font):
    if 'cmap' not in font.keys():
        return False

    for cmap in font['cmap'].tables:
        if cmap.isUnicode():
            if ord(unicode_char) in cmap.cmap:
                return True
    return False


def draw_char(char, typeface, size):
    # Set canvas size
    W, H = (int(size * 1.5) * 3, size)
    # Set font
    font = ImageFont.truetype(typeface, size)
    # Make empty image
    img = Image.new('RGB', (W, H), color='#969696')
    # Draw text to image
    draw = ImageDraw.Draw(img)
    _, _, w, h = font.getbbox(char)
    draw.text(((W - w) / 2, (H - h) / 2 - size / 8), char, fill='#696969', font=font)

    return np.asarray(img)


def generate_text(_char):
    return _char * 4


def compute(pdfname):
    # Download file from Minio
    pdfpath = "tmps/" + pdfname
    client.fget_object("documents", pdfname, pdfpath)

    # Open file
    pdf = fitz.open(pdfpath)
    data = {
        'fonts': {},
        'pages': [],
    }

    # Get all fonts across document
    fonts = list({el for i in range(pdf.page_count) for el in pdf.get_page_fonts(i)})
    embedded_fonts = []

    # Loop through fonts
    for font in fonts:
        # Extract font
        name, ext, _, content = pdf.extract_font(font[0])
        name = name.split('+')[-1]

        # If font is embedded
        if ext == 'ttf':
            # Write fonts
            filename = hashlib.md5(name.encode('utf-8')).hexdigest() + '.' + ext  # Generate filename
            f = open('tmps/' + filename, 'wb')  # Open file
            f.write(content)  # Write content
            f.close()  # Close file

            # Append to array
            embedded_fonts.append((filename, name))

    # Setup problematic font map
    hashmap = {}

    # Loop through embedded fonts
    for filename, fontname in embedded_fonts:
        font = TTFont('tmps/' + filename)
        hashmap[fontname] = {}

        # Loop through characters
        for char in chars:
            if not char_in_font(char, font):
                continue

            # Render characters
            img = draw_char(generate_text(char), 'tmps/' + filename, 250)
            # Detect characters with OCR
            result = reader.readtext(img, allowlist=chars)

            # If character detected
            if len(result) > 0:
                # Calculate most character appear
                most_char, total = collections.Counter(result[0][1]).most_common(1)[0]
                # If char not the same
                if most_char.lower() != char.lower():
                    # Add to hash map
                    hashmap[fontname][char] = True

        if len(hashmap[fontname].keys()) == 0:
            del hashmap[fontname]

    # Set hashmap to data
    data['fonts'] = hashmap

    # Loop through pages
    for page in pdf:
        page_width, page_height = page.mediabox_size  # Get page width and height
        result = page.get_text('rawdict')  # read page text as a dictionary

        items = []
        for block in result['blocks']:  # iterate through the text blocks
            if 'lines' not in block.keys():
                continue

            for line in block['lines']:  # iterate through the text lines
                for span in line['spans']:  # iterate through the text spans
                    for char in span['chars']:  # iterate through text chars
                        if span['font'] in hashmap and char['c'] in hashmap[span['font']]:
                            items.append({
                                'font': span['font'],
                                'char': char['c'],
                                'rect': {
                                    'x1': char['bbox'][0],
                                    'y1': char['bbox'][1],
                                    'x2': char['bbox'][2],
                                    'y2': char['bbox'][3]
                                }
                            })

        if len(items) > 0:
            data['pages'].append({
                'page': page.number,
                'width': page_width,
                'height': page_height,
                'items': items
            })

    # Close resource
    pdf.close()

    # Delete file
    os.remove(pdfpath)
    for filename, fontname in embedded_fonts:
        os.remove('tmps/' + filename)

    return {
        'filename': pdfname,
        'data': data
    }


# Redis
r = redis.StrictRedis(host='host.docker.internal', port=6379, db=0)
p = r.pubsub()
p.subscribe('documents')
print('Redis connected')

while True:
    message = p.get_message()
    if message and message['type'] == 'message':
        start = time.time()
        filename = message['data'].decode('utf-8')
        print('Working on', filename, end=' ')

        try:
            result = compute(filename)
            r.publish('result', json.dumps(result))
            end = time.time()
            print('[', end - start, 'seconds]')
        except Exception as e:
            print('[Error]')
            print(e)
            r.publish('error', filename)

    time.sleep(1)
