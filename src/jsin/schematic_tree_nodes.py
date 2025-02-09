'''
define the nodes used in schematic tree representations
'''

from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from collections import Counter
from collections.abc import MutableMapping
from collections.abc import Iterator

from types import NoneType

from typing import Self
from typing import Any
from typing import TypedDict
from typing import NotRequired


class SchematicTreeNodeType(StrEnum):
    '''
    enum class describing types used by the parsed schema
    '''
    # placeholder for the value type of empty arrays
    ANY = 'ANY'
    # placeholder for the value type of null fields
    NULL = 'NULL'
    # true/false
    BOOLEAN = 'BOOLEAN'
    # int/float
    NUMBER = 'NUMBER'
    STRING = 'STRING'
    # objects that are "data classes"
    # that is, field_names paired with values frequently made up of different t ypes
    # NOTE: object with values of the same type, indexed by their keys,
    # are considered KEY_INDEXED_ARRAYs
    OBJECT = 'OBJECT'
    # array containing values of the same type.
    ARRAY = 'ARRAY'
    # objects containing values of the same type.
    KEY_INDEXED_ARRAY = 'KEY_INDEXED_ARRAY'


class BaseNode(ABC):
    '''
    the base class for schematic tree nodes
    '''
    t: SchematicTreeNodeType

    def __init__(self, t: SchematicTreeNodeType):
        self.t = t

    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[Self, str]]:
        '''
        iterate nodes and name from the root up
        '''
        yield self, name

    @abstractmethod
    def __add__(self, other) -> Self:
        '''
        combine two nodes
        '''
        return NotImplemented

    @abstractmethod
    def __str__(self):
        return '<BaseNode>'

    @abstractmethod
    def to_python_type(self) -> type:
        '''
        get the corresponding Python type for the node
        '''
        return type(object)

    # @classmethod
    # @abstractmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     '''
    #     combine an iterable of similar nodes into a single node
    #     '''
    #     return NotImplemented


class SingletonNode(BaseNode):
    '''
    singleton node for nodes that do not need multiple instances
    '''

    _instance: Self | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __add__(self, other):
        if other is self:
            return self

        return NotImplemented

    # @classmethod
    # def rollup(cls, _):
    #     return cls._instance


class AnyNode(SingletonNode):
    '''
    node used as a placeholder for empty arrays
    '''

    def __init__(self):
        super().__init__(SchematicTreeNodeType.ANY)

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other

    def __str__(self):
        return '<AnyNode>'

    def to_python_type(self):
        return Any


class NullNode(SingletonNode):
    '''
    node used as a placeholder for null values
    '''

    def __init__(self):
        super().__init__(SchematicTreeNodeType.NULL)

    def __add__(self, other):
        if isinstance(other, AnyNode):
            return self

        return other

    def __radd__(self, other):
        if isinstance(other, AnyNode):
            return self

        return other

    def __str__(self):
        return '<NullNode>'

    def to_python_type(self):
        return NoneType


class BooleanNode(SingletonNode):
    '''
    node used for boolean values
    '''

    def __init__(self):
        super().__init__(SchematicTreeNodeType.BOOLEAN)

    def __str__(self):
        return '<BooleanNode>'

    def to_python_type(self):
        return bool


class NumberNode(BaseNode):
    '''
    node used for numeric values
    '''

    contains_float: bool

    def __init__(self):
        super().__init__(SchematicTreeNodeType.NUMBER)
        self.contains_float = False

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, cls):
            new_node = cls()
            new_node.contains_float = (
                self.contains_float or other.contains_float
            )

            return new_node

        return NotImplemented

    def __str__(self):
        return f'<NumberNode float={self.contains_float}>'

    def to_python_type(self):
        if self.contains_float:
            return float

        return int

    # @classmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     new_node = cls()
    #     new_node.contains_float = any(node.contains_float for node in nodes)

    #     return new_node


class StringNode(BaseNode):
    '''
    node used for string values
    '''

    counter: Counter[str]

    def __init__(self):
        super().__init__(SchematicTreeNodeType.STRING)
        self.counter = Counter()

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, cls):
            new_node = cls()
            new_node.counter = self.counter + other.counter

            return new_node

        return NotImplemented

    def __str__(self):
        return '<StringNode>'

    def to_python_type(self):
        return str

    # @classmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     new_node = cls()
    #     new_node.counter = sum(
    #         (node.counter for node in nodes),
    #         start=new_node.counter,
    #     )

    #     return new_node

    def infer_whether_is_enum(self) -> bool:
        '''
        guess whether if string node represents an enum field
        '''

        # if number of choices is way less than the number of entries
        # we think there is an enum behind the scenes
        return len(self.counter) ** 2 < self.counter.total()


