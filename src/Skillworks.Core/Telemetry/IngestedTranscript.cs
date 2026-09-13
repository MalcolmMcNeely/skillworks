namespace Skillworks.Core.Telemetry;

/// <summary>
/// How far into one transcript the last pass got. This is what makes a second run cheap: the next
/// pass seeks to the offset instead of reading the file again.
/// </summary>
public sealed class IngestedTranscript
{
    public required string Path { get; set; }

    /// <summary>A byte offset, always on a line boundary.</summary>
    public long Offset { get; set; }

    /// <summary>
    /// Lines read so far. Counting them costs nothing and is the only way a fault found on the
    /// second pass can name a line number a developer's editor agrees with.
    /// </summary>
    public long Lines { get; set; }
}
