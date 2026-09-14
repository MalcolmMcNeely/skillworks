using System.Text.Json;

namespace Skillworks.Core.Activations;

internal static class RecordedArguments
{
    public static IReadOnlyList<ActivationArgument> Read(string? recorded)
    {
        if (string.IsNullOrWhiteSpace(recorded))
        {
            return [];
        }

        // Nothing writes this but the ingest, so it parses and it is an object. If it ever is not,
        // the text itself is still the evidence, and showing it beats showing nothing.
        if (Parse(recorded) is not { } block)
        {
            return [new ActivationArgument("recorded", recorded)];
        }

        using (block)
        {
            return
            [
                .. block.RootElement
                    .EnumerateObject()
                    .Select(argument => new ActivationArgument(argument.Name, Value(argument.Value)))
            ];
        }
    }

    private static JsonDocument? Parse(string recorded)
    {
        JsonDocument document;

        try
        {
            document = JsonDocument.Parse(recorded);
        }
        catch (JsonException)
        {
            return null;
        }

        if (document.RootElement.ValueKind == JsonValueKind.Object)
        {
            return document;
        }

        document.Dispose();

        return null;
    }

    // Quoting a string would put marks round an argument the developer typed without them.
    private static string Value(JsonElement value) =>
        value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : value.GetRawText();
}
