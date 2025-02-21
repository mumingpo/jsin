'''
define the function that constructs
a unique signature for supported types
'''

import itertools

from dataclasses import dataclass

from types import UnionType
from types import NoneType
from typing import Any
from typing import NotRequired
from typing import Literal

from functools import cache

_EMPTY_FROZEN_SET = frozenset()

_DEP_ANY = ('typing', 'Any')
_DEP_LITERAL = ('typing', 'Literal')
_DEP_OPTIONAL = ('typing', 'Optional')
_DEP_BASE_CLASS = ('pydantic', 'BaseModel')

SIGNATURE_OF_BUILTINS = {
    Any: 'Any',
    NoneType: 'None',
    bool: 'bool',
    int: 'int',
    float: 'float',
    str: 'str',
}


@dataclass(frozen=True)
class Signature():
    '''
    a unique representation of a type represented by
    a schematic tree node
    '''
    _s: str
    default_none: bool
    dependencies: frozenset[tuple[str, str]]

    def __str__(self):
        return self._s


@cache
def signature(t: type) -> Signature:
    '''
    generate a unique signature for the following types
    - Any
    - None
    - bool
    - int
    - float
    - str
    - list[<type>]
    - dict[str, <type>]
    - TypedDict: ...
    - <type> | <type>
    - Literal[value, ...]
    - NotRequired[type]
    '''

    if t in SIGNATURE_OF_BUILTINS:
        dependencies = _EMPTY_FROZEN_SET

        if t is Any:
            dependencies = dependencies.union(
                (_DEP_ANY,),
            )

        return Signature(
            _s=SIGNATURE_OF_BUILTINS[t],
            default_none=False,
            dependencies=dependencies,
        )

    if hasattr(t, '__origin__') and hasattr(t, '__args__'):
        if t.__origin__ is Literal:

            for arg in t.__args__:
                if not isinstance(arg, str):
                    raise NotImplementedError(
                        'literals of non-string types are not currently supported',
                    )

            return Signature(
                _s=f"Literal{sorted(t.__args__)}",
                default_none=False,
                dependencies=frozenset((_DEP_LITERAL,)),
            )

        if t.__origin__ is NotRequired:
            (arg, ) = t.__args__
            arg_sig = signature(arg)

            return Signature(
                _s=f'Optional[{arg_sig}]',
                default_none=True,
                dependencies=arg_sig.dependencies.union(
                    (_DEP_OPTIONAL,),
                ),
            )

        if t.__origin__ is list:
            (arg, ) = t.__args__
            arg_sig = signature(arg)

            return Signature(
                _s=f'list[{arg_sig}]',
                default_none=False,
                dependencies=arg_sig.dependencies,
            )

        if t.__origin__ is dict:
            (arg1, arg2) = t.__args__
            arg1_sig = signature(arg1)
            arg2_sig = signature(arg2)

            return Signature(
                _s=f'dict[{arg1_sig}, {arg2_sig}]',
                default_none=False,
                dependencies=arg1_sig.dependencies.union(
                    arg2_sig.dependencies,
                ),
            )

    if issubclass(t, UnionType):
        arg_sigs = sorted(
            (signature(arg) for arg in t.__args__),
            key=str,
        )

        s = ' | '.join(str(sig) for sig in arg_sigs)
        default_none = any(sig.default_none for sig in arg_sigs)
        dependencies = _EMPTY_FROZEN_SET.union(
            itertools.chain(
                *(sig.dependencies for sig in arg_sigs),
            ),
        )

        return Signature(
            _s=s,
            default_none=default_none,
            dependencies=dependencies,
        )

    if issubclass(t, dict) and hasattr(t, '__annotations__'):
        fields = tuple(sorted(
            (key, signature(value)) for key, value in t.__annotations__.items()
        ))

        dependencies = frozenset((_DEP_BASE_CLASS,)).union(
            itertools.chain(
                *(sig.dependencies for _, sig in fields),
            )
        )

        return Signature(
            _s=f'_{str(abs(hash(fields)))}',
            default_none=False,
            dependencies=dependencies,
        )

    raise NotImplementedError(f'Unsupported type {t}')
