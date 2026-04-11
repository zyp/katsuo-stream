from amaranth import *
from amaranth import ShapeLike
from amaranth.lib import wiring, stream, memory
from amaranth.utils import ceil_log2

from . import Packet

class PacketQueue(wiring.Component):
    '''FIFO queue for packetized data streams.

    A packet will only be released on the output side once it is fully received on the input side.
    If the input semantics includes the `first` signal, a partially received packet will be discarded when a new packet starts.
    If the `max_inflight` parameter is set, the queue includes acknowledgment and replay functionality to allow retransmission of unacknowledged packets.

    This makes the queue suitable for the following use cases:
    - Ingress buffering where packets may be dropped partway on error conditions.
    - Egress buffering where packets must be sent as contiguous bursts.
    - Egress buffering with retransmission capabilities.

    Behavior is undefined if a packet larger than the queue depth is received.

    Args:
        shape: Shape of the packetized data stream.
        depth: Depth of the FIFO queue.
        i_semantics: Packet semantics of the input stream.
        o_semantics: Packet semantics of the output stream.
        max_inflight: Maximum number of in-flight packets for replay functionality.

    Attributes:
        i (stream): Input stream.
        o (stream): Output stream.
        ack (in): Acknowledgment signal for completed packets (if `max_inflight` is set).
        replay (in): Replay signal to resend unacknowledged packets (if `max_inflight` is set).
    '''

    def __init__(self, shape: ShapeLike, *, depth: int, i_semantics: Packet.Semantics, o_semantics: Packet.Semantics, max_inflight: int | None = None):
        signature = {
            'i': wiring.In(stream.Signature(Packet(shape, semantics = i_semantics))),
            'o': wiring.Out(stream.Signature(Packet(shape, semantics = o_semantics))),
        }

        if (depth  & (depth - 1) != 0) or depth <= 0:
            raise ValueError('depth must be a power of two')

        if max_inflight is None:
            pass
        elif (max_inflight & (max_inflight - 1) != 0) or max_inflight <= 0:
            raise ValueError('max_inflight must be a power of two')
        else:
            signature['ack'] = wiring.In(range(max_inflight + 1))
            signature['replay'] = wiring.In(1)

        super().__init__(signature)

        self._shape = shape
        self._depth = depth
        self._max_inflight = max_inflight

    def elaborate(self, platform):
        m = Module()

        addr_width = ceil_log2(self._depth)

        m.submodules.mem = mem = memory.Memory(shape = Packet(self._shape, semantics = Packet.Semantics.LAST), depth = self._depth, init = [])

        m.submodules.input_logic = input_logic = _InputLogic(shape = self._shape, semantics = self.i.payload.shape().semantics, addr_width = addr_width)
        m.submodules.output_logic = output_logic = _OutputLogic(shape = self._shape, semantics = self.o.payload.shape().semantics, addr_width = addr_width, max_inflight = self._max_inflight)

        wiring.connect(m, wiring.flipped(self.i), input_logic.i)
        wiring.connect(m, wiring.flipped(self.o), output_logic.o)
        wiring.connect(m, input_logic.w_port, mem.write_port())
        wiring.connect(m, output_logic.r_port, mem.read_port())
        wiring.connect(m, input_logic.ptrs, output_logic.ptrs)

        if self._max_inflight is not None:
            m.d.comb += [
                output_logic.ack.eq(self.ack),
                output_logic.replay.eq(self.replay),
            ]

        return m

class _PtrSignature(wiring.Signature):
    def __init__(self, addr_width):
        super().__init__({
            'w_ptr': wiring.Out(addr_width),
            'r_ptr': wiring.In(addr_width),
        })

class _InputLogic(wiring.Component):
    def __init__(self, *, shape: ShapeLike, semantics: Packet.Semantics, addr_width: int):
        super().__init__({
            'i': wiring.In(stream.Signature(Packet(shape, semantics = semantics))),
            'w_port': wiring.In(memory.WritePort.Signature(shape = Packet(shape, semantics = Packet.Semantics.LAST), addr_width = addr_width)),
            'ptrs': wiring.Out(_PtrSignature(addr_width)),
        })

        self._addr_width = addr_width

    def elaborate(self, platform):
        m = Module()

        w_ptr = Signal.like(self.ptrs.w_ptr)

        if self.i.payload.shape().semantics.has_first:
            w_actual_ptr = Mux(self.i.payload.first, self.ptrs.w_ptr, w_ptr)
        else:
            w_actual_ptr = w_ptr

        if self.i.payload.shape().semantics.has_last:
            last = self.i.payload.last
            data = self.i.payload.data
            valid = self.i.valid
        elif self.i.payload.shape().semantics.has_end:
            last = self.i.payload.end
            data = Signal.like(self.i.payload.data)
            data_valid = Signal()
            if self.i.payload.shape().semantics.has_first:
                valid = self.i.valid & data_valid & ~self.i.payload.first
                first = Signal()
                with m.If(self.i.valid & self.i.ready):
                    m.d.sync += first.eq(self.i.payload.first)
                w_actual_ptr = Mux(first, self.ptrs.w_ptr, w_ptr)
            else:
                valid = self.i.valid & data_valid
            with m.If(self.i.valid & self.i.ready):
                m.d.sync += data.eq(self.i.payload.data)
                m.d.sync += data_valid.eq(~self.i.payload.end)

        m.d.comb += [
            #self.i.ready.eq(w_ptr + 1 != self.ptrs.r_ptr),
            self.i.ready.eq((w_ptr + 1) & ((1 << self._addr_width) - 1) != self.ptrs.r_ptr),
            self.w_port.en.eq(valid & self.i.ready),
            self.w_port.addr.eq(w_actual_ptr),
            self.w_port.data.data.eq(data),
            self.w_port.data.last.eq(last),
        ]

        with m.If(valid & self.i.ready):
            m.d.sync += w_ptr.eq(w_actual_ptr + 1)
            with m.If(last):
                m.d.sync += self.ptrs.w_ptr.eq(w_actual_ptr + 1)

        return m

