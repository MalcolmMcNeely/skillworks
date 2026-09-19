namespace Skillworks.Core.Watch.Activations;

public sealed record Activation(
    string Skill,
    DateTimeOffset AtUtc,
    string Session,
    string? Repository,
    string? Trigger);
