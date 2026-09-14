namespace Skillworks.Core.Telemetry;

public sealed class TelemetryOptions
{
    public const string SectionName = "Telemetry";

    public string DatabasePath { get; set; } = "";

    // Zero or less stops the sweep for tests, where a pass nobody asked for would spoil the pass count.
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
