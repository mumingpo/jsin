'''
define the nodes used in the schematic tree representation
'''

from abc import ABC
from abc import abstractmethod

import itertools

from collections import Counter

from collections.abc import MutableMapping
from collections.abc import Iterator
from collections.abc import Iterable

from dataclasses import dataclass

from types import NoneType

from typing import Any
from typing import Self
from typing import Literal
from typing import TypedDict
from typing import NotRequired

from typing_extensions import override

from .exceptions import NodeInhomogeneityError
from .exceptions import InsufficientOverlapError


def rollup(nodes: Iterable['BaseNode']) -> 'BaseNode':
    '''
    combine an iterable of similar nodes into a single node
    '''

    l = list(nodes)

    contains_null = any(
        isinstance(node, NullNode) for node in l
    )
    meaningful = [
        node for node in l
        if not isinstance(node, (AnyNode, NullNode))
    ]

    types = {type(node) for node in meaningful}

    if len(types) == 0:
        if contains_null:
            return NullNode()

        return AnyNode()

    if len(types) >= 2:
        if types != {ObjectNode, KeyIndexedArrayNode}:
            raise NodeInhomogeneityError(l)

        new_nodes = [
            node.convert_to_object_node()
            if isinstance(node, KeyIndexedArrayNode)
            else node
            for node in meaningful
        ]

        return rollup(new_nodes)

    # valid iff types contain a single type
    (t, ) = types

    return t.rollup(meaningful)


class BaseNode(ABC):
    '''
    the base class for schematic tree nodes
    '''

    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[str, 'BaseNode']]:
        '''
        iterate (name, node) in the post-order
        '''

        yield (name, self)

    @abstractmethod
    def __str__(self):
        return 'Base'

    @abstractmethod
    def __repr__(self):
        return 'BaseNode()'

    @abstractmethod
    def to_python_type(self) -> type:
        '''
        get the corresponding Python type for the node
        '''

        return type

    @classmethod
    @abstractmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        '''
        combine an iterable of similar nodes into a single node
        '''
        return cls()


class SingletonNode(BaseNode):
    '''
    singleton node for nodes that do not need multiple instances
    '''
    _instance: Self | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __repr__(self):
        return f'{str(self)}Node()'

    @classmethod
    def rollup(cls, _):
        return cls._instance


class AnyNode(SingletonNode):
    '''
    node used as a placeholder for empty arrays
    '''

    def __str__(self):
        return 'Any'

    def to_python_type(self):
        return Any


class NullNode(SingletonNode):
    '''
    node used as a placeholder for { [key]: null } fields in JSON objects
    '''

    def __str__(self):
        return 'Null'

    def to_python_type(self):
        return NoneType


class BooleanNode(SingletonNode):
    '''
    node used for boolean values
    '''

    def __str__(self):
        return 'Boolean'

    def to_python_type(self):
        return bool


class NumberNode(BaseNode):
    '''
    node used for numeric values
    '''

    contains_float: bool

    def __init__(self, contains_float=False):
        self.contains_float = contains_float

    def __str__(self):
        return 'Number'

    def __repr__(self):
        return f'NumberNode(contains_float={self.contains_float})'

    def to_python_type(self):
        if self.contains_float:
            return float

        return str

    @classmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        new_node = cls(
            contains_float=any(
                node.contains_float for node in nodes
            ),
        )

        return new_node


class StringNode(BaseNode):
    '''
    node used for string values
    '''

    counter: Counter[str]

    def __init__(self, initial_string: str | None = None):
        self.counter = Counter()

        if initial_string is not None:
            self.counter[initial_string] += 1

    def __str__(self):
        return 'String'

    def __repr__(self):
        return 'StringNode()'

    def infer_whether_is_enum(self):
        '''
        guess whether if string node represent an enum field
        '''

        return all([
            # if number of choices is way less than the number of entries
            # we think there is an enum behind the scenes
            len(self.counter) ** 2 < self.counter.total(),
            # enum values shouldn't be too complicated,
            # so long strings are a no-no
            all(len(key) < 30 for key in self.counter),
        ])

    def to_python_type(self) -> type:
        if self.infer_whether_is_enum():
            return Literal[*self.counter.keys()]
        return str

    @classmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        new_node = cls()

        for node in nodes:
            new_node.counter += node.counter

        return new_node


@dataclass
class ObjectNodeField():
    '''
    dataclass represent a field of an object node
    '''

    node: BaseNode
    nullable: bool = False
    optional: bool = False

    @classmethod
    def missing_default(cls):
        '''
        the default value for accessing missing fields
        '''
        return cls(
            node=AnyNode(),
            optional=True,
        )

    def __str__(self):
        return str(self.node)

    def __repr__(self):
        return f'Field(node={repr(self.node)}, nullable={self.nullable}, optional={self.optional})'


