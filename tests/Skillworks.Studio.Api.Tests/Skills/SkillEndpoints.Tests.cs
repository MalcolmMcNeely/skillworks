using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    private const string OnlyTheFourteenth = "?from=2026-09-14&to=2026-09-14";

    [Fact]
    public async Task Answers_with_a_head_then_one_day_per_UTC_day_newest_first_then_an_end()
    {
        using var studio = new StudioHost();

        var lines = await studio.SkillLines("?from=2026-09-12&to=2026-09-14");

        // Newest first, so the recent end a developer cares about lands before the rest.
        Assert.Equal(["head", "day", "day", "day", "end"], lines.Select(SkillsAnswer.KindOf));
        Assert.Equal(["2026-09-14", "2026-09-13", "2026-09-12"], lines.Skip(1).SkipLast(1).Select(line => (string?)line["day"]));
    }

    [Fact]
    public async Task Answers_one_JSON_object_per_line()
    {
        using var studio = new StudioHost();

        using var response = await studio.AskForSkills("");

        Assert.Equal("application/x-ndjson", response.Content.Headers.ContentType?.MediaType);
    }

    [Fact]
    public async Task Names_in_the_head_the_days_that_will_arrive_in_the_order_they_will_arrive()
    {
        using var studio = new StudioHost();

        var answer = await studio.SkillAnswer("?from=2026-09-12&to=2026-09-14");

        // Known before any day is read, so a screen can show the days still to come.
        Assert.Equal([Day("2026-09-14"), Day("2026-09-13"), Day("2026-09-12")], answer.Head.Days);
        Assert.Equal(answer.Head.Days, answer.Days.Select(day => day.Day));
    }

    [Fact]
    public async Task Answers_with_a_head_and_days_that_hold_only_what_a_screen_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"));

        var head = await studio.SkillLine("head");
        var day = await studio.SkillLine("day", OnlyTheFourteenth);

        Assert.Equal(["catalogueSkills", "days", "kind", "span"], StudioHost.Fields(head));
        Assert.Equal(["from", "fromUtc", "lookback", "to", "untilUtc"], StudioHost.Fields(head["span"]));

        // No Each: a day's Each would not add up across days, so the screen works it out from the totals.
        Assert.Equal(["day", "kind", "skills", "unnamedSpend", "unnarrowedEvents"], StudioHost.Fields(day));
        Assert.Equal(
            ["activations", "efforts", "models", "name", "origins", "repositories", "spend"],
            StudioHost.Fields(day["skills"]?[0]));
    }

    [Fact]
    public async Task Names_the_span_as_the_instants_from_its_first_midnight_to_the_midnight_after_its_last_day()
    {
        using var studio = new StudioHost();

        var span = (await studio.SkillAnswer("?from=2026-09-01&to=2026-09-05")).Head.Span;

        Assert.Equal(DateTimeOffset.Parse("2026-09-01T00:00:00Z", CultureInfo.InvariantCulture), span.FromUtc);
        Assert.Equal(DateTimeOffset.Parse("2026-09-06T00:00:00Z", CultureInfo.InvariantCulture), span.UntilUtc);
    }

    [Fact]
    public async Task Counts_every_skill_activated_event_whatever_set_the_skill_off()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Trigger: "nested-skill"),
            new SkillActivated("grilling", "2026-09-14T09:15:00.000Z", Trigger: "agent-preload"),
            new SkillActivated("tdd", "2026-09-14T09:20:00.000Z", Trigger: "claude-proactive"));

        var skills = await studio.SkillsOn("2026-09-14");

        // A typed skill is use too, so an entry point never reads as a skill nobody runs.
        Assert.Equal(["grilling", "tdd"], skills.Select(skill => skill.Name));
        Assert.Equal([4, 1], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Counts_a_firing_on_the_UTC_day_it_happened()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-04T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-05T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-05T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-06T00:00:00.000Z"));

        var answer = await studio.SkillAnswer("?from=2026-09-04&to=2026-09-06");

        // A late session evening and an early one next morning are two days, however close together.
        Assert.Equal([1, 2, 1], answer.Days.Select(day => Assert.Single(day.Skills).Activations));
    }

    [Fact]
    public async Task Counts_every_firing_and_turn_of_a_day_however_the_filter_narrows_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("tdd", "2026-09-14T09:05:00.000Z"));
        await studio.Push(new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "grilling"));

        var day = (await studio.SkillAnswer("?repository=acme/nu")).Day("2026-09-14");

        // What the store holds, not what the filter kept, or a filter that matches nothing would read as a quiet day.
        Assert.Empty(day.Skills);
        Assert.Equal(3, day.UnnarrowedEvents);
    }

    [Fact]
    public async Task Names_a_repository_by_its_owner_and_its_name()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "malcolmania", RepositoryName: "skillworks"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "acme", RepositoryName: "skillworks"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Owner: "acme", RepositoryName: "skillworks"));

        // Two organisations can each have a skillworks, and one name for both would merge them.
        Assert.Equal(["acme/skillworks", "malcolmania/skillworks"], (await studio.SkillOn("2026-09-14", "grilling")).Repositories);
    }

    [Fact]
    public async Task Counts_a_firing_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "acme"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", RepositoryName: "skillworks"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling");

        // An older Claude Code, or a repository with no origin remote, still fired the skill.
        Assert.Equal(3, grilling.Activations);
        Assert.Empty(grilling.Repositories);
    }

    [Fact]
    public async Task Reports_nothing_when_no_skill_fired()
    {
        using var studio = new StudioHost();

        var answer = await studio.SkillAnswer();

        Assert.Empty(answer.Head.CatalogueSkills);
        Assert.Empty(answer.Skills);
    }

    [Fact]
    public async Task Lists_a_catalogue_skill_that_did_not_fire_in_the_lookback_in_the_head()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        await studio.Push(
            new SkillActivated("probekit:probe-local", "2026-09-01T09:00:00.000Z"),
            new SkillActivated("probekit:probe-plugin", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("probekit:probe-plugin", "2026-09-14T09:05:00.000Z"));

        var answer = await studio.SkillAnswer();

        // probe-local last fired before the lookback, and its zero says its description may have stopped working.
        Assert.Equal(["probekit:probe-local", "probekit:probe-plugin"], answer.Head.CatalogueSkills);
        Assert.DoesNotContain("probekit:probe-local", answer.Skills.Select(skill => skill.Name));
        Assert.Equal(2, (await studio.SkillOn("2026-09-14", "probekit:probe-plugin")).Activations);
    }

    [Fact]
    public async Task Leaves_the_branch_out_of_the_answer()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"));

        var grilling = (await studio.SkillLine("day", OnlyTheFourteenth))["skills"]?[0];

        // No telemetry event carries a branch, so a field for one would stay empty for good.
        Assert.Equal("grilling", (string?)grilling?["name"]);
        Assert.DoesNotContain("branches", StudioHost.Fields(grilling));
    }

    private static DateOnly Day(string day) => DateOnly.Parse(day, CultureInfo.InvariantCulture);
}
