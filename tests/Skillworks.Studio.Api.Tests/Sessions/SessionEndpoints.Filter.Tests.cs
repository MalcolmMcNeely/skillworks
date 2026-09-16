using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Narrows_the_table_to_a_span_of_days_and_takes_both_ends_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-12T09:00:00.000Z", "The run before"),
            SessionEvent.Titled(Afternoon, "2026-09-13T09:00:00.000Z", "The first day"),
            SessionEvent.Titled(Evening, "2026-09-14T09:00:00.000Z", "The last day"));

        var names = (await studio.SessionsIn("?from=2026-09-13&to=2026-09-14")).Select(session => session.Name);

        Assert.Equal(["The last day", "The first day"], names);
    }

    [Fact]
    public async Task Counts_a_span_of_days_in_whole_utc_days()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-13T00:00:00.000Z", "The first instant"),
            SessionEvent.Titled(Afternoon, "2026-09-13T23:59:59.000Z", "The last instant"));

        // A local day would put a late run on another day and drop it from the answer.
        Assert.Equal(2, (await studio.SessionsIn("?from=2026-09-13&to=2026-09-13")).Count);
    }

    [Fact]
    public async Task Says_which_days_a_narrowed_table_covers_and_that_they_are_not_the_lookback()
    {
        using var studio = new StudioHost();

        var span = (await studio.SessionAnswer("?from=2026-09-13&to=2026-09-14")).Head.Span;

        Assert.False(span.Lookback);
        Assert.Equal(Day("2026-09-13"), span.From);
        Assert.Equal(Day("2026-09-14"), span.To);
    }

    [Fact]
    public async Task Narrows_the_table_to_one_repository()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The chosen run", "acme/xi"),
            Ran(Afternoon, "2026-09-14T14:00:00.000Z", "The other run", "acme/nu"));

        Assert.Equal(["The chosen run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Answers_with_no_runs_for_a_repository_that_is_a_near_miss()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, "2026-09-14T09:00:00.000Z", "The chosen run", "acme/xi"));

        Assert.Empty(await studio.SessionsIn("?repository=acme/x"));
    }

    [Fact]
    public async Task Leaves_a_run_that_names_no_repository_out_when_one_is_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The placed run", "acme/xi"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The run from nowhere"));

        Assert.Equal(["The placed run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_repository_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        SessionEvent Placed(SessionEvent recorded) => recorded with { Owner = "acme", RepositoryName = "xi" };

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The placed run", "acme/xi"),
            Placed(SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z")),
            Placed(SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z")));

        var session = Assert.Single(await studio.SessionsIn("?repository=acme/xi"));

        // Every read is narrowed in the store, so a run whose events all name the Repository is counted in full.
        Assert.Equal(2, session.ToolCalls);
        Assert.Equal(1, session.Faults);
    }

    [Fact]
    public async Task Narrows_the_table_to_the_sessions_in_which_a_skill_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run that swept"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The run that did not"));
        await studio.Push(
            new SkillActivated("comment-sweep", "2026-09-14T09:05:00.000Z") { Session = Morning },
            new SkillActivated("tdd", "2026-09-14T14:05:00.000Z") { Session = Afternoon });

        Assert.Equal(
            ["The run that swept"],
            (await studio.SessionsIn("?skill=comment-sweep")).Select(session => session.Name));
    }

    [Fact]
    public async Task Leaves_a_session_the_skill_never_fired_in_out_even_when_it_ran_the_same_day()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The quiet run"));

        Assert.Empty(await studio.SessionsIn("?skill=comment-sweep"));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_skill_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run that swept"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z"));
        await studio.Push(new SkillActivated("comment-sweep", "2026-09-14T09:05:00.000Z") { Session = Morning });

        var session = Assert.Single(await studio.SessionsIn("?skill=comment-sweep"));

        Assert.Equal(2, session.ToolCalls);
        Assert.Equal(1, session.Faults);
    }

    [Fact]
    public async Task Narrows_the_table_by_the_span_the_repository_and_the_skill_together()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The run that matches", "acme/xi"),
            Ran(Afternoon, "2026-09-12T09:00:00.000Z", "The run outside the span", "acme/xi"),
            Ran(Evening, "2026-09-14T14:00:00.000Z", "The run in another repository", "acme/nu"));
        await studio.Push(
            new SkillActivated("tdd", "2026-09-14T09:05:00.000Z") { Session = Morning },
            new SkillActivated("tdd", "2026-09-12T09:05:00.000Z") { Session = Afternoon },
            new SkillActivated("tdd", "2026-09-14T14:05:00.000Z") { Session = Evening });

        var names = (await studio.SessionsIn("?from=2026-09-14&to=2026-09-14&repository=acme/xi&skill=tdd"))
            .Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Answers_with_an_empty_table_when_a_combination_matches_nothing()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, "2026-09-14T09:00:00.000Z", "The only run", "acme/xi"));
        await studio.Push(new SkillActivated("tdd", "2026-09-14T09:05:00.000Z") { Session = Morning });

        var answer = await studio.SessionAnswer("?repository=acme/nu&skill=tdd");

        // A combination that matches nothing must not read as a store that fell short.
        Assert.Empty(answer.Sessions);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    private static SessionEvent Ran(string session, string at, string title, string repository)
    {
        var placed = repository.Split('/');

        return SessionEvent.Titled(session, at, title) with { Owner = placed[0], RepositoryName = placed[1] };
    }
}
