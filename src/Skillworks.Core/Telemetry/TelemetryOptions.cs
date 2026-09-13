namespace Skillworks.Core.Telemetry;

/// <summary>Where the parsed transcripts are kept, and how often they are looked at.</summary>
public sealed class TelemetryOptions
{
    public const string SectionName = "Telemetry";

    /// <summary>Empty means a file under the user's local application data.</summary>
    public string DatabasePath { get; set; } = "";

    /// <summary>
    /// Seconds between looks for new sessions. Zero or less waits for a request instead, which is
    /// what a test wants: a pass it did not ask for makes counting passes meaningless.
    /// </summary>
    public int SweepSeconds { get; set; } = 10;

    public string ResolvedDatabasePath() => string.IsNullOrWhiteSpace(DatabasePath)
        ? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Skillworks",
            "telemetry.db")
        : Path.GetFullPath(DatabasePath);

    public TimeSpan SweepInterval() =>
        SweepSeconds > 0 ? TimeSpan.FromSeconds(SweepSeconds) : Timeout.InfiniteTimeSpan;
}
