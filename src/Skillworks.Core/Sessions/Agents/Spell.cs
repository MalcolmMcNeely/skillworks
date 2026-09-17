namespace Skillworks.Core.Sessions.Agents;

// Only a Span measures this, and a Span never says which part it belongs to.
public sealed record Spell(DateTimeOffset AtUtc, long LengthMs);
