using System.Text.Json;

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
        var fields = Fields(input);

        return new AgentCall(toolUse, Text(fields, NameField), Text(fields, TypeField), Text(fields, BriefField));
    }

    // Claude Code writes the input as JSON, and an older one or a switched-off content setting writes none.
    private static JsonElement? Fields(string? input)
    {
        if (input is not { Length: > 0 })
        {
            return null;
        }

        try
        {
            using var read = JsonDocument.Parse(input);

            return read.RootElement.Clone();
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string? Text(JsonElement? fields, string field) =>
        fields is { ValueKind: JsonValueKind.Object } held &&
        held.TryGetProperty(field, out var value) &&
        value.ValueKind == JsonValueKind.String &&
        value.GetString() is { Length: > 0 } text
            ? text
            : null;
}
