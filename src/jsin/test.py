import os
import pickle
from typing import Any
from typing import Literal

import httpx

from .pydanticalize import pydanticalize

EXAMPLES_PATH = os.path.expanduser('~/.temp/jsin_test_examples.pickle')


def get_example(
    method: Literal['GET', 'POST'],
    url: str,
    *,
    json: Any | None = None,
):
    os.makedirs(os.path.dirname(EXAMPLES_PATH), exist_ok=True)
    if not os.path.isfile(EXAMPLES_PATH):
        with open(EXAMPLES_PATH, 'wb') as f:
            pickle.dump({}, f)

    with open(EXAMPLES_PATH, 'rb') as f:
        examples = pickle.load(f)

    with httpx.Client() as client:
        request = client.build_request(
            method=method,
            url=url,
            json=json,
        )

        request_hash = hash(request)

        if request_hash not in examples:
            response = client.send(request)
            response.raise_for_status()

            examples[request_hash] = response.json()

            with open(EXAMPLES_PATH, 'wb') as f:
                pickle.dump(examples, f)

    return examples[request_hash]


def main():
    obj = get_example(
        'GET',
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=snp&id=268&rettype=json&retmode=text',
    )

    # obj = get_example(
    #     'POST',
    #     'https://rest.ensembl.org/lookup/id',
    #     json={
    #         "ids": ["ENSG00000157764", "ENSG00000248378"],
    #         "expand": 1,
    #     },
    # )

    print(pydanticalize(obj))


if __name__ == '__main__':
    main()
