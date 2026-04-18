'''General stream components.'''

from amaranth import *
from amaranth.lib import stream, wiring, data

from .packet import Packet

__all__ = ['Serializer', 'Flush']

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

class Flush(wiring.Component):
    def __init__(self, timeout, *, shape = 8):
        super().__init__({
            'input': wiring.In(stream.Signature(Packet(shape))),
            'output': wiring.Out(stream.Signature(Packet(shape))),
        })

        self._shape = shape
        self._timeout = timeout

    def elaborate(self, platform):
        m = Module()

        timeout_cnt = Signal(range(self._timeout + 1))
        timeout_hit = Signal()

        data = Signal(self._shape)
        last = Signal()
        valid = Signal()

        m.d.comb += [
            timeout_hit.eq(timeout_cnt == 0),

            self.input.ready.eq(~valid | (self.output.ready & self.output.valid)),

            self.output.payload.data.eq(data),
            self.output.payload.last.eq(last | timeout_hit),
            self.output.valid.eq(valid & (self.input.valid | timeout_hit)),
        ]

        with m.If(valid & ~timeout_hit):
            m.d.sync += timeout_cnt.eq(timeout_cnt - 1)

        with m.If(self.output.valid & self.output.ready):
            m.d.sync += valid.eq(0)

        with m.If(self.input.valid & self.input.ready):
            m.d.sync += [
                data.eq(self.input.payload.data),
                last.eq(self.input.payload.last),
                valid.eq(1),
                timeout_cnt.eq(self._timeout),
            ]

        return m
