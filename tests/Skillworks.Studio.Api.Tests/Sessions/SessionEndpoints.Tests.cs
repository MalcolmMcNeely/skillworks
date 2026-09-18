using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string Morning = "8f1c0a9e-0000-4000-8000-000000000001";

    private const string Afternoon = "8f1c0a9e-0000-4000-8000-000000000002";

    private const string Evening = "8f1c0a9e-0000-4000-8000-000000000003";

    [Fact]
    public async Task Answers_with_a_head_then_the_sessions_then_the_measures_then_an_end()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var lines = await studio.SessionLines();

        Assert.Equal(
            ["head", "sessions", "measure", "measure", "measure", "measure", "end"],
            lines.Select(StudioHost.KindOf));
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

        Assert.Equal(["descending", "kind", "sort", "span"], StudioHost.Fields(head));
        Assert.Equal(["from", "fromUtc", "lookback", "to", "untilUtc"], StudioHost.Fields(head["span"]));

        Assert.Equal(["kind", "sessions"], StudioHost.Fields(page));
        Assert.Equal(
            ["id", "lengthMs", "name", "person", "repository", "running", "startedUtc"],
            StudioHost.Fields(page["sessions"]?[0]));

        Assert.Equal(["kind", "measure", "values"], StudioHost.Fields(measure));
    }

    [Fact]
    public async Task Covers_the_lookback_when_no_span_is_asked_for_and_says_so()
    {
        using var studio = new StudioHost();

        var span = (await studio.SessionAnswer()).Head.Span;

        // The page says which days it covers, so a reader never takes a quiet week for the whole record.
        Assert.True(span.Lookback);
        Assert.Equal(DaysBack(6), span.From);
        Assert.Equal(Today, span.To);
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
    public async Task Lists_the_sessions_newest_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(3), "09:00:00.000"), "The early run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"));

        // Newest first, so the run a developer just finished is the first row on the page.
        Assert.Equal(["The later run", "The early run"], (await studio.SessionsIn()).Select(session => session.Name));
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
    public async Task Leaves_out_a_session_that_ran_outside_the_span()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(3), "09:00:00.000"), "The early run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"));

        Assert.Equal(["The later run"], (await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}")).Select(s => s.Name));
    }

    [Fact]
    public async Task Names_a_session_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

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
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.SessionAnswer();

        // Every row is the events store's answer, so a store that never answered leaves none standing.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("events store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}
