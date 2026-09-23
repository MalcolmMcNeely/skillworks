namespace Skillworks.Core.Dashboard.Spend;

public sealed record TurnTotals(
    long InputTokens,
    long OutputTokens,
    long CacheReadTokens,
    long CacheCreationTokens,
    decimal Cost)
{
    public static readonly TurnTotals Nothing = new(0, 0, 0, 0, 0m);
}
