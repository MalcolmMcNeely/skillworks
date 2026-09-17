namespace Skillworks.Core.Sessions.Split;

public sealed record Spell(SplitPart Part, DateTimeOffset AtUtc, long LengthMs);
