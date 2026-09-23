using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private static readonly string[] EveryMeasure = ["toolCalls", "cost", "faults", "friction"];

    [Fact]
    public async Task Adds_every_childs_measures_into_its_parents_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.Refused(Morning, At(Yesterday, "09:02:00.000")),
            SessionEvent.Turned(Morning, At(Yesterday, "09:03:00.000"), cost: 0.25m),
            SessionEvent.ToolFailed(Afternoon, At(Yesterday, "09:10:00.000")) with { Parent = Morning },
            SessionEvent.ModelFailed(Afternoon, At(Yesterday, "09:11:00.000")) with { Parent = Morning },
            SessionEvent.HookBlocked(Afternoon, At(Yesterday, "09:12:00.000")) with { Parent = Morning },
            SessionEvent.Turned(Afternoon, At(Yesterday, "09:13:00.000"), cost: 0.5m) with { Parent = Morning },
            SessionEvent.ToolRan(Evening, At(Yesterday, "09:20:00.000")) with { Parent = Morning },
            SessionEvent.ToolFailed(Evening, At(Yesterday, "09:21:00.000")) with { Parent = Morning },
            SessionEvent.Turned(Evening, At(Yesterday, "09:22:00.000"), cost: 0.25m) with { Parent = Morning });

        var answer = await studio.SessionAnswer();

        Assert.Equal((4m, 3m, 2m), Counts(answer, Morning));
        Assert.Equal(1m, answer.Measured("cost", Morning));
    }

    [Fact]
    public async Task Keys_no_measure_value_by_a_folded_child()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.ToolFailed(Afternoon, At(Yesterday, "09:10:00.000")) with { Parent = Morning },
            SessionEvent.Refused(Afternoon, At(Yesterday, "09:11:00.000")) with { Parent = Morning },
            SessionEvent.Turned(Afternoon, At(Yesterday, "09:12:00.000"), cost: 0.5m) with { Parent = Morning },
            SessionEvent.Titled(Evening, At(Yesterday, "14:00:00.000"), "The chat"),
            SessionEvent.ToolRan(Evening, At(Yesterday, "14:01:00.000")));

        var answer = await studio.SessionAnswer();

        // A value keyed by a row that does not exist is a figure no reader can see.
        Assert.All(EveryMeasure, measure => Assert.DoesNotContain(Afternoon, answer.Measures[measure].Keys));
    }

    [Fact]
    public async Task Keeps_a_parentless_sessions_figures_beside_a_parent()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.ToolFailed(Afternoon, At(Yesterday, "09:10:00.000")) with { Parent = Morning },
            SessionEvent.Titled(Evening, At(Yesterday, "14:00:00.000"), "The chat"),
            SessionEvent.ToolRan(Evening, At(Yesterday, "14:01:00.000")),
            SessionEvent.Refused(Evening, At(Yesterday, "14:02:00.000")),
            SessionEvent.Turned(Evening, At(Yesterday, "14:03:00.000"), cost: 0.5m));

        var answer = await studio.SessionAnswer();

        Assert.Equal((1m, 0m, 1m), Counts(answer, Evening));
        Assert.Equal(0.5m, answer.Measured("cost", Evening));
    }

    [Fact]
    public async Task Keeps_the_figures_of_a_child_whose_parent_left_no_events()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = AbsentParent },
            SessionEvent.ToolFailed(Afternoon, At(Yesterday, "09:06:00.000")) with { Parent = AbsentParent },
            SessionEvent.Refused(Afternoon, At(Yesterday, "09:07:00.000")) with { Parent = AbsentParent },
            SessionEvent.Turned(Afternoon, At(Yesterday, "09:08:00.000"), cost: 0.5m) with { Parent = AbsentParent });

        var answer = await studio.SessionAnswer();

        Assert.Equal((1m, 1m, 1m), Counts(answer, Afternoon));
        Assert.Equal(0.5m, answer.Measured("cost", Afternoon));
    }

    [Fact]
    public async Task Sorts_a_parent_by_its_combined_measure()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The spec run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "09:10:00.000")) with { Parent = Morning },
            SessionEvent.ToolRan(Afternoon, At(Yesterday, "09:11:00.000")) with { Parent = Morning },
            SessionEvent.Titled(Evening, At(Yesterday, "14:00:00.000"), "The chat"),
            SessionEvent.ToolRan(Evening, At(Yesterday, "14:01:00.000")),
            SessionEvent.ToolRan(Evening, At(Yesterday, "14:02:00.000")));

        // On its own calls the spec run would sit below the chat, which is not what its row shows.
        Assert.Equal(["The spec run", "The chat"], await Names(studio, "?sort=toolCalls&descending=true"));
        Assert.Equal(["The chat", "The spec run"], await Names(studio, "?sort=toolCalls&descending=false"));
    }
}
