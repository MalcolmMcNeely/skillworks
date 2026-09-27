namespace Skillworks.Studio.Api.Tests.Sessions.Rows.Exchanges;

public sealed record SubagentCostRow
{
    public required string Agent { get; init; }

    public required decimal Cost { get; init; }
}
