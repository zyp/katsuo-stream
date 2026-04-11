`katsuo.stream` supports packetized streams with the [Packet][katsuo.stream.Packet] type that can be used as a stream payload shape.

Packets have a `data` field (shorthand `d`) with `data_shape`, and an optional `header` field (shorthand `h`) with `header_shape`.

The `data` field changes on each transfer, while the `header` field must have the same value for all transfers (including the `end` transfer, if applicable) belonging to the same packet.

## Semantics

There are multiple ways tokens on a stream can be delimited into packets, using different flags with different semantics.

### Last semantics

Last semantics is the most common way to packetize a stream.
Last semantics adds a `last` flag to the payload token that is asserted during the last `data` transfer of the packet.

wavedrom (
    {signal: [
        { name: "clk", wave: "p......." },
        { name: "ready", wave: "01.....0" },
        { name: "valid", wave: "01.....0" },
        { name: "payload.header", wave: "x7..8..x" },
        { name: "payload.data", wave: "x345345x" },
        { name: "payload.last", wave: "0..10.10" },
    ]}
)

### End semantics

End semantics adds an `end` flag to the payload token that is asserted during a separate transfer after the last `data` transfer of the packet.
The `data` field is not valid during this transfer.

wavedrom (
    {signal: [
        { name: "clk", wave: "p........." },
        { name: "ready", wave: "01.......0" },
        { name: "valid", wave: "01.......0" },
        { name: "payload.header", wave: "x7...8...x" },
        { name: "payload.data", wave: "x345x345x." },
        { name: "payload.end", wave: "0...10..10" },
    ]}
)

### First semantics

First semantics adds a `first` flag to the payload token that is asserted during the first data transfer of the packet. The end of the packet is marked by a `last` or `end` flag like above.

Reception of a `first` token before the `last`/`end` token of the previous packet indicates that the previous packet was incomplete and may be discarded.

#### First and last

wavedrom (
    {signal: [
        { name: "clk", wave: "p........." },
        { name: "ready", wave: "01.......0" },
        { name: "valid", wave: "01.......0" },
        { name: "payload.header", wave: "x7..8.9..x" },
        { name: "payload.data", wave: "x34534345x" },
        { name: "payload.first", wave: "010.1010.." },
        { name: "payload.last", wave: "0..10...10" },
    ]}
)

#### First and end

wavedrom (
    {signal: [
        { name: "clk", wave: "p..........." },
        { name: "ready", wave: "01.........0" },
        { name: "valid", wave: "01.........0" },
        { name: "payload.header", wave: "x7...8.9...x" },
        { name: "payload.data", wave: "x345x34345x." },
        { name: "payload.first", wave: "010..1010..." },
        { name: "payload.end", wave: "0...10....10" },
    ]}
)
