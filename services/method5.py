import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import collections
import easyocr
import fitz
import hashlib
import numpy as np
import pymongo
import string
import sys
import time
from pprint import pprint
from PIL import Image, ImageDraw, ImageFont


# Define reusable function
def draw_char(s, typeface, size):
    # Set canvas size
    width, height = (int(size * 1.5) * 3, int(size * 1.5))
    # Set font
    draw_font = ImageFont.truetype(typeface, size)
    # Make empty image
    canvas = Image.new('L', (width, height), color='white')
    # Draw text to image
    draw = ImageDraw.Draw(canvas)
    _, _, w, h = draw_font.getbbox(s)
    draw.text(((width - w) / 2, (height - h) / 2), s, 0, font=draw_font)

    return np.asarray(canvas)


# Define mongoDB connection
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['skripsi']
col = db['method5']

# Define system variable
reader = easyocr.Reader(['id', 'en'], gpu=True)  # OCR tool
chars = list(string.ascii_letters)  # Get list possible character

# Read input
filename = sys.argv[1]
# Delete document if exists
col.delete_many({'filename': filename})
# Start timer
start = time.time()

# Open file
pdf = fitz.open(filename)
data = {
    'filename': filename,
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
        f = open('fonts/' + filename, 'wb')  # Open file
        f.write(content)  # Write content
        f.close()  # Close file

        # Append to array
        embedded_fonts.append((filename, name))

# Setup problematic font map
hashmap = {}

# Loop through embedded fonts
for filename, fontname in embedded_fonts:
    hashmap[fontname] = {}
    # Loop through characters
    for char in chars:
        # Render characters
        img = draw_char(char * 5, 'fonts/' + filename, 250)
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
    result = page.get_text("rawdict")  # read page text as a dictionary

    items = []
    for block in result["blocks"]:  # iterate through the text blocks
        for line in block["lines"]:  # iterate through the text lines
            for span in line["spans"]:  # iterate through the text spans
                for char in span["chars"]:  # iterate through text chars
                    if span['font'] in hashmap and char['c'] in hashmap[span['font']]:
                        items.append({
                            'x0': char['bbox'][0],
                            'y0': char['bbox'][1],
                            'x1': char['bbox'][2],
                            'y1': char['bbox'][3]
                        })

    if len(items) > 0:
        data['pages'].append({
            'page': page.number,
            'page_width': page_width,
            'page_height': page_height,
            'items': items
        })

# Close resource
pdf.close()
# Stop timer
end = time.time()
# Print execution time
print('Execution time: ' + str(end - start) + ' seconds')
# Save data to mongo
col.insert_one(data)
