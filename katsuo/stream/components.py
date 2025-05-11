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
        input (stream): Input stream with an array payload.
        output (stream): Output stream of individual elements.
    '''

    def __init__(self, shape: data.ArrayLayout):
        assert isinstance(shape, data.ArrayLayout)

        super().__init__({
            'input': wiring.In(stream.Signature(shape)),
            'output': wiring.Out(stream.Signature(shape.elem_shape)),
        })

        self.shape = shape

    def elaborate(self, platform):
        m = Module()

        idx = Signal(range(self.shape.length))

        m.d.comb += [
            self.input.ready.eq(self.output.ready & (idx == self.shape.length - 1)),
            self.output.valid.eq(self.input.valid),
            self.output.payload.eq(self.input.payload[idx]),
        ]

        with m.If(self.output.valid & self.output.ready):
            m.d.sync += idx.eq(idx + 1)

            with m.If(idx == self.shape.length - 1):
                m.d.sync += idx.eq(0)

        return m
