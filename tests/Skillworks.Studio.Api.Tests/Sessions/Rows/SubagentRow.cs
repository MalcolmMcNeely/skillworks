namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

public sealed record SubagentRow
{
    public required string Id { get; init; }

    public required string Name { get; init; }

    public required string? Type { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long LengthMs { get; init; }

    public required int ToolCalls { get; init; }

    public required decimal Cost { get; init; }

    public required int Faults { get; init; }

    public required string? Brief { get; init; }

    public required string? Report { get; init; }
}
