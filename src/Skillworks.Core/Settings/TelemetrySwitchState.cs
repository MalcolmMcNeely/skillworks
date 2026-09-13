namespace Skillworks.Core.Settings;

/// <summary>One variable the switch would write, and the value it would displace.</summary>
/// <param name="From">Null means the variable is not in the settings yet.</param>
public sealed record TelemetryChange(string Name, string? From, string To);

/// <summary>
/// Whether Claude Code is emitting to Studio, and exactly what flipping the switch would change.
/// The front end shows <see cref="Changes"/> and asks before the first write.
/// </summary>
/// <param name="Emitting">True when every variable Studio needs already holds the value it needs.</param>
/// <param name="Readable">False means Studio could not parse the settings, so it will not write them.</param>
/// <param name="Changes">Empty when telemetry is already on, or when the settings are unreadable.</param>
/// <param name="Problem">Why the settings are unreadable, when they are.</param>
public sealed record TelemetrySwitchState(
    bool Emitting,
    string SettingsPath,
    bool Readable,
    string CollectorEndpoint,
    IReadOnlyList<TelemetryChange> Changes,
    string RestartNote,
    string? Problem);

/// <summary>Where the switch ended up, and why nothing was written when nothing was.</summary>
/// <param name="Refusal">Null means the settings were written.</param>
public sealed record TelemetrySwitchResult(TelemetrySwitchState State, string? Refusal);
