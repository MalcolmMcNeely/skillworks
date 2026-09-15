using Skillworks.Core.EventsStore;

namespace Skillworks.Core.Provenance;

public sealed record SkillEvent(string Skill, DateTimeOffset At, SkillOrigin Origin)
{
    internal const string EventName = "skill_activated";

    internal static SkillEvent? From(TelemetryEvent recorded) => recorded.Attribute(EventAttributes.Skill) is { } skill
        ? new SkillEvent(skill, recorded.At, SkillOrigin.Of(recorded.Attribute))
        : null;
}
