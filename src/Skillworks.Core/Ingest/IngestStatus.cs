namespace Skillworks.Core.Ingest;

public sealed record IngestStatus(
    bool Running,
    int CompletedPasses,
    int TranscriptsSeen,
    int TranscriptsTotal,
    int TranscriptsRead,
    int ActivationsAdded,
    bool LastPassWasFull,
    DateTimeOffset? LastRefreshUtc,
    int Faults);
