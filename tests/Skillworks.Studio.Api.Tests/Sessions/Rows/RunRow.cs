namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

// The Session page counts one run's figures from its own events, so they ride the head that opens it.
public sealed record RunRow
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
