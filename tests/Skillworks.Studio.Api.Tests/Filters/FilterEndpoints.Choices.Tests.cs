using System.Globalization;
using Skillworks.Core.EventsStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    private const string FiveDays = "?from=2026-09-11&to=2026-09-15";

    [Fact]
    public async Task Offers_the_repositories_seen_on_each_day_of_the_span_newest_day_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-08-31T23:59:59.999Z", Owner: "acme", RepositoryName: "before"),
            new SkillActivated("grilling", "2026-09-01T10:00:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-05T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("unslop", "2026-09-05T09:05:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("tdd", "2026-09-05T09:10:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("tdd", "2026-09-05T09:15:00.000Z"),
            new SkillActivated("grilling", "2026-09-06T00:00:00.000Z", Owner: "acme", RepositoryName: "after"));

        var lines = await studio.FilterChoiceLines(BothDays);
        var answer = FilterChoicesAnswer.Of(lines);

        Assert.Equal(["head", "day", "day", "day", "day", "day", "end"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            [Day("2026-09-05"), Day("2026-09-04"), Day("2026-09-03"), Day("2026-09-02"), Day("2026-09-01")],
            answer.HeadDays);
        Assert.Equal(answer.HeadDays, answer.Days.Select(day => day.Day));
        Assert.Equal(["acme/nu", "acme/xi"], answer.Day("2026-09-05").Repositories);
        Assert.Equal(["acme/nu"], answer.Day("2026-09-01").Repositories);
        Assert.All(answer.Days.Skip(1).Take(3), day => Assert.Empty(day.Repositories));
    }

    [Fact]
    public async Task Offers_every_repository_in_the_span_whatever_repository_is_picked()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "acme", RepositoryName: "xi"));

        var answer = await studio.FilterChoices("?from=2026-09-14&to=2026-09-14&repository=acme/nu");

        // The picked repository narrows the map, and the choices must still offer the way across.
        Assert.Equal(["acme/nu", "acme/xi"], Assert.Single(answer.Days).Repositories);
    }

    [Fact]
    public async Task Offers_the_repositories_of_every_day_of_a_span_longer_than_one_query_may_cover()
    {
        using var studio = new StudioHost();

        // At both ends of the span, so no one query could hold both.
        await studio.Push(
            new SkillActivated("grilling", "2026-09-01T09:00:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-10T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"));

        var answer = await studio.FilterChoices(TenDays);

        Assert.Equal(10, answer.Days.Count);
        Assert.Equal(["acme/xi"], answer.Day("2026-09-10").Repositories);
        Assert.Equal(["acme/nu"], answer.Day("2026-09-01").Repositories);
    }

    [Fact]
    public async Task Answers_with_lines_that_offer_no_skill_choices()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        await studio.Push(new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "nu"));

        var lines = await studio.FilterChoiceLines("?from=2026-09-14&to=2026-09-14");

        // No screen offers a skill dropdown, so a list of skills would be read for nothing.
        Assert.Equal(["days", "kind", "span"], StudioHost.Fields(lines[0]));
        Assert.Equal(["day", "kind", "repositories"], StudioHost.Fields(lines[1]));
        Assert.Equal(["kind"], StudioHost.Fields(lines[2]));
    }

    [Fact]
    public async Task Offers_no_day_at_all_when_the_store_cannot_offer_choices_from_the_start()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var lines = await studio.FilterChoiceLines(FiveDays);

        Assert.Equal(["head", "end"], lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Keeps_the_choices_already_sent_and_leaves_out_the_day_it_could_not_read_when_the_store_fails_part_way()
    {
        using var events = BrokenEventsStore.DownBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-15T09:00:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-13T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"));

        var lines = await studio.FilterChoiceLines(FiveDays);
        var answer = FilterChoicesAnswer.Of(lines);

        Assert.Equal([Day("2026-09-15"), Day("2026-09-14")], answer.Days.Select(day => day.Day));
        Assert.Equal(["acme/nu"], answer.Day("2026-09-15").Repositories);
        Assert.DoesNotContain("acme/xi", answer.Repositories);
        Assert.Equal(["kind"], StudioHost.Fields(lines[^1]));
    }

    [Fact]
    public async Task Lets_go_of_the_store_when_the_choices_request_is_closed()
    {
        using var events = BrokenEventsStore.StallingBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        // Head and two days, then closed while the store holds the third, as when the span changes.
        await studio.FilterChoiceLines(FiveDays, count: 3);

        Assert.True(await events.HeldFor < TimeSpan.FromSeconds(new LokiOptions().TimeoutSeconds));
    }

    private static DateOnly Day(string day) => DateOnly.Parse(day, CultureInfo.InvariantCulture);
}
