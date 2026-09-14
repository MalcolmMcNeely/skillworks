namespace Skillworks.Studio.Api.Tests.Ingest;

public sealed record FaultRow
{
    public required string Path { get; init; }

    public required long Line { get; init; }

    public required string Reason { get; init; }

    public required DateTimeOffset NoticedUtc { get; init; }
}
