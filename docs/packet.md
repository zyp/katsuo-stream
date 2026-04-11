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

### First semantics

First semantics adds a `first` flag to the payload token that is asserted during the first data transfer of the packet. The end of the packet is marked by a `last` or `end` flag like above.

Reception of a `first` token in the middle of an incomplete packet indicates that the previous packet may be discarded.

#### First and last

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

#### First and end

wavedrom (
    {signal: [
        { name: "clk", wave: "p....." },
        { name: "ready", wave: "01...0" },
        { name: "valid", wave: "01...0" },
        { name: "payload.data", wave: "x345x." },
        { name: "payload.first", wave: "010..." },
        { name: "payload.last", wave: "0...10" },
    ]}
)
