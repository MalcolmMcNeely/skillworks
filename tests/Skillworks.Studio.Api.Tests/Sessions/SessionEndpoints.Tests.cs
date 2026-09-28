using System.Globalization;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string Morning = "8f1c0a9e-0000-4000-8000-000000000001";

    private const string Afternoon = "8f1c0a9e-0000-4000-8000-000000000002";

    private const string Evening = "8f1c0a9e-0000-4000-8000-000000000003";

    [Fact]
    public async Task Answers_with_a_head_then_the_sessions_then_the_measures_and_the_depths_then_an_end()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var kinds = (await studio.SessionLines()).Select(StudioHost.KindOf).ToList();

        // Each line behind the rows lands when its read does, so only their number is fixed.
        Assert.Equal(["head", "sessions"], kinds.Take(2));
        Assert.Equal(
            ["depths", "measure", "measure", "measure", "measure"],
            kinds.Skip(2).SkipLast(1).Order(StringComparer.Ordinal));
        Assert.Equal("end", kinds[^1]);
    }

    [Fact]
    public async Task Answers_one_JSON_object_per_line()
    {
        using var studio = new StudioHost();

        using var response = await studio.AskForSessions("");

        Assert.Equal("application/x-ndjson", response.Content.Headers.ContentType?.MediaType);
    }

    [Fact]
    public async Task Answers_with_lines_that_hold_only_what_a_screen_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var head = await studio.SessionLine("head");
        var page = await studio.SessionLine("sessions");
        var measure = await studio.SessionLine("measure");
        var depths = await studio.SessionLine("depths");

        var end = await studio.SessionLine("end");

        Assert.Equal(["asOfUtc", "kind"], StudioHost.Fields(head));

        Assert.Equal(["kind", "sessions"], StudioHost.Fields(page));
        Assert.Equal(
            ["firstDay", "id", "lastDay", "latestUtc", "lengthMs", "name", "person", "repository", "running", "startedUtc"],
            StudioHost.Fields(page["sessions"]?[0]));

        Assert.Equal(["kind", "measure", "values"], StudioHost.Fields(measure));
        Assert.Equal(["depths", "kind"], StudioHost.Fields(depths));

        Assert.Equal(["gap", "kind", "oldestLatestUtc", "quietSinceUtc"], StudioHost.Fields(end));
    }

    [Fact]
    public async Task Says_in_its_head_the_instant_it_read_up_to()
    {
        using var studio = new StudioHost();

        // A later read passes it back, so the rows already drawn never move under a reader.
        Assert.Equal(studio.Clock.GetUtcNow(), (await studio.SessionAnswer()).Head.AsOfUtc);
    }

    [Fact]
    public async Task Lists_every_session_of_the_lookback_without_a_repository_being_chosen()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", At(Yesterday, "09:00:00.000")) { Owner = "acme", RepositoryName = "xi" },
            new SessionEvent(Afternoon, "user_prompt", At(Yesterday, "14:00:00.000")) { Owner = "acme", RepositoryName = "nu" });

        // Nothing is asked for, so a reader sees the whole organisation the moment the page opens.
        Assert.Equal(["acme/nu", "acme/xi"], (await studio.SessionsIn()).Select(session => session.Repository).Order());
    }

    [Fact]
    public async Task Shows_when_a_session_started_who_ran_it_and_where()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", At(Yesterday, "09:00:00.000"))
            {
                Owner = "malcolmania",
                RepositoryName = "skillworks",
                Person = "grace@acme.test",
            });

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), session.StartedUtc);
        Assert.Equal("malcolmania/skillworks", session.Repository);
        Assert.Equal("grace@acme.test", session.Person);
    }

    [Fact]
    public async Task Measures_a_session_from_its_first_event_to_its_last()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            new SessionEvent(Morning, "tool_result", At(Yesterday, "09:20:30.000")),
            new SessionEvent(Morning, "assistant_response", At(Yesterday, "09:41:00.000")));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), session.StartedUtc);
        Assert.Equal((long)TimeSpan.FromMinutes(41).TotalMilliseconds, session.LengthMs);
    }

    [Fact]
    public async Task Keeps_a_session_that_ran_past_midnight_as_one_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(2), "23:30:00.000"), "Fix the build"),
            new SessionEvent(Morning, "assistant_response", At(Yesterday, "00:30:00.000")));

        // A run cut at midnight would read as two halves that mean nothing on their own.
        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment(At(DaysBack(2), "23:30:00.000")), session.StartedUtc);
        Assert.Equal((long)TimeSpan.FromHours(1).TotalMilliseconds, session.LengthMs);
    }

    [Fact]
    public async Task Names_a_session_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        // An older Claude Code, or a repository with no origin remote, still ran the Session.
        Assert.Null(Assert.Single(await studio.SessionsIn()).Repository);
    }

    [Fact]
    public async Task Reports_no_sessions_when_the_store_holds_nothing()
    {
        using var studio = new StudioHost();

        Assert.Empty(await studio.SessionsIn());
    }

    [Fact]
    public async Task Empties_the_table_when_the_events_store_never_answered()
    {
        using var events = StandInEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.SessionAnswer();

        // Every row is the events store's answer, so a store that never answered leaves none standing.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("events store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);

    // A Prompt marks a run's activity, so each run named by a title is also asked something in the same instant.
    private static Task PushWithPrompts(StudioHost studio, params SessionEvent[] events) =>
        studio.Push([.. events.SelectMany(WithPrompt)]);

    private static SessionEvent[] WithPrompt(SessionEvent recorded) =>
        recorded.QuerySource == SessionEvent.TitleSource
            ?
            [
                recorded,
                SessionEvent.Prompted(recorded.Session, recorded.At, recorded.Response ?? "") with
                {
                    Person = recorded.Person,
                    Owner = recorded.Owner,
                    RepositoryName = recorded.RepositoryName,
                    Parent = recorded.Parent,
                },
            ]
            : [recorded];
}
