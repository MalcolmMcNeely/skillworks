namespace Skillworks.Core.Sessions.Agents;

// What a Span says and no event does: a stretch of the run, with no word yet about which part it belongs to.
public sealed record Stretch(DateTimeOffset AtUtc, long LengthMs);
