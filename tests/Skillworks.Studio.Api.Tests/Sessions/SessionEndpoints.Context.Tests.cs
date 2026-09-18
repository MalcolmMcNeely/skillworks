using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const long MillionLimit = 1_000_000;

    private const string ModelWithAMillion = "claude-opus-5[1m]";

    private const string ModelWithNoMarker = "claude-opus-5";

    [Fact]
    public async Task Answers_one_run_with_lines_that_hold_only_what_the_context_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")));

        var page = await studio.StepLine("context", Morning);

        Assert.Equal(["kind", "limitTokens", "points"], StudioHost.Fields(page));
        Assert.Equal(
            ["atUtc", "id", "lengthMs", "rebuilt", "skill", "tokens", "unnamed", "writtenToCache"],
            StudioHost.Fields(page["points"]?[0]));
    }

    [Fact]
    public async Task Draws_a_point_for_every_turn_of_the_run_in_order()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { InputTokens = 100 },
            Turn(At(Yesterday, "09:05:00.000")) with { InputTokens = 200 },
            Turn(At(Yesterday, "09:10:00.000")) with { InputTokens = 300 });

        Assert.Equal([100, 200, 300], (await studio.ContextIn(Morning)).Select(point => point.Tokens));
    }

    [Fact]
    public async Task Counts_the_context_of_a_turn_as_what_was_sent_read_from_the_cache_and_written_to_it()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with
        {
            InputTokens = 1_200,
            CacheReadTokens = 40_000,
            CacheCreationTokens = 800,
            OutputTokens = 5_000,
        });

        // What the model answered is not context, so the output tokens are no part of the figure.
        var point = Assert.Single(await studio.ContextIn(Morning));

        Assert.Equal(42_000, point.Tokens);
        Assert.Equal(800, point.WrittenToCache);
    }

    [Fact]
    public async Task Names_the_skill_in_force_on_a_turn()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { Skill = "tdd" });

        var point = Assert.Single(await studio.ContextIn(Morning));

        Assert.Equal("tdd", point.Skill);
        Assert.False(point.Unnamed);
    }

    [Fact]
    public async Task Names_no_skill_on_a_turn_that_had_none_in_force()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")));

        // The Turn that chose a skill belongs to no skill, and Studio never names one Claude Code did not.
        var point = Assert.Single(await studio.ContextIn(Morning));

        Assert.Null(point.Skill);
        Assert.False(point.Unnamed);
    }

    [Fact]
    public async Task Marks_a_turn_whose_skill_claude_code_will_not_name_apart_from_one_with_no_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { Skill = "third-party" });

        // A skill was in force, so reading it as no skill would say the opposite of what happened.
        var point = Assert.Single(await studio.ContextIn(Morning));

        Assert.Null(point.Skill);
        Assert.True(point.Unnamed);
    }

    [Fact]
    public async Task Reads_the_context_limit_off_the_model_the_turns_named()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { Model = ModelWithAMillion });

        Assert.Equal(MillionLimit, (await studio.StepAnswer(Morning)).LimitTokens);
    }

    [Fact]
    public async Task Knows_no_context_limit_where_no_model_named_one()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { Model = ModelWithNoMarker });

        // A limit nobody stated, read as a figure, would make every run look safe or doomed by invention.
        Assert.Null((await studio.StepAnswer(Morning)).LimitTokens);
    }

    [Fact]
    public async Task Keeps_the_limit_one_model_named_though_another_turn_named_none()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { Model = ModelWithAMillion },
            Turn(At(Yesterday, "09:05:00.000")) with { Model = ModelWithNoMarker });

        // A Subagent on a smaller model is a Turn of the same run, and it states nothing about the window.
        Assert.Equal(MillionLimit, (await studio.StepAnswer(Morning)).LimitTokens);
    }

    [Fact]
    public async Task Marks_the_turn_the_prompt_cache_was_rebuilt_on()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { CacheReadTokens = 60_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { CacheReadTokens = 1_000, CacheCreationTokens = 61_000 });

        Assert.Equal([false, true], (await studio.ContextIn(Morning)).Select(point => point.Rebuilt));
    }

    [Fact]
    public async Task Leaves_the_first_turn_of_a_run_unmarked_though_it_wrote_the_whole_cache()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { CacheCreationTokens = 80_000 });

        // Every run writes its cache at the start, so marking that would mark every run.
        Assert.False(Assert.Single(await studio.ContextIn(Morning)).Rebuilt);
    }

    [Fact]
    public async Task Leaves_a_turn_that_wrote_too_few_tokens_to_matter_unmarked()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { CacheCreationTokens = 60_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { CacheReadTokens = 5_000, CacheCreationTokens = 15_000 });

        // Most of a small context, but too little of it to have cost anything worth telling a reader about.
        Assert.Equal([false, false], (await studio.ContextIn(Morning)).Select(point => point.Rebuilt));
    }

    [Fact]
    public async Task Leaves_a_turn_that_only_topped_a_large_cache_up_unmarked()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { CacheCreationTokens = 60_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { CacheReadTokens = 270_000, CacheCreationTokens = 30_000 });

        // Plenty of tokens written, but a cache read back nearly whole is the cache working, not failing.
        Assert.Equal([false, false], (await studio.ContextIn(Morning)).Select(point => point.Rebuilt));
    }

    [Fact]
    public async Task Starts_a_point_where_the_turn_it_stands_for_started()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:10.000")) with { DurationMs = 4_000 });

        // A point drawn where Claude Code wrote the event would sit outside the Spell its Step covers.
        var point = Assert.Single(await studio.ContextIn(Morning));

        Assert.Equal(Moment(At(Yesterday, "09:00:06.000")), point.AtUtc);
        Assert.Equal(4_000, point.LengthMs);
    }

    [Fact]
    public async Task Gives_a_point_the_identity_of_the_step_it_stands_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")),
            Turn(At(Yesterday, "09:05:00.000")));

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal(
            answer.Steps.Where(step => step.Kind == "turn").Select(step => step.Id),
            answer.Context.Select(point => point.Id));
    }

    [Fact]
    public async Task Reads_the_context_of_the_run_that_was_asked_for_alone()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { InputTokens = 100 },
            Turn(At(Yesterday, "14:00:00.000")) with { InputTokens = 900, Session = Afternoon });

        Assert.Equal([100], (await studio.ContextIn(Morning)).Select(point => point.Tokens));
    }

    [Fact]
    public async Task Finds_no_context_in_a_run_that_made_no_turn()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        Assert.Empty(await studio.ContextIn(Morning));
    }

    [Fact]
    public async Task Answers_no_context_when_one_run_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.StepAnswer(Morning);

        Assert.Empty(answer.Context);
        Assert.Null(answer.LimitTokens);
    }

    private static ApiRequest Turn(string at) => new(at) { Session = Morning };
}
