using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// One skill's tokens on one model, which is the grain money can be worked out at: a skill that ran
/// on two models was billed at two sets of rates, and one blended rate would land nowhere near.
/// </summary>
public sealed record ModelTokens(
    string Model,
    string? Effort,
    long InputTokens,
    long OutputTokens,
    long ThinkingTokens,
    long CacheReadTokens,
    long CacheWrite5mTokens,
    long CacheWrite1hTokens);

/// <summary>
/// Reads the turns back out as tokens per skill. It hands back tokens and not money, because money
/// depends on a price table that can change long after the turn was stored.
/// </summary>
public sealed class SpendStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    private readonly record struct SkillTokens(string Skill, ModelTokens Tokens);

    /// <summary>A skill absent from the answer made no request of its own and so owes nothing.</summary>
    public async Task<IReadOnlyDictionary<string, IReadOnlyList<ModelTokens>>> TokensBySkillAsync(
        TelemetryFilter filter,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        // Summed in the database, so a history of hundreds of thousands of turns never comes back
        // over the wire to be added up here.
        var totals = await Narrowed(store.Turns, filter)
            .GroupBy(turn => new { Skill = turn.SkillName!, turn.Model, turn.Effort })
            .Select(group => new SkillTokens(
                group.Key.Skill,
                new ModelTokens(
                    group.Key.Model,
                    group.Key.Effort,
                    group.Sum(turn => turn.InputTokens),
                    group.Sum(turn => turn.OutputTokens),
                    group.Sum(turn => turn.ThinkingTokens),
                    group.Sum(turn => turn.CacheReadTokens),
                    group.Sum(turn => turn.CacheWrite5mTokens),
                    group.Sum(turn => turn.CacheWrite1hTokens))))
            .ToListAsync(cancellationToken);

        return totals
            .GroupBy(total => total.Skill)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<ModelTokens> (group) => [.. group.Select(total => total.Tokens)]);
    }

    /// <summary>
    /// The same filter, over the turns. A filtered count against an all-time cost would report one
    /// firing as having cost a fortune, so both are narrowed the same way: each answers for what
    /// happened inside the span. A firing late on the last day whose requests ran past midnight
    /// therefore keeps its count and loses those requests, because that is when they happened.
    /// </summary>
    private static IQueryable<Turn> Narrowed(IQueryable<Turn> turns, TelemetryFilter filter)
    {
        // A turn charged to no skill was spent choosing one, so it belongs in no skill's total.
        turns = turns.Where(turn => turn.SkillName != null);

        if (filter.FromUtc is { } from)
        {
            turns = turns.Where(turn => turn.TimestampUtc >= from);
        }

        if (filter.UntilUtc is { } until)
        {
            turns = turns.Where(turn => turn.TimestampUtc < until);
        }

        if (filter.Repository is { } repository)
        {
            turns = turns.Where(turn => turn.Repository == repository);
        }

        if (filter.Skill is { } skill)
        {
            turns = turns.Where(turn => turn.SkillName == skill);
        }

        return turns;
    }
}
