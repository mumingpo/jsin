import os
import json as json_lib
import hashlib

from typing import Any
from typing import Literal
from typing import Callable

import httpx

TEMP_DIR = os.path.expanduser('~/.temp/jsin')


def _data(
    url: str,
    *,
    method: Literal['GET', 'POST'] = 'GET',
    json: Any = None,
    post_processing: Callable[[str], object] = json_lib.loads,
):

    if method == 'GET':
        assert json is None, 'GET cannot be sent with a body'

    json_str = json_lib.dumps(json, sort_keys=True)

    h = hashlib.sha256()

    for s in (method, url, json_str):
        h.update(s.encode('utf-8'))

    digest = h.hexdigest()

    base_name = f'{digest[:16]}.txt'
    os.makedirs(TEMP_DIR, exist_ok=True)
    path = os.path.join(TEMP_DIR, base_name)

    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return json_lib.load(f)

    if method == 'GET':
        response = httpx.get(url)
    else:
        response = httpx.post(url, json=json)

    response.raise_for_status()

    obj = post_processing(response.text)

    with open(path, 'wt', encoding='utf-8') as f:
        json_lib.dump(obj, f)

    return obj
