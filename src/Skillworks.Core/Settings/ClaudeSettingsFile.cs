using System.Text.Json;
using System.Text.Json.Nodes;

namespace Skillworks.Core.Settings;

/// <summary>Claude Code's settings document as Studio sees it.</summary>
/// <param name="Root">The parsed object, or null when the file could not be read as one.</param>
/// <param name="Existed">False means there is no file yet, which is not a problem.</param>
/// <param name="Problem">Why the file could not be read, when it could not.</param>
public sealed record ClaudeSettingsDocument(JsonObject? Root, bool Existed, string? Problem);

/// <summary>
/// Reads and writes one JSON settings file. It never hands back a half-understood document and never
/// leaves a half-written one: anything it could not parse comes back with a null root, and every
/// write lands through a staging file, so a crash cannot truncate the developer's settings.
/// </summary>
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
            // Strict JSON on purpose. Comments and trailing commas would parse but could not be
            // written back, so Studio refuses the file rather than quietly dropping them.
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
