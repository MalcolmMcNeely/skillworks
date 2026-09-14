namespace Skillworks.Core.Telemetry;

public sealed class ClaudeSettingsOptions
{
    public const string SectionName = "ClaudeSettings";

    public string Path { get; set; } = "";

    public string StampPath { get; set; } = "";

    // The host port is pinned: this value is written into the developer's settings and must stay right.
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
