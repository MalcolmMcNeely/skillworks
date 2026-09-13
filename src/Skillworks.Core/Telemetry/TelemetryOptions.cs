namespace Skillworks.Core.Telemetry;

/// <summary>Where the parsed transcripts are kept.</summary>
public sealed class TelemetryOptions
{
    public const string SectionName = "Telemetry";

    /// <summary>Empty means a file under the user's local application data.</summary>
    public string DatabasePath { get; set; } = "";

    public string ResolvedDatabasePath() => string.IsNullOrWhiteSpace(DatabasePath)
        ? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Skillworks",
            "telemetry.db")
        : Path.GetFullPath(DatabasePath);
}
