namespace Skillworks.Core.TranscriptStore;

public sealed class TranscriptStoreOptions
{
    public const string SectionName = "TranscriptStore";

    public string DatabasePath { get; set; } = "";

    // Zero or less stops the sweep for tests, where a pass nobody asked for would spoil the pass count.
    public int SweepSeconds { get; set; } = 10;

    public string ResolvedDatabasePath() => string.IsNullOrWhiteSpace(DatabasePath)
        ? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Skillworks",
            "transcript-store.db")
        : Path.GetFullPath(DatabasePath);

    public TimeSpan SweepInterval() =>
        SweepSeconds > 0 ? TimeSpan.FromSeconds(SweepSeconds) : Timeout.InfiniteTimeSpan;
}
