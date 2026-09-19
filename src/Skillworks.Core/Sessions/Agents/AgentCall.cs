using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Agents;

// Claude Code cuts the instruction to its opening characters, and nothing else records what a Subagent was asked.
public sealed record AgentCall(string ToolUse, string? Name, string? Type, string? Brief)
{
    public const string Tool = "Agent";

    private const string NameField = "description";

    private const string TypeField = "subagent_type";

    private const string BriefField = "prompt";

    public static AgentCall Of(string toolUse, string? input)
    {
        var fields = ToolInput.Fields(input);

        return new AgentCall(
            toolUse,
            ToolInput.Text(fields, NameField),
            ToolInput.Text(fields, TypeField),
            ToolInput.Text(fields, BriefField));
    }
}
