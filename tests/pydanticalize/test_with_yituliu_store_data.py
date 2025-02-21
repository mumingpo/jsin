from jsin import pydanticalize

from ..utils import _data

RESOURCE_URL = 'https://backend.yituliu.cn/custom/store/act'


def test_with_yituliu_store_data():
    data = _data(
        url=RESOURCE_URL,
        method='POST',
        json={
            "id": 202412050002,
            "expCoefficient": 0.633,
            "lmdCoefficient": 1,
            "useActivityStage": False,
            "stageBlacklist": [],
            "source": "penguin",
            "customItem": [
                {
                    "itemId": "30073",
                    "itemValue": 1.8,
                }
            ],
        },
    )

    with open('.temp/yituliu_store.py', 'wt', encoding='utf-8') as f:
        f.write(pydanticalize(data))
