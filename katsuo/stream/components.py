'''General stream components.'''

from amaranth import *
from amaranth.lib import stream, wiring, data

from .packet import Packet

__all__ = ['Serializer']

class Serializer(wiring.Component):
    '''Serializer converting a stream with an array payload into a stream of individual elements.

    Args:
        shape: Shape of the input stream.

    Attributes:
        i (stream): Input stream with an array payload.
        o (stream): Output stream of individual elements.
    '''

    def __init__(self, shape: data.ArrayLayout):
        assert isinstance(shape, data.ArrayLayout)

        super().__init__({
            'i': wiring.In(stream.Signature(shape)),
            'o': wiring.Out(stream.Signature(shape.elem_shape)),
        })

        self.shape = shape

    def elaborate(self, platform):
        m = Module()

        idx = Signal(range(self.shape.length))

        m.d.comb += [
            self.i.ready.eq(self.o.ready & (idx == self.shape.length - 1)),
            self.o.valid.eq(self.i.valid),
            self.o.payload.eq(self.i.payload[idx]),
        ]

        with m.If(self.o.valid & self.o.ready):
            m.d.sync += idx.eq(idx + 1)

            with m.If(idx == self.shape.length - 1):
                m.d.sync += idx.eq(0)

        return m
