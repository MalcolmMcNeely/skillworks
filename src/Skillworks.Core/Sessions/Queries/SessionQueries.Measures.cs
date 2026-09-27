using System.Runtime.CompilerServices;
using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class SessionQueries
{
    private const string ToolCallEvent = "tool_result";

    // Claude Code writes no tool_result for a call that never ran, so a refusal is only ever a decision.
    private const string DecisionEvent = "tool_decision";

    private const string ModelErrorEvent = "api_error";

    private const string TurnEvent = "api_request";

    private const string SuccessAttribute = "success";

    private const string DecisionAttribute = "decision";

    private const string CostAttribute = "cost_usd";

    private const string Unsuccessful = "false";

    private const string Rejected = "reject";

    private static readonly IReadOnlyDictionary<string, decimal> NoValues = new Dictionary<string, decimal>();

    private Dictionary<Measure, Task<MeasureLanding>> Measuring(
        EventQuery own,
        EventQuery children,
        CancellationToken cancellationToken)
    {
        Task<EventTotals> Counted(EventQuery query, IReadOnlyList<string> by) =>
            events.CountAsync(query, by, cancellationToken);

        Task<EventTotals> Costed(EventQuery query, IReadOnlyList<string> by) =>
            events.SumAsync(query, CostAttribute, by, cancellationToken);

        // One read answers how many Tool calls a run made and how many of them failed.
        var calling = BothAsync(Counted, own, children, ToolCallEvent, SuccessAttribute);
        var deciding = BothAsync(Counted, own, children, DecisionEvent, DecisionAttribute);
        var erring = BothAsync(Counted, own, children, ModelErrorEvent, null);
        var costing = BothAsync(Costed, own, children, TurnEvent, null);

        return new Dictionary<Measure, Task<MeasureLanding>>
        {
            [Measure.ToolCalls] = TotalledAsync(Measure.ToolCalls, calling, _ => true),
            [Measure.Cost] = TotalledAsync(Measure.Cost, costing, _ => true),
            [Measure.Faults] = FaultsAsync(calling, erring),
            [Measure.Friction] = TotalledAsync(Measure.Friction, deciding, Refused),
        };
    }

    // A Parent row stands for the whole piece of work, so each read is asked of the rows and of their Children.
    private static async Task<Both> BothAsync(
        Func<EventQuery, IReadOnlyList<string>, Task<EventTotals>> read,
        EventQuery own,
        EventQuery children,
        string eventName,
        string? attribute)
    {
        string[] bySession = attribute is null ? [EventAttributes.Session] : [EventAttributes.Session, attribute];
        string[] byParent = attribute is null ? [EventAttributes.Parent] : [EventAttributes.Parent, attribute];

        var owning = read(own with { EventName = eventName }, bySession);
        var childing = read(children with { EventName = eventName }, byParent);

        return new Both(await owning, await childing);
    }

    // Each lands on its own, so nothing ready is held back to buy an order a test could read top to bottom.
    private static async IAsyncEnumerable<MeasureLanding> LandingAsync(
        IEnumerable<Task<MeasureLanding>> measuring,
        IReadOnlyList<SessionRow> rows,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await foreach (var landing in Task.WhenEach(measuring).WithCancellation(cancellationToken))
        {
            var measured = await landing;

            yield return measured.Unreachable is null ? measured with { Values = Only(rows, measured.Values) } : measured;
        }
    }

    private static async Task<MeasureLanding> TotalledAsync(Measure measure, Task<Both> reading, Func<EventTotal, bool> counts)
    {
        var read = await reading;

        return new MeasureLanding(measure, read.Unreachable is null ? read.Totalled(counts) : NoValues, read.Unreachable);
    }

    // Both halves are added before the figure goes out, so a reader never watches the count climb from one to both.
    private static async Task<MeasureLanding> FaultsAsync(Task<Both> calling, Task<Both> erring)
    {
        var (called, erred) = (await calling, await erring);
        var unreachable = called.Unreachable ?? erred.Unreachable;

        var values = unreachable is null ? Added(called.Totalled(Failed), erred.Totalled(_ => true)) : NoValues;

        return new MeasureLanding(Measure.Faults, values, unreachable);
    }

    // A run no row names was narrowed away, and handing its figure back would undo the narrowing.
    private static Dictionary<string, decimal> Only(
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, decimal> values) =>
        rows.Where(row => values.ContainsKey(row.Id)).ToDictionary(row => row.Id, row => values[row.Id]);

    private static bool Failed(EventTotal call) => call.Attribute(SuccessAttribute) == Unsuccessful;

    private static bool Refused(EventTotal decision) => decision.Attribute(DecisionAttribute) == Rejected;

    private static Dictionary<string, decimal> TotalledIn(IEnumerable<EventTotal> groups, string attribute) =>
        Grouped(groups, attribute).ToDictionary(run => run.Key, run => run.Sum(total => total.Total));

    private static Dictionary<string, decimal> Added(
        IReadOnlyDictionary<string, decimal> one,
        IReadOnlyDictionary<string, decimal> other) =>
        one.Keys
            .Union(other.Keys)
            .ToDictionary(id => id, id => one.GetValueOrDefault(id) + other.GetValueOrDefault(id));

    private sealed record Both(EventTotals Own, EventTotals Children)
    {
        public string? Unreachable => Own.Unreachable ?? Children.Unreachable;

        public Dictionary<string, decimal> Totalled(Func<EventTotal, bool> counts) =>
            Added(
                TotalledIn(Own.Groups.Where(counts), EventAttributes.Session),
                TotalledIn(Children.Groups.Where(counts), EventAttributes.Parent));
    }
}
