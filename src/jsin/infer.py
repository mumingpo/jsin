'''
define the infer function to construct
a schematic tree from a loaded json object
'''

from enum import StrEnum
from typing import Self
from collections.abc import Mapping
from collections.abc import Collection


from . import schematic_tree_nodes as stn
from .exceptions import JsinError
from .exceptions import UnidentifiableTypeError


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

        if obj is None:
            return cls.NULL

        if isinstance(obj, bool):
            if obj:
                return cls.TRUE
            return cls.FALSE

        if isinstance(obj, (int, float)):
            return cls.NUMBER

        if isinstance(obj, str):
            return cls.STRING

        if isinstance(obj, Mapping):
            return cls.OBJECT

        if isinstance(obj, Collection):
            return cls.ARRAY

        raise UnidentifiableTypeError(obj)


def infer(obj) -> stn.BaseNode:
    '''
    infer a schematic tree from a loaded json object
    '''

    t = JsonPrimitiveType.tell(obj)

    match t:
        case JsonPrimitiveType.NULL:
            return stn.NullNode()

        case JsonPrimitiveType.TRUE | JsonPrimitiveType.FALSE:
            return stn.BooleanNode()

        case JsonPrimitiveType.NUMBER:
            return stn.NumberNode(contains_float=isinstance(obj, float))

        case JsonPrimitiveType.STRING:
            return stn.StringNode(initial_string=obj)

        case JsonPrimitiveType.ARRAY:
            try:
                value_nodes = [infer(elem) for elem in obj]
                value_node = stn.rollup(value_nodes)
            except JsinError as e:
                raise e.under('ARRAY_ELEMENT') from e.__cause__

            return stn.ArrayNode(value_node=value_node)

        case JsonPrimitiveType.OBJECT:
            object_node = stn.ObjectNode()

            for key, value in obj.items():
                try:
                    value_node = infer(value)
                except JsinError as e:
                    raise e.under(key) from e.__cause__

                object_node[key] = stn.ObjectNodeField(
                    node=value_node,
                    nullable=isinstance(value_node, stn.NullNode),
                )

            try:
                # TODO: the optional and nullable attributes are currently ignored
                # what are the implications?
                value_node = stn.rollup(
                    value.node for value in object_node.values()
                )

                return stn.KeyIndexedArrayNode(
                    value_node=value_node,
                    keys=set(object_node.keys()),
                )

            except JsinError as e:
                return object_node

        case _:
            raise RuntimeError('Should be unreachable.')
