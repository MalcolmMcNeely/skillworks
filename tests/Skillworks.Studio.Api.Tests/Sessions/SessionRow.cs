namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record SessionRow
{
    public required string Id { get; init; }

    public required DateTimeOffset StartedUtc { get; init; }

    public required string? Repository { get; init; }

    public required string? Person { get; init; }

    public required string Name { get; init; }

    public required long LengthMs { get; init; }

    public required bool Running { get; init; }
}
