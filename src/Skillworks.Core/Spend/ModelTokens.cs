namespace Skillworks.Core.Spend;

// Per model: a skill that ran on two models was billed at two rates, and one blended rate would be wrong.
public sealed record ModelTokens(
    string Model,
    string? Effort,
    long InputTokens,
    long OutputTokens,
    long ThinkingTokens,
    long CacheReadTokens,
    long CacheWrite5mTokens,
    long CacheWrite1hTokens);
