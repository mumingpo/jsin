'''
define the pydanticalize function that infers the pydantic schema
from a loaded JSON object
'''

from . import schematic_tree_nodes as stn
from .infer import infer
from .signature import signature


class _Model():
    t: type[dict]
    name_suggestions: set[str]

    def __init__(self, t: type[dict]):
        self.t = t
        self.name_suggestions = set()

    def __str__(self):
        lines = []

        if len(self.name_suggestions) > 0:
            lines.append(f'# name suggestions: {self.name_suggestions}')

        lines.append(f'class {signature(self.t)}(BaseModel):')

        for key, value in self.t.__annotations__.items():
            lines.append(
                f'    {key}: {signature(value)}',
            )

        return '\n'.join(lines)


def pydanticalize(obj):
    '''
    infer the pydantic classes from a loaded JSON object
    '''
    schematic_tree: stn.ObjectNode = infer(
        {'json': obj},
    ).to_object_node()

    models: dict[str, _Model] = dict()

    for node, name in schematic_tree.iter_nodes_postorder('Response'):
        if isinstance(node, stn.ObjectNode):
            t = node.to_python_type()
            sig = signature(t)

            if sig not in models:
                models[sig] = _Model(t)

            if name != '':
                models[sig].name_suggestions.add(
                    ''.join(
                        segment.capitalize() for segment in name.split('_')
                    )
                )

    lines = [
        'from typing import Any',
        'from pydantic import BaseModel',
        ''
    ]

    for model in models.values():
        lines.extend([
            '',
            str(model),
            '',
        ])

    return '\n'.join(lines)
