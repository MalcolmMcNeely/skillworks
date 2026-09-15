using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Charges_a_skill_only_for_the_turns_inside_the_whole_days_a_span_names()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new ApiRequest("2026-09-04T23:59:59.999Z", Skill: "grilling", CostUsd: 0.01m),
            new ApiRequest("2026-09-05T00:00:00.000Z", Skill: "grilling", CostUsd: 0.02m, InputTokens: 200),
            new ApiRequest("2026-09-05T23:59:59.999Z", Skill: "grilling", CostUsd: 0.04m, InputTokens: 400),
            new ApiRequest("2026-09-06T00:00:00.000Z", Skill: "grilling", CostUsd: 0.08m));

        var grilling = await studio.Skill("grilling", "?from=2026-09-05&to=2026-09-05");

        // Narrowed as Activations are, or cost per activation would set one day's firings against other days' spend.
        Assert.Equal(0.06m, grilling.Spend.Cost);
        Assert.Equal(600, grilling.Spend.InputTokens);
    }

    [Fact]
    public async Task Charges_a_skill_for_the_turns_in_the_lookback_when_no_span_is_given()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new ApiRequest("2026-09-08T23:59:59.999Z", Skill: "grilling", CostUsd: 0.01m),
            new ApiRequest("2026-09-09T00:00:00.000Z", Skill: "grilling", CostUsd: 0.02m),
            new ApiRequest("2026-09-15T00:00:00.000Z", Skill: "grilling", CostUsd: 0.04m));

        Assert.Equal(0.06m, (await studio.Skill("grilling")).Spend.Cost);
    }

    [Fact]
    public async Task Charges_a_skill_only_for_the_turns_in_the_repository_asked_for()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "grilling", CostUsd: 0.01m, InputTokens: 100, Owner: "acme", RepositoryName: "nu"),
            new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "grilling", CostUsd: 0.02m, InputTokens: 200, Owner: "acme", RepositoryName: "xi"),
            new ApiRequest("2026-09-14T09:02:00.000Z", Skill: "grilling", CostUsd: 0.04m, InputTokens: 400),
            new ApiRequest("2026-09-14T09:03:00.000Z", Skill: "grilling", CostUsd: 0.08m, InputTokens: 800, Owner: "acme"));

        var everywhere = await studio.Skill("grilling");
        var inNu = await studio.Skill("grilling", "?repository=acme/nu");

        // A Turn with no Repository, or half of one, might have run anywhere, so it is not spend in acme/nu.
        Assert.Equal(0.15m, everywhere.Spend.Cost);
        Assert.Equal(0.01m, inNu.Spend.Cost);
        Assert.Equal(100, inNu.Spend.InputTokens);
    }

    [Fact]
    public async Task Lists_only_the_spend_of_the_skill_asked_for()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "grilling", CostUsd: 0.01m, Model: "claude-sonnet-5"),
            new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "tdd", CostUsd: 0.02m, Model: "claude-haiku-4-5"));

        var skills = await studio.Skills("?skill=grilling");

        Assert.Equal(["grilling"], skills.Select(skill => skill.Name));
        Assert.Equal(0.01m, skills[0].Spend.Cost);
        Assert.Equal(["claude-sonnet-5"], skills[0].Models);
    }
}
