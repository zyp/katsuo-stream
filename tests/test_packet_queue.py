import pytest

from amaranth import *
from amaranth.sim import Simulator, SimulatorContext

from katsuo.stream import Packet, PacketQueue
from katsuo.stream.packet.queue import _InputLogic, _OutputLogic
from katsuo.stream.sim import *

@pytest.mark.parametrize('i_semantics', [Packet.Semantics.LAST, Packet.Semantics.FIRST_LAST, Packet.Semantics.END, Packet.Semantics.FIRST_END])
@pytest.mark.parametrize('o_semantics', [Packet.Semantics.LAST, Packet.Semantics.FIRST_LAST, Packet.Semantics.END, Packet.Semantics.FIRST_END])
def test_packet_queue(i_semantics, o_semantics):
    dut = PacketQueue(8, depth = 8, i_semantics = i_semantics, o_semantics = o_semantics)
    sim = Simulator(dut)
    sim.add_clock(1e-6)

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        await send_packet(ctx, dut.i, [1, 2, 3])
        await send_packet(ctx, dut.i, [4, 5, 6, 7, 8])

        # If input semantics supports discard, send an incomplete packet.
        if i_semantics.has_first:
            await send_packet(ctx, dut.i, [9, 10, 11], omit_end = True)

        await send_packet(ctx, dut.i, [12, 13, 14])
        await send_packet(ctx, dut.i, [15, 16, 17])
        
    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        assert await recv_packet(ctx, dut.o) == [1, 2, 3]
        assert await recv_packet(ctx, dut.o) == [4, 5, 6, 7, 8]
        assert await recv_packet(ctx, dut.o) == [12, 13, 14]
        assert await recv_packet(ctx, dut.o) == [15, 16, 17]

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    with sim.write_vcd('test.vcd'):
        sim.run()

@pytest.mark.parametrize('i_semantics', [Packet.Semantics.LAST, Packet.Semantics.FIRST_LAST, Packet.Semantics.END, Packet.Semantics.FIRST_END])
@pytest.mark.parametrize('o_semantics', [Packet.Semantics.FIRST_LAST, Packet.Semantics.FIRST_END])
def test_packet_queue_replay(i_semantics, o_semantics):
    dut = PacketQueue(8, depth = 8, i_semantics = i_semantics, o_semantics = o_semantics, max_inflight = 1)
    sim = Simulator(dut)
    sim.add_clock(1e-6)

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        await send_packet(ctx, dut.i, [1, 2, 3])
        await send_packet(ctx, dut.i, [4, 5, 6, 7, 8])
        await send_packet(ctx, dut.i, [9, 10, 11])
        
    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        assert await recv_packet(ctx, dut.o) == [1, 2, 3]
        await ctx.tick().repeat(5)
        assert ctx.get(dut.o.valid) == 0

        ctx.set(dut.replay, 1)
        await ctx.tick()
        ctx.set(dut.replay, 0)

        assert await recv_packet(ctx, dut.o) == [1, 2, 3]
        await ctx.tick().repeat(5)
        assert ctx.get(dut.o.valid) == 0

        ctx.set(dut.ack, 1)
        await ctx.tick()
        ctx.set(dut.ack, 0)

        assert await recv_packet(ctx, dut.o) == [4, 5, 6, 7, 8]

        ctx.set(dut.ack, 1)
        await ctx.tick()
        ctx.set(dut.ack, 0)

        assert await recv_packet(ctx, dut.o) == [9, 10, 11]

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    with sim.write_vcd('test.vcd'):
        sim.run()

from amaranth.hdl import Assume, Cover

def assume_stream_rules(m, stream):
    '''Assume that a stream obeys stream rules.'''
    past_valid = Signal()
    past_ready = Signal()
    past_payload = Signal.like(stream.payload)

    m.d.sync += [
        past_valid.eq(stream.valid),
        past_ready.eq(stream.ready),
        past_payload.eq(stream.payload),
    ]

    with m.If(past_valid & ~past_ready):
        m.d.comb += [
            Assume(stream.valid),
            Assume(stream.payload == past_payload),
        ]

