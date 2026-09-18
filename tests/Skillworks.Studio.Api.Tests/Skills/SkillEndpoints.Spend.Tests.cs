using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Reports_a_skills_cost_as_the_sum_of_what_Claude_Code_estimated_for_its_turns()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "grilling", CostUsd: 0.1m),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", CostUsd: 0.2m));

        // Added in floating point these make 0.30000000000000004, which is not what the Turns cost.
        Assert.Equal(0.3m, (await studio.SkillOn(Yesterday, "grilling")).Spend?.Cost);
    }

    [Fact]
    public async Task Reports_a_skills_tokens_as_input_output_cache_read_and_cache_creation()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "grilling", InputTokens: 1_000, OutputTokens: 4_000, CacheReadTokens: 2_000_000, CacheCreationTokens: 100_000),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", InputTokens: 500, OutputTokens: 2_000, CacheReadTokens: 1_000_000, CacheCreationTokens: 300_000));

        var spend = (await studio.SkillOn(Yesterday, "grilling")).Spend;

        Assert.Equal(1_500, spend?.InputTokens);
        Assert.Equal(6_000, spend?.OutputTokens);
        Assert.Equal(3_000_000, spend?.CacheReadTokens);
        Assert.Equal(400_000, spend?.CacheCreationTokens);
    }

    [Fact]
    public async Task Leaves_a_turn_that_names_no_skill_out_of_every_skills_spend()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", At(Yesterday, "09:00:00.000")));
        await studio.Push(
            new ApiRequest(At(Yesterday, "08:59:58.000"), CostUsd: 0.05m, InputTokens: 900),
            new ApiRequest(At(Yesterday, "09:00:10.000"), Skill: "grilling", CostUsd: 0.02m, InputTokens: 200));

        var grilling = Assert.Single(await studio.SkillsOn(Yesterday));

        // The Turn that chose grilling ran before grilling was in force, so it is no skill's.
        Assert.Equal("grilling", grilling.Name);
        Assert.Equal(0.02m, grilling.Spend?.Cost);
        Assert.Equal(200, grilling.Spend?.InputTokens);
    }

    [Fact]
    public async Task Leaves_a_turn_under_a_skill_Claude_Code_will_not_name_out_of_every_skills_spend()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:10.000"), Skill: "third-party", CostUsd: 0.07m, OutputTokens: 700),
            new ApiRequest(At(Yesterday, "09:02:00.000"), Skill: "grilling", CostUsd: 0.02m));

        var skills = await studio.SkillsOn(Yesterday);

        // third-party stands for any skill from a plugin outside Anthropic's marketplaces, so no one skill has that name.
        Assert.Equal(["grilling"], skills.Select(skill => skill.Name));
        Assert.Equal(0.02m, skills[0].Spend?.Cost);
    }

    [Fact]
    public async Task Names_the_models_and_efforts_a_skills_turns_ran_on()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "grilling", Model: "claude-opus-5[1m]", Effort: "high"),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", Model: "claude-sonnet-5", Effort: "medium"),
            new ApiRequest(At(Yesterday, "09:02:00.000"), Skill: "grilling", Model: "claude-sonnet-5"),
            new ApiRequest(At(Yesterday, "09:03:00.000"), Skill: "tdd", Model: "claude-haiku-4-5", Effort: "low"));

        var grilling = await studio.SkillOn(Yesterday, "grilling");

        // Its cost was charged at two models' rates, and naming one would hide the other.
        Assert.Equal(["claude-opus-5[1m]", "claude-sonnet-5"], grilling.Models!);
        Assert.Equal(["high", "medium"], grilling.Efforts!);
    }

    [Fact]
    public async Task Charges_a_skill_nothing_when_no_turn_ran_under_it()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", At(Yesterday, "09:00:00.000")));

        var grilling = await studio.SkillOn(Yesterday, "grilling");

        Assert.Equal(1, grilling.Activations);
        Assert.Equal(new TurnTotalsRow { InputTokens = 0, OutputTokens = 0, CacheReadTokens = 0, CacheCreationTokens = 0, Cost = 0m }, grilling.Spend);
        Assert.Empty(grilling.Models!);
        Assert.Empty(grilling.Efforts!);
    }

    [Fact]
    public async Task Reports_spend_as_only_the_token_kinds_telemetry_sends_and_the_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "grilling", CostUsd: 0.1m));

        var spend = (await studio.SkillLine("day", OnlyYesterday))["skills"]?[0]?["spend"];

        // Telemetry sends no thinking tokens and no split of cache writes, so a field for either would stay empty for good.
        Assert.Equal(
            ["cacheCreationTokens", "cacheReadTokens", "cost", "inputTokens", "outputTokens"],
            StudioHost.Fields(spend));
    }
}
