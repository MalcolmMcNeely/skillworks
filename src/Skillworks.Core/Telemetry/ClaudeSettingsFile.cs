using System.Text.Json;
using System.Text.Json.Nodes;

namespace Skillworks.Core.Telemetry;

public sealed class ClaudeSettingsFile
{
    private static readonly JsonSerializerOptions Layout = new() { WriteIndented = true };

    public ClaudeSettingsDocument Read(string path)
    {
        if (!File.Exists(path))
        {
            return new ClaudeSettingsDocument(new JsonObject(), Existed: false, Problem: null);
        }

        try
        {
            // Strict on purpose: comments and trailing commas could not be written back, so the file is refused.
            return JsonNode.Parse(File.ReadAllText(path)) is JsonObject root
                ? new ClaudeSettingsDocument(root, Existed: true, Problem: null)
                : new ClaudeSettingsDocument(null, Existed: true, Problem: "its top level is not an object");
        }
        catch (Exception failure) when (failure is JsonException or IOException or UnauthorizedAccessException)
        {
            return new ClaudeSettingsDocument(null, Existed: true, Problem: failure.Message);
        }
    }

    public string Render(JsonObject root) => root.ToJsonString(Layout);

    public string? Write(string path, JsonObject root)
    {
        var staging = path + ".skillworks-new";

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(staging, Render(root));

            // A failure here leaves the settings as they were, so the switch never writes some of them and not the rest.
            File.Move(staging, path, overwrite: true);

            return null;
        }
        catch (Exception failure) when (failure is IOException or UnauthorizedAccessException)
        {
            Discard(staging);

            return failure.Message;
        }
    }

    private static void Discard(string staging)
    {
        try
        {
            File.Delete(staging);
        }
        catch (Exception failure) when (failure is IOException or UnauthorizedAccessException)
        {
            // Nothing was changed, and the next write replaces this file, so a stray staging file is no fault.
        }
    }
}
