using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string Swept = "?skill=comment-sweep";

    [Fact]
    public async Task Lists_the_work_where_the_skill_activated_most_recently_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "20:00:00.000"), "Carry on"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "10:00:00.000"), "Tidy up"),
            SessionEvent.Prompted(Evening, At(Yesterday, "08:00:00.000"), "Read the logs"));
        await studio.Push(
            new SkillActivated("comment-sweep", At(Yesterday, "09:00:00.000")) { Session = Morning },
            new SkillActivated("comment-sweep", At(Yesterday, "11:00:00.000")) { Session = Afternoon },
            new SkillActivated("tdd", At(Yesterday, "21:00:00.000")) { Session = Afternoon });

        var sessions = await studio.SessionsIn(Swept);

        // The newest Prompt and the newest Activation of another Skill place no row under the filter.
        Assert.Equal([Afternoon, Morning], sessions.Select(session => session.Id));
        Assert.Equal(Moment(At(Yesterday, "11:00:00.000")), sessions[0].LatestUtc);
    }

    [Fact]
    public async Task Brings_fifty_rows_of_a_skill_where_newer_work_never_activated_it()
    {
        using var studio = new StudioHost();

        await PushSweptAmong(studio, RowsPerRead + 5);

        var answer = await studio.SessionAnswer(Swept);

        Assert.Equal(Enumerable.Range(0, RowsPerRead).Select(Numbered), answer.Sessions.Select(session => session.Id));
        Assert.Equal(answer.Sessions[^1].LatestUtc, answer.OldestLatestUtc);
    }

    [Fact]
    public async Task Reads_the_next_fifty_rows_of_a_skill_and_never_repeats_one()
    {
        using var studio = new StudioHost();

        await PushSweptAmong(studio, (RowsPerRead * 2) + 5);

        // Each of the newest fifty activated the Skill once more, long before the rest, so a later read hears it again.
        await studio.Push(
        [
            .. Enumerable.Range(0, RowsPerRead).Select(step =>
                new SkillActivated("comment-sweep", At(DaysBack(9), "09:00:00.000")) { Session = Numbered(step) }),
        ]);

        var first = await studio.SessionAnswer(Swept);
        var second = await studio.LaterSessionAnswer(first, Swept);
        var third = await studio.LaterSessionAnswer(second, Swept);

        Assert.Equal(Enumerable.Range(0, RowsPerRead).Select(Numbered), first.Sessions.Select(session => session.Id));
        Assert.Equal(Enumerable.Range(RowsPerRead, RowsPerRead).Select(Numbered), second.Sessions.Select(session => session.Id));
        Assert.Equal(Enumerable.Range(RowsPerRead * 2, 5).Select(Numbered), third.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Places_a_parents_row_where_a_child_activated_the_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(3), "09:00:00.000"), "Run the spec"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "09:00:00.000"), "Build the ticket") with { Parent = Morning },
            SessionEvent.Prompted(Evening, At(Yesterday, "10:00:00.000"), "Read the logs"));
        await studio.Push(
            new SkillActivated("comment-sweep", At(DaysBack(3), "09:05:00.000")) { Session = Morning },
            new SkillActivated("comment-sweep", At(Yesterday, "12:00:00.000")) { Session = Afternoon, Parent = Morning },
            new SkillActivated("comment-sweep", At(Yesterday, "11:00:00.000")) { Session = Evening });

        var sessions = await studio.SessionsIn(Swept);

        Assert.Equal([Morning, Evening], sessions.Select(session => session.Id));
        Assert.Equal(Moment(At(Yesterday, "12:00:00.000")), sessions[0].LatestUtc);
    }

    // A run that never activated the Skill sits between each pair, newer than the run that did.
    private static async Task PushSweptAmong(StudioHost studio, int many)
    {
        DateTimeOffset Asked(int step) => Moment(At(Yesterday, "22:00:00.000")) - TimeSpan.FromMinutes(2 * step);

        var steps = Enumerable.Range(0, many).ToList();

        await studio.Push(
        [
            .. steps.SelectMany(step => new[]
            {
                SessionEvent.Prompted(Numbered(1000 + step), Stamped(Asked(step)), "Elsewhere"),
                SessionEvent.Prompted(Numbered(step), Stamped(Asked(step) - TimeSpan.FromMinutes(1)), "Work"),
            }),
        ]);
        await studio.Push(
        [
            .. steps.Select(step =>
                new SkillActivated("comment-sweep", Stamped(Asked(step) - TimeSpan.FromMinutes(1))) { Session = Numbered(step) }),
        ]);
    }
}
