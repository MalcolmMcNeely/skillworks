using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string Morning = "8f1c0a9e-0000-4000-8000-000000000001";

    private const string Afternoon = "8f1c0a9e-0000-4000-8000-000000000002";

    [Fact]
    public async Task Answers_with_a_head_then_the_sessions_then_an_end()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var lines = await studio.SessionLines();

        Assert.Equal(["head", "sessions", "end"], lines.Select(StudioHost.KindOf));
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

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        var head = await studio.SessionLine("head");
        var page = await studio.SessionLine("sessions");

        Assert.Equal(["descending", "kind", "sort", "span"], StudioHost.Fields(head));
        Assert.Equal(["from", "fromUtc", "lookback", "to", "untilUtc"], StudioHost.Fields(head["span"]));

        Assert.Equal(["kind", "sessions"], StudioHost.Fields(page));
        Assert.Equal(
            ["cost", "faults", "friction", "id", "lengthMs", "name", "person", "repository", "running", "startedUtc", "toolCalls"],
            StudioHost.Fields(page["sessions"]?[0]));
    }

    [Fact]
    public async Task Covers_the_lookback_when_no_span_is_asked_for_and_says_so()
    {
        using var studio = new StudioHost();

        var span = (await studio.SessionAnswer()).Head.Span;

        // The page says which days it covers, so a reader never takes a quiet week for the whole record.
        Assert.True(span.Lookback);
        Assert.Equal(Day("2026-09-09"), span.From);
        Assert.Equal(Day("2026-09-15"), span.To);
    }

    [Fact]
    public async Task Lists_every_session_of_the_lookback_without_a_repository_being_chosen()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", "2026-09-14T09:00:00.000Z") { Owner = "acme", RepositoryName = "xi" },
            new SessionEvent(Afternoon, "user_prompt", "2026-09-14T14:00:00.000Z") { Owner = "acme", RepositoryName = "nu" });

        // Nothing is asked for, so a reader sees the whole organisation the moment the page opens.
        Assert.Equal(["acme/nu", "acme/xi"], (await studio.SessionsIn()).Select(session => session.Repository).Order());
    }

    [Fact]
    public async Task Lists_the_sessions_newest_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-12T09:00:00.000Z", "The early run"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The later run"));

        // Newest first, so the run a developer just finished is the first row on the page.
        Assert.Equal(["The later run", "The early run"], (await studio.SessionsIn()).Select(session => session.Name));
    }

    [Fact]
    public async Task Shows_when_a_session_started_who_ran_it_and_where()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", "2026-09-14T09:00:00.000Z")
            {
                Owner = "malcolmania",
                RepositoryName = "skillworks",
                Person = "grace@acme.test",
            });

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment("2026-09-14T09:00:00.000Z"), session.StartedUtc);
        Assert.Equal("malcolmania/skillworks", session.Repository);
        Assert.Equal("grace@acme.test", session.Person);
    }

    [Fact]
    public async Task Measures_a_session_from_its_first_event_to_its_last()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"),
            new SessionEvent(Morning, "tool_result", "2026-09-14T09:20:30.000Z"),
            new SessionEvent(Morning, "assistant_response", "2026-09-14T09:41:00.000Z"));

        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment("2026-09-14T09:00:00.000Z"), session.StartedUtc);
        Assert.Equal((long)TimeSpan.FromMinutes(41).TotalMilliseconds, session.LengthMs);
    }

    [Fact]
    public async Task Keeps_a_session_that_ran_past_midnight_as_one_row()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, "2026-09-13T23:30:00.000Z", "Fix the build"),
            new SessionEvent(Morning, "assistant_response", "2026-09-14T00:30:00.000Z"));

        // A run cut at midnight would read as two halves that mean nothing on their own.
        var session = Assert.Single(await studio.SessionsIn());

        Assert.Equal(Moment("2026-09-13T23:30:00.000Z"), session.StartedUtc);
        Assert.Equal((long)TimeSpan.FromHours(1).TotalMilliseconds, session.LengthMs);
    }

    [Fact]
    public async Task Leaves_out_a_session_that_ran_outside_the_span()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-12T09:00:00.000Z", "The early run"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The later run"));

        Assert.Equal(["The later run"], (await studio.SessionsIn("?from=2026-09-14&to=2026-09-14")).Select(s => s.Name));
    }

    [Fact]
    public async Task Names_a_session_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run"));

        // An older Claude Code, or a repository with no origin remote, still ran the Session.
        Assert.Null(Assert.Single(await studio.SessionsIn()).Repository);
    }

    [Fact]
    public async Task Reports_no_sessions_when_the_store_holds_nothing()
    {
        using var studio = new StudioHost();

        Assert.Empty(await studio.SessionsIn());
    }

    private static DateOnly Day(string day) => DateOnly.Parse(day, CultureInfo.InvariantCulture);

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}
