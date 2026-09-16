using System.Globalization;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed record SessionEvent(string Session, string EventName, string At)
{
    internal const string TitleSource = "generate_session_title";

    // Claude Code writes this in place of the words when the content switches are off.
    internal const string Withheld = "<REDACTED>";

    public string? Person { get; init; } = TestLoki.Person;

    public string? Owner { get; init; }

    public string? RepositoryName { get; init; }

    public string? Prompt { get; init; }

    public string? Response { get; init; }

    public string? QuerySource { get; init; }

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("prompt", Prompt),
        ("response", Response),
        ("query_source", QuerySource),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
    ];

    internal static SessionEvent Prompted(string session, string at, string prompt) =>
        new(session, "user_prompt", at) { Prompt = prompt };

    internal static SessionEvent Titled(string session, string at, string title) =>
        new(session, "assistant_response", at) { Response = title, QuerySource = TitleSource };

    internal static SessionEvent[] Every(string session, string firstAt, TimeSpan apart, int many) =>
    [
        .. Enumerable
            .Range(0, many)
            .Select(step => new SessionEvent(
                session,
                "tool_result",
                DateTimeOffset
                    .Parse(firstAt, CultureInfo.InvariantCulture)
                    .Add(apart * step)
                    .ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture)))
    ];
}
