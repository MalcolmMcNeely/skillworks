# Health knocks on the Collector instead of counting Spans

A Collector that answers but hands nothing on is invisible to every reader Studio has. The stores
answer, the switch is on, and no Session can be read in full.

This happened. The Collector was started before its settings told it to take Spans, so it served the
events door and answered 404 on the Spans one. Every Span Claude Code sent was refused at the door
for two days, and Health showed the Trace store working throughout. The Trace store was working. It
had simply never been sent anything.

**Counting is the obvious test, and it is wrong.** Health could read what the Trace store holds and
call an empty store broken. But an empty store is the ordinary state of a quiet machine, of a new
install, and of anyone who has not run Claude Code today. All three would read broken and none of
them is. What a store holds measures how much work a person did, not whether the wiring holds.

**Knocking tests the wiring alone.** Health sends an empty payload to each of the Collector's two
doors and reads the answer. An empty payload holds no Span and no event, so it writes nothing, and
no figure a reader sees can move because Health asked. A door that answers 404 is not wired to a
store. A door that refuses the connection has no Collector behind it. Both are faults, and both name
the action that would change them.

## Consequences

The Collector is a part of its own, with a Lamp of its own. It was the one link in the chain nobody
watched, and it is the link that broke.

One Lamp covers both doors, and its Detail names the door that is shut. A part is one Lamp. Hanging
the Spans door off the Trace store's Lamp is what let this fault hide behind a part that was
working.

Health writes, which it never did before. The write is empty and it goes to the Collector, never to
a store, so a health check can move nothing Studio measures.

A Collector that takes a payload and drops it further on is still invisible. Knocking proves the
door, not the road behind it. The Trace store's own Lamp still answers for the road.
