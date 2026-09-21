using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Counts_a_skill_s_Activations_by_the_UTC_hour_they_happened_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:40:00.000")),
            new SkillActivated("grilling", At(Yesterday, "17:30:00.000")),
            new SkillActivated("tdd", At(Yesterday, "02:15:00.000")));

        var skills = await studio.SkillsOn(Yesterday, OnlyYesterday);

        Assert.Equal(Hours((9, 2), (17, 1)), skills.Single(skill => skill.Name == "grilling").Hours);
        Assert.Equal(Hours((2, 1)), skills.Single(skill => skill.Name == "tdd").Hours);
    }

    [Fact]
    public async Task Counts_an_activation_on_the_hour_in_the_hour_it_starts()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(2), "23:59:59.999")),
            new SkillActivated("grilling", At(Yesterday, "00:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:59:59.999")),
            new SkillActivated("grilling", At(Yesterday, "10:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "23:59:59.999")),
            new SkillActivated("grilling", At(Today, "00:00:00.000")));

        var answer = await studio.SkillAnswer($"?from={Written(DaysBack(2))}&to={Written(Today)}");

        Assert.Equal(Hours((23, 1)), answer.Day(DaysBack(2)).Skills.Single().Hours);
        Assert.Equal(Hours((0, 1), (9, 1), (10, 1), (23, 1)), answer.Day(Yesterday).Skills.Single().Hours);
        Assert.Equal(Hours((0, 1)), answer.Day(Today).Skills.Single().Hours);
    }

    [Fact]
    public async Task Counts_a_day_s_Activations_as_the_sum_of_its_hours()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(2), "23:59:59.999")),
            new SkillActivated("grilling", At(Yesterday, "00:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "13:30:00.000")),
            new SkillActivated("grilling", At(Yesterday, "23:59:59.999")),
            new SkillActivated("grilling", At(Today, "00:00:00.000")));

        var days = (await studio.SkillAnswer($"?from={Written(DaysBack(2))}&to={Written(Today)}")).Days.Select(day => day.Skills.Single()).ToArray();

        // Two figures for one day that disagree would leave the developer unsure which to believe.
        Assert.Equal([1, 3, 1], days.Select(grilling => grilling.Activations));
        Assert.Equal(
            [Hours((0, 1)), Hours((0, 1), (13, 1), (23, 1)), Hours((23, 1))],
            days.Select(grilling => grilling.Hours));
    }

    [Fact]
    public async Task Counts_by_hour_only_the_activations_the_filter_keeps()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", At(Yesterday, "11:00:00.000"), Owner: "acme", RepositoryName: "nu"));

        var grilling = await studio.SkillOn(Yesterday, "grilling", $"?from={Written(Yesterday)}&to={Written(Yesterday)}&repository=acme/nu");

        Assert.Equal(Hours((11, 1)), grilling.Hours);
    }

    [Fact]
    public async Task Gives_a_skill_that_spent_but_never_fired_a_zero_for_every_hour()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", CostUsd: 0.2m));

        var grilling = await studio.SkillOn(Yesterday, "grilling", OnlyYesterday);

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
