'''
define the errors caused by Json Schema Inferer
'''

from typing import Self


class JsinError(TypeError):
    '''
    base class defining the type of errors thrown by the jsin module
    '''

    loc: tuple[str, ...]

    def __init__(self, *args):
        super(TypeError, self).__init__(*args)
        self.loc = tuple()

    def under(self, parent_loc: str) -> Self:
        '''
        log the parent location

        usage:
            try:
                ...
            except JsinError as e:
                raise e.under(location) from None
        '''
        new_error = type(self)(*self.args)
        new_error.loc = (parent_loc, *self.loc)

        return new_error

    def _lines(self, **info: dict[str, str]):
        return (
            'Error occurred while inferring schema from a JSON object',
            f'\tlocation: {self.loc}',
            *(f'\t{key}: {value}' for key, value in info.items()),
        )

    def __str__(self):
        return '\n'.join(self._lines())
