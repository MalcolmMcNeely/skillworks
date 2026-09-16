namespace Skillworks.Core.Activations;

public sealed record Activation(
    string Skill,
    DateTimeOffset AtUtc,
    string Session,
    string? Repository,
    string? Trigger);
