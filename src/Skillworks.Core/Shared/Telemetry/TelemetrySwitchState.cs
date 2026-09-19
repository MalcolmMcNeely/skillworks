namespace Skillworks.Core.Shared.Telemetry;

public sealed record TelemetrySwitchState(
    bool Emitting,
    string SettingsPath,
    bool Readable,
    string CollectorEndpoint,
    string RestartNote,
    string? Problem,
    TeamSettings Team);
