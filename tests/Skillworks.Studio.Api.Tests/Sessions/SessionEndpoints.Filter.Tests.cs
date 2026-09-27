using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Opens_as_usual_on_an_address_that_still_carries_a_span_a_sort_or_a_depth()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(DaysBack(3), "09:00:00.000"), "The early run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"));

        // An old link names days, a column and a Depth the list no longer takes, and must still open the list.
        var names = (await studio.SessionsIn(
                $"?from={Written(Yesterday)}&to={Written(Yesterday)}&sort=name&descending=false&depth=full"))
            .Select(session => session.Name);

        Assert.Equal(["The later run", "The early run"], names);
    }

    [Fact]
    public async Task Narrows_the_table_to_one_repository()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"),
            Ran(Afternoon, At(Yesterday, "14:00:00.000"), "The other run", "acme/nu"));

        Assert.Equal(["The chosen run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Answers_with_no_runs_for_a_repository_that_is_a_near_miss()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"));

        Assert.Empty(await studio.SessionsIn("?repository=acme/x"));
    }

    [Fact]
    public async Task Leaves_a_run_that_names_no_repository_out_when_one_is_asked_for()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The placed run", "acme/xi"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run from nowhere"));

        Assert.Equal(["The placed run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_repository_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        SessionEvent Placed(SessionEvent recorded) => recorded with { Owner = "acme", RepositoryName = "xi" };

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The placed run", "acme/xi"),
            Placed(SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000"))),
            Placed(SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000"))));

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // Every read is narrowed in the store, so a run whose events all name the Repository is counted in full.
        Assert.Equal(Morning, Assert.Single(answer.Sessions).Id);
        Assert.Equal(2m, answer.Measured("toolCalls", Morning));
        Assert.Equal(1m, answer.Measured("faults", Morning));
    }

    [Fact]
    public async Task Narrows_the_table_to_the_sessions_in_which_a_skill_fired()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run that did not"));
        await studio.Push(
            new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning },
            new SkillActivated("tdd", At(Yesterday, "14:05:00.000")) { Session = Afternoon });

        Assert.Equal(
            ["The run that swept"],
            (await studio.SessionsIn("?skill=comment-sweep")).Select(session => session.Name));
    }

    [Fact]
    public async Task Leaves_a_session_the_skill_never_fired_in_out_even_when_it_ran_the_same_day()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The quiet run"));

        Assert.Empty(await studio.SessionsIn("?skill=comment-sweep"));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_skill_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000")));
        await studio.Push(new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning });

        var answer = await studio.SessionAnswer("?skill=comment-sweep");

        Assert.Equal(Morning, Assert.Single(answer.Sessions).Id);
        Assert.Equal(2m, answer.Measured("toolCalls", Morning));
        Assert.Equal(1m, answer.Measured("faults", Morning));
    }

    [Fact]
    public async Task Narrows_the_table_by_the_repository_and_the_skill_together()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(
            studio,
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The run that matches", "acme/xi"),
            Ran(Afternoon, At(DaysBack(3), "09:00:00.000"), "The run that never swept", "acme/xi"),
            Ran(Evening, At(Yesterday, "14:00:00.000"), "The run in another repository", "acme/nu"));
        await studio.Push(
            new SkillActivated("tdd", At(Yesterday, "09:05:00.000"), Owner: "acme", RepositoryName: "xi") { Session = Morning },
            new SkillActivated("comment-sweep", At(DaysBack(3), "09:05:00.000"), Owner: "acme", RepositoryName: "xi")
            {
                Session = Afternoon,
            },
            new SkillActivated("tdd", At(Yesterday, "14:05:00.000"), Owner: "acme", RepositoryName: "nu") { Session = Evening });

        var names = (await studio.SessionsIn("?repository=acme/xi&skill=tdd")).Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Answers_with_an_empty_table_when_a_combination_matches_nothing()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, Ran(Morning, At(Yesterday, "09:00:00.000"), "The only run", "acme/xi"));
        await studio.Push(
            new SkillActivated("tdd", At(Yesterday, "09:05:00.000"), Owner: "acme", RepositoryName: "xi") { Session = Morning });

        var answer = await studio.SessionAnswer("?repository=acme/nu&skill=tdd");

        // A combination that matches nothing must not read as a store that fell short.
        Assert.Empty(answer.Sessions);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    private static SessionEvent Ran(string session, string at, string title, string repository)
    {
        var cut = repository.IndexOf('/');

        return SessionEvent.Titled(session, at, title) with { Owner = repository[..cut], RepositoryName = repository[(cut + 1)..] };
    }
}
