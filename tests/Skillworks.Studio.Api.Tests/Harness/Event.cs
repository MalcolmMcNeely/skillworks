namespace Skillworks.Studio.Api.Tests.Harness;

public sealed record Event(
    string Skill,
    string At,
    string? Trigger = null,
    string? Source = null,
    string? Plugin = null,
    string? Marketplace = null);
