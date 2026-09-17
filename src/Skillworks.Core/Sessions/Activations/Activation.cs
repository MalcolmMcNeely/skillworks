namespace Skillworks.Core.Sessions.Activations;

// No event says a Skill finished, so FollowedMs runs to the next Activation or to the end of the run.
public sealed record Activation(
    string Id,
    string Skill,
    DateTimeOffset AtUtc,
    long FollowedMs,
    string? Trigger);
