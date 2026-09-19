using System.Text.Json.Nodes;

namespace Skillworks.Core.Shared.Telemetry;

public sealed record ClaudeSettingsDocument(JsonObject? Root, bool Existed, string? Problem);
