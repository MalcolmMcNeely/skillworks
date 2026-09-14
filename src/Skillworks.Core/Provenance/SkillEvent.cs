namespace Skillworks.Core.Provenance;

// Trigger stays verbatim (claude-proactive, user-slash): putting it into words is the screen's job.
public sealed record SkillEvent(
    string Skill,
    DateTimeOffset At,
    string? Trigger,
    string? Source,
    string? Plugin,
    string? Marketplace);
