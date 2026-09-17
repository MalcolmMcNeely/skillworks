using System.Globalization;

namespace Skillworks.Studio.Api.Tests.Harness;

// Claude Code sends every number on an event as a string.
public sealed record ApiRequest(
    string At,
    string? Skill = null,
    string Model = "claude-opus-5[1m]",
    string? Effort = null,
    decimal CostUsd = 0m,
    long InputTokens = 0,
    long OutputTokens = 0,
    long CacheReadTokens = 0,
    long CacheCreationTokens = 0,
    string? Owner = null,
    string? RepositoryName = null)
{
    internal const string EventName = "api_request";

    public string Session { get; init; } = TestLoki.Session;

    public string? Person { get; init; } = TestLoki.Person;

    public long DurationMs { get; init; } = 2140;

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("skill.name", Skill),
        ("model", Model),
        ("effort", Effort),
        ("cost_usd", CostUsd.ToString(CultureInfo.InvariantCulture)),
        ("input_tokens", InputTokens.ToString(CultureInfo.InvariantCulture)),
        ("output_tokens", OutputTokens.ToString(CultureInfo.InvariantCulture)),
        ("cache_read_tokens", CacheReadTokens.ToString(CultureInfo.InvariantCulture)),
        ("cache_creation_tokens", CacheCreationTokens.ToString(CultureInfo.InvariantCulture)),
        ("request_id", $"req_{Guid.NewGuid():N}"),
        ("duration_ms", DurationMs.ToString(CultureInfo.InvariantCulture)),
        ("speed", "normal"),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
    ];
}
