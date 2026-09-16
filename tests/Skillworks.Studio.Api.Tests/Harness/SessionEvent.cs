using System.Globalization;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed record SessionEvent(string Session, string EventName, string At)
{
    internal const string TitleSource = "generate_session_title";

    private const string ToolResult = "tool_result";

    // Claude Code writes this in place of the words when the content switches are off.
    internal const string Withheld = "<REDACTED>";

    public string? Person { get; init; } = TestLoki.Person;

    public string? Owner { get; init; }

    public string? RepositoryName { get; init; }

    public string? Prompt { get; init; }

    public string? Response { get; init; }

    public string? QuerySource { get; init; }

    public string? ToolName { get; init; }

    public string? Success { get; init; }

    public string? ErrorType { get; init; }

    public string? Decision { get; init; }

    public string? DecisionSource { get; init; }

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("prompt", Prompt),
        ("response", Response),
        ("query_source", QuerySource),
        ("tool_name", ToolName),
        ("success", Success),
        ("error_type", ErrorType),
        ("decision", Decision),
        ("source", DecisionSource),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
    ];

    internal static SessionEvent Prompted(string session, string at, string prompt) =>
        new(session, "user_prompt", at) { Prompt = prompt };

    internal static SessionEvent Titled(string session, string at, string title) =>
        new(session, "assistant_response", at) { Response = title, QuerySource = TitleSource };

    internal static SessionEvent ToolRan(string session, string at, string tool = "Bash") =>
        new(session, ToolResult, at) { ToolName = tool, Success = "true", DecisionSource = "config" };

    internal static SessionEvent ToolFailed(string session, string at, string tool = "Bash") =>
        new(session, ToolResult, at) { ToolName = tool, Success = "false", ErrorType = "ShellError", DecisionSource = "config" };

    internal static SessionEvent ModelFailed(string session, string at) => new(session, "api_error", at);

    internal static SessionEvent Refused(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "reject", "user_reject");

    internal static SessionEvent HookBlocked(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "reject", "hook");

    internal static SessionEvent Allowed(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "accept", "config");

    private static SessionEvent Decided(string session, string at, string tool, string decision, string source) =>
        new(session, "tool_decision", at) { ToolName = tool, Decision = decision, DecisionSource = source };

    internal static SessionEvent[] Every(string session, string firstAt, TimeSpan apart, int many) =>
    [
        .. Enumerable
            .Range(0, many)
            .Select(step => new SessionEvent(
                session,
                ToolResult,
                DateTimeOffset
                    .Parse(firstAt, CultureInfo.InvariantCulture)
                    .Add(apart * step)
                    .ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture)))
    ];
}
