namespace Skillworks.Core.Sessions.Split;

public sealed record PartSpell(SplitPart Part, DateTimeOffset AtUtc, long LengthMs);
