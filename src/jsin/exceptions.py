'''
define the errors caused by Json Schema Inferer
'''

from typing import Self


def _str_arr_of_nodes(nodes):
    return f"[{', '.join(str(node) for node in nodes)}]"


class JsinError(TypeError):
    '''
    base class defining the type of errors thrown by the jsin module
    '''

    loc: tuple[str, ...]

    def __init__(self, *args):
        super().__init__(*args)
        self.loc = tuple()

    def under(self, parent_loc: str) -> Self:
        '''
        log the parent location

        usage:
            try:
                ...
            except JsinError as e:
                raise e.under(location) from e.__cause__
        '''
        new_error = type(self)(*self.args)
        new_error.loc = (parent_loc, *self.loc)

        return new_error

    def _format(self, **info: dict[str, str]):
        return ''.join((
            'Error occurred while inferring schema from a loaded JSON object',
            f'\tlocation: {self.loc}',
            *(f'\t{key}: {value}' for key, value in info.items()),
        ))

    def __str__(self):
        return self._format()


class NodeInhomogeneityError(JsinError):
    '''
    error thrown while attempting to rollup incompatible nodes
    '''

    def __init__(self, nodes):
        super().__init__(nodes)

    def __str__(self):
        return self._format(
            reason='unable to rollup incompatible nodes',
            nodes=_str_arr_of_nodes(self.args[0]),
        )


class InsufficientOverlapError(JsinError):
    '''
    error thrown while attempting to rollup ObjectNodes with no overlapping fields
    '''

    def __init__(self, nodes):
        super().__init__(nodes)

    def __str__(self):
        return self._format(
            reason='unable to rollup ObjectNodes with insufficient overlaps',
            nodes=_str_arr_of_nodes(self.args[0]),
        )


class UnidentifiableTypeError(JsinError):
    '''
    error thrown for unable to identify the JSON primitive
    for a loaded JSON object
    '''

    def __init__(self, obj):
        super().__init__(obj)

    def __str__(self):
        return self._format(
            reason='unable to identify the JSON primitive from Python object',
            object=self.args[0],
        )
