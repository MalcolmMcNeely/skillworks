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
