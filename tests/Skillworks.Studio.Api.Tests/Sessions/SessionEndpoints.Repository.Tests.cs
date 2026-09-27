using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string Chosen = "?repository=acme/xi";

    [Fact]
    public async Task Brings_fifty_rows_of_a_repository_where_newer_work_ran_elsewhere()
    {
        using var studio = new StudioHost();

        await studio.Push(AskedIn(RowsPerRead + 5, "acme/xi", "acme/nu"));

        var answer = await studio.SessionAnswer(Chosen);

        Assert.Equal(Enumerable.Range(0, RowsPerRead).Select(InChosen), answer.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Reads_the_next_fifty_rows_of_a_repository_and_never_repeats_one()
    {
        using var studio = new StudioHost();

        await studio.Push(AskedIn((RowsPerRead * 2) + 5, "acme/xi", "acme/nu"));

        var first = await studio.SessionAnswer(Chosen);
        var second = await studio.LaterSessionAnswer(first, Chosen);
        var third = await studio.LaterSessionAnswer(second, Chosen);

        Assert.Equal(Enumerable.Range(RowsPerRead, RowsPerRead).Select(InChosen), second.Sessions.Select(session => session.Id));
        Assert.Equal(Enumerable.Range(RowsPerRead * 2, 5).Select(InChosen), third.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Loads_later_the_work_whose_prompts_since_the_place_ran_in_another_repository()
    {
        using var studio = new StudioHost();

        var wandered = Numbered(900);

        await studio.Push(AskedIn(RowsPerRead, "acme/xi", "acme/nu"));
        await studio.Push(
            InRepository(SessionEvent.Prompted(wandered, At(DaysBack(3), "09:00:00.000"), "Start here"), "acme/xi"),
            InRepository(SessionEvent.Prompted(wandered, At(Yesterday, "23:30:00.000"), "Now over there"), "acme/nu"));

        var first = await studio.SessionAnswer(Chosen);
        var second = await studio.LaterSessionAnswer(first, Chosen);

        // Under the Repository its newest Prompt is the old one, so the first read never drew it.
        Assert.DoesNotContain(wandered, first.Sessions.Select(session => session.Id));
        Assert.Equal([wandered], second.Sessions.Select(session => session.Id));
    }

    [Fact]
    public async Task Places_a_parents_row_by_the_newest_prompt_a_child_asked_in_the_repository()
    {
        using var studio = new StudioHost();

        await studio.Push(
            InRepository(SessionEvent.Prompted(Morning, At(Yesterday, "08:00:00.000"), "Run the spec"), "acme/nu"),
            InRepository(SessionEvent.Prompted(Evening, At(Yesterday, "10:00:00.000"), "Read the logs"), "acme/xi"),
            InRepository(SessionEvent.Prompted(Morning, At(Yesterday, "20:00:00.000"), "Carry on"), "acme/nu"),
            InRepository(SessionEvent.Prompted(Afternoon, At(Yesterday, "09:00:00.000"), "Build the ticket"), "acme/xi")
                with { Parent = Morning });

        var answer = await studio.SessionAnswer(Chosen);

        // The Parent's own later Prompt ran elsewhere, so its Child's Prompt in the Repository places the row.
        Assert.Equal([Evening, Morning], answer.Sessions.Select(session => session.Id));
    }

    private static SessionEvent[] AskedIn(int many, string chosen, string other) =>
    [
        .. Enumerable.Range(0, many).SelectMany(step =>
        {
            var at = Moment(At(Yesterday, "22:00:00.000")) - TimeSpan.FromMinutes(2 * step);

            return new[]
            {
                InRepository(SessionEvent.Prompted(Numbered(1000 + step), Stamped(at), "Elsewhere"), other),
                InRepository(SessionEvent.Prompted(InChosen(step), Stamped(at - TimeSpan.FromMinutes(1)), "Work"), chosen),
            };
        }),
    ];

    private static string InChosen(int step) => Numbered(step);

    private static SessionEvent InRepository(SessionEvent recorded, string repository)
    {
        var cut = repository.IndexOf('/');

        return recorded with { Owner = repository[..cut], RepositoryName = repository[(cut + 1)..] };
    }
}
