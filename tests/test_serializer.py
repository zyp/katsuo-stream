from amaranth.lib import data
from amaranth.sim import Simulator, SimulatorContext

from katsuo.stream import Serializer
from katsuo.stream.sim import stream_put, stream_get

def test_serializer():
    dut = Serializer(data.ArrayLayout(8, 3))

    sim = Simulator(dut)
    sim.add_clock(1e-6)

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        payloads = [
            (1, 2, 3),
            (4, 5, 6),
        ]

        for payload in payloads:
            await stream_put(ctx, dut.i, payload)

    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        for expected in [1, 2, 3, 4, 5, 6]:
            assert await stream_get(ctx, dut.o) == expected

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    sim.run()
