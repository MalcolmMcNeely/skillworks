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

    public void Write(string path, JsonObject root)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);

        var staging = path + ".skillworks-new";
        File.WriteAllText(staging, root.ToJsonString(Layout));
        File.Move(staging, path, overwrite: true);
    }
}
