namespace Skillworks.Studio.Api.Tests;

public sealed record IngestRow
{
    public required bool Running { get; init; }

    public required int CompletedPasses { get; init; }

    public required int TranscriptsSeen { get; init; }

    public required int TranscriptsTotal { get; init; }

    public required int TranscriptsRead { get; init; }

    public required int ActivationsAdded { get; init; }

    public required bool LastPassWasFull { get; init; }

    public required DateTimeOffset? LastRefreshUtc { get; init; }

    public required int Faults { get; init; }
}
