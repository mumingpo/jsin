# jsin
JSon Schema INferer

## installation

```shell
python -m pip install --upgrade pip
python -m pip install jsin
```

## usage

```python
from jsin import pydanticalize

obj = httpx.get('resource_uri').json()

with open('inferred_pydantic_model.py', 'wt', encoding='utf-8') as f:
    f.write(pydanticalize(obj))
```
