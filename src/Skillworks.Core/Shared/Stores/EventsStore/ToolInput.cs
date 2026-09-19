using System.Text.Json;

namespace Skillworks.Core.Shared.Stores.EventsStore;

// Claude Code cuts each string inside this JSON to its opening characters, so the shape holds but a value may end early.
public static class ToolInput
{
    private const string CommandField = "command";

    private const string FileField = "file_path";

    private const string NotebookField = "notebook_path";

    public static string? ActedOn(string? input)
    {
        var fields = Fields(input);

        return Text(fields, CommandField) ?? FileIn(fields);
    }

    public static string? FileIn(string? input) => FileIn(Fields(input));

    public static string? Text(JsonElement? fields, string field) =>
        fields is { ValueKind: JsonValueKind.Object } held &&
        held.TryGetProperty(field, out var value) &&
        value.ValueKind == JsonValueKind.String &&
        value.GetString() is { Length: > 0 } text
            ? text
            : null;

    // An older Claude Code and a switched-off content setting both write no input at all.
    public static JsonElement? Fields(string? input)
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

    // NotebookEdit names its file under a key of its own, so a notebook reads as the file it is.
    private static string? FileIn(JsonElement? fields) => Text(fields, FileField) ?? Text(fields, NotebookField);
}
