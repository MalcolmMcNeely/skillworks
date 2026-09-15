namespace Skillworks.Studio.Api.Tests.Skills;

// Required, so a field renamed in the API fails the deserialize rather than quietly reading as zero.
public sealed record SkillRow
{
    public required string Name { get; init; }

    public required int Activations { get; init; }

    public required string[] Repositories { get; init; }

    public required string[]? Models { get; init; }

    public required string[]? Efforts { get; init; }

    public required SpendRow? Spend { get; init; }

    public required decimal? AverageCost { get; init; }

    public required OriginRow[] Origins { get; init; }
}