class ObjectNode(BaseNode, MutableMapping[str, ObjectNodeField]):
    '''
    node used for objects that are "dataclasses"
    i.e. { field_name: value } dicts where values
    hold different types and meanings depending
    on the name of the field.

    { key: value } dicts where values are of a uniform type
    indexed by key is considered a KeyIndexedArray
    '''

    fields: dict[str, ObjectNodeField]

    def __init__(self, fields: dict[str, ObjectNodeField] | None = None):
        if fields is None:
            self.fields = dict()
        else:
            self.fields = fields

    def __str__(self):
        s = ', '.join(
            f'{key}: {value}' for key, value in self.items()
        )

        return ''.join((
            'Object({',
            s,
            '})',
        ))

    def __repr__(self):
        s = ', '.join(
            f'"{key}": {repr(value)}' for key, value in self.items()
        )
        return ''.join((
            'ObjectNode({',
            s,
            '})',
        ))

    def to_python_type(self) -> type:
        fields = dict()

        for key, value in sorted(self.items()):
            t = value.node.to_python_type()

            # NoneType | NoneType = NoneType
            # no redundancy would result.
            if value.nullable:
                t = t | NoneType

            if value.optional:
                t = NotRequired[t]

            fields[key] = t

        return TypedDict('Model', fields)

    @classmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        fields: dict[str, ObjectNodeField] = dict()

        keys = set().union(itertools.chain(
            *(node.keys() for node in nodes)
        ))

        for key in keys:
            value_node = rollup(
                node[key].node
                for node in nodes
                if key in node
            )
            nullable = any(
                node[key].nullable
                for node in nodes
                if key in node
            )
            optionals = list(
                node[key].optional
                for node in nodes
                if key in node
            )

            optional = any(optionals) or len(optionals) < len(nodes)

            fields[key] = ObjectNodeField(
                node=value_node,
                nullable=nullable,
                optional=optional,
            )

        if all(field.optional for field in fields.values()):
            raise InsufficientOverlapError(
                [field.node for field in fields.values()],
            )

        return cls(fields)

    def __getitem__(self, key: str) -> ObjectNodeField:
        return self.fields[key]

    def __setitem__(self, key: str, value: ObjectNodeField):
        if isinstance(value.node, NullNode):
            assert value.nullable is True

        self.fields[key] = value

    def __delitem__(self, key: str):
        del self.fields[key]

    def __iter__(self):
        yield from self.fields

    def __len__(self):
        return len(self.fields)

    @override
    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[str, BaseNode]]:
        for key, value in self.items():
            yield from value.node.iter_nodes_postorder(key)

        yield (name, self)


class ArrayNode(BaseNode):
    '''
    node used to represent arrays of values of
    the same underlying schema
    '''
    value_node: BaseNode

    def __init__(self, value_node: BaseNode | None = None):
        if value_node is None:
            self.value_node = AnyNode()
        else:
            self.value_node = value_node

    def __str__(self):
        return f'[{self.value_node}, ...]'

    def __repr__(self):
        return f'ArrayNode(value_node={repr(self.value_node)})'

    def to_python_type(self) -> type:
        return list[self.value_node.to_python_type()]

    @classmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        new_node = cls(
            value_node=rollup(
                node.value_node for node in nodes
            ),
        )

        return new_node

    @override
    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[str, BaseNode]]:
        yield from self.value_node.iter_nodes_postorder(name.removesuffix('s'))
        yield (name, self)


class KeyIndexedArrayNode(BaseNode):
    '''
    node used to represent objects that are basically arrays,
    but that are indexed by keys of values
    '''
    keys: set[str]
    value_node: BaseNode

    def __init__(self, value_node: BaseNode | None = None, keys: set[str] | None = None):
        if value_node is None:
            self.value_node = AnyNode()
        else:
            self.value_node = value_node

        if keys is None:
            self.keys = set()
        else:
            self.keys = keys

    def __str__(self):
        return f'{{[key]: {self.value_node}, ...}}'

    def __repr__(self):
        return f'KeyIndexedArrayNode(value_node={repr(self.value_node)}, keys={repr(self.keys)})'

    def to_python_type(self) -> type:
        return dict[str, self.value_node.to_python_type()]

    @classmethod
    def rollup(cls, nodes: Iterable[Self]) -> Self:
        new_node = cls()

        for node in nodes:
            new_node.keys.update(node.keys)

        new_node.value_node = rollup(
            node.value_node for node in nodes
        )

        return new_node

    @override
    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[str, BaseNode]]:
        yield from self.value_node.iter_nodes_postorder(name.removesuffix('s'))
        yield (name, self)

    def convert_to_object_node(self):
        '''
        convert a KeyIndexedArrayNode to an equivalent ObjectNode
        '''
        new_node = ObjectNode()

        for key in self.keys:
            new_node[key] = ObjectNodeField(
                node=self.value_node,
                nullable=isinstance(self.value_node, NullNode),
            )

        return new_node


# class _Dummy(BaseNode):
#     def __init__(self):
#         pass

#     def __str__(self):
#         return ''

#     def __repr__(self):
#         return ''

#     def to_python_type(self) -> type:
#         return type

#     @classmethod
#     def rollup(cls, nodes: Iterable[Self]) -> Self:
#         return cls()
