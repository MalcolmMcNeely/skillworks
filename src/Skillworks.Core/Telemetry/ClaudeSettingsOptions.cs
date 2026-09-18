namespace Skillworks.Core.Telemetry;

public sealed class ClaudeSettingsOptions
{
    public const string SectionName = "ClaudeSettings";

    public string Path { get; set; } = "";

    public string StampPath { get; set; } = "";

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
