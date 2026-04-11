import pytest

from amaranth.sim import Simulator, SimulatorContext

from katsuo.stream import Packet, SyncFIFOBuffered
from katsuo.stream.sim import *

def test_put_get():
    dut = SyncFIFOBuffered(shape = 8, depth = 1)

    sim = Simulator(dut)
    sim.add_clock(1e-6)

    payloads = [1, 2, 3, 4, 5, 6]

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        for payload in payloads:
            await stream_put(ctx, dut.i, payload)

    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        for expected in payloads:
            assert await stream_get(ctx, dut.o) == expected

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    sim.run()

@pytest.mark.parametrize('semantics', Packet.Semantics)
def test_send_recv_packet(semantics):
    dut = SyncFIFOBuffered(shape = Packet(semantics = semantics), depth = 1)

    sim = Simulator(dut)
    sim.add_clock(1e-6)

    payloads = [
        [1, 2, 3],
        [4, 5, 6],
    ]

    # End semantics supports zero-length packets.
    if semantics == Packet.Semantics.END:
        payloads.append([])

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        for payload in payloads:
            await send_packet(ctx, dut.i, payload)

            if semantics == Packet.Semantics.FIRST_LAST:
                # With first and last semantics, we can send extra tokens between packets that will be dropped upon reception of the first token of the next packet.
                await stream_put(ctx, dut.i, {'data': 100})

    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        for expected in payloads:
            assert await recv_packet(ctx, dut.o) == expected

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    sim.run()
