namespace Skillworks.Core.Sessions.Measures;

// Faults holds both halves already added, so a reader never watches it climb from the tool half to the whole.
public sealed record SessionMeasures(
    IReadOnlyDictionary<string, decimal> ToolCalls,
    IReadOnlyDictionary<string, decimal> Cost,
    IReadOnlyDictionary<string, decimal> Faults,
    IReadOnlyDictionary<string, decimal> Friction)
{
    private static readonly IReadOnlyDictionary<string, decimal> None = new Dictionary<string, decimal>();

    public static readonly SessionMeasures Nothing = new(None, None, None, None);

    public IEnumerable<SessionMeasure> Lines() =>
    [
        new(Measure.ToolCalls, ToolCalls),
        new(Measure.Cost, Cost),
        new(Measure.Faults, Faults),
        new(Measure.Friction, Friction),
    ];

    // A run no row names was narrowed away, and handing its figure back would undo the narrowing.
    public SessionMeasures Covering(IReadOnlyList<SessionRow> rows) =>
        new(Only(rows, ToolCalls), Only(rows, Cost), Only(rows, Faults), Only(rows, Friction));

    private static IReadOnlyDictionary<string, decimal> Only(
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, decimal> values) =>
        rows.Where(row => values.ContainsKey(row.Id)).ToDictionary(row => row.Id, row => values[row.Id]);
}
