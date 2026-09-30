namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

public sealed record HookRunRow
{
    public required int Count { get; init; }

    public required long LengthMs { get; init; }
}
