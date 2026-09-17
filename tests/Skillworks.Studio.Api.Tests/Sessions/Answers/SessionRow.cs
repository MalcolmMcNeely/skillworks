namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record SessionRow
{
    public required string Id { get; init; }

    public required DateTimeOffset StartedUtc { get; init; }

    public required string? Repository { get; init; }

    public required string? Person { get; init; }

    public required string Name { get; init; }

    public required long LengthMs { get; init; }

    public required bool Running { get; init; }

    public required int ToolCalls { get; init; }

    public required decimal Cost { get; init; }

    public required int Faults { get; init; }

    public required int Friction { get; init; }
}
