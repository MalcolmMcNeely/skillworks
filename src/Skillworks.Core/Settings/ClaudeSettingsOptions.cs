namespace Skillworks.Core.Settings;

/// <summary>Where Claude Code's own settings live, and the address to point them at.</summary>
public sealed class ClaudeSettingsOptions
{
    public const string SectionName = "ClaudeSettings";

    /// <summary>
    /// Claude Code reads its user settings from <c>~/.claude/settings.json</c>. Empty means that
    /// file, so nothing has to be configured on a normal machine.
    /// </summary>
    public string Path { get; set; } = "";

    /// <summary>
    /// Where the switch records what it displaced, so turning telemetry off puts the old values back
    /// instead of deleting them. Empty means a file beside Studio's own database.
    /// </summary>
    public string StampPath { get; set; } = "";

    /// <summary>
    /// The collector's OTLP address. ADR 0002 pins the host port, because this value goes into the
    /// developer's settings and has to still be right tomorrow.
    /// </summary>
    public string CollectorEndpoint { get; set; } = "http://localhost:4318";

    public string ResolvedPath() => string.IsNullOrWhiteSpace(Path)
        ? System.IO.Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".claude",
            "settings.json")
        : System.IO.Path.GetFullPath(Path);

    public string ResolvedStampPath() => string.IsNullOrWhiteSpace(StampPath)
        ? System.IO.Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Skillworks",
            "telemetry-switch.json")
        : System.IO.Path.GetFullPath(StampPath);
}
