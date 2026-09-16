namespace Skillworks.Core.Sessions;

// A column asked for with no direction opens the way a reader wants it first: the worst figure on top, words from A.
public sealed record SessionOrder
{
    // Letter case is not a rank a reader has in mind, so a run titled "alpha" sorts beside one titled "Alpha".
    private static readonly StringComparer Alphabetical = StringComparer.OrdinalIgnoreCase;

    private static readonly IReadOnlyList<Column> Columns =
    [
        new("started", (run, other) => run.StartedUtc.CompareTo(other.StartedUtc), OpensHighestFirst: true),
        new("repository", (run, other) => Alphabetical.Compare(run.Repository, other.Repository), OpensHighestFirst: false),
        new("person", (run, other) => Alphabetical.Compare(run.Person, other.Person), OpensHighestFirst: false),
        new("name", (run, other) => Alphabetical.Compare(run.Name, other.Name), OpensHighestFirst: false),
        new("length", (run, other) => run.LengthMs.CompareTo(other.LengthMs), OpensHighestFirst: true),
        new("toolCalls", (run, other) => run.ToolCalls.CompareTo(other.ToolCalls), OpensHighestFirst: true),
        new("cost", (run, other) => run.Cost.CompareTo(other.Cost), OpensHighestFirst: true),
        new("faults", (run, other) => run.Faults.CompareTo(other.Faults), OpensHighestFirst: true),
    ];

    public string? Sort { get; init; }

    // Text, not a bool: a hand-typed address that misspells the direction must still open a table.
    public string? Descending { get; init; }

    public string SortedOn => Chosen.Name;

    public bool HighestFirst => bool.TryParse(Descending, out var descending) ? descending : Chosen.OpensHighestFirst;

    // A column nobody has is no reason to draw nothing, so the table falls back to the order it opens on.
    private Column Chosen => Columns.FirstOrDefault(column => column.Name == Sort) ?? Columns[0];

    public IReadOnlyList<Session> Sorted(IEnumerable<Session> sessions)
    {
        var (column, descending) = (Chosen, HighestFirst);
        var rows = sessions.ToList();

        rows.Sort((run, other) =>
        {
            var ranked = Math.Sign(column.Rank(run, other));

            // The id breaks a tie, so two runs that sit level read the same way twice.
            return ranked == 0 ? string.CompareOrdinal(run.Id, other.Id) : descending ? -ranked : ranked;
        });

        return rows;
    }

    private sealed record Column(string Name, Comparison<Session> Rank, bool OpensHighestFirst);
}
