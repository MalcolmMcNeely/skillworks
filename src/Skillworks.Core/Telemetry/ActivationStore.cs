using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Telemetry;

/// <summary>Everything the store knows about the skills that fired, gathered in one read.</summary>
/// <param name="Counts">Activations per skill. A skill absent here never fired.</param>
/// <param name="Repositories">Distinct repositories per skill, sorted.</param>
/// <param name="Branches">Distinct git branches per skill, sorted.</param>
/// <param name="Models">Distinct models per skill, sorted.</param>
/// <param name="Efforts">Distinct effort levels per skill, sorted.</param>
public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Branches,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Models,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Efforts);

/// <summary>One firing in a list, carrying enough of itself to be told apart and opened.</summary>
/// <param name="Id">The tool use id, which is how one firing is asked for by name.</param>
/// <param name="Repository">Null when the transcript recorded no working directory.</param>
public sealed record ActivationSummary(
    string Id,
    string Skill,
    string? Repository,
    string? Branch,
    string? Model,
    string? Effort,
    DateTimeOffset TimestampUtc)
{
    /// <summary>
    /// Where this firing came from, joined on afterwards. It is not read with the rest because the
    /// store this comes out of holds transcripts, and transcripts do not record it.
    /// </summary>
    public SkillOrigin? Origin { get; init; }
}

/// <summary>
/// One firing opened: everything the list holds, plus the session it belongs to and what the skill
/// was actually called with. This is what turns a count into evidence.
/// </summary>
/// <param name="Arguments">
/// In the order the transcript wrote them. Empty when the firing recorded nothing at all, which is
/// a fact about the firing rather than a gap.
/// </param>
public sealed record ActivationDetail(
    string Id,
    string Skill,
    string SessionId,
    string? Repository,
    string? Branch,
    string? Model,
    string? Effort,
    DateTimeOffset TimestampUtc,
    IReadOnlyList<ActivationArgument> Arguments)
{
    /// <summary>Where this firing came from, joined on afterwards. Null when no event matches it.</summary>
    public SkillOrigin? Origin { get; init; }
}

/// <summary>
/// One thing a skill was called with. The value is text whatever the transcript wrote, because the
/// reader is judging the words that were used, not the shape they arrived in.
/// </summary>
public sealed record ActivationArgument(string Name, string Value);

/// <summary>
/// Reads the activations back out. It sits beside the ingest that writes them, so the store's shape
/// is known in one place and callers see tallies rather than tables.
/// </summary>
public sealed class ActivationStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    private readonly record struct SkillValue(string Skill, string? Value);

    private readonly record struct SkillCount(string Skill, int Activations);

    public async Task<ActivationTally> TallyBySkillAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var activations = Narrowed(store.Activations, filter);

        // Narrow reads beat one wide one. SQLite has no distinct-within-group, and pulling every
        // activation back to fold it in memory would not survive a full transcript folder.
        var counts = await activations
            .GroupBy(a => a.SkillName)
            .Select(group => new SkillCount(group.Key, group.Count()))
            .ToListAsync(cancellationToken);

        return new ActivationTally(
            counts.ToDictionary(count => count.Skill, count => count.Activations),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Repository), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.GitBranch), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Model), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Effort), cancellationToken));
    }

    /// <summary>
    /// The firings the filter takes in, newest first, so the reader opening one is looking at the
    /// most recent by default. Narrowed by the same filter as the skill table, so the list reached
    /// from a row is the same slice of history that row was counting.
    /// </summary>
    public async Task<IReadOnlyList<ActivationSummary>> ListAsync(
        TelemetryFilter filter,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await Narrowed(store.Activations, filter)
            .OrderByDescending(a => a.TimestampUtc)
            .Select(a => new ActivationSummary(
                a.ToolUseId,
                a.SkillName,
                a.Repository,
                a.GitBranch,
                a.Model,
                a.Effort,
                a.TimestampUtc))
            .ToListAsync(cancellationToken);
    }

    /// <summary>
    /// One firing by its tool use id, or null when the ingest has never read it. Not narrowed by a
    /// filter: a reader who has a firing's id is asking about that firing, not about a week.
    /// </summary>
    public async Task<ActivationDetail?> OpenAsync(string id, CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var activation = await store.Activations
            .AsNoTracking()
            .FirstOrDefaultAsync(a => a.ToolUseId == id, cancellationToken);

        return activation is null
            ? null
            : new ActivationDetail(
                activation.ToolUseId,
                activation.SkillName,
                activation.SessionId,
                activation.Repository,
                activation.GitBranch,
                activation.Model,
                activation.Effort,
                activation.TimestampUtc,
                RecordedArguments.Read(activation.Arguments));
    }

    /// <summary>
    /// The repositories and skills the whole history holds, sorted. Deliberately not narrowed: they
    /// are what a filter can be set to, so a filter that has cut the answer to nothing must still be
    /// able to offer the way back out.
    /// </summary>
    public async Task<(IReadOnlyList<string> Repositories, IReadOnlyList<string> Skills)> ChoicesAsync(
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var repositories = await store.Activations
            .Select(a => a.Repository)
            .Distinct()
            .ToListAsync(cancellationToken);

        var skills = await store.Activations
            .Select(a => a.SkillName)
            .Distinct()
            .ToListAsync(cancellationToken);

        return (Sorted(repositories.OfType<string>()), Sorted(skills));
    }

    /// <summary>
    /// The filter applied where the ticket asks for it: in the query. Narrowing after the rows came
    /// back would read a whole history to answer a question about one week of it.
    /// </summary>
    /// <remarks>
    /// Written again over in <see cref="SpendStore"/> rather than shared. Both ways of sharing it
    /// cost more than the repetition: an interface over the two tables leaves EF translating a
    /// member it cannot see the column behind, and a helper taking a selector per column has to
    /// graft the expressions together by hand. What repeats here is four predicates, and what does
    /// not repeat is the rule behind them, which <see cref="TelemetryFilter"/> owns alone.
    /// </remarks>
    private static IQueryable<Activation> Narrowed(IQueryable<Activation> activations, TelemetryFilter filter)
    {
        if (filter.FromUtc is { } from)
        {
            activations = activations.Where(a => a.TimestampUtc >= from);
        }

        if (filter.UntilUtc is { } until)
        {
            activations = activations.Where(a => a.TimestampUtc < until);
        }

        if (filter.Repository is { } repository)
        {
            activations = activations.Where(a => a.Repository == repository);
        }

        if (filter.Skill is { } skill)
        {
            activations = activations.Where(a => a.SkillName == skill);
        }

        return activations;
    }

    private static IReadOnlyList<string> Sorted(IEnumerable<string> names) =>
        [.. names.OrderBy(name => name, StringComparer.OrdinalIgnoreCase)];

    /// <summary>
    /// The distinct values of one column per skill. Taking the whole pair as an expression keeps
    /// the distinct in SQLite, which is the point: only the handful of pairs a skill actually has
    /// comes back, never a row per activation. The rows that recorded nothing are dropped here,
    /// because a predicate over a projected pair is the one thing SQLite will not be told.
    /// </summary>
    private static async Task<IReadOnlyDictionary<string, IReadOnlyList<string>>> BySkillAsync(
        IQueryable<Activation> activations,
        Expression<Func<Activation, SkillValue>> pair,
        CancellationToken cancellationToken)
    {
        var pairs = await activations
            .Select(pair)
            .Distinct()
            .ToListAsync(cancellationToken);

        return pairs
            .Where(pair => pair.Value != null)
            .GroupBy(pair => pair.Skill)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(pair => pair.Value!).Order()]);
    }
}
