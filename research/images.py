import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import io
import fitz
import pymongo
import tkinter as tk
import easyocr
from PIL import Image, ImageOps, ImageTk, ImageChops, ImageDraw

# Initialize OCR
with_ocr = False
if with_ocr:
    reader = easyocr.Reader(['id', 'en'], gpu=True)

# Define mongoDB connection
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['skripsi']
col = db['images']


def main():
    args = {'area': {'$lt': 40}}
    data = col.find(args).sort([('area', pymongo.DESCENDING)])
    length = col.count_documents(args)

    app = App(data, length)
    app.mainloop()


def get_image(doc):
    pdf = fitz.open(doc['filename'])
    base_image = pdf.extract_image(doc['xref'])
    img = Image.open(io.BytesIO(base_image['image']))
    pdf.close()

    if with_ocr:
        # Trim image
        img = img.convert('RGB')
        bg = Image.new(img.mode, img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)

        # Expand image
        img = ImageOps.expand(img, border=10, fill='white')

        # Find the bounding box of those pixels
        result = reader.readtext(np.asarray(img))

        # Draw bounding box
        draw = ImageDraw.ImageDraw(img)
        total_area = 0
        for item in result:
            top_left = tuple(item[0][0])
            bottom_right = tuple(item[0][2])

            total_area += abs(bottom_right[0] - top_left[0]) * abs(bottom_right[1] - top_left[1])
            draw.rectangle((top_left, bottom_right), outline='red')

    img = ImageOps.pad(img, (480, 480), color='gray')

    return img


class App(tk.Tk):
    def __init__(self, data, length):
        super().__init__()
        self.geometry("480x520")
        self.cur_image = 0
        self.data = data
        self.length = length

        self.image = ImageTk.PhotoImage(
            get_image(self.data[self.cur_image])
        )
        self.image_panel = tk.Label(self, image=self.image)
        self.image_panel.pack(side="top")

        self.left_btn = tk.Button(
            self,
            text="<",
            fg='red',
            font=('', 11, 'bold'),
            command=self.left
        )
        self.bind("<Left>", lambda event: self.left())
        self.left_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        self.image_name = tk.Label(
            self,
            text=str(round(self.data[self.cur_image]['area'], 2)),
            font=('', 10, 'bold')
        )
        self.image_name.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        self.right_btn = tk.Button(
            self,
            text=">",
            fg='red',
            font=('', 11, 'bold'),
            command=self.right
        )
        self.bind("<Right>", lambda event: self.right())
        self.right_btn.pack(side=tk.RIGHT, fill=tk.BOTH, expand=tk.YES)

    def left(self):
        self.cur_image = (self.cur_image - 1) % self.length
        self.update_image()

    def right(self):
        self.cur_image = (self.cur_image + 1) % self.length
        self.update_image()

    def update_image(self):
        self.image_name.config(text=str(round(self.data[self.cur_image]['area'], 2)))
        self.image = ImageTk.PhotoImage(
            get_image(self.data[self.cur_image])
        )
        self.image_panel.config(image=self.image)


if __name__ == '__main__':
    main()
