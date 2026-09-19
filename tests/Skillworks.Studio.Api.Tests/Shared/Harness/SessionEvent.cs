using System.Globalization;
using System.Text.Json.Nodes;

namespace Skillworks.Studio.Api.Tests.Shared.Harness;

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

    public string? PromptLength { get; init; }

    public string? Response { get; init; }

    public string? ResponseLength { get; init; }

    public string? QuerySource { get; init; }

    public string? ToolName { get; init; }

    public string? Success { get; init; }

    public string? ErrorType { get; init; }

    public string? Decision { get; init; }

    public string? DecisionSource { get; init; }

    public string? DurationMs { get; init; }

    public string? Model { get; init; }

    public string? CostUsd { get; init; }

    public string? ToolInput { get; init; }

    public string? ToolUseId { get; init; }

    public string? RequestId { get; init; }

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("prompt", Prompt),
        ("prompt_length", PromptLength),
        ("response", Response),
        ("response_length", ResponseLength),
        ("query_source", QuerySource),
        ("tool_name", ToolName),
        ("success", Success),
        ("error_type", ErrorType),
        ("decision", Decision),
        ("source", DecisionSource),
        ("duration_ms", DurationMs),
        ("model", Model),
        ("cost_usd", CostUsd),
        ("tool_input", ToolInput),
        ("tool_use_id", ToolUseId),
        ("request_id", RequestId),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
    ];

    // Claude Code counts the characters on the event whether or not the switch lets the words through.
    internal static SessionEvent Prompted(string session, string at, string prompt) =>
        new(session, "user_prompt", at) { Prompt = prompt, PromptLength = Figure(prompt.Length) };

    internal static SessionEvent PromptWithheld(string session, string at, int length) =>
        new(session, "user_prompt", at) { Prompt = Withheld, PromptLength = Figure(length) };

    internal static SessionEvent Titled(string session, string at, string title) =>
        new(session, "assistant_response", at) { Response = title, QuerySource = TitleSource };

    internal static SessionEvent Answered(string session, string at, string response, string? request = null) =>
        new(session, "assistant_response", at)
        {
            Response = response,
            ResponseLength = Figure(response.Length),
            RequestId = request,
        };

    internal static SessionEvent AnswerWithheld(string session, string at, int length) =>
        new(session, "assistant_response", at) { Response = Withheld, ResponseLength = Figure(length) };

    internal static SessionEvent Turned(
        string session,
        string at,
        int lengthMs = 0,
        decimal cost = 0m,
        string? request = null,
        string? source = null) =>
        new(session, "api_request", at)
        {
            Model = "claude-opus-5",
            DurationMs = Figure(lengthMs),
            CostUsd = cost.ToString(CultureInfo.InvariantCulture),
            RequestId = request,
            QuerySource = source,
        };

    internal static SessionEvent ToolRan(
        string session,
        string at,
        string tool = "Bash",
        int lengthMs = 0,
        string? use = null) =>
        new(session, ToolResult, at)
        {
            ToolName = tool,
            Success = "true",
            DecisionSource = "config",
            DurationMs = Figure(lengthMs),
            ToolUseId = use,
        };

    internal static SessionEvent ToolFailed(string session, string at, string tool = "Bash", string? use = null) =>
        new(session, ToolResult, at)
        {
            ToolName = tool,
            Success = "false",
            ErrorType = "ShellError",
            DecisionSource = "config",
            ToolUseId = use,
        };

    // Claude Code cuts a Tool call's input to its opening characters, so only the description survives whole.
    internal static SessionEvent AgentRan(
        string session,
        string at,
        string use,
        string? name = null,
        string? type = null,
        string? brief = null,
        int lengthMs = 0) =>
        ToolRan(session, at, "Agent", lengthMs, use) with { ToolInput = Asked(name, type, brief) };

    internal static SessionEvent AgentInputWithheld(string session, string at, string use, int lengthMs = 0) =>
        ToolRan(session, at, "Agent", lengthMs, use) with { ToolInput = Withheld };

    private static string Asked(string? name, string? type, string? brief) =>
        new JsonObject
        {
            ["description"] = name,
            ["subagent_type"] = type,
            ["prompt"] = brief,
        }.ToJsonString();

    internal static SessionEvent ModelFailed(string session, string at) =>
        new(session, "api_error", at) { ErrorType = "RateLimited" };

    internal static SessionEvent Refused(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "reject", "user_reject");

    internal static SessionEvent HookBlocked(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "reject", "hook");

    internal static SessionEvent Allowed(string session, string at, string tool = "Bash") =>
        Decided(session, at, tool, "accept", "config");

    private static string Figure(int value) => value.ToString(CultureInfo.InvariantCulture);

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