def assert_stream_rules(m, stream):
    '''Assert that a stream obeys stream rules.'''
    past_valid = Signal()
    past_ready = Signal()
    past_payload = Signal.like(stream.payload)

    m.d.sync += [
        past_valid.eq(stream.valid),
        past_ready.eq(stream.ready),
        past_payload.eq(stream.payload),
    ]

    with m.If(past_valid & ~past_ready):
        m.d.comb += [
            Assert(stream.valid),
            Assert(stream.payload == past_payload),
        ]

def test_formal_input_logic_ptrs(formal):
    '''Write pointer must only advance and is not allowed to catch up to read pointer.'''

    m = Module()
    m.submodules.dut = dut = _InputLogic(shape = 8, semantics = Packet.Semantics.FIRST_LAST, addr_width = 3)

    past_w_ptr = Signal.like(dut.ptrs.w_ptr)
    past_r_ptr = Signal.like(dut.ptrs.r_ptr)

    m.d.sync += [
        past_w_ptr.eq(dut.ptrs.w_ptr),
        past_r_ptr.eq(dut.ptrs.r_ptr),
    ]

    with m.If(past_w_ptr >= past_r_ptr):
        m.d.comb += [
            Assume((dut.ptrs.r_ptr >= past_r_ptr) & (dut.ptrs.r_ptr <= past_w_ptr)),
            Assert((dut.ptrs.w_ptr >= past_w_ptr) | (dut.ptrs.w_ptr < past_r_ptr)),
        ]
    with m.Else():
        m.d.comb += [
            Assume((dut.ptrs.r_ptr >= past_r_ptr) | (dut.ptrs.r_ptr <= past_w_ptr)),
            Assert((dut.ptrs.w_ptr >= past_w_ptr) & (dut.ptrs.w_ptr < past_r_ptr)),
        ]

    formal(m, ports = dut, depth = 20)

def test_formal_output_logic_ptrs(formal):
    '''Read pointer must only advance and is not allowed to advance past write pointer.'''

    m = Module()
    m.submodules.dut = dut = _OutputLogic(shape = 8, semantics = Packet.Semantics.FIRST_LAST, addr_width = 3)

    past_w_ptr = Signal.like(dut.ptrs.w_ptr)
    past_r_ptr = Signal.like(dut.ptrs.r_ptr)

    m.d.sync += [
        past_w_ptr.eq(dut.ptrs.w_ptr),
        past_r_ptr.eq(dut.ptrs.r_ptr),
    ]

    with m.If(past_w_ptr >= past_r_ptr):
        m.d.comb += [
            Assume((dut.ptrs.w_ptr >= past_w_ptr) | (dut.ptrs.w_ptr < past_r_ptr)),
            Assert((dut.ptrs.r_ptr >= past_r_ptr) & (dut.ptrs.r_ptr <= past_w_ptr)),
        ]
    with m.Else():
        m.d.comb += [
            Assume((dut.ptrs.w_ptr >= past_w_ptr) & (dut.ptrs.w_ptr < past_r_ptr)),
            Assert((dut.ptrs.r_ptr >= past_r_ptr) | (dut.ptrs.r_ptr <= past_w_ptr)),
        ]

    formal(m, ports = dut, depth = 20)

def test_formal_replay_stream_rules(formal):
    '''Output stream must obey stream rules.'''

    m = Module()
    m.submodules.dut = dut = PacketQueue(8, depth = 8, i_semantics = Packet.Semantics.FIRST_LAST, o_semantics = Packet.Semantics.FIRST_LAST, max_inflight = 1)

    assert_stream_rules(m, dut.o)

    formal(m, ports = dut, depth = 20)

def test_formal_stream_rules(formal):
    '''Output stream must obey stream rules.'''

    m = Module()
    m.submodules.dut = dut = PacketQueue(8, depth = 8, i_semantics = Packet.Semantics.FIRST_LAST, o_semantics = Packet.Semantics.FIRST_LAST)

    assert_stream_rules(m, dut.o)

    formal(m, ports = dut, depth = 20)

def test_formal_no_complete_input(formal):
    '''Output stream must not produce anything before a complete packet has been input.'''

    m = Module()
    m.submodules.dut = dut = PacketQueue(8, depth = 8, i_semantics = Packet.Semantics.FIRST_LAST, o_semantics = Packet.Semantics.FIRST_LAST)

    m.d.comb += [
        Assume(dut.i.payload.last == 0),
        Assert(dut.o.valid == 0),
    ]

    formal(m, ports = dut, depth = 20)