class _OutputLogic(wiring.Component):
    def __init__(self, *, shape: ShapeLike, semantics: Packet.Semantics, addr_width: int, max_inflight: int | None = None):
        signature = {
            'o': wiring.Out(stream.Signature(Packet(shape, semantics = semantics))),
            'r_port': wiring.In(memory.ReadPort.Signature(shape = Packet(shape, semantics = Packet.Semantics.LAST), addr_width = addr_width)),
            'ptrs': wiring.In(_PtrSignature(addr_width)),
        }

        if max_inflight is None:
            pass
        elif (max_inflight & (max_inflight - 1) != 0) or max_inflight <= 0:
            raise ValueError('max_inflight must be a power of two')
        elif not semantics.has_first:
            raise ValueError('Replay functionality requires packet semantics to include the `first` signal.')
        else:
            signature['ack'] = wiring.In(range(max_inflight + 1))
            signature['replay'] = wiring.In(1)

        super().__init__(signature)

        self._max_inflight = max_inflight

    def elaborate(self, platform):
        m = Module()

        busy = Signal()
        r_ptr = Signal.like(self.ptrs.r_ptr)
        r_valid = r_ptr != self.ptrs.w_ptr
        r_en = r_valid & (~self.o.valid | (self.o.ready)) & ~busy

        if self.o.payload.shape().semantics.has_end:
            r_en = r_valid & (~self.o.valid | (self.o.ready & ~self.r_port.data.last) | self.o.payload.end)

        m.d.comb += [
            self.ptrs.r_ptr.eq(r_ptr),
            self.r_port.en.eq(r_en),
            self.r_port.addr.eq(r_ptr),
            self.o.payload.data.eq(self.r_port.data.data),
        ]

        with m.If(self.o.ready):
            m.d.sync += self.o.valid.eq(0)

        with m.If(r_en):
            m.d.sync += r_ptr.eq(r_ptr + 1)
            m.d.sync += self.o.valid.eq(1)

        if self.o.payload.shape().semantics.has_first:
            first = Signal(init = 1)
            m.d.comb += self.o.payload.first.eq(first)

            with m.If(self.o.valid & self.o.ready):
                if self.o.payload.shape().semantics.has_last:
                    m.d.sync += first.eq(self.o.payload.last)
                if self.o.payload.shape().semantics.has_end:
                    m.d.sync += first.eq(self.o.payload.end)

        if self.o.payload.shape().semantics.has_last:
            eop = self.o.payload.last
            m.d.comb += self.o.payload.last.eq(self.r_port.data.last)
        
        if self.o.payload.shape().semantics.has_end:
            eop = self.o.payload.end
            with m.If(self.o.valid & self.o.ready):
                m.d.sync += self.o.payload.end.eq(0)

            with m.If(self.o.valid & self.o.ready & self.r_port.data.last & ~self.o.payload.end):
                m.d.sync += self.o.payload.end.eq(1)
                m.d.sync += self.o.valid.eq(1)

        if self._max_inflight is not None:
            assert self._max_inflight == 1

            commit_ptr = Signal.like(r_ptr)
            pending_replay = Signal()
            inflight = Signal()

            m.d.comb += [
                self.ptrs.r_ptr.eq(commit_ptr),
                busy.eq(inflight),
            ]

            with m.If(self.o.valid & self.o.ready & eop):
                m.d.sync += inflight.eq(1)

            with m.If(self.replay):
                m.d.sync += pending_replay.eq(1)

            with m.If((self.replay | pending_replay) & (~self.o.valid | self.o.ready)):
                m.d.sync += [
                    pending_replay.eq(0),
                    inflight.eq(0),
                    first.eq(1),
                    r_ptr.eq(commit_ptr),
                ]

            with m.If(self.ack):
                m.d.sync += [
                    inflight.eq(0),
                    commit_ptr.eq(r_ptr),
                ]

        return m
