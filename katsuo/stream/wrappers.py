'''Stream wrappers for upstream components.'''

from amaranth import *
from amaranth import ShapeLike
from amaranth.lib import stream, wiring, fifo

__all__ = ['SyncFIFOBuffered', 'AsyncFIFOBuffered']

class SyncFIFOBuffered(wiring.Component):
    '''Wrapper around [amaranth.lib.fifo.SyncFIFOBuffered][].

    Args:
        shape: Shape of the stream.
        depth: Depth of the FIFO.

    Attributes:
        i (stream): Input stream.
        o (stream): Output stream.
    '''

    def __init__(self, *, shape: ShapeLike, depth: int):
        super().__init__({
            'i': wiring.In(stream.Signature(shape)),
            'o': wiring.Out(stream.Signature(shape)),
        })
        self.shape = shape
        self.depth = depth
        self.fifo = fifo.SyncFIFOBuffered(width = Shape.cast(self.shape).width, depth = self.depth)

    def elaborate(self, platform):
        m = Module()
        m.submodules.fifo = self.fifo

        m.d.comb += [
            # Input
            self.i.ready.eq(self.fifo.w_rdy),
            self.fifo.w_en.eq(self.i.valid),
            self.fifo.w_data.eq(self.i.payload),

            # Output
            self.o.valid.eq(self.fifo.r_rdy),
            self.o.payload.eq(self.fifo.r_data),
            self.fifo.r_en.eq(self.o.ready),
        ]

        return m

class AsyncFIFOBuffered(wiring.Component):
    '''Wrapper around [amaranth.lib.fifo.AsyncFIFOBuffered][].

    Args:
        shape: Shape of the stream.
        depth: Depth of the FIFO.

    Attributes:
        i (stream): Input stream.
        o (stream): Output stream.
    '''

    def __init__(self, *, shape: ShapeLike, depth: int):
        super().__init__({
            'i': wiring.In(stream.Signature(shape)),
            'o': wiring.Out(stream.Signature(shape)),
        })
        self.shape = shape
        self.depth = depth
        self.fifo = fifo.AsyncFIFOBuffered(width = Shape.cast(self.shape).width, depth = self.depth)

    def elaborate(self, platform):
        m = Module()
        m.submodules.fifo = self.fifo

        m.d.comb += [
            # Input
            self.i.ready.eq(self.fifo.w_rdy),
            self.fifo.w_en.eq(self.i.valid),
            self.fifo.w_data.eq(self.i.payload),

            # Output
            self.o.valid.eq(self.fifo.r_rdy),
            self.o.payload.eq(self.fifo.r_data),
            self.fifo.r_en.eq(self.o.ready),
        ]

        return m
