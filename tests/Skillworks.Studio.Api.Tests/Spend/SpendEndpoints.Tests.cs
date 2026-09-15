using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Spend;

public sealed class SpendEndpointsTests
{
    // Each cost is at the rates the price table is seeded with for its model.
    private const decimal OpusCost =
        (1_000m * 15m) / 1_000_000m +          // input
        (4_000m * 75m) / 1_000_000m +          // output, thinking included
        (2_000_000m * 1.50m) / 1_000_000m +    // cache read
        (100_000m * 18.75m) / 1_000_000m +     // cache written for five minutes
        (300_000m * 30m) / 1_000_000m;         // cache written for an hour

    private const decimal SonnetCost =
        (500m * 3m) / 1_000_000m +
        (2_000m * 15m) / 1_000_000m +
        (1_000_000m * 0.30m) / 1_000_000m;

    private const decimal HaikuCost =
        (200m * 1m) / 1_000_000m +
        (400m * 5m) / 1_000_000m +
        (500_000m * 0.10m) / 1_000_000m;

    private const decimal SweepCost = OpusCost + SonnetCost;

    [Fact]
    public async Task Splits_a_skills_tokens_by_kind()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var spend = (await studio.Skill("comment-sweep")).Spend;

        Assert.Equal(1_500, spend.InputTokens);
        Assert.Equal(6_000, spend.OutputTokens);
        Assert.Equal(3_000_000, spend.CacheReadTokens);
        Assert.Equal(400_000, spend.CacheWriteTokens);
    }

    [Fact]
    public async Task Counts_the_thinking_inside_a_skills_output_tokens()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var spend = (await studio.Skill("comment-sweep")).Spend;

        // Thinking is billed inside output: reported apart it explains a high output, and added on it would charge twice.
        Assert.Equal(3_000, spend.ThinkingTokens);
        Assert.True(spend.ThinkingTokens < spend.OutputTokens);
    }

    [Fact]
    public async Task Counts_one_request_once_however_many_records_it_was_written_across()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        // The fixture's opus request is three records, each repeating the whole usage, so summing them would treble it.
        Assert.Equal(6_000, (await studio.Skill("comment-sweep")).Spend.OutputTokens);
    }

    [Fact]
    public async Task Names_the_model_and_effort_a_skill_was_fired_at()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var sweep = await studio.Skill("comment-sweep");

        // It ran on opus and sonnet, and naming only the model that chose it would hide a cost charged at two rates.
        Assert.Equal(["claude-opus-5", "claude-sonnet-5"], sweep.Models);
        Assert.Equal(["high", "medium"], sweep.Efforts);
    }

    [Fact]
    public async Task Reports_cost_in_money_from_the_price_table()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var sweep = await studio.Skill("comment-sweep");

        Assert.Equal(SweepCost, sweep.Spend.Cost);
        Assert.False(sweep.Spend.CostIsPartial);
    }

    [Fact]
    public async Task Prices_each_model_a_skill_ran_on_at_its_own_rate()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        // The two rates are an order of magnitude apart, so one blended rate lands nowhere near.
        Assert.NotEqual(OpusCost, SonnetCost);
        Assert.Equal(SweepCost, (await studio.Skill("comment-sweep")).Spend.Cost);
    }

    [Fact]
    public async Task Reports_the_average_cost_of_an_activation_beside_the_total()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));
        await PushCostlyFirings(studio);

        var sweep = await studio.Skill("comment-sweep");

        Assert.Equal(2, sweep.Activations);
        Assert.Equal(SweepCost / 2, sweep.AverageCost);
    }

    [Fact]
    public async Task Ranks_skills_by_what_they_cost()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));
        await PushCostlyFirings(studio);

        var skills = await studio.Skills();

        // Name order, as the rank is the reader's to choose; sorting the totals here would only test that LINQ sorts.
        Assert.Equal(["comment-sweep", "grilling", "tdd", "unslop"], skills.Select(skill => skill.Name));
        Assert.Equal([SweepCost, 0m, 0m, HaikuCost], skills.Select(skill => skill.Spend.Cost));
    }

    [Fact]
    public async Task Changes_reported_cost_when_a_price_changes_and_reads_no_transcript_again()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var before = await studio.Skill("comment-sweep");
        var passes = (await studio.Status()).CompletedPasses;

        var opus = (await studio.Prices()).Single(price => price.Model == "claude-opus-5");
        await studio.Reprice(opus with { OutputPerMillion = opus.OutputPerMillion * 2 });

        var after = await studio.Skill("comment-sweep");

        Assert.Equal(SweepCost + (4_000m * 75m) / 1_000_000m, after.Spend.Cost);
        Assert.Equal(before.Spend.OutputTokens, after.Spend.OutputTokens);
        Assert.Equal(passes, (await studio.Status()).CompletedPasses);
    }

    [Fact]
    public async Task Says_a_cost_is_partial_when_a_skill_ran_on_a_model_with_no_price()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var tdd = await studio.Skill("tdd");

        // The tokens are real and the money unknown, and a silent zero is the one lie a cost tool cannot afford.
        Assert.Equal(100, tdd.Spend.InputTokens);
        Assert.Equal(0m, tdd.Spend.Cost);
        Assert.True(tdd.Spend.CostIsPartial);
    }

    [Fact]
    public async Task Charges_a_skill_nothing_when_no_request_was_made_under_it()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));
        await PushCostlyFirings(studio);

        var grilling = await studio.Skill("grilling");

        // grilling fired and the session ended, so it owns no tokens at all.
        Assert.Equal(1, grilling.Activations);
        Assert.Equal(0, grilling.Spend.OutputTokens);
        Assert.Equal(0m, grilling.Spend.Cost);
        Assert.False(grilling.Spend.CostIsPartial);
        Assert.Equal(0m, grilling.AverageCost);
    }

    [Fact]
    public async Task Charges_a_skill_for_the_requests_made_under_it_and_no_others()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        var unslop = await studio.Skill("unslop");

        // unslop owns its haiku request; the opus request that fired it is comment-sweep's, and choosing turns are no skill's.
        Assert.Equal(200, unslop.Spend.InputTokens);
        Assert.Equal(HaikuCost, unslop.Spend.Cost);
        Assert.Equal(1_500, (await studio.Skill("comment-sweep")).Spend.InputTokens);
    }

    // The costly transcript's firings as events, because the count comes from the events store.
    private static Task PushCostlyFirings(StudioHost studio) => studio.Push(
        new SkillActivated("comment-sweep", "2026-09-10T09:00:04.000Z"),
        new SkillActivated("unslop", "2026-09-10T09:01:10.000Z"),
        new SkillActivated("comment-sweep", "2026-09-10T09:05:03.000Z"),
        new SkillActivated("tdd", "2026-09-10T09:20:02.000Z"),
        new SkillActivated("grilling", "2026-09-10T09:40:03.000Z"));
}