class ObjectNode(BaseNode, MutableMapping[str, tuple[BaseNode, bool, bool]]):
    '''
    node used for objects that are "data classes".
    that is, { field_name: value, ... } dicts where
    values are typically of different types.

    { key: value, ... } where values are of a uniform type
    where key is typically an attribute of value
    is considered a KEY_INDEXED_OBJECT
    '''

    # { field_name: (node, optional, nullable) }
    fields: dict[str, tuple[BaseNode, bool, bool]]

    def __init__(self):
        super().__init__(SchematicTreeNodeType.OBJECT)
        self.fields = dict()

    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[Self, str]]:
        for key, (node, _, _) in self.items():
            yield from node.iter_nodes_postorder(key)

        yield self, name

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        assert len(value) == 3
        assert isinstance(value[0], BaseNode)
        assert isinstance(value[1], bool)
        assert isinstance(value[2], bool)

        self.fields[key] = value

    def __delitem__(self, key):
        del self.fields[key]

    def __iter__(self):
        return iter(self.fields)

    def __len__(self):
        return len(self.fields)

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, cls):
            new_node = cls()

            for key, value in self.items():
                if key in other:
                    node = value[0] + other[key][0]
                    optional = value[1] or other[key][1]
                    nullable = value[2] or other[key][2]
                else:
                    node = value[0]
                    optional = True
                    nullable = value[2]

                new_node[key] = (node, optional, nullable)

            for key in set(other.keys()).difference(self.keys()):
                node = other[key][0]
                optional = True
                nullable = other[key][2]

                new_node[key] = (node, optional, nullable)

            return new_node

        return NotImplemented

    def __str__(self):
        fields_string = ', '.join(
            f'{key}: {str(value[0])}' for key, value in sorted(self.fields.items())
        )
        return f'<ObjectNode fields={fields_string}>'

    def to_python_type(self):
        fields = dict()
        for key, (node, optional, nullable) in sorted(self.items()):
            if optional or nullable:
                fields[key] = NotRequired[node.to_python_type()]
            else:
                fields[key] = node.to_python_type()

        # CamelCase is the proper casing for a type
        # pylint: disable-next=C0103
        Model = TypedDict('Model', fields)

        return Model

    # @classmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     return sum(nodes, start=AnyNode())


class ArrayNode(BaseNode):
    '''
    node used to represent arrays
    '''

    value_node: BaseNode

    def __init__(self):
        super().__init__(SchematicTreeNodeType.ARRAY)
        self.value_node = AnyNode()

    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[Self, str]]:
        yield from self.value_node.iter_nodes_postorder(name.removesuffix('s'))
        yield self, name

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, cls):
            new_node = cls()
            new_node.value_node = self.value_node + other.value_node

            return new_node

        return NotImplemented

    def __str__(self):
        return f'<ArrayNode value_node={str(self.value_node)}>'

    def to_python_type(self):
        return list[self.value_node.to_python_type()]

    # @classmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     meaningful = [
    #         node for node in nodes
    #         if not isinstance(node.value_node, AnyNode)
    #     ]
    #     node_types = {type(node.value_node) for node in meaningful}

    #     new_node = cls()

    #     if len(node_types) == 1:
    #         (t, ) = node_types
    #         new_node.value_node = t.rollup(
    #             node.value_node for node in meaningful
    #         )
    #     else:
    #         new_node.value_node = sum(
    #             (node.value_node for node in meaningful),
    #             start=AnyNode(),
    #         )

    #     return new_node


class KeyIndexedArrayNode(BaseNode):
    '''
    node used to represent objects that are basically arrays,
    but that are indexed by keys of values
    '''

    keys: set[str]
    value_node: BaseNode

    def __init__(self):
        super().__init__(SchematicTreeNodeType.KEY_INDEXED_ARRAY)
        self.keys = set()
        self.value_node = AnyNode()

    def iter_nodes_postorder(self, name: str) -> Iterator[tuple[Self, str]]:
        yield from self.value_node.iter_nodes_postorder(name.removesuffix('s'))
        yield self, name

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, cls):
            new_node = cls()
            new_node.keys = self.keys.union(other.keys)

            try:
                new_node.value_node = self.value_node + other.value_node

                return new_node
            except NotImplementedError():
                # proceed to trying to add by converting to object node
                pass

        # fall back to trying with object node
        return self.to_object_node() + other

    def __str__(self):
        return f'<KeyIndexedArrayNode value_node={str(self.value_node)}>'

    def to_python_type(self):
        return dict[str, self.value_node.to_python_type()]

    # @classmethod
    # def rollup(cls, nodes: Iterable[Self]) -> Self:
    #     meaningful = [
    #         node for node in nodes
    #         if not isinstance(node.value_node, AnyNode)
    #     ]
    #     node_types = {type(node.value_node) for node in meaningful}

    #     new_node = cls()
    #     new_node.keys.update(node.keys for node in meaningful)

    #     try:
    #         if len(node_types) == 1:
    #             (t, ) = node_types
    #             new_node.value_node = t.rollup(
    #                 node.value_node for node in meaningful
    #             )
    #         else:
    #             new_node.value_node = sum(
    #                 (node.value_node for node in meaningful),
    #                 start=AnyNode(),
    #             )
    #     except NotImplementedError as e:
    #         try:
    #             new_node = ObjectNode.rollup(
    #                 node.to_object_node() for node in meaningful
    #             )
    #         except NotImplementedError:
    #             raise e from None

    #     return new_node

    def to_object_node(self):
        '''
        convert into an ObjectNode
        '''

        nullable = isinstance(self.value_node, NullNode)
        new_node = ObjectNode()

        for key in self.keys:
            new_node[key] = (self.value_node, False, nullable)

        return new_node
