import json

from jsin import pydanticalize

from ..utils import _data

RESOURCE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=snp&id=268,328,1001654958,1002404220,1003400802,1003610832,1003640385,1004901898,1005362844,1005381126,1005605852,1005647635,1005659710,1005987312,1006868105,1007107036,1007451921,1007980333,1008636307,1009450092,1009914415,1010449023&rettype=json&retmode=text'


def _parse_idiotically_concatenated_json(s: str):
    jsons = s.split('}{')

    for i in range(len(jsons) - 1):
        jsons[i] = jsons[i] + '}'
        jsons[i+1] = '{' + jsons[i+1]

    arr = [
        json.loads(j) for j in jsons
    ]

    return arr


def test_with_entrez_snp_data():
    data = _data(
        url=RESOURCE_URL,
        method='GET',
        post_processing=_parse_idiotically_concatenated_json,
    )

    with open('.temp/entrez_snp.py', 'wt', encoding='utf-8') as f:
        f.write(pydanticalize(data))
