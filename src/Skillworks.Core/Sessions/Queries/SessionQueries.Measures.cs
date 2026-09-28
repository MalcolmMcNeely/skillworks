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

    private static readonly string[] CountedEvents = [ToolCallEvent, DecisionEvent, ModelErrorEvent];

    private static readonly string[] CountedBy = [EventAttributes.EventName, SuccessAttribute, DecisionAttribute];

    private Dictionary<Measure, Task<MeasureLanding>> Measuring(
        EventQuery own,
        EventQuery children,
        CancellationToken cancellationToken)
    {
        Task<EventTotals> Counted(EventQuery query, IReadOnlyList<string> by) =>
            events.CountAsync(query with { EventName = EventQuery.AnyEvent, AnyOfEvents = CountedEvents }, by, cancellationToken);

        Task<EventTotals> Costed(EventQuery query, IReadOnlyList<string> by) =>
            events.SumAsync(query with { EventName = TurnEvent }, CostAttribute, by, cancellationToken);

        // One count serves three Measures, so the store gets fewer questions and they land or fall short together.
        var counting = BothAsync(Counted, own, children, CountedBy);
        var costing = BothAsync(Costed, own, children, []);

        return new Dictionary<Measure, Task<MeasureLanding>>
        {
            [Measure.ToolCalls] = TotalledAsync(Measure.ToolCalls, counting, Called),
            [Measure.Cost] = TotalledAsync(Measure.Cost, costing, _ => true),
            [Measure.Faults] = TotalledAsync(Measure.Faults, counting, Faulted),
            [Measure.Friction] = TotalledAsync(Measure.Friction, counting, Refused),
        };
    }

    // A Parent row stands for its Children too, and one read grouped by run and Parent ran past the store's series limit.
    private static async Task<Both> BothAsync(
        Func<EventQuery, IReadOnlyList<string>, Task<EventTotals>> read,
        EventQuery own,
        EventQuery children,
        IReadOnlyList<string> by)
    {
        var owning = read(own, [EventAttributes.Session, .. by]);
        var childing = read(children, [EventAttributes.Parent, .. by]);

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

    // A run no row names was narrowed away, and handing its figure back would undo the narrowing.
    private static Dictionary<string, decimal> Only(
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, decimal> values) =>
        rows.Where(row => values.ContainsKey(row.Id)).ToDictionary(row => row.Id, row => values[row.Id]);

    private static bool Called(EventTotal counted) => counted.Attribute(EventAttributes.EventName) == ToolCallEvent;

    private static bool Faulted(EventTotal counted) =>
        (Called(counted) && counted.Attribute(SuccessAttribute) == Unsuccessful) ||
        counted.Attribute(EventAttributes.EventName) == ModelErrorEvent;

    private static bool Refused(EventTotal counted) =>
        counted.Attribute(EventAttributes.EventName) == DecisionEvent && counted.Attribute(DecisionAttribute) == Rejected;

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
