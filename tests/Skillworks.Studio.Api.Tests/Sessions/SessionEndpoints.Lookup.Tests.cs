using System.Globalization;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private static readonly TimeSpan LookupReach = TimeSpan.FromDays(90);

    [Fact]
    public async Task Finds_by_its_whole_id_a_run_older_than_the_lookback_and_draws_it_as_one_row()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(DaysBack(21), "09:00:00.000"), "The old run", "acme/xi"),
            SessionEvent.ToolRan(Morning, At(DaysBack(20), "10:00:00.000")) with { Owner = "acme", RepositoryName = "xi" },
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The recent run"));

        var answer = await studio.LookupAnswer(Morning);

        // One row in the list's own shape, so the page folds and draws it as it does any other and opens it on its own days.
        var row = Assert.Single(answer.Sessions);

        Assert.Equal(Morning, row.Id);
        Assert.Equal("The old run", row.Name);
        Assert.Equal("acme/xi", row.Repository);
        Assert.Equal(Moment(At(DaysBack(21), "09:00:00.000")), row.StartedUtc);
        Assert.Equal((long)TimeSpan.FromHours(25).TotalMilliseconds, row.LengthMs);
        Assert.Equal((DaysBack(21), DaysBack(20)), (row.FirstDay, row.LastDay));
    }

    [Fact]
    public async Task Answers_a_whole_id_that_names_no_run_with_no_row_and_no_gap()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.LookupAnswer(Evening);

        // No run is a whole answer to a whole id, and never a quiet period or a store that fell short.
        Assert.Empty(answer.Sessions);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Finds_no_run_by_a_whole_id_older_than_the_reach_and_says_how_far_it_looked()
    {
        using var studio = new StudioHost(lookupReachDays: 10);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(DaysBack(12), "09:00:00.000"), "The run past the reach"));

        var answer = await studio.LookupAnswer(Morning);

        Assert.Empty(answer.Sessions);
        Assert.Equal(answer.Head.AsOfUtc - TimeSpan.FromDays(10), answer.QuietSinceUtc);
    }

    [Fact]
    public async Task Measures_the_row_a_whole_id_found()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(DaysBack(10), "09:00:00.000"), "The old run"),
            SessionEvent.ToolRan(Morning, At(DaysBack(10), "09:01:00.000")),
            SessionEvent.ToolFailed(Morning, At(DaysBack(10), "09:02:00.000")));

        var answer = await studio.LookupAnswer(Morning);

        Assert.Equal((2m, 1m), (answer.Measured("toolCalls", Morning), answer.Measured("faults", Morning)));
    }

    [Fact]
    public async Task Reads_the_depth_of_the_row_a_whole_id_found()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(DaysBack(10), "09:00:00.000"), "The old run"));
        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));

        var answer = await studio.LookupAnswer(Morning);

        Assert.Equal("full", answer.Depths[Morning]);
    }

    [Fact]
    public async Task Finds_its_run_by_a_whole_id_whatever_repository_or_skill_the_filter_holds()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, Ran(Morning, At(DaysBack(10), "09:00:00.000"), "The run elsewhere", "acme/xi"));
        await studio.Push(
            new SkillActivated("tdd", At(DaysBack(10), "09:05:00.000"), Owner: "acme", RepositoryName: "xi") { Session = Morning });

        var answer = await studio.LookupAnswer(Morning, "?repository=acme/nu&skill=comment-sweep");

        // The row shows the run's own Repository, so a reader sees it sits outside the one they chose.
        Assert.Equal("acme/xi", Assert.Single(answer.Sessions).Repository);
    }

    [Fact]
    public async Task Reads_a_lookup_as_of_now_whatever_paging_a_load_more_left_on_the_address()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var stale = Instant(studio.Clock.GetUtcNow() - TimeSpan.FromDays(10));
        var answer = await studio.LookupAnswer(Morning, $"?asOf={stale}&latestBefore={stale}");

        // The paging says where a list stopped, and a Lookup names one run, so it reads as of now.
        Assert.Equal([Morning], answer.Sessions.Select(session => session.Id));
        Assert.Equal(studio.Clock.GetUtcNow(), answer.Head.AsOfUtc);
    }

    [Fact]
    public async Task Ends_a_lookup_answer_with_the_start_of_its_ninety_day_reach_and_no_oldest_latest()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(DaysBack(21), "09:00:00.000"), "The old run"));

        var answer = await studio.LookupAnswer(Morning);

        // The page says how far back the Lookup looked from these, without knowing the setting, and offers no Load more.
        Assert.Null(answer.OldestLatestUtc);
        Assert.Equal(answer.Head.AsOfUtc - LookupReach, answer.QuietSinceUtc);
    }

    [Fact]
    public async Task Names_the_events_store_when_a_lookup_could_not_read_it()
    {
        using var events = StandInEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.LookupAnswer(Morning);

        // A store that fell short must never read as a run that does not exist.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("events store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    private static string Instant(DateTimeOffset moment) =>
        Uri.EscapeDataString(moment.ToString("O", CultureInfo.InvariantCulture));
}
