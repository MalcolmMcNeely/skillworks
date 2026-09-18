using Skillworks.Core.Sessions.Measures;

namespace Skillworks.Core.Sessions;

// A column asked for with no direction opens the way a reader wants it first: the worst figure on top, words from A.
public sealed record SessionOrder
{
    // Letter case is not a rank a reader has in mind, so a run titled "alpha" sorts beside one titled "Alpha".
    private static readonly StringComparer Alphabetical = StringComparer.OrdinalIgnoreCase;

    private static readonly IReadOnlyList<Column> Columns =
    [
        new("started", null, _ => (run, other) => run.StartedUtc.CompareTo(other.StartedUtc), OpensHighestFirst: true),
        new("repository", null, _ => (run, other) => Alphabetical.Compare(run.Repository, other.Repository), OpensHighestFirst: false),
        new("person", null, _ => (run, other) => Alphabetical.Compare(run.Person, other.Person), OpensHighestFirst: false),
        new("name", null, _ => (run, other) => Alphabetical.Compare(run.Name, other.Name), OpensHighestFirst: false),
        new("length", null, _ => (run, other) => run.LengthMs.CompareTo(other.LengthMs), OpensHighestFirst: true),
        new("toolCalls", Measure.ToolCalls, By, OpensHighestFirst: true),
        new("cost", Measure.Cost, By, OpensHighestFirst: true),
        new("faults", Measure.Faults, By, OpensHighestFirst: true),
    ];

    public string? Sort { get; init; }

    // Text, not a bool: a hand-typed address that misspells the direction must still open a table.
    public string? Descending { get; init; }

    public string SortedOn => Chosen.Name;

    public Measure? SortedMeasure => Chosen.Measure;

    public bool HighestFirst => bool.TryParse(Descending, out var descending) ? descending : Chosen.OpensHighestFirst;

    // A column nobody has is no reason to draw nothing, so the table falls back to the order it opens on.
    private Column Chosen => Columns.FirstOrDefault(column => column.Name == Sort) ?? Columns[0];

    public IReadOnlyList<SessionRow> Sorted(
        IEnumerable<SessionRow> sessions,
        IReadOnlyDictionary<string, decimal> ranked)
    {
        var (column, descending) = (Chosen, HighestFirst);
        var rank = column.Ranking(ranked);
        var rows = sessions.ToList();

        rows.Sort((run, other) =>
        {
            var ranked = Math.Sign(rank(run, other));

            // The id breaks a tie, so two runs that sit level read the same way twice.
            return ranked == 0 ? string.CompareOrdinal(run.Id, other.Id) : descending ? -ranked : ranked;
        });

        return rows;
    }

    private static Comparison<SessionRow> By(IReadOnlyDictionary<string, decimal> values) =>
        (run, other) => values.GetValueOrDefault(run.Id).CompareTo(values.GetValueOrDefault(other.Id));

    private sealed record Column(
        string Name,
        Measure? Measure,
        Func<IReadOnlyDictionary<string, decimal>, Comparison<SessionRow>> Ranking,
        bool OpensHighestFirst);
}
