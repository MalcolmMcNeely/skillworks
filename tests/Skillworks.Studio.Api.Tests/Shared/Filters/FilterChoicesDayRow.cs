namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public sealed record FilterChoicesDayRow
{
    public required DateOnly Day { get; init; }

    public required string[] Repositories { get; init; }
}
