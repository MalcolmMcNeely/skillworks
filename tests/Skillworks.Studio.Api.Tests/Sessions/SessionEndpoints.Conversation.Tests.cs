using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Answers_one_run_with_lines_that_hold_only_what_the_conversation_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var page = await studio.StepLine("exchanges", Morning);

        Assert.Equal(["exchanges", "kind"], StudioHost.Fields(page));
        Assert.Equal(
            ["answer", "answerLength", "atUtc", "cost", "index", "lengthMs", "prompt", "promptLength", "toolCalls", "turns"],
            StudioHost.Fields(page["exchanges"]?[0]));
    }

    [Fact]
    public async Task Opens_an_exchange_at_each_prompt_and_lists_them_in_order()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), "Built."),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:05:00.000"), "Now the docs"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:06:00.000"), "Written."));

        var said = await studio.ExchangesIn(Morning);

        Assert.Equal([0, 1], said.Select(each => each.Index));
        Assert.Equal(["Fix the build", "Now the docs"], said.Select(each => each.Prompt));
        Assert.Equal(["Built.", "Written."], said.Select(each => each.Answer));
    }

    [Fact]
    public async Task Counts_the_turns_the_tool_calls_and_the_cost_inside_one_exchange()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 2_000, 0.10m),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:08.000")),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:12.000"), 2_000, 0.32m),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:15.000")),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:20.000"), "Built."),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:05:00.000"), "Now the docs"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:05:05.000"), 1_000, 0.05m));

        var said = await studio.ExchangesIn(Morning);

        Assert.Equal([2, 1], said.Select(each => each.Turns));
        Assert.Equal([2, 0], said.Select(each => each.ToolCalls));
        Assert.Equal([0.42m, 0.05m], said.Select(each => each.Cost));
    }

    [Fact]
    public async Task Closes_an_exchange_at_the_answer_that_followed_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), "Built."),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:05:00.000"), "Now the docs"));

        var said = await studio.ExchangesIn(Morning);

        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), said[0].AtUtc);
        Assert.Equal(10_000, said[0].LengthMs);
    }

    [Fact]
    public async Task Closes_an_exchange_with_no_answer_at_the_last_step_that_followed_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Bash", 3_000));

        Assert.Equal(5_000, Assert.Single(await studio.ExchangesIn(Morning)).LengthMs);
    }

    [Fact]
    public async Task Closes_an_exchange_at_the_last_answer_when_the_agent_spoke_more_than_once()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), "Looking at it."),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:40.000"), "Built."));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Equal("Built.", said.Answer);
        Assert.Equal(40_000, said.LengthMs);
    }

    [Fact]
    public async Task Leaves_work_before_the_first_prompt_out_of_every_exchange()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, At(Yesterday, "08:59:00.000")),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), said.AtUtc);
        Assert.Equal(1, said.ToolCalls);
    }

    [Fact]
    public async Task Keeps_the_request_that_named_the_run_out_of_the_conversation()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:05.000"), "The build fix"));

        // Claude Code asked for the title itself, so it is no part of what the agent answered.
        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Null(said.Answer);
        Assert.Equal(0, said.AnswerLength);
        Assert.Equal(0, said.LengthMs);
    }

    [Fact]
    public async Task Shows_the_true_length_of_a_prompt_whose_words_were_withheld()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.PromptWithheld(Morning, At(Yesterday, "09:00:00.000"), 1_840),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), "Built."));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Null(said.Prompt);
        Assert.Equal(1_840, said.PromptLength);
    }

    [Fact]
    public async Task Shows_the_true_length_of_an_answer_whose_words_were_withheld()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.AnswerWithheld(Morning, At(Yesterday, "09:00:10.000"), 4_206));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Null(said.Answer);
        Assert.Equal(4_206, said.AnswerLength);
    }

    [Fact]
    public async Task Counts_the_words_of_a_prompt_and_an_answer_that_were_not_withheld()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), "Built."));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Equal("Fix the build".Length, said.PromptLength);
        Assert.Equal("Built.".Length, said.AnswerLength);
    }

    [Fact]
    public async Task Reads_a_long_prompt_and_a_long_answer_whole_so_a_reader_can_read_them()
    {
        using var studio = new StudioHost();

        var asked = new string('a', 900);
        var answered = new string('b', 900);

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), asked),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:10.000"), answered));

        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Equal(asked, said.Prompt);
        Assert.Equal(answered, said.Answer);
    }

    [Fact]
    public async Task Says_nothing_was_recorded_where_neither_the_words_nor_their_length_were()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", At(Yesterday, "09:00:00.000")) { Prompt = SessionEvent.Withheld });

        // An older Claude Code wrote no length, so the panel can say only that it holds nothing.
        var said = Assert.Single(await studio.ExchangesIn(Morning));

        Assert.Null(said.Prompt);
        Assert.Equal(0, said.PromptLength);
    }

    [Fact]
    public async Task Keeps_the_placeholder_that_stands_in_for_withheld_words_off_every_screen()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.PromptWithheld(Morning, At(Yesterday, "09:00:00.000"), 1_840),
            SessionEvent.AnswerWithheld(Morning, At(Yesterday, "09:00:10.000"), 4_206));

        // The timeline and the conversation read the same run, so neither may show Claude Code's stand-in.
        Assert.All(await studio.StepsIn(Morning), step => Assert.Null(step.Words));
        Assert.All(await studio.ExchangesIn(Morning), said => Assert.Null(said.Prompt));
    }

    [Fact]
    public async Task Finds_no_exchange_in_a_run_nobody_typed_into()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:00.000")));

        Assert.Empty(await studio.ExchangesIn(Morning));
    }

    [Fact]
    public async Task Answers_no_exchanges_when_one_run_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        Assert.Empty(await studio.ExchangesIn(Morning));
    }
}
