using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Agents;

// No log event carries an agent id or a parent, so a Step reaches its Span only through these keys.
public sealed record StepKey(string Step, string Key)
{
    // Both are spelled the same on the event and on the Span, which is what makes the join hold.
    public const string ToolUse = "tool_use_id";

    public const string Request = "request_id";

    private const string ToolSpan = "claude_code.tool";

    private const string TurnSpan = "claude_code.llm_request";

    // Spans beneath a Subagent repeat the tool use id of the call that started it, so only its own Span answers.
    public static string? Of(Span span) => span.Name switch
    {
        ToolSpan => span.Attributes.GetValueOrDefault(ToolUse),

        TurnSpan => span.Attributes.GetValueOrDefault(Request),

        _ => null,
    };
}
