using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Gives_a_fault_the_error_text_its_status_code_and_its_attempt()
    {
        using var studio = new StudioHost();

        await FaultedWith(studio, SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")) with
        {
            Error = "Overloaded: the API is busy, try again shortly",
            StatusCode = "529",
            Attempt = "3",
        });

        var fault = await OnlyFaultIn(studio);

        Assert.Equal(("Overloaded: the API is busy, try again shortly", 529, 3), (fault.Error, fault.StatusCode, fault.Attempt));
    }

    [Fact]
    public async Task Gives_a_fault_its_error_kind_where_claude_code_sent_no_text()
    {
        using var studio = new StudioHost();

        await FaultedWith(studio, SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")));

        var fault = await OnlyFaultIn(studio);

        Assert.Equal("RateLimited", fault.Error);
    }

    [Fact]
    public async Task Gives_a_fault_no_status_code_and_no_attempt_where_claude_code_sent_none()
    {
        using var studio = new StudioHost();

        await FaultedWith(studio, SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")));

        var fault = await OnlyFaultIn(studio);

        Assert.Equal((null, null), (fault.StatusCode, fault.Attempt));
    }

    [Fact]
    public async Task Gives_a_fault_the_model_and_effort_of_its_turn()
    {
        using var studio = new StudioHost();

        await FaultedWith(studio, SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")) with
        {
            Model = "claude-opus-5",
            Effort = "high",
        });

        var fault = await OnlyFaultIn(studio);

        Assert.Equal(("claude-opus-5", "high"), (fault.Model, fault.Effort));
    }

    [Fact]
    public async Task Gives_a_fault_the_purpose_of_the_turn_it_was_sent_for()
    {
        using var studio = new StudioHost();

        await FaultedWith(studio, SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")) with { QuerySource = "away_summary" });

        var fault = await OnlyFaultIn(studio);

        Assert.Equal(("side", "awaySummary", "away_summary"), (fault.Purpose, fault.Side, fault.SentAs));
    }

    private static Task FaultedWith(StudioHost studio, SessionEvent fault) =>
        studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"), fault);

    private static async Task<FaultDetailsRow> OnlyFaultIn(StudioHost studio)
    {
        var answer = await studio.StepAnswer(Morning);
        var fault = Assert.Single(answer.Steps, step => step.Kind == "fault");

        return answer.Faults[fault.Id];
    }
}
