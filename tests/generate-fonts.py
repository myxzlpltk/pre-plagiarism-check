import os
import pymongo
import random
import string
from copy import deepcopy
from fontTools import ttLib
from tqdm import tqdm

# App variable
font_input_path = '../inputs/times.ttf'

# Read input
total = int(input("Enter the total number of fonts: "))

# Database connection
print("MongoDB connection", end=' ')
mongo = pymongo.MongoClient('mongodb+srv://myxzlpltk:fJqPVlWLQxfZpFRz@cluster0.stwjzjx.mongodb.net')
db = mongo['skripsi2']
col = db['fonts']
print("Connected")

font_keys = dict(zip(
    list(string.digits + string.ascii_lowercase + string.ascii_uppercase),
    ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'],
))

for i in tqdm(range(total)):
    while True:
        # Generate random mapping
        letters = list(string.digits + string.ascii_lowercase + string.ascii_uppercase)
        random.shuffle(letters)  # Shuffle letters

        total_swaps = random.randint(5, 30)  # Random number of swaps
        random_letters = letters[:total_swaps]  # Pick letters
        letters = letters[:total_swaps]  # Pick letters

        random.shuffle(letters)  # Shuffle random letters

        # Create mapping
        swaps = dict(zip(letters, random_letters))
        # swaps = {k: v for k, v in swaps.items() if k.lower() != v.lower()}

        # Check if there is no element that is mapped to itself
        if len([k for k, v in swaps.items() if k.lower() == v.lower()]) == 0:
            break

    # Generate random font name
    font_output_filename = str(i) + '.ttf'
    font_output_path = '../tmps/' + font_output_filename

    font = ttLib.TTFont(font_input_path)
    original_font = deepcopy(font)

    for key, value in swaps.items():
        font['glyf'][font_keys[key]] = original_font['glyf'][font_keys[value]]  # Swap glyph
        font['hmtx'].metrics[font_keys[key]] = original_font['hmtx'].metrics[font_keys[value]]  # Swap metric

    font.save(font_output_path)

    # Rename font
    os.system(f"python rename_fonts.py \"{font_output_path}\" -s \" Fake {i}\" --inplace")

    # Save to database
    col.insert_one({
        'swaps': swaps,
        'font': font_output_filename,
        'fontname': f'Times New Roman Fake {i}',
    })
