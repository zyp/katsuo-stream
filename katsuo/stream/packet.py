'''Packetized data streams.'''

from amaranth import ShapeLike
from amaranth.lib import data

import enum

__all__ = ['Packet']

class Packet(data.StructLayout):
    '''Payload shape for a packetized data stream.

    Args:
        data_shape: Shape of a data token.
        semantics: Semantics of the packetized data stream.
    '''

    class Semantics(enum.Enum):
        '''Semantics of the packetized data stream.'''

        LAST = enum.auto()
        '''Payload has a `last` field that's asserted during the last data transfer of a packet.'''

        FIRST_LAST = enum.auto()
        '''Payload has a `first` field that's asserted during the first data transfer of a packet in addition to the `last` field.'''

        END = enum.auto()
        '''Payload has an `end` field that's asserted during a separate transfer after the last data transfer of a packet.'''

        FIRST_END = enum.auto()
        '''Payload has a `first` field that's asserted during the first data transfer of a packet in addition to the `end` field.'''

        @property
        def has_first(self):
            '''True if the semantics includes a `first` field.'''
            return self in {self.FIRST_LAST, self.FIRST_END}

        @property
        def has_last(self):
            '''True if the semantics includes a `last` field.'''
            return self in {self.LAST, self.FIRST_LAST}

        @property
        def has_end(self):
            '''True if the semantics includes an `end` field.'''
            return self in {self.END, self.FIRST_END}

    def __init__(self, data_shape: ShapeLike = 8, *, semantics: Semantics = Semantics.LAST):
        if not isinstance(semantics, self.Semantics):
            raise TypeError(f'semantics must be of type Packet.Semantics, not {type(semantics)}')

        self.semantics = semantics

        layout = {'data': data_shape}
        if semantics.has_first:
            layout['first'] = 1
        if semantics.has_last:
            layout['last'] = 1
        if semantics.has_end:
            layout['end'] = 1

        super().__init__(layout)
