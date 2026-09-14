namespace Skillworks.Core.Ingest;

public sealed class IngestedTranscript
{
    public required string Path { get; set; }

    public long Offset { get; set; }

    // A later pass starts mid-file, so without this count a fault could not name its real line number.
    public long Lines { get; set; }
}
