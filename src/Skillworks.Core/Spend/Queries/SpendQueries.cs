using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Filters;
using Skillworks.Core.TranscriptStore;

namespace Skillworks.Core.Spend.Queries;

public sealed class SpendQueries(IDbContextFactory<TranscriptStoreDbContext> contexts)
{
    private readonly record struct SkillTokens(string Skill, ModelTokens Tokens);

    public async Task<IReadOnlyDictionary<string, IReadOnlyList<ModelTokens>>> TokensBySkillAsync(
        Filter filter,
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

    // Narrowed like the activations, or a filtered count would sit beside an all-time cost.
    private static IQueryable<Turn> Narrowed(IQueryable<Turn> turns, Filter filter)
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
