using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Sends_the_rows_before_any_measure()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var kinds = (await studio.SessionLines()).Select(StudioHost.KindOf).ToList();

        // The rows are the table, so a reader has it in hand before a single number reaches them.
        Assert.True(kinds.IndexOf("sessions") < kinds.IndexOf("measure"));
    }

    [Fact]
    public async Task Sends_every_measure_on_a_line_of_its_own()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        // Each lands on its own, so the order they come in is no part of the answer.
        Assert.Equal(
            ["cost", "faults", "friction", "toolCalls"],
            (await studio.SessionAnswer()).Measures.Keys.Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task Names_a_value_on_each_measure_for_every_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The early run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"),
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "14:01:00.000")),
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "14:02:00.000")));

        var answer = await studio.SessionAnswer();

        Assert.Equal([Morning, Afternoon], answer.Sessions.Select(session => session.Id).Order(StringComparer.Ordinal));
        Assert.Equal(1m, answer.Measured("toolCalls", Morning));
        Assert.Equal(2m, answer.Measured("toolCalls", Afternoon));
    }

    [Fact]
    public async Task Names_no_run_the_filter_left_out_on_a_measure()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")) with { Owner = "acme", RepositoryName = "xi" },
            Ran(Afternoon, At(Yesterday, "14:00:00.000"), "The other run", "acme/nu"),
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "14:01:00.000")) with { Owner = "acme", RepositoryName = "nu" });

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // A figure for a run nobody can see would hand back what the filter narrowed away.
        Assert.Equal([Morning], answer.Measures["toolCalls"].Keys);
    }

    [Fact]
    public async Task Sends_faults_whole_rather_than_the_tool_half_and_the_model_half()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The broken run"),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ModelFailed(Morning, At(Yesterday, "09:02:00.000")));

        var answer = await studio.SessionAnswer();

        // One line, so a reader never watches the count climb from one half to both.
        Assert.Equal(2m, Assert.Single(answer.Measures["faults"]).Value);
    }

    [Fact]
    public async Task Sends_no_measure_when_the_events_store_never_answered()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        // No rows to hang a number on, so a Measure for them would be a figure about nothing.
        Assert.Empty((await studio.SessionAnswer()).Measures);
    }
}
