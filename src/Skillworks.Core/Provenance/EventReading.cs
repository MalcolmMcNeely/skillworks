namespace Skillworks.Core.Provenance;

public sealed record EventReading(IReadOnlyList<SkillEvent> Events, string? Unreachable, bool Truncated = false)
{
    public static EventReading Of(IReadOnlyList<SkillEvent> events, bool truncated) =>
        new(events, null, truncated);

    public static EventReading Failed(string reason) => new([], reason);
}
