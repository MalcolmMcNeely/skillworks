using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Counts_a_skill_s_Activations_by_the_UTC_hour_they_happened_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:40:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T17:30:00.000Z"),
            new SkillActivated("tdd", "2026-09-14T02:15:00.000Z"));

        var skills = await studio.SkillsOn("2026-09-14", OnlyTheFourteenth);

        Assert.Equal(Hours((9, 2), (17, 1)), skills.Single(skill => skill.Name == "grilling").Hours);
        Assert.Equal(Hours((2, 1)), skills.Single(skill => skill.Name == "tdd").Hours);
    }

    [Fact]
    public async Task Counts_a_firing_on_the_hour_in_the_hour_it_starts()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-13T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-14T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-14T10:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-15T00:00:00.000Z"));

        var answer = await studio.SkillAnswer("?from=2026-09-13&to=2026-09-15");

        Assert.Equal(Hours((23, 1)), answer.Day("2026-09-13").Skills.Single().Hours);
        Assert.Equal(Hours((0, 1), (9, 1), (10, 1), (23, 1)), answer.Day("2026-09-14").Skills.Single().Hours);
        Assert.Equal(Hours((0, 1)), answer.Day("2026-09-15").Skills.Single().Hours);
    }

    [Fact]
    public async Task Counts_a_day_s_Activations_as_the_sum_of_its_hours()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-13T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-14T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T13:30:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-15T00:00:00.000Z"));

        var days = (await studio.SkillAnswer("?from=2026-09-13&to=2026-09-15")).Days.Select(day => day.Skills.Single()).ToArray();

        // Two figures for one day that disagree would leave the developer unsure which to believe.
        Assert.Equal([1, 3, 1], days.Select(grilling => grilling.Activations));
        Assert.Equal(days.Select(grilling => grilling.Activations), days.Select(grilling => grilling.Hours.Sum()));
    }

    [Fact]
    public async Task Counts_by_hour_only_the_firings_the_filter_keeps()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T11:00:00.000Z", Owner: "acme", RepositoryName: "nu"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", "?from=2026-09-14&to=2026-09-14&repository=acme/nu");

        Assert.Equal(Hours((11, 1)), grilling.Hours);
    }

    [Fact]
    public async Task Gives_a_skill_that_spent_but_never_fired_a_zero_for_every_hour()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "grilling", CostUsd: 0.2m));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", OnlyTheFourteenth);

        // Every hour, so a screen reads a quiet hour as a zero it was told, not a slot left out.
        Assert.Equal(Hours(), grilling.Hours);
    }

    private static int[] Hours(params (int Hour, int Activations)[] fired)
    {
        var hours = new int[24];

        foreach (var (hour, activations) in fired)
        {
            hours[hour] = activations;
        }

        return hours;
    }
}
