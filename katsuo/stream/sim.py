'''Simulation helpers for streams.'''

from collections.abc import Iterable
from typing import Any

from amaranth.sim import SimulatorContext

from amaranth.lib import stream

from . import Packet

__all__ = ['stream_put', 'stream_get', 'send_packet', 'recv_packet']

async def stream_put(ctx: SimulatorContext, stream: stream.Interface, payload, *, domain = 'sync', context = None):
    '''Put a payload token into a stream.

    Args:
        ctx: Simulator context.
        stream: Target stream.
        payload: Payload token.
        domain: Clock domain.
        context: Context for looking up the clock domain.
    '''

    ctx.set(stream.valid, 1)
    ctx.set(stream.payload, payload)

    await ctx.tick(domain = domain, context = context).until(stream.ready == 1)

    ctx.set(stream.valid, 0)

async def stream_get(ctx: SimulatorContext, stream: stream.Interface, *, domain = 'sync', context = None):
    '''Get a payload token from a stream.

    Args:
        ctx: Simulator context.
        stream: Target stream.
        domain: Clock domain.
        context: Context for looking up the clock domain.

    Returns:
        Payload token.
    '''

    ctx.set(stream.ready, 1)

    payload, = await ctx.tick(domain = domain, context = context).sample(stream.payload).until(stream.valid == 1)

    ctx.set(stream.ready, 0)
    return payload

async def send_packet(ctx: SimulatorContext, stream: stream.Interface, packet: Iterable[Any], *, domain = 'sync', context = None):
    '''Send a packet to a packetized stream.

    Args:
        ctx: Simulator context.
        stream: Target stream.
        packet: Packet contents.
        domain: Clock domain.
        context: Context for looking up the clock domain.
    '''

    shape = stream.payload.shape()
    if not isinstance(shape, Packet):
        raise TypeError('send_packet() can only be used on streams with Packet payloads')

    ctx.set(stream.valid, 1)

    for i, e in enumerate(packet):
        ctx.set(stream.payload.data, e)
        if shape.semantics.has_first:
            ctx.set(stream.payload.first, i == 0)
        if shape.semantics.has_last:
            ctx.set(stream.payload.last, i == len(packet) - 1)
        if shape.semantics.has_end:
            ctx.set(stream.payload.end, 0)

        await ctx.tick(domain = domain, context = context).until(stream.ready == 1)

    if shape.semantics.has_end:
        ctx.set(stream.payload.end, 1)
        await ctx.tick(domain = domain, context = context).until(stream.ready == 1)
        ctx.set(stream.payload.end, 0)

    ctx.set(stream.valid, 0)

async def recv_packet(ctx: SimulatorContext, stream: stream.Interface, *, domain = 'sync', context = None) -> list[Any]:
    '''Receive a packet from a packetized stream.

    Note:
        Does not support streams with FIRST semantics, as we can't tell the end of the current packet before receiving
        the first token of the next packet, and we have nowhere to store that token until the next `recv_packet()` call.

    Args:
        ctx: Simulator context.
        stream: Target stream.
        domain: Clock domain.
        context: Context for looking up the clock domain.

    Returns:
        Packet contents.
    '''

    shape = stream.payload.shape()
    if not isinstance(shape, Packet):
        raise TypeError('recv_packet() can only be used on streams with Packet payloads')
    if shape.semantics == Packet.Semantics.FIRST:
        raise TypeError('recv_packet() does not support FIRST semantics')

    buf = []

    ctx.set(stream.ready, 1)

    while True:
        payload, = await ctx.tick(domain = domain, context = context).sample(stream.payload).until(stream.valid == 1)

        if shape.semantics.has_first and payload.first:
            buf.clear()

        if shape.semantics.has_end and payload.end:
            break

        buf.append(payload.data)

        if shape.semantics.has_last and payload.last:
            break

    ctx.set(stream.ready, 0)

    return buf
