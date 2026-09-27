namespace Skillworks.Core.Sessions.Steps;

// Claude Code writes an event when a Step ends, so AtUtc is worked back from the length.
// Skill is null both where none was in force and where Claude Code would not name one, so Unnamed tells them apart.
// Only a Span names the agent behind a Tool call, so without one SkillKnown is false and Skill is never guessed.
public sealed record Step(
    string Id,
    StepKind Kind,
    DateTimeOffset AtUtc,
    long LengthMs,
    string? Tool,
    bool Fault,
    string? Words,
    string? Skill = null,
    bool Unnamed = false,
    decimal Cost = 0,
    bool SkillKnown = true);
