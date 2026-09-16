namespace Skillworks.Core.Sessions.SkillCalls;

// No event says a Skill finished, so FollowedMs runs to the next Skill call or to the end of the run.
public sealed record SkillCall(
    string Id,
    string Skill,
    DateTimeOffset AtUtc,
    long FollowedMs,
    string? Trigger);
