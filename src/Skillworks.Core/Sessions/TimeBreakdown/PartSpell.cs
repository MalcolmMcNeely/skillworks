namespace Skillworks.Core.Sessions.TimeBreakdown;

public sealed record PartSpell(Part Part, DateTimeOffset AtUtc, long LengthMs);
