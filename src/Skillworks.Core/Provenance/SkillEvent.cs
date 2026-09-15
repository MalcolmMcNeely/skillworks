using Skillworks.Core.EventsStore;

namespace Skillworks.Core.Provenance;

// Trigger stays verbatim (claude-proactive, user-slash): putting it into words is the screen's job.
public sealed record SkillEvent(
    string Skill,
    DateTimeOffset At,
    string? Trigger,
    string? Source,
    string? Plugin,
    string? Marketplace)
{
    internal const string EventName = "skill_activated";

    internal static SkillEvent? From(TelemetryEvent recorded) => recorded.Attribute("skill.name") is { } skill
        ? new SkillEvent(
            skill,
            recorded.At,
            recorded.Attribute("invocation_trigger"),
            recorded.Attribute("skill.source"),
            recorded.Attribute("plugin.name"),
            recorded.Attribute("marketplace.name"))
        : null;
}
