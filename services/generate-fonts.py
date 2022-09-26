import os
import pymongo
import random
import string
import uuid
from copy import deepcopy
from fontTools import ttLib
from tqdm import tqdm

# App variable
font_input_path = '../inputs/times.ttf'

# Read input
total = int(input("Enter the total number of fonts: "))

# Database connection
print("Init MongoDB connection...")
mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['skripsi']
col = db['generator']

for i in tqdm(range(total)):
    # Generate random mapping
    lowercase_letters = list(string.ascii_lowercase)
    uppercase_letters = list(string.ascii_uppercase)
    random.shuffle(lowercase_letters)  # Shuffle lowercase letters
    random.shuffle(uppercase_letters)  # Shuffle uppercase letters

    total_swaps = random.randint(10, 20)  # Random number of swaps
    random_lowercase_letters = lowercase_letters[:total_swaps]  # Random lowercase letters
    random_uppercase_letters = uppercase_letters[:total_swaps]  # Random uppercase letters
    lowercase_letters = lowercase_letters[:total_swaps]  # Pair lowercase letters
    uppercase_letters = uppercase_letters[:total_swaps]  # Pair uppercase letters

    random.shuffle(random_lowercase_letters)  # Shuffle random lowercase letters
    random.shuffle(random_uppercase_letters)  # Shuffle random uppercase letters

    # Create mapping
    swaps = dict(zip(lowercase_letters + uppercase_letters, random_lowercase_letters + random_uppercase_letters))

    # Generate random font name
    font_output_filename = str(uuid.uuid4().hex) + '.ttf'
    font_output_path = '../tmps/' + font_output_filename

    font = ttLib.TTFont(font_input_path)
    original_font = deepcopy(font)

    for key, value in swaps.items():
        font['glyf'][key] = original_font['glyf'][value]  # Swap glyph
        font['hmtx'].metrics[key] = original_font['hmtx'].metrics[value]  # Swap metric

    font.save(font_output_path)

    # Rename font
    os.system(f"python rename_fonts.py \"{font_output_path}\" -s \" Fake\" --inplace")

    # Save to database
    col.insert_one({
        'swaps': swaps,
        'font': font_output_filename,
        'fontname': 'Times New Roman Fake',
    })
