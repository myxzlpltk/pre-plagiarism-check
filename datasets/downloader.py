import os
import time

import pymongo
import requests
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

mongo = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo['arxiv']
col = db['metadata']


def download(vector):
    link, filelocation = vector
    r = requests.get(link, stream=True)
    # bytesRead = 0
    with open(filelocation, 'wb') as f:
        for chunk in r.iter_content(1024):
            if chunk:
                # bytesRead += len(chunk)
                f.write(chunk)

    # if bytesRead == 0:
        # os.remove(filelocation)


def download_files(_vectors):
    with ThreadPoolExecutor(max_workers=5) as executor:
        result = executor.map(download, _vectors)
        return list(result)


# Total documents
total = col.count_documents({
    '$or': [
        {'categories': {'$regex': '^cs'}},
        {'categories': {'$regex': '^eess'}}],
    'status': {'$exists': False}
})
counter = 0
bar = tqdm(total=total)

for i in range(0, total, 100):
    # Get all documents
    docs = col.find({
        '$or': [
            {'categories': {'$regex': '^cs'}},
            {'categories': {'$regex': '^eess'}}],
        'status': {'$exists': False}
    }).limit(100)

    # Loop through documents
    for doc in docs:
        url = 'https://arxiv.org/pdf/' + doc['id']
        file = 'arxiv/' + ('_'.join(doc['id'].split('.'))) + '.pdf'

        download((url, file))

        counter += 1
        bar.update(counter)

    col.update_many(
        {'_id': {'$in': [doc['_id'] for doc in docs]}},
        {'$set': {'status': True}}
    )

    time.sleep(0.1)