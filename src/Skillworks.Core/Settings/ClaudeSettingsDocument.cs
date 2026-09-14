using System.Text.Json.Nodes;

namespace Skillworks.Core.Settings;

public sealed record ClaudeSettingsDocument(JsonObject? Root, bool Existed, string? Problem);
