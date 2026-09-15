using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Spend;

public sealed class SpendEndpointsTests
{
    [Fact]
    public async Task Leaves_what_a_skill_cost_as_Claude_Code_sent_it_when_a_price_changes()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "grilling", Model: "claude-opus-5", CostUsd: 0.42m, OutputTokens: 4_000));

        var opus = (await studio.Prices()).Single(price => price.Model == "claude-opus-5");
        await studio.Reprice(opus with { OutputPerMillion = opus.OutputPerMillion * 2 });

        // The organisation gives Claude Code its prices, so a price held in Studio would be a second opinion.
        Assert.Equal(0.42m, (await studio.Skill("grilling")).Spend?.Cost);
    }
}
