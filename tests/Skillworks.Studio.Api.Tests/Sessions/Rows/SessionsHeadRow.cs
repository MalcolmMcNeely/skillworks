namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

public sealed record SessionsHeadRow
{
    public required DateTimeOffset AsOfUtc { get; init; }
}
