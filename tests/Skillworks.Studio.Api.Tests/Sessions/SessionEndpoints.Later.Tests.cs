using System.Globalization;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Reads_the_next_fifty_older_rows_and_never_repeats_one()
    {
        using var studio = new StudioHost();

        await studio.Push(Asked((RowsPerRead * 2) + 5));

        var first = await studio.SessionAnswer();
        var second = await studio.LaterSessionAnswer(first);
        var third = await studio.LaterSessionAnswer(second);

        Assert.Equal(Enumerable.Range(RowsPerRead, RowsPerRead).Select(Numbered), second.Sessions.Select(session => session.Id));
        Assert.Equal(Enumerable.Range(RowsPerRead * 2, 5).Select(Numbered), third.Sessions.Select(session => session.Id));
        Assert.Equal(first.Head.AsOfUtc, second.Head.AsOfUtc);
    }

    [Fact]
    public async Task Draws_each_of_two_pieces_of_work_that_share_the_latest_a_read_ends_on_once()
    {
        using var studio = new StudioHost();

        var last = Numbered(RowsPerRead - 1);
        var tied = Numbered(900);
        var asked = Asked(RowsPerRead + 5);

        // Loki keeps one of two lines sharing a stream, an instant and a body, so the two differ inside the millisecond the list reads.
        var sameMillisecond = Moment(asked[RowsPerRead - 1].At) + TimeSpan.FromTicks(5_000);

        await studio.Push(asked);
        await studio.Push(SessionEvent.Prompted(tied, sameMillisecond.ToString("O", CultureInfo.InvariantCulture), "Same instant"));

        var first = await studio.SessionAnswer();
        var second = await studio.LaterSessionAnswer(first);

        string[] drawn = [.. first.Sessions.Concat(second.Sessions).Select(session => session.Id)];

        Assert.Contains(last, first.Sessions.Select(session => session.Id));
        Assert.Contains(tied, first.Sessions.Select(session => session.Id));
        Assert.Equal(drawn.Distinct().Count(), drawn.Length);
        Assert.Equal([.. asked.Select(said => said.Session).Append(tied).Order()], drawn.Order());
    }

    [Fact]
    public async Task Measures_the_rows_a_later_read_loaded()
    {
        using var studio = new StudioHost();

        var older = Numbered(RowsPerRead);

        await studio.Push(Asked(RowsPerRead + 1));
        await studio.Push(SessionEvent.ToolRan(older, At(Yesterday, "23:00:00.000")));

        var second = await studio.LaterSessionAnswer(await studio.SessionAnswer());

        Assert.Equal([older], second.Sessions.Select(session => session.Id));
        Assert.Equal(1m, second.Measured("toolCalls", older));
    }

    [Fact]
    public async Task Leaves_out_of_a_later_read_the_work_with_a_prompt_after_its_latest()
    {
        using var studio = new StudioHost();

        var plain = Numbered(900);
        var parent = Numbered(901);
        var child = Numbered(902);

        await studio.Push(Asked(RowsPerRead + 5));
        await studio.Push(
            SessionEvent.Prompted(plain, At(DaysBack(3), "09:00:00.000"), "Start the spec"),
            SessionEvent.Prompted(plain, At(Yesterday, "23:30:00.000"), "Now push it"),
            SessionEvent.Prompted(parent, At(DaysBack(3), "10:00:00.000"), "Run the spec"),
            SessionEvent.Prompted(child, At(Yesterday, "23:00:00.000"), "Build the ticket") with { Parent = parent });

        var first = await studio.SessionAnswer();
        var second = await studio.LaterSessionAnswer(first);

        // Their older Prompts sit past the Latest, but each piece of work was already drawn at its newest.
        Assert.Equal([plain, parent], first.Sessions.Take(2).Select(session => session.Id));
        Assert.Equal(Enumerable.Range(RowsPerRead - 2, 7).Select(Numbered), second.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Reads_nothing_after_the_as_of_instant_it_is_handed()
    {
        using var studio = new StudioHost();

        var older = Numbered(RowsPerRead + 2);

        await studio.Push(Asked(RowsPerRead + 5));

        var first = await studio.SessionAnswer();

        studio.Clock.Advance(TimeSpan.FromMinutes(5));

        await studio.Push(
            SessionEvent.Prompted(older, Stamped(first.Head.AsOfUtc + TimeSpan.FromMinutes(1)), "Back to it"),
            SessionEvent.Prompted(Numbered(900), Stamped(first.Head.AsOfUtc + TimeSpan.FromMinutes(2)), "Something new"));

        var second = await studio.LaterSessionAnswer(first);

        // Read as the list stood at the as-of instant, so a row neither jumps up nor drops out as the reader scrolls.
        Assert.Equal(first.Head.AsOfUtc, second.Head.AsOfUtc);
        Assert.Equal(Enumerable.Range(RowsPerRead, 5).Select(Numbered), second.Sessions.Select(session => session.Id));
    }
}