def test_formal_contiguous_packets(formal):
    '''Output stream must produce contiguous packets as long as the output is ready.'''

    m = Module()
    m.submodules.dut = dut = PacketQueue(8, depth = 8, i_semantics = Packet.Semantics.FIRST_LAST, o_semantics = Packet.Semantics.FIRST_LAST)

    m.d.comb += dut.o.ready.eq(1)

    past_valid = Signal()
    m.d.sync += past_valid.eq(dut.o.valid)

    with m.If(dut.o.valid):
        m.d.comb += Assert(past_valid | dut.o.payload.first)

    formal(m, ports = dut, depth = 20)

def test_formal_packets(formal):
    '''Check that packets are transmitted correctly regardless of flow control.'''
    m = Module()
    m.submodules.dut = dut = PacketQueue(8, depth = 8, i_semantics = Packet.Semantics.FIRST_LAST, o_semantics = Packet.Semantics.FIRST_LAST)

    input_tokens = [
        {'data': 1, 'last': 1},
        {'data': 2},
        {'data': 3, 'first': 1},
        {'data': 4},
        {'data': 5, 'last': 1},
        {'data': 6, 'first': 1},
        {'data': 7},
        {'data': 8, 'last': 1},
    ]
    input_array = Array(Const(v, Packet(8, semantics = Packet.Semantics.FIRST_LAST)) for v in input_tokens)
    input_idx = Signal(range(len(input_tokens) + 1))

    m.d.comb += dut.i.payload.eq(input_array[input_idx])
    with m.If(input_idx >= len(input_tokens)):
        m.d.comb += Assume(dut.i.valid == 0)

    with m.If(dut.i.valid & dut.i.ready):
        m.d.sync += input_idx.eq(input_idx + 1)

    output_tokens = [
        {'data': 1, 'first': 1, 'last': 1},
        {'data': 3, 'first': 1},
        {'data': 4},
        {'data': 5, 'last': 1},
        {'data': 6, 'first': 1},
        {'data': 7},
        {'data': 8, 'last': 1},
    ]
    output_array = Array(Const(v, Packet(8, semantics = Packet.Semantics.FIRST_LAST)) for v in output_tokens)
    output_idx = Signal(range(len(output_tokens) + 1))

    with m.If(dut.o.valid):
        m.d.comb += Assert(Value.cast(dut.o.payload) == output_array[output_idx])
        with m.If(dut.o.ready):
            m.d.sync += output_idx.eq(output_idx + 1)

    # Count the number of cycles the output is ready after we know all input has been provided.
    ready_cycles = Signal(range(20))
    with m.If((input_idx == len(input_tokens)) & dut.o.ready):
        m.d.sync += ready_cycles.eq(ready_cycles + 1)
    
    # If we've had enough ready cycles to output all output tokens, assert that we've done so.
    with m.If(ready_cycles >= len(output_tokens)):
        m.d.comb += Assert(output_idx == len(output_tokens))

    m.d.comb += Cover(output_idx == len(output_tokens))

    formal(m, ports = dut, depth = 20)

import subprocess
import textwrap
from amaranth.back import rtlil
from amaranth import ValueLike

class FormalError(Exception):
    pass

def flatten_ports(ports):
    if isinstance(ports, ValueLike):
        yield Value.cast(ports)
    elif hasattr(ports, 'signature'):
        yield from (Value.cast(v) for *_, v in ports.signature.flatten(ports))
    else:
        for p in ports:
            yield from flatten_ports(p)

@pytest.fixture
def formal(tmp_path):
    def _exec(spec, ports, depth):
        __tracebackhide__ = True

        ports = list(flatten_ports(ports))

        top = rtlil.convert(spec, ports = ports, platform = 'formal')

        config = textwrap.dedent(f'''\
            [options]
            mode bmc
            depth {depth}
            wait on
            
            [engines]
            smtbmc
                                
            [script]
            read_rtlil top.il
            prep
                                
            [file top.il]
            {top}
        ''')

        res = subprocess.run(['sby', '-f', '-d', tmp_path], input = config, text = True)
        if res.returncode != 0:
            raise FormalError('Formal verification failed')

    return _exec
