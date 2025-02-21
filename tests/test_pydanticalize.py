import os
import json
import hashlib

import httpx

from jsin.pydanticalize import pydanticalize

RESOURCE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=snp&id=268,328,1001654958,1002404220,1003400802,1003610832,1003640385,1004901898,1005362844,1005381126,1005605852,1005647635,1005659710,1005987312,1006868105,1007107036,1007451921,1007980333,1008636307,1009450092,1009914415,1010449023&rettype=json&retmode=text'
TEMP_DIR = os.path.expanduser('~/.temp/jsin')

os.makedirs(TEMP_DIR, exist_ok=True)


def _get(url: str):
    base_name = f'{hashlib.sha256(url.encode()).hexdigest()[:16]}.txt'
    path = os.path.join(TEMP_DIR, base_name)

    if not os.path.isfile(path):
        response = httpx.get(RESOURCE_URL)
        response.raise_for_status()

        with open(path, 'wb') as f:
            f.write(response.content)

    with open(path, 'rt', encoding='utf-8') as f:
        return f.read()


def test_pydanticalize():
    jsons = _get(RESOURCE_URL).split('}{')

    for i in range(len(jsons) - 1):
        jsons[i] = jsons[i] + '}'
        jsons[i+1] = '{' + jsons[i+1]

    arr = [
        json.loads(j) for j in jsons
    ]

    content = pydanticalize(arr)

    with open('.temp/model.py', 'wt', encoding='utf-8') as f:
        f.write(content)
