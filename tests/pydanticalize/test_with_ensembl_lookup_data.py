from jsin import pydanticalize

from ..utils import _data

RESOURCE_URL = 'https://rest.ensembl.org/lookup/id'


def test_with_entrez_snp_data():
    data = _data(
        url=RESOURCE_URL,
        method='POST',
        json={
            "ids": [
                "ENSG00000157764",
                "ENSG00000248378",
            ],
            "expand": 1,
        },
    )

    with open('.temp/ensembl_lookup.py', 'wt', encoding='utf-8') as f:
        f.write(pydanticalize(data))
