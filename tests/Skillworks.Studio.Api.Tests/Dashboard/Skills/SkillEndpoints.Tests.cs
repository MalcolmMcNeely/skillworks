using System.Globalization;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed partial class SkillEndpointsTests
{
    private static readonly string OnlyYesterday = $"?from={Written(Yesterday)}&to={Written(Yesterday)}";

    [Fact]
    public async Task Answers_with_a_head_then_one_day_per_UTC_day_newest_first_then_an_end()
    {
        using var studio = new StudioHost();

        var lines = await studio.SkillLines($"?from={Written(DaysBack(3))}&to={Written(Yesterday)}");

        // Newest first, so the recent end a developer cares about lands before the rest.
        Assert.Equal(["head", "day", "day", "day", "end"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            [Written(Yesterday), Written(DaysBack(2)), Written(DaysBack(3))],
            lines.Skip(1).SkipLast(1).Select(line => (string?)line["day"]));
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

        var answer = await studio.SkillAnswer($"?from={Written(DaysBack(3))}&to={Written(Yesterday)}");

        // Known before any day is read, so a screen can show the days still to come.
        Assert.Equal([Yesterday, DaysBack(2), DaysBack(3)], answer.Head.Days);
        Assert.Equal(answer.Head.Days, answer.Days.Select(day => day.Day));
    }

    [Fact]
    public async Task Answers_with_a_head_and_days_that_hold_only_what_a_screen_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", At(Yesterday, "09:00:00.000")));

        var head = await studio.SkillLine("head");
        var day = await studio.SkillLine("day", OnlyYesterday);

        Assert.Equal(["days", "kind", "pluginSkills", "span"], StudioHost.Fields(head));
        Assert.Equal(["from", "fromUtc", "lookback", "to", "untilUtc"], StudioHost.Fields(head["span"]));

        // No Each: a day's Each would not add up across days, so the screen works it out from the totals.
        Assert.Equal(["day", "kind", "skills", "unnamedSpend", "unnarrowedEvents"], StudioHost.Fields(day));
        Assert.Equal(
            ["activations", "efforts", "hours", "models", "name", "origins", "repositories", "spend", "triggers"],
            StudioHost.Fields(day["skills"]?[0]));
    }

    [Fact]
    public async Task Names_the_span_as_the_instants_from_its_first_midnight_to_the_midnight_after_its_last_day()
    {
        using var studio = new StudioHost();

        var span = (await studio.SkillAnswer($"?from={Written(DaysBack(14))}&to={Written(DaysBack(10))}")).Head.Span;

        Assert.Equal(DateTimeOffset.Parse(At(DaysBack(14), "00:00:00"), CultureInfo.InvariantCulture), span.FromUtc);
        Assert.Equal(DateTimeOffset.Parse(At(DaysBack(9), "00:00:00"), CultureInfo.InvariantCulture), span.UntilUtc);
    }

    [Fact]
    public async Task Counts_every_skill_activated_event_whatever_set_the_skill_off()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Trigger: "claude-proactive"),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Trigger: "user-slash"),
            new SkillActivated("grilling", At(Yesterday, "09:10:00.000"), Trigger: "nested-skill"),
            new SkillActivated("grilling", At(Yesterday, "09:15:00.000"), Trigger: "agent-preload"),
            new SkillActivated("tdd", At(Yesterday, "09:20:00.000"), Trigger: "claude-proactive"));

        var skills = await studio.SkillsOn(Yesterday);

        // A typed skill is use too, so an entry point never reads as a skill nobody runs.
        Assert.Equal(["grilling", "tdd"], skills.Select(skill => skill.Name));
        Assert.Equal([4, 1], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Counts_an_activation_on_the_UTC_day_it_happened()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(11), "23:59:59.999")),
            new SkillActivated("grilling", At(DaysBack(10), "00:00:00.000")),
            new SkillActivated("grilling", At(DaysBack(10), "23:59:59.999")),
            new SkillActivated("grilling", At(DaysBack(9), "00:00:00.000")));

        var answer = await studio.SkillAnswer($"?from={Written(DaysBack(11))}&to={Written(DaysBack(9))}");

        // A late session evening and an early one next morning are two days, however close together.
        Assert.Equal([1, 2, 1], answer.Days.Select(day => Assert.Single(day.Skills).Activations));
    }

    [Fact]
    public async Task Counts_every_activation_and_turn_of_a_day_however_the_filter_narrows_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("tdd", At(Yesterday, "09:05:00.000")));
        await studio.Push(new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling"));

        var day = (await studio.SkillAnswer("?repository=acme/nu")).Day(Yesterday);

        // What the store holds, not what the filter kept, or a filter that matches nothing would read as a quiet day.
        Assert.Empty(day.Skills);
        Assert.Equal(3, day.UnnarrowedEvents);
    }

    [Fact]
    public async Task Names_a_repository_by_its_owner_and_its_name()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Owner: "malcolmania", RepositoryName: "skillworks"),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Owner: "acme", RepositoryName: "skillworks"),
            new SkillActivated("grilling", At(Yesterday, "09:10:00.000"), Owner: "acme", RepositoryName: "skillworks"));

        // Two organisations can each have a skillworks, and one name for both would merge them.
        Assert.Equal(["acme/skillworks", "malcolmania/skillworks"], (await studio.SkillOn(Yesterday, "grilling")).Repositories);
    }

    [Fact]
    public async Task Counts_an_activation_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Owner: "acme"),
            new SkillActivated("grilling", At(Yesterday, "09:10:00.000"), RepositoryName: "skillworks"));

        var grilling = await studio.SkillOn(Yesterday, "grilling");

        // An older Claude Code, or a repository with no origin remote, still fired the skill.
        Assert.Equal(3, grilling.Activations);
        Assert.Empty(grilling.Repositories);
    }

    [Fact]
    public async Task Reports_nothing_when_no_skill_fired()
    {
        using var studio = new StudioHost();

        var answer = await studio.SkillAnswer();

        Assert.Empty(answer.Head.PluginSkills);
        Assert.Empty(answer.Skills);
    }

    [Fact]
    public async Task Lists_a_plugin_skill_that_did_not_fire_in_the_lookback_in_the_head()
    {
        using var studio = new StudioHost(StudioHost.Marketplace());

        await studio.Push(
            new SkillActivated("probekit:probe-local", At(DaysBack(14), "09:00:00.000")),
            new SkillActivated("probekit:probe-plugin", At(Yesterday, "09:00:00.000")),
            new SkillActivated("probekit:probe-plugin", At(Yesterday, "09:05:00.000")));

        var answer = await studio.SkillAnswer();

        // probe-local last fired before the lookback, and its zero says its description may have stopped working.
        Assert.Equal(["probekit:probe-local", "probekit:probe-plugin"], answer.Head.PluginSkills);
        Assert.DoesNotContain("probekit:probe-local", answer.Skills.Select(skill => skill.Name));
        Assert.Equal(2, (await studio.SkillOn(Yesterday, "probekit:probe-plugin")).Activations);
    }

    [Fact]
    public async Task Leaves_the_branch_out_of_the_answer()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", At(Yesterday, "09:00:00.000")));

        var grilling = (await studio.SkillLine("day", OnlyYesterday))["skills"]?[0];

        // No telemetry event carries a branch, so a field for one would stay empty for good.
        Assert.Equal("grilling", (string?)grilling?["name"]);
        Assert.DoesNotContain("branches", StudioHost.Fields(grilling));
    }
}
