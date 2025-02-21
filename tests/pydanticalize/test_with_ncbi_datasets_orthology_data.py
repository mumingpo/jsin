
from jsin import pydanticalize

from ..utils import _data

RESOURCE_URL = 'https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/2778/orthologs?returned_content=COMPLETE&taxon_filter=homo+sapiens&taxon_filter=mus+musculus'


def test_with_ncbi_datasets_orthology_data():
    data = _data(
        url=RESOURCE_URL,
        method='GET',
    )

    with open('.temp/ncbi_datasets_orthology.py', 'wt', encoding='utf-8') as f:
        f.write(pydanticalize(data))
