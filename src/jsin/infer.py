'''
define the infer function to construct
a schematic tree from a loaded json object
'''

from enum import StrEnum
from typing import Self
from collections.abc import Mapping
from collections.abc import Collection

from . import schematic_tree_nodes as stn
from .jsin_error import JsinError


class UnrecognizableTypeError(JsinError):
    '''
    failure to identify the JSON primitive type
    as represented by a Python object
    '''

    def __init__(self, obj):
        super().__init__(obj)

    def __str__(self):
        return '\n'.join(self._lines(
            reason='unable to identify the JSON primitive type',
            object=str(self.args[0]),
        ))


class IncompatibleNodesError(JsinError):
    '''
    failure to combine two schematic tree nodes into one
    '''

    def __init__(self, nodes: list[stn.BaseNode]):
        super().__init__(nodes)

    def __str__(self):
        return '\n'.join(self._lines(
            reason='attempting to combine incompatible schematic tree nodes',
            nodes=str([str(node) for node in self.args[0]]),
        ))


class JsonPrimitiveType(StrEnum):
    '''
    enum class describing JSON primitive types
    '''
    NULL = 'NULL'
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    NUMBER = 'NUMBER'
    STRING = 'STRING'
    ARRAY = 'ARRAY'
    OBJECT = 'OBJECT'

    @classmethod
    def tell(cls, obj) -> Self:
        '''
        identify the JSON primitive type of an object
        '''

        t: Self | None = None

        if obj is None:
            t = cls.NULL

        elif isinstance(obj, bool):
            if obj:
                t = cls.TRUE
            t = cls.FALSE

        elif isinstance(obj, (int, float)):
            t = cls.NUMBER

        elif isinstance(obj, str):
            t = cls.STRING

        elif isinstance(obj, Mapping):
            t = cls.OBJECT

        elif isinstance(obj, Collection):
            t = cls.ARRAY

        else:
            raise UnrecognizableTypeError(obj)

        return t


def infer(obj) -> stn.BaseNode:
    '''
    infer a schematic tree from a loaded json object
    '''

    t = JsonPrimitiveType.tell(obj)

    match t:
        case JsonPrimitiveType.NULL:
            node = stn.NullNode()

        case JsonPrimitiveType.TRUE | JsonPrimitiveType.FALSE:
            node = stn.BooleanNode()

        case JsonPrimitiveType.NUMBER:
            node = stn.NumberNode()
            node.contains_float = isinstance(obj, float)

        case JsonPrimitiveType.STRING:
            node = stn.StringNode()
            node.counter[obj] += 1

        case JsonPrimitiveType.ARRAY:
            node = stn.ArrayNode()

            try:
                children = [infer(elem) for elem in obj]
            except JsinError as e:
                raise e.under('ARRAY_ELEMENT') from e.__cause__

            try:
                node.value_node = sum(
                    children,
                    start=stn.AnyNode(),
                )
            except TypeError as e:
                raise IncompatibleNodesError(children) from e

        case JsonPrimitiveType.OBJECT:
            object_node = stn.ObjectNode()

            for key, value in obj.items():
                try:
                    value_node = infer(value)
                except JsinError as e:
                    raise e.under(key) from e.__cause__

                object_node[key] = (
                    value_node,
                    False,
                    isinstance(value_node, stn.NullNode),
                )

            try:
                key_indexed_array_node = stn.KeyIndexedArrayNode()
                key_indexed_array_node.keys = set(object_node.keys())

                children = (tup[0] for tup in object_node.values())
                try:

                    key_indexed_array_node.value_node = sum(
                        children,
                        start=stn.AnyNode(),
                    )
                except TypeError as e:
                    raise IncompatibleNodesError(children) from e

                node = key_indexed_array_node
            except JsinError:
                node = object_node

        case _:
            raise UnrecognizableTypeError(obj)

    return node
