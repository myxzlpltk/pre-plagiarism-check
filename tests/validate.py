import os
from pprint import pprint

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import string
import numpy as np
import easyocr
import fitz
import collections
import hashlib
import pymongo
import time
from bson.objectid import ObjectId
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from fontTools.ttLib import TTFont


# Define reusable function
def char_in_font(unicode_char, font):
    for cmap in font['cmap'].tables:
        if cmap.isUnicode():
            if ord(unicode_char) in cmap.cmap:
                return True
    return False


def draw_char(s, typeface, size):
    # Set canvas size
    width, height = (int(size * 1.5) * 3, int(size * 1.5))
    # Set font
    draw_font = ImageFont.truetype(typeface, size)
    # Make empty image
    canvas = Image.new('RGB', (width, height), color='#B7C274')
    # Draw text to image
    draw = ImageDraw.Draw(canvas)
    _, _, w, h = draw_font.getbbox(s)
    draw.text(((width - w) / 2, (height - h) / 2), s, fill='#483d8b', font=draw_font)

    return np.asarray(canvas)


# Define mongoDB connection
print("Initialize MongoDB", end=' ')
mongo = pymongo.MongoClient('mongodb://root:root@localhost:27017/?authMechanism=DEFAULT')
db = mongo['skripsi']
fonts = db['fonts']
documents = db['documents']
print("SUCCESS")

# Define system variable
print("Initialize OCR", end=' ')
reader = easyocr.Reader([], gpu=True)  # OCR tool
chars = list(string.digits + string.ascii_letters)  # Get list possible character
print("SUCCESS")

# Fetch data
docs = list(documents.find({}))

for doc in tqdm(docs):
    # Fetch font data
    font_doc = fonts.find_one({'_id': ObjectId(doc['font'])})
    # Read input
    filename = "../outputs/" + doc["document"]

    # Open file
    start = time.time()
    pdf = fitz.open(filename)
    result = {}

    # Get all fonts across document
    detected_fonts = list({el for i in range(pdf.page_count) for el in pdf.get_page_fonts(i)})
    embedded_fonts = set()

    # Loop through fonts
    for font in detected_fonts:
        # Extract font
        name, ext, _, content = pdf.extract_font(font[0])
        name = name.split('+')[-1]

        # If font is embedded
        if ext != 'n/a' and name.startswith("TimesNewRomanFake"):
            # Write fonts
            fontfile = hashlib.md5(name.encode('utf-8')).hexdigest() + '.' + ext  # Generate fontfile
            f = open('../fonts/' + fontfile, 'wb')  # Open file
            f.write(content)  # Write content
            f.close()  # Close file

            # Append to array
            embedded_fonts.add((fontfile, name))

    embedded_fonts = list(embedded_fonts)
    # Setup problematic font map
    hashmap = {}
    setmap = set(font_doc['swaps'].keys())
    y_true = []
    y_pred = []

    # Loop through embedded fonts
    for fontfile, fontname in embedded_fonts:
        font = TTFont('../fonts/' + fontfile)
        hashmap[fontname] = set()

        # Loop through characters
        for char in chars:
            # If character detected
            if char_in_font(char, font):
                # Render characters
                img = draw_char(char * 4, '../fonts/' + fontfile, 250)
                # Detect characters with OCR
                result = reader.readtext(img, allowlist=chars)

                if len(result) == 0:
                    raise Exception("OCR failed to detect character", char, "in font", fontname)

                # Calculate most character appear
                most_char, total = collections.Counter(result[0][1]).most_common(1)[0]
                # If char not the same
                if most_char.lower() == char.lower():
                    if char not in setmap or font_doc['swaps'][char] == char:
                        # True Negative
                        y_true.append('Real')
                        y_pred.append('Real')
                    else:
                        # False Negative
                        y_true.append('Fake')
                        y_pred.append('Real')
                else:
                    # Add to hash map
                    hashmap[fontname].add(char)

                    # Print char
                    if char not in setmap:
                        # False Positive
                        y_true.append('Real')
                        y_pred.append('Fake')
                    else:
                        # True Positive
                        y_true.append('Fake')
                        y_pred.append('Fake')

            # Char in font not embedded
            elif char not in setmap or font_doc['swaps'][char] == char:
                # True Negative
                y_true.append('Real')
                y_pred.append('Real')
            elif char in setmap:
                hashmap[fontname].add(char)
                # True Positive
                y_true.append('Fake')
                y_pred.append('Fake')

        if len(hashmap[fontname]) == 0:
            del hashmap[fontname]

    # Close resource
    pdf.close()
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=["Fake", "Real"]).ravel()
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, pos_label="Fake", zero_division=1),
        'recall': recall_score(y_true, y_pred, pos_label="Fake", zero_division=1),
        'f1': f1_score(y_true, y_pred, pos_label="Fake", zero_division=1),
        'confusion_matrix': {
            'tp': int(tp),
            'tn': int(tn),
            'fp': int(fp),
            'fn': int(fn),
        },
        'y_true': dict(zip(chars, y_true)),
        'y_pred': dict(zip(chars, y_pred)),
        'time': time.time() - start,
    }
    documents.update_one({'_id': doc["_id"]}, {"$set": {"metrics": dict(metrics)}})
