using Skillworks.Studio.Api.Tests.Shared.Filters;

namespace Skillworks.Studio.Api.Tests.Sessions.Rows;

public sealed record SessionsHeadRow
{
    public required SpanRow Span { get; init; }

    public required string Sort { get; init; }

    public required bool Descending { get; init; }
}
