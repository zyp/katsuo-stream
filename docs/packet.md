`katsuo.stream` supports packetized streams with the [Packet][katsuo.stream.Packet] type that can be used as a stream payload shape.

## Semantics

There are multiple ways tokens on a stream can be delimited into packets, using different flags with different semantics.

### Last semantics

Last semantics is the most common way to packetize a stream.
Last semantics adds a `last` flag to the payload token that is asserted during the last data transfer of the packet.

wavedrom (
    {signal: [
        { name: "clk", wave: "p...." },
        { name: "ready", wave: "01..0" },
        { name: "valid", wave: "01..0" },
        { name: "payload.data", wave: "x345x" },
        { name: "payload.last", wave: "0..10" },
    ]}
)

### First semantics

First semantics adds a `first` flag to the payload token that is asserted during the first data transfer of the packet.

When packet completion is known (e.g. by the packet size being fixed or by using first and last semantics), reception of a `first` token in the middle of an incomplete packet can be used to discard partial state and start over.

wavedrom (
    {signal: [
        { name: "clk", wave: "p...." },
        { name: "ready", wave: "01..0" },
        { name: "valid", wave: "01..0" },
        { name: "payload.data", wave: "x345x" },
        { name: "payload.first", wave: "010.." },
    ]}
)

### First and last semantics

First and last semantics combines the behavior of first semantics and last semantics.

wavedrom (
    {signal: [
        { name: "clk", wave: "p...." },
        { name: "ready", wave: "01..0" },
        { name: "valid", wave: "01..0" },
        { name: "payload.data", wave: "x345x" },
        { name: "payload.first", wave: "010.." },
        { name: "payload.last", wave: "0..10" },
    ]}
)

### End semantics

End semantics adds an `end` flag to the payload token that is asserted during a separate transfer after the last data transfer of the packet.
The `data` field is not valid during this transfer.

wavedrom (
    {signal: [
        { name: "clk", wave: "p....." },
        { name: "ready", wave: "01...0" },
        { name: "valid", wave: "01...0" },
        { name: "payload.data", wave: "x345x." },
        { name: "payload.end", wave: "0...10" },
    ]}
)

