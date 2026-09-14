namespace Skillworks.Studio.Api.Tests.Filters;

public sealed record FilterChoiceRow
{
    public required string[] Repositories { get; init; }

    public required string[] Skills { get; init; }
}
