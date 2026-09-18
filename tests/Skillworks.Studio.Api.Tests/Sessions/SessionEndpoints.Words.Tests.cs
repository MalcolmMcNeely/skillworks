using Skillworks.Core.Telemetry;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Reads_a_run_thin_when_its_spans_are_whole_and_a_prompt_had_its_words_withheld()
    {
        using var studio = new StudioHost();

        await WordsWithheld(studio);

        Assert.Equal("thin", (await studio.StepAnswer(Morning)).Depth);
    }

    [Fact]
    public async Task Reads_a_run_full_when_its_spans_are_whole_and_its_prompts_carry_their_words()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"));

        await studio.PushSpans(Morning, MainTrace, Ran(ToolSpan, "toolu_01", "agent-a"));

        Assert.Equal("full", (await studio.StepAnswer(Morning)).Depth);
    }

    [Fact]
    public async Task Keeps_naming_the_agent_that_ran_a_step_when_the_words_were_withheld()
    {
        using var studio = new StudioHost();

        await WordsWithheld(studio);

        var answer = await studio.StepAnswer(Morning);

        // The Spans landed, so what only a Span can say is still said.
        Assert.Equal("agent-a", answer.Agents[answer.Steps[1].Id]);
    }

    [Fact]
    public async Task Says_the_words_were_withheld_and_names_the_switch_to_change()
    {
        using var studio = new StudioHost(words: false);

        await WordsWithheld(studio);

        var gap = (await studio.StepAnswer(Morning)).Events;

        Assert.Equal("wordsOff", gap.Kind);
        Assert.NotNull(gap.Missing);
        Assert.Contains(TelemetrySwitch.TurnOnNote, gap.Missing, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Tells_withheld_words_apart_from_telemetry_that_was_never_switched_on()
    {
        using var studio = new StudioHost(emitting: false);

        await WordsWithheld(studio);

        Assert.Equal("wordsOff", (await studio.StepAnswer(Morning)).Events.Kind);
    }

    [Fact]
    public async Task Says_the_words_were_withheld_whatever_this_machine_has_switched_on()
    {
        using var studio = new StudioHost();

        await WordsWithheld(studio);

        // A teammate recorded this run on their own machine, so nothing here can decide what it holds.
        var gap = (await studio.StepAnswer(Morning)).Events;

        Assert.Equal("wordsOff", gap.Kind);
        Assert.NotNull(gap.Missing);
        Assert.Contains("cannot be raised", gap.Missing, StringComparison.Ordinal);
        Assert.DoesNotContain(TelemetrySwitch.TurnOnNote, gap.Missing, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Refuses_to_say_the_words_are_recorded_here_when_it_cannot_read_the_settings()
    {
        using var studio = new StudioHost(settings: "{ not json");

        await WordsWithheld(studio);

        // A guess either way sends the developer to a file Studio never read.
        var gap = (await studio.StepAnswer(Morning)).Events;

        Assert.Equal("wordsOff", gap.Kind);
        Assert.NotNull(gap.Missing);
        Assert.Contains("cannot read Claude Code's settings", gap.Missing, StringComparison.Ordinal);
    }

    private static async Task WordsWithheld(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.PromptWithheld(Morning, "2026-09-14T09:00:00.000Z", 1_840),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:00:10.000Z", "Bash", 4_000, use: "toolu_01"));

        await studio.PushSpans(Morning, MainTrace, Ran(ToolSpan, "toolu_01", "agent-a"));
    }
}
