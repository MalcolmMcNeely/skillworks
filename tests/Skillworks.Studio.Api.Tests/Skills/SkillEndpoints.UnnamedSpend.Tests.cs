using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Adds_the_turns_Claude_Code_will_not_name_a_skill_for_into_one_unnamed_amount()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "third-party", CostUsd: 0.1m, InputTokens: 1_000, OutputTokens: 4_000, CacheReadTokens: 2_000_000, CacheCreationTokens: 100_000),
            new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "third-party", CostUsd: 0.2m, InputTokens: 500, OutputTokens: 2_000, CacheReadTokens: 1_000_000, CacheCreationTokens: 300_000),
            new ApiRequest("2026-09-14T09:02:00.000Z", Skill: "grilling", CostUsd: 0.4m, InputTokens: 40),
            new ApiRequest("2026-09-14T09:03:00.000Z", CostUsd: 0.8m, InputTokens: 80));

        var answer = await studio.SkillTable();

        // A Turn under no skill hides no skill, so it is not unnamed.
        Assert.Equal(
            new TurnTotalsRow { InputTokens = 1_500, OutputTokens = 6_000, CacheReadTokens = 3_000_000, CacheCreationTokens = 400_000, Cost = 0.3m },
            answer.UnnamedSpend);
    }

    [Fact]
    public async Task Reports_the_spend_of_a_plugin_skill_with_no_turns_under_its_name_as_not_named()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("probekit:probe-plugin", "2026-09-14T09:00:00.000Z", Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"));
        await studio.Push(new ApiRequest("2026-09-14T09:00:10.000Z", Skill: "third-party", Model: "claude-sonnet-5", Effort: "high", CostUsd: 0.1m));

        var probe = await studio.Skill("probekit:probe-plugin");

        // Its Turns may be among the unnamed ones, and a zero would say it spent nothing.
        Assert.Equal(1, probe.Activations);
        Assert.Null(probe.Spend);
        Assert.Null(probe.AverageCost);
        Assert.Null(probe.Models);
        Assert.Null(probe.Efforts);
    }

    [Fact]
    public async Task Reports_what_a_plugin_skill_spent_when_its_turns_carry_its_name()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("skill-creator:skill-creator", "2026-09-14T09:00:00.000Z", Source: "plugin", Plugin: "skill-creator", Marketplace: "claude-plugins-official"));
        await studio.Push(new ApiRequest("2026-09-14T09:00:10.000Z", Skill: "skill-creator:skill-creator", Model: "claude-sonnet-5", Effort: "high", CostUsd: 0.1m));

        var creator = await studio.Skill("skill-creator:skill-creator");

        // A plugin from Anthropic's marketplaces keeps its name on its Turns.
        Assert.Equal(0.1m, creator.Spend?.Cost);
        Assert.Equal(0.1m, creator.AverageCost);
        Assert.Equal(["claude-sonnet-5"], creator.Models!);
        Assert.Equal(["high"], creator.Efforts!);
    }

    [Fact]
    public async Task Charges_a_catalogue_skill_that_never_fired_nothing_rather_than_leaving_it_not_named()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        await studio.Push(new ApiRequest("2026-09-14T09:00:10.000Z", Skill: "third-party", CostUsd: 0.1m));

        var probe = await studio.Skill("probekit:probe-plugin");

        // No firing says a plugin delivered it, so nothing says its Turns went unnamed.
        Assert.Equal(0, probe.Activations);
        Assert.Equal(new TurnTotalsRow { InputTokens = 0, OutputTokens = 0, CacheReadTokens = 0, CacheCreationTokens = 0, Cost = 0m }, probe.Spend);
        Assert.Equal(0m, probe.AverageCost);
        Assert.Empty(probe.Models!);
        Assert.Empty(probe.Efforts!);
    }
}
