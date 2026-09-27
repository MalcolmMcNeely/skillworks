namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

public sealed record SessionRow
{
    public required string Id { get; init; }

    public required DateTimeOffset StartedUtc { get; init; }

    public required string? Repository { get; init; }

    public required string? Person { get; init; }

    public required string Name { get; init; }

    public required long LengthMs { get; init; }

    public required bool Running { get; init; }

    public required DateTimeOffset LastActivityUtc { get; init; }

    public required DateOnly FirstDay { get; init; }

    public required DateOnly LastDay { get; init; }
}
