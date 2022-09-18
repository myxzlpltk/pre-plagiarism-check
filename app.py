import pdfplumber
from flask import Flask

app = Flask(__name__)
filename = 'input.pdf'


@app.route('/')
def hello_world():
    with pdfplumber.open(filename) as pdf:
        page = pdf.pages[0]
        text = page.images
    return text


if __name__ == '__main__':
    app.run()
