using Skillworks.Studio.Api.Tests.Filters;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record SessionsHeadRow
{
    public required SpanRow Span { get; init; }
}
