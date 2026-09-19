using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Adds_the_turns_Claude_Code_will_not_name_a_skill_for_into_one_unnamed_amount_for_the_day()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "third-party", CostUsd: 0.1m, InputTokens: 1_000, OutputTokens: 4_000, CacheReadTokens: 2_000_000, CacheCreationTokens: 100_000),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "third-party", CostUsd: 0.2m, InputTokens: 500, OutputTokens: 2_000, CacheReadTokens: 1_000_000, CacheCreationTokens: 300_000),
            new ApiRequest(At(Yesterday, "09:02:00.000"), Skill: "grilling", CostUsd: 0.4m, InputTokens: 40),
            new ApiRequest(At(Yesterday, "09:03:00.000"), CostUsd: 0.8m, InputTokens: 80),
            new ApiRequest(At(DaysBack(2), "09:00:00.000"), Skill: "third-party", CostUsd: 1.6m));

        var answer = await studio.SkillAnswer();

        // A Turn under no skill hides no skill, so it is not unnamed.
        Assert.Equal(
            new TurnTotalsRow { InputTokens = 1_500, OutputTokens = 6_000, CacheReadTokens = 3_000_000, CacheCreationTokens = 400_000, Cost = 0.3m },
            answer.Day(Yesterday).UnnamedSpend);
        Assert.Equal(1.6m, answer.Day(DaysBack(2)).UnnamedSpend?.Cost);
    }

    [Fact]
    public async Task Reports_the_spend_of_a_plugin_skill_with_no_turns_under_its_name_as_not_named()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("probekit:probe-plugin", At(Yesterday, "09:00:00.000"), Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"));
        await studio.Push(new ApiRequest(At(Yesterday, "09:00:10.000"), Skill: "third-party", Model: "claude-sonnet-5", Effort: "high", CostUsd: 0.1m));

        var probe = await studio.SkillOn(Yesterday, "probekit:probe-plugin");

        // Its Turns may be among the unnamed ones, and a zero would say it spent nothing.
        Assert.Equal(1, probe.Activations);
        Assert.Null(probe.Spend);
        Assert.Null(probe.Models);
        Assert.Null(probe.Efforts);
    }

    [Fact]
    public async Task Reports_what_a_plugin_skill_spent_when_its_turns_carry_its_name()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("skill-creator:skill-creator", At(Yesterday, "09:00:00.000"), Source: "plugin", Plugin: "skill-creator", Marketplace: "claude-plugins-official"));
        await studio.Push(new ApiRequest(At(Yesterday, "09:00:10.000"), Skill: "skill-creator:skill-creator", Model: "claude-sonnet-5", Effort: "high", CostUsd: 0.1m));

        var creator = await studio.SkillOn(Yesterday, "skill-creator:skill-creator");

        // A plugin from Anthropic's marketplaces keeps its name on its Turns.
        Assert.Equal(0.1m, creator.Spend?.Cost);
        Assert.Equal(["claude-sonnet-5"], creator.Models!);
        Assert.Equal(["high"], creator.Efforts!);
    }

    [Fact]
    public async Task Reports_what_a_plugin_skill_spent_on_a_day_it_did_not_fire()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("probekit:probe-plugin", At(DaysBack(2), "23:59:00.000"), Source: "plugin", Plugin: "probekit", Marketplace: "skillworks"));
        await studio.Push(new ApiRequest(At(Yesterday, "00:00:10.000"), Skill: "probekit:probe-plugin", CostUsd: 0.1m));

        var probe = await studio.SkillOn(Yesterday, "probekit:probe-plugin");

        // Its Turns carry its name, so a day it did not fire on still knows what it spent.
        Assert.Equal(0, probe.Activations);
        Assert.Equal(0.1m, probe.Spend?.Cost);
    }
}
