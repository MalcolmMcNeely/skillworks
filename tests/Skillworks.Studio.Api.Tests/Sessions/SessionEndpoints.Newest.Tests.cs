using System.Globalization;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const int RowsPerRead = 50;

    [Fact]
    public async Task Lists_the_work_with_the_newest_prompt_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(3), "09:00:00.000"), "Start the spec"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "14:00:00.000"), "Fix the build"),
            SessionEvent.Prompted(Evening, At(DaysBack(2), "09:00:00.000"), "Read the logs"),
            SessionEvent.Prompted(Morning, At(Yesterday, "15:00:00.000"), "Now push it"));

        var sessions = await studio.SessionsIn();

        // The run a developer spoke to last is on top, however long ago it began.
        Assert.Equal([Morning, Afternoon, Evening], sessions.Select(session => session.Id));
        Assert.Equal(Moment(At(Yesterday, "15:00:00.000")), sessions[0].LatestUtc);
    }

    [Fact]
    public async Task Places_a_parent_where_its_childs_newest_prompt_is()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(3), "09:00:00.000"), "Run the spec"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "12:00:00.000"), "Read the logs"),
            SessionEvent.Prompted(Evening, At(Yesterday, "14:00:00.000"), "Build the ticket") with { Parent = Morning });

        var sessions = await studio.SessionsIn();

        // The loop driver asks its Children, so the Parent's own Prompts alone would sink work that is still going.
        Assert.Equal([Morning, Afternoon], sessions.Select(session => session.Id));
        Assert.Equal(Moment(At(Yesterday, "14:00:00.000")), sessions[0].LatestUtc);
    }

    [Fact]
    public async Task Shows_each_piece_of_work_once_however_many_prompts_it_holds()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Run the spec"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "10:00:00.000"), "Build one") with { Parent = Morning },
            SessionEvent.Prompted(Evening, At(Yesterday, "11:00:00.000"), "A chat"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "12:00:00.000"), "Build two") with { Parent = Morning },
            SessionEvent.Prompted(Evening, At(Yesterday, "13:00:00.000"), "More chat"),
            SessionEvent.Prompted(Morning, At(Yesterday, "14:00:00.000"), "Carry on"));

        Assert.Equal([Morning, Evening], (await studio.SessionsIn()).Select(session => session.Id));
    }

    [Fact]
    public async Task Answers_fifty_rows_where_more_exist_and_names_the_latest_of_the_oldest()
    {
        using var studio = new StudioHost();

        await studio.Push(Asked(RowsPerRead + 5));

        var answer = await studio.SessionAnswer();

        // The newest fifty, so the next read starts where this one stopped.
        Assert.Equal(Enumerable.Range(0, RowsPerRead).Select(Numbered), answer.Sessions.Select(session => session.Id));
        Assert.Equal(answer.Sessions[^1].LatestUtc, answer.OldestLatestUtc);
    }

    [Fact]
    public async Task Measures_the_rows_it_loaded_and_no_others()
    {
        using var studio = new StudioHost();

        var oldest = Numbered(RowsPerRead);

        await studio.Push(Asked(RowsPerRead + 1));
        await studio.Push(
            SessionEvent.ToolRan(Numbered(0), At(Yesterday, "23:00:00.000")),
            SessionEvent.ToolRan(oldest, At(Yesterday, "23:00:00.000")));

        var answer = await studio.SessionAnswer();

        Assert.DoesNotContain(oldest, answer.Sessions.Select(session => session.Id));
        Assert.Equal(1m, answer.Measured("toolCalls", Numbered(0)));
        Assert.DoesNotContain(oldest, answer.Measures["toolCalls"].Keys);
    }

    [Fact]
    public async Task Reads_nothing_after_the_instant_it_reads_up_to()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, Stamped(Now - TimeSpan.FromHours(1)), "Fix the build"),
            new SessionEvent(Morning, "tool_result", Stamped(Now - TimeSpan.FromMinutes(30))),
            new SessionEvent(Morning, "tool_result", Stamped(Now + TimeSpan.FromMinutes(1))),
            SessionEvent.Prompted(Afternoon, Stamped(Now + TimeSpan.FromMinutes(2)), "Read the logs"));

        var before = await studio.SessionsIn();

        // Moved past the later events on purpose, so the same store answers with them in.
        studio.Clock.Advance(TimeSpan.FromMinutes(5));

        var after = await studio.SessionsIn();

        Assert.Equal([Morning], before.Select(session => session.Id));
        Assert.Equal((long)TimeSpan.FromMinutes(30).TotalMilliseconds, before[0].LengthMs);
        Assert.Equal([Afternoon, Morning], after.Select(session => session.Id));
    }

    [Fact]
    public async Task Lists_no_session_that_was_never_asked_anything()
    {
        using var studio = new StudioHost();

        await studio.Push(new SessionEvent(Morning, "tool_result", At(Yesterday, "09:00:00.000")));

        // A Prompt marks activity, as one busy run writes thousands of other events.
        Assert.Empty(await studio.SessionsIn());
    }

    [Fact]
    public async Task Answers_rows_and_no_gap_for_a_week_of_more_than_five_hundred_sessions()
    {
        using var studio = new StudioHost();

        // Loki refuses a read of more than 500 series, and a read of one total per Session met that limit.
        string[] parents = [Numbered(900), Numbered(901), Numbered(902)];
        var children = Enumerable.Range(0, 450).Select(child => (Id: Numbered(1_000 + child), Parent: parents[child % 3]));
        var busyWeek = Enumerable.Range(0, 60).Select(plain => (Id: Numbered(plain), Parent: (string?)null))
            .Concat(children.Select(child => (child.Id, Parent: (string?)child.Parent)))
            // By the last two digits, so plain Sessions and Children take turns down the week.
            .OrderBy(run => run.Id[^2..], StringComparer.Ordinal)
            .ThenBy(run => run.Id, StringComparer.Ordinal)
            .Select((run, step) => SessionEvent.Prompted(run.Id, Stamped(Now - TimeSpan.FromMinutes(19 * (step + 1))), "Work") with
            {
                Parent = run.Parent,
            })
            .Concat(parents.Select(parent => SessionEvent.Prompted(parent, At(DaysBack(6), "09:00:00.000"), "Run the spec")))
            .ToList();

        foreach (var batch in busyWeek.Chunk(100))
        {
            await studio.Push(batch);
        }

        var answer = await studio.SessionAnswer();

        Assert.Equal(RowsPerRead, answer.Sessions.Count);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    // Each a minute older than the one before, so the numbering is the order the list reads them in.
    private static SessionEvent[] Asked(int many) =>
    [
        .. Enumerable.Range(0, many).Select(step =>
            SessionEvent.Prompted(Numbered(step), Stamped(Moment(At(Yesterday, "22:00:00.000")) - TimeSpan.FromMinutes(step)), "Work")),
    ];

    private static string Numbered(int run) =>
        $"8f1c0a9e-0000-4000-8000-{run.ToString("D12", CultureInfo.InvariantCulture)}";
}
