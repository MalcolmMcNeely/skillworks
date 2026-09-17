namespace Skillworks.Core.Sessions.Agents;

// No log event carries an agent id, so a Step reaches its agent only through the Span these keys find.
public sealed record StepKey(string Step, string Key)
{
    // Both are spelled the same on the event and on the Span, which is what makes the join hold.
    public const string ToolUse = "tool_use_id";

    public const string Request = "request_id";
}
