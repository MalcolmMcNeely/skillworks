namespace Skillworks.Studio.Api.Tests;

public sealed record FilterChoiceRow
{
    public required string[] Repositories { get; init; }

    public required string[] Skills { get; init; }
}
