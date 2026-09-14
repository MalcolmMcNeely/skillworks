namespace Skillworks.Core.Telemetry;

// Kept in the store: a later pass never rereads the bad line, so a restart would make the fault look fixed.
public sealed class TranscriptFault
{
    public const long WholeFile = 0;

    public required string Path { get; set; }

    public long Line { get; set; }

    public required string Reason { get; set; }

    public DateTimeOffset NoticedUtc { get; set; }
}
