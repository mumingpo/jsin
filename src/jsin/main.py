from .pydanticalize import pydanticalize


def main():
    content = pydanticalize({
        'hello': 'world',
        'chicken': True,
        'buy': 100.,
    })

    print(content)


if __name__ == '__main__':
    main()
