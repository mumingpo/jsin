'''
define the function that constructs
a unique signature for supported types
'''

from types import UnionType
from typing import Any
from typing import NotRequired

import functools

SIGNATURE_OF_BUILTINS = {
    Any: 'Any',
    None: 'None',
    bool: 'bool',
    int: 'int',
    float: 'float',
    str: 'str',
}


@functools.cache
def signature(t: type) -> str:
    '''
    generate a unique signature for the following types
    - Any
    - None
    - bool
    - int
    - float
    - str
    - list[<type>]
    - dict[<type>, <type>]
    - TypedDict: ...
    - <type> | <type>
    '''
    if t in SIGNATURE_OF_BUILTINS:
        return SIGNATURE_OF_BUILTINS[t]

    if hasattr(t, '__origin__') and hasattr(t, '__args__'):
        if t.__origin__ is NotRequired:
            args = list(t.__args__)
            args.append(None)

            return ' | '.join(sorted(signature(arg) for arg in args))
        if t.__origin__ is list:
            return f'list[{signature(t.__args__[0])}]'

        if t.__origin__ is dict:
            return f'dict[{signature(t.__args__[0])}, {signature(t.__args__[1])}]'

    if issubclass(t, UnionType):
        return ' | '.join(sorted(signature(sub_t) for sub_t in t.__args__))

    if issubclass(t, dict) and hasattr(t, '__annotations__'):
        fields = tuple(sorted(
            (key, signature(value)) for key, value in t.__annotations__.items()
        ))

        return f'_{str(abs(hash(fields)))}'
