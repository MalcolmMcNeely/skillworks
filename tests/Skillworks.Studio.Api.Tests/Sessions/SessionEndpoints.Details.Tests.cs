using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Answers_with_the_details_of_the_steps_after_the_spans()
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, "main");

        var kinds = (await studio.StepLines(Morning)).Select(StudioHost.KindOf).ToList();

        Assert.True(kinds.IndexOf("details") > kinds.IndexOf("agents"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("main")]
    [InlineData("sdk")]
    [InlineData("repl_main_thread:outputStyle:custom")]
    public async Task Gives_a_turn_the_main_agent_sent_for_the_prompt_the_purpose_of_work(string? sentAs)
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, sentAs);

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("work", null), (turn.Purpose, turn.Side));
    }

    [Fact]
    public async Task Gives_a_turn_a_subagent_sent_the_purpose_of_a_subagents_work()
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, "agent:custom");

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("subagent", null), (turn.Purpose, turn.Side));
    }

    [Theory]
    [InlineData("away_summary", "awaySummary")]
    [InlineData("prompt_suggestion", "promptSuggestion")]
    [InlineData("generate_session_title", "sessionTitle")]
    [InlineData("compact", "compaction")]
    [InlineData("agent_summary", "subagentSummary")]
    [InlineData("web_fetch_apply", "webPageRead")]
    [InlineData("web_search_tool", "webSearch")]
    public async Task Names_the_side_request_a_turn_claude_code_sent_for_itself_was(string sentAs, string side)
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, sentAs);

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("side", side), (turn.Purpose, turn.Side));
    }

    [Fact]
    public async Task Keeps_claude_codes_own_value_for_a_side_request_studio_has_no_name_for()
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, "bespoke_request");

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("side", "other", "bespoke_request"), (turn.Purpose, turn.Side, turn.SentAs));
    }

    [Fact]
    public async Task Gives_a_turn_its_output_tokens_and_its_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, cost: 0.42m) with { OutputTokens = "1200" });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal((1_200L, 0.42m), (turn.OutputTokens, turn.Cost));
    }

    [Fact]
    public async Task Splits_a_turns_tokens_into_read_from_cache_written_to_cache_new_input_and_output()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000) with
            {
                CacheReadTokens = "40000",
                CacheCreationTokens = "3000",
                InputTokens = "12",
                OutputTokens = "800",
            });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(
            (40_000L, 3_000L, 12L, 800L),
            (turn.CacheReadTokens, turn.CacheWriteTokens, turn.InputTokens, turn.OutputTokens));
    }

    [Fact]
    public async Task Gives_a_turn_its_wait_for_the_first_word_beside_its_length()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000) with { FirstWordMs = "1400" });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal((1_400L, 5_000L), (turn.FirstWordMs, turn.LengthMs));
    }

    [Fact]
    public async Task Leaves_the_first_word_not_known_where_claude_code_gave_no_wait()
    {
        using var studio = new StudioHost();

        await TurnedFor(studio, "main");

        var turn = await OnlyTurnIn(studio);

        Assert.Null(turn.FirstWordMs);
    }

    [Fact]
    public async Task Gives_a_turn_its_model_its_effort_and_its_speed()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000) with { Effort = "high", Speed = "fast" });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("claude-opus-5", "high", "fast"), (turn.Model, turn.Effort, turn.Speed));
    }

    [Fact]
    public async Task Gives_a_turn_the_words_of_the_answer_that_carries_its_request_id()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, request: "req_recap", source: "away_summary"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:05.010"), "You were fixing the build.", request: "req_recap"));

        var turn = await OnlyTurnIn(studio);

        Assert.Equal(("You were fixing the build.", 26), (turn.Words, turn.WordsLength));
    }

    [Fact]
    public async Task Gives_a_turn_whose_answer_was_withheld_no_words_and_their_size()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, request: "req_1"),
            SessionEvent.AnswerWithheld(Morning, At(Yesterday, "09:00:05.010"), 1_234) with { RequestId = "req_1" });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal((null, 1_234), (turn.Words, turn.WordsLength));
    }

    [Fact]
    public async Task Gives_a_turn_whose_answer_came_with_its_size_alone_no_words_and_their_size()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, request: "req_1"),
            new SessionEvent(Morning, "assistant_response", At(Yesterday, "09:00:05.010")) { ResponseLength = "640", RequestId = "req_1" });

        var turn = await OnlyTurnIn(studio);

        Assert.Equal((null, 640), (turn.Words, turn.WordsLength));
    }

    [Fact]
    public async Task Gives_a_turn_no_answer_carries_the_request_id_of_no_words()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, request: "req_1"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:05.010"), "Done.", request: "req_2"));

        var turn = await OnlyTurnIn(studio);

        Assert.Equal((null, null), (turn.Words, turn.WordsLength));
    }

    private static Task TurnedFor(StudioHost studio, string? sentAs) =>
        studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, source: sentAs));

    private static async Task<TurnDetailsRow> OnlyTurnIn(StudioHost studio)
    {
        var answer = await studio.StepAnswer(Morning);
        var turn = Assert.Single(answer.Steps, step => step.Kind == "turn");

        return answer.Turns[turn.Id];
    }
}
