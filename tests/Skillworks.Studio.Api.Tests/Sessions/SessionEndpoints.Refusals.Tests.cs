using System.Net;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string SeriesLimit = "maximum of series (500) reached for a single query";

    [Fact]
    public async Task Names_the_events_stores_own_reason_in_the_Gap_for_a_read_it_refused()
    {
        using var events = StandInEventsStore.Refusing(HttpStatusCode.BadRequest, SeriesLimit);
        using var studio = new StudioHost(events: events);

        var answer = await studio.SessionAnswer();

        // A bare status would leave a reader unable to tell a refused query from a store that is down.
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("400", answer.Gap.Missing ?? "", StringComparison.Ordinal);
        Assert.Contains(SeriesLimit, answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Names_the_status_in_the_Gap_for_a_refusal_that_gave_no_reason()
    {
        using var events = StandInEventsStore.Failing(HttpStatusCode.BadRequest);
        using var studio = new StudioHost(events: events);

        var answer = await studio.SessionAnswer();

        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("answered 400.", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Names_the_trace_stores_own_reason_in_the_Gap_for_a_read_it_refused()
    {
        const string reason = "invalid TraceQL query: parse error";

        using var traces = BrokenTraceStore.Refusing(HttpStatusCode.BadRequest, reason);
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("unreachable", answer.Traces.Kind);
        Assert.Contains("400", answer.Traces.Missing ?? "", StringComparison.Ordinal);
        Assert.Contains(reason, answer.Traces.Missing ?? "", StringComparison.Ordinal);
    }
}
