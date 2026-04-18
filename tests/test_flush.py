from amaranth.sim import Simulator, SimulatorContext

from katsuo.stream import Flush
from katsuo.stream.sim import stream_put, recv_packet

def test_flush():
    dut = Flush(4)

    sim = Simulator(dut)
    sim.add_clock(1e-6)

    @sim.add_testbench
    async def input_testbench(ctx: SimulatorContext):
        await ctx.tick()

        for i in range(10):
            await stream_put(ctx, dut.input, {'data': i, 'last': 0})

    @sim.add_testbench
    async def output_testbench(ctx: SimulatorContext):
        packet = await recv_packet(ctx, dut.output)
        
        assert packet == list(range(10))

    @sim.add_process
    async def timeout(ctx: SimulatorContext):
        await ctx.tick().repeat(10_000)
        raise TimeoutError('Simulation timed out')

    sim.run()
