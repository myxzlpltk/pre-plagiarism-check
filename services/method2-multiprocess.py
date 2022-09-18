import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import easyocr
import fitz
import multiprocessing
import numpy as np
import pymongo
import re
import sys
import time
from PIL import Image, ImageChops, ImageOps

# Define mongoDB connection
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['skripsi']
col = db['documents']

# Define system variables
pattern = r'^Gambar[ ]?\d+[.]?[\d]*'
reader = easyocr.Reader(['id', 'en'], gpu=True)

# Global thread local
session = None


# Set session
def set_global_session(filename):
    global session
    if not session:
        session = fitz.open(filename)


# Close session
def close_session():
    global session
    if session:
        session.close()
        session = None


# Process image
def process_image(vector):
    # Split vector
    index, xref = vector

    # Get image data
    pix = fitz.Pixmap(session, xref)  # Get pixmap from image xref
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)  # Convert pixmap to PIL image
    image_rect = session[index].get_image_rects(xref)[0]  # Get image rect position

    # Search for image caption
    clip_area = fitz.Rect(0, image_rect.y1, session[index].mediabox_size[0], image_rect.y1 + 50)  # Define clip area
    text = session[index].get_textbox(clip_area)  # Get text from clip area

    # If image caption is not found, skip to next image
    if text is None or len(text) == 0 or not re.match(pattern, text, re.IGNORECASE | re.MULTILINE):
        # Preprocess image
        img = ImageOps.grayscale(img)  # Convert image to grayscale

        # Trim image
        bg = Image.new(img.mode, img.size, 255)  # Create background
        diff = ImageChops.difference(img, bg)  # Get difference between image and background
        diff = ImageChops.add(diff, diff, 2.0, -100)  # Add difference to image
        bbox = diff.getbbox()  # Get bounding box
        if bbox:
            img = img.crop(bbox)  # Crop image if bounding box is found

        # Expand image
        img = ImageOps.expand(img, border=10, fill='white')  # Expand image by 10 pixels

        # Find the bounding box of those pixels
        result = reader.readtext(np.asarray(img))  # Read text from image using OCR

        # Calculate area
        total_area = 0
        for item in result:
            top_left = tuple(item[0][0])  # Get top left coordinate
            bottom_right = tuple(item[0][2])  # Get bottom right coordinate
            total_area += (bottom_right[0] - top_left[0]) * (bottom_right[1] - top_left[1])  # Calculate area

        # Calculate percentage text area
        percentage = total_area / (img.width * img.height)

        if percentage > 0.25:
            return {
                'xref': xref,
                'rect': {
                    'x0': image_rect.x0,
                    'y0': image_rect.y0,
                    'x1': image_rect.x1,
                    'y1': image_rect.y1
                },
            }

    return None


# Start concurrent process
def process_all_images(filename, vectors):
    with multiprocessing.Pool(processes=8, initializer=set_global_session, initargs=[filename]) as pool:
        result = pool.map(process_image, vectors)
        result = [x for x in result if x is not None]
        print(result)
        return result


# Main process
def main():
    # Read input
    filename = sys.argv[1]
    print('Processing file: ' + filename)
    # Delete document if exists
    col.delete_many({'filename': filename})
    try:
        # Start timer
        start = time.time()
        # Open PDF file
        pdf = fitz.open(filename)
        vectors = []

        # Loop through all pages
        for index, page in enumerate(pdf):
            images = page.get_images()  # Get page images

            # Loop through all images
            for image in images:
                vectors.append((index, image[0]))

        # Close resource
        pdf.close()
        # Start concurrent process
        process_all_images(filename, vectors)
        # Stop timer
        end = time.time()
        # Print execution time
        print('Execution time: ' + str(end - start) + ' seconds')

    except RuntimeError as err:
        print('Runtime Error', err)

    except Exception as err:
        print('Error', err)


if __name__ == '__main__':
    main()
