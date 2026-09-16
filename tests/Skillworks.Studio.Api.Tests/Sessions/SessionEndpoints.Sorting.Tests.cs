using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private static readonly string[] EveryColumn =
        ["started", "repository", "person", "name", "length", "toolCalls", "cost", "faults"];

    [Fact]
    public async Task Sorts_every_column_from_the_lowest_up()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        Assert.Equal(
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["started"] = "Alpha run, Beta run, Gamma run",
                ["repository"] = "Gamma run, Beta run, Alpha run",
                ["person"] = "Alpha run, Beta run, Gamma run",
                ["name"] = "Alpha run, Beta run, Gamma run",
                ["length"] = "Alpha run, Gamma run, Beta run",
                ["toolCalls"] = "Alpha run, Gamma run, Beta run",
                ["cost"] = "Alpha run, Gamma run, Beta run",
                ["faults"] = "Alpha run, Gamma run, Beta run",
            },
            await OrderedBy(studio, descending: false));
    }

    [Fact]
    public async Task Sorts_every_column_from_the_highest_down()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        Assert.Equal(
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["started"] = "Gamma run, Beta run, Alpha run",
                ["repository"] = "Alpha run, Beta run, Gamma run",
                ["person"] = "Gamma run, Beta run, Alpha run",
                ["name"] = "Gamma run, Beta run, Alpha run",
                ["length"] = "Beta run, Gamma run, Alpha run",
                ["toolCalls"] = "Beta run, Gamma run, Alpha run",
                ["cost"] = "Beta run, Gamma run, Alpha run",
                ["faults"] = "Beta run, Gamma run, Alpha run",
            },
            await OrderedBy(studio, descending: true));
    }

    [Fact]
    public async Task Opens_a_column_the_way_a_reader_wants_it_first()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        // One click on Faults must put the worst run on top, and one on Person must start the words at A.
        Assert.Equal(["Beta run", "Gamma run", "Alpha run"], await Names(studio, "?sort=faults"));
        Assert.Equal(["Alpha run", "Beta run", "Gamma run"], await Names(studio, "?sort=person"));
    }

    [Fact]
    public async Task Sorts_the_newest_first_when_no_column_is_asked_for()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        // Asking for the column the table already opens on changes nothing.
        Assert.Equal(["Gamma run", "Beta run", "Alpha run"], await Names(studio, ""));
        Assert.Equal(["Gamma run", "Beta run", "Alpha run"], await Names(studio, "?sort=started"));
    }

    [Fact]
    public async Task Falls_back_to_the_newest_first_when_the_column_asked_for_is_not_one_of_them()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        // A table that draws nothing says less than one that draws the order it opens on.
        Assert.Equal(["Gamma run", "Beta run", "Alpha run"], await Names(studio, "?sort=weather"));
    }

    [Fact]
    public async Task Says_in_its_head_which_column_it_sorted_on_and_which_way()
    {
        using var studio = new StudioHost();

        var opening = (await studio.SessionAnswer()).Head;
        var asked = (await studio.SessionAnswer("?sort=cost")).Head;
        var turned = (await studio.SessionAnswer("?sort=cost&descending=false")).Head;

        // A reader sent a link must see the mark on the column the answer was actually sorted on.
        Assert.Equal(("started", true), (opening.Sort, opening.Descending));
        Assert.Equal(("cost", true), (asked.Sort, asked.Descending));
        Assert.Equal(("cost", false), (turned.Sort, turned.Descending));
    }

    [Fact]
    public async Task Sorts_words_without_letter_case_deciding_the_order()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "apple run"),
            SessionEvent.Titled(Afternoon, "2026-09-14T10:00:00.000Z", "Banana run"),
            SessionEvent.Titled(Evening, "2026-09-14T11:00:00.000Z", "Cherry run"));

        // A title Claude Code wrote in lower case belongs among the words, not banished past every capital.
        Assert.Equal(["apple run", "Banana run", "Cherry run"], await Names(studio, "?sort=name"));
    }

    [Fact]
    public async Task Falls_back_to_the_opening_direction_when_what_was_asked_for_is_not_a_direction()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        // A hand-typed address still opens a table, as an unknown column already does.
        Assert.Equal(["Gamma run", "Beta run", "Alpha run"], await Names(studio, "?sort=started&descending=banana"));
    }

    [Fact]
    public async Task Sorts_the_same_way_twice_when_two_runs_sit_level()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "One run"),
            SessionEvent.Titled(Afternoon, "2026-09-14T09:00:00.000Z", "Another run"));

        var first = await Names(studio, "?sort=faults");

        Assert.Equal(first, await Names(studio, "?sort=faults"));
    }

    private static async Task<IReadOnlyList<string>> Names(StudioHost studio, string order) =>
        [.. (await studio.SessionsIn(order)).Select(session => session.Name)];

    private static async Task<Dictionary<string, string>> OrderedBy(StudioHost studio, bool descending)
    {
        var orders = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var column in EveryColumn)
        {
            var order = $"?sort={column}&descending={(descending ? "true" : "false")}";

            orders[column] = string.Join(", ", await Names(studio, order));
        }

        return orders;
    }

    // Three runs that differ on every column, so one order can never stand in for another.
    private static async Task ThreeRuns(StudioHost studio)
    {
        await studio.Push(
        [
            .. Run(Morning, "2026-09-12T09:00:00.000Z", "Alpha run", "acme/xi", "ada@acme.test", minutes: 10, toolCalls: 1, faults: 0),
            .. Run(Afternoon, "2026-09-13T14:00:00.000Z", "Beta run", "acme/nu", "bea@acme.test", minutes: 30, toolCalls: 3, faults: 2),
            .. Run(Evening, "2026-09-14T19:00:00.000Z", "Gamma run", "acme/mu", "cal@acme.test", minutes: 20, toolCalls: 2, faults: 1),
        ]);

        await studio.Push(
            new ApiRequest("2026-09-12T09:01:00.000Z", CostUsd: 0.1m) { Session = Morning, Person = "ada@acme.test" },
            new ApiRequest("2026-09-13T14:01:00.000Z", CostUsd: 0.3m) { Session = Afternoon, Person = "bea@acme.test" },
            new ApiRequest("2026-09-14T19:01:00.000Z", CostUsd: 0.2m) { Session = Evening, Person = "cal@acme.test" });
    }

    private static SessionEvent[] Run(
        string id,
        string startedAt,
        string name,
        string repository,
        string person,
        int minutes,
        int toolCalls,
        int faults)
    {
        var started = DateTimeOffset.Parse(startedAt, CultureInfo.InvariantCulture);
        var placed = repository.Split('/');

        SessionEvent Placed(SessionEvent recorded) =>
            recorded with { Owner = placed[0], RepositoryName = placed[1], Person = person };

        string Minute(int minute) => At(started.AddMinutes(minute));

        return
        [
            Placed(SessionEvent.Titled(id, startedAt, name)),
            .. Enumerable.Range(0, toolCalls - faults).Select(step => Placed(SessionEvent.ToolRan(id, Minute(step + 1)))),
            .. Enumerable.Range(0, faults).Select(step => Placed(SessionEvent.ToolFailed(id, Minute(step + 5)))),
            Placed(new SessionEvent(id, "assistant_response", Minute(minutes))),
        ];
    }
}
