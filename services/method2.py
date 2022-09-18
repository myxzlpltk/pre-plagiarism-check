import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import easyocr
import fitz
import numpy as np
import pymongo
import re
import sys
import time
from PIL import Image, ImageChops, ImageOps

# Define mongoDB connection
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['skripsi']
col = db['method2']

# Define system variables
pattern = r'^Gambar[ ]?\d+[.]?[\d]*'
reader = easyocr.Reader(['id', 'en'], gpu=True)

# Read input
filename = sys.argv[1]
print('Processing file: ' + filename)
# Delete document if exists
col.delete_many({'filename': filename})

# Start timer
start = time.time()
# Open PDF file
pdf = fitz.open(filename)
data = {
    'filename': filename,
    'pages': [],
}

# Loop through all pages
for page in pdf:
    page_width, page_height = page.mediabox_size  # Get page width and height
    images = page.get_images()  # Get page images

    # Set data
    items = []

    # Loop through all images
    for image in images:
        # Get image data
        pix = fitz.Pixmap(pdf, image[0])  # Get pixmap from image xref
        img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)  # Convert pixmap to PIL image
        image_rect = page.get_image_rects(image[0])[0]  # Get image rect position

        # Search for image caption
        clip_area = fitz.Rect(0, image_rect.y1, page_width, image_rect.y1 + 50)  # Define clip area
        text = page.get_textbox(clip_area)  # Get text from clip area

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
                items.append({
                    'xref': image[0],
                    'rect': {
                        'x0': image_rect.x0,
                        'y0': image_rect.y0,
                        'x1': image_rect.x1,
                        'y1': image_rect.y1
                    },
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