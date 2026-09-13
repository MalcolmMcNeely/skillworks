namespace Skillworks.Core.Telemetry;

/// <summary>
/// A piece of a transcript the ingest could not read and stepped over, with enough detail to open
/// the file at the right place.
/// </summary>
/// <remarks>
/// Kept in the store rather than in memory because a later pass never revisits the line that caused
/// it. A count held only for the run would read as zero tomorrow and look like the problem had gone.
/// </remarks>
public sealed class TranscriptFault
{
    /// <summary>The line a whole file that would not open is recorded against.</summary>
    public const long WholeFile = 0;

    public required string Path { get; set; }

    /// <summary>The 1-based line, or <see cref="WholeFile"/>.</summary>
    public long Line { get; set; }

    public required string Reason { get; set; }

    public DateTimeOffset NoticedUtc { get; set; }
}
