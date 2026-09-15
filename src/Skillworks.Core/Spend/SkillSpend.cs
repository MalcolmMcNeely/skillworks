namespace Skillworks.Core.Spend;

public sealed record SkillSpend(
    long InputTokens,
    long OutputTokens,
    long CacheReadTokens,
    long CacheCreationTokens,
    decimal Cost)
{
    public static readonly SkillSpend Nothing = new(0, 0, 0, 0, 0m);
}
