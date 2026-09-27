using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private static readonly TimeSpan Reach = TimeSpan.FromDays(30);

    [Fact]
    public async Task Ends_a_read_that_finds_no_older_prompts_in_its_thirty_days_and_names_the_date()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var answer = await studio.SessionAnswer();

        Assert.Equal([Morning], answer.Sessions.Select(session => session.Id));
        Assert.Null(answer.NextBeforeUtc);
        Assert.Equal(answer.Head.AsOfUtc - Reach, answer.QuietSinceUtc);
    }

    [Fact]
    public async Task Names_the_date_of_a_quiet_thirty_days_and_never_claims_the_store_is_empty()
    {
        using var studio = new StudioHost();

        var answer = await studio.SessionAnswer();

        Assert.Empty(answer.Sessions);
        Assert.Equal(answer.Head.AsOfUtc - Reach, answer.QuietSinceUtc);
    }

    [Fact]
    public async Task Names_the_next_place_and_no_quiet_date_while_older_prompts_remain()
    {
        using var studio = new StudioHost();

        await studio.Push(Asked(RowsPerRead + 1));

        var answer = await studio.SessionAnswer();

        Assert.NotNull(answer.NextBeforeUtc);
        Assert.Null(answer.QuietSinceUtc);
    }

    [Fact]
    public async Task Looks_a_further_thirty_days_back_and_finds_older_work_past_a_quiet_month()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Prompted(Afternoon, At(DaysBack(45), "09:00:00.000"), "Read the logs"),
            SessionEvent.Prompted(Evening, At(DaysBack(70), "09:00:00.000"), "Start the spec"));

        var first = await studio.SessionAnswer();
        var further = await studio.FurtherBackSessionAnswer(first);
        var furthest = await studio.FurtherBackSessionAnswer(further);

        Assert.Equal([Afternoon], further.Sessions.Select(session => session.Id));
        Assert.Equal(first.Head.AsOfUtc - (Reach * 2), further.QuietSinceUtc);
        Assert.Equal([Evening], furthest.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Leaves_out_of_a_further_read_the_work_already_drawn_at_a_newer_prompt()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(45), "09:00:00.000"), "Start the spec"),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Now push it"),
            SessionEvent.Prompted(Afternoon, At(DaysBack(50), "09:00:00.000"), "Read the logs"));

        var first = await studio.SessionAnswer();
        var further = await studio.FurtherBackSessionAnswer(first);

        Assert.Equal([Morning], first.Sessions.Select(session => session.Id));
        Assert.Equal([Afternoon], further.Sessions.Select(session => session.Id));
    }
}
