namespace Skillworks.Core.Settings;

public sealed record TelemetrySwitchState(
    bool Emitting,
    string SettingsPath,
    bool Readable,
    string CollectorEndpoint,
    IReadOnlyList<TelemetryChange> Changes,
    string RestartNote,
    string? Problem);
