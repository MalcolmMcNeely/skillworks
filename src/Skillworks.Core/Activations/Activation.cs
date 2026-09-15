using Skillworks.Core.EventsStore;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

// Only what the one event says: filling a field from another event would be a guess shown as a fact.
public sealed record Activation(
    string Id,
    string Skill,
    string? SessionId,
    string? Repository,
    DateTimeOffset TimestampUtc,
    SkillOrigin Origin)
{
    // A firing Claude Code did not name belongs to no skill, as it does in the skill table.
    internal static Activation? From(TelemetryEvent recorded) => recorded.Attribute(EventAttributes.Skill) is { } skill
        ? new Activation(
            ActivationId.Of(recorded).ToString(),
            skill,
            recorded.Attribute(EventAttributes.Session),
            recorded.Repository,
            recorded.At,
            SkillOrigin.Of(recorded.Attribute))
        : null;
}
