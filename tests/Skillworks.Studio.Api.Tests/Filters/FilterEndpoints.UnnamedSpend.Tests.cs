using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Counts_unnamed_spend_only_for_the_turns_inside_the_whole_days_a_span_names()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest("2026-09-04T23:59:59.999Z", Skill: "third-party", CostUsd: 0.01m),
            new ApiRequest("2026-09-05T00:00:00.000Z", Skill: "third-party", CostUsd: 0.02m, OutputTokens: 200),
            new ApiRequest("2026-09-05T23:59:59.999Z", Skill: "third-party", CostUsd: 0.04m, OutputTokens: 400),
            new ApiRequest("2026-09-06T00:00:00.000Z", Skill: "third-party", CostUsd: 0.08m));

        var unnamed = Assert.Single((await studio.SkillAnswer("?from=2026-09-05&to=2026-09-05")).Days).UnnamedSpend;

        Assert.Equal(0.06m, unnamed?.Cost);
        Assert.Equal(600, unnamed?.OutputTokens);
    }

    [Fact]
    public async Task Counts_unnamed_spend_only_for_the_turns_in_the_repository_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "third-party", CostUsd: 0.01m, Owner: "acme", RepositoryName: "nu"),
            new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "third-party", CostUsd: 0.02m, Owner: "acme", RepositoryName: "xi"),
            new ApiRequest("2026-09-14T09:02:00.000Z", Skill: "third-party", CostUsd: 0.04m));

        var everywhere = (await studio.SkillAnswer()).Day("2026-09-14");
        var inNu = (await studio.SkillAnswer("?repository=acme/nu")).Day("2026-09-14");

        Assert.Equal(0.07m, everywhere.UnnamedSpend?.Cost);
        Assert.Equal(0.01m, inNu.UnnamedSpend?.Cost);
    }

    [Fact]
    public async Task Leaves_unnamed_spend_out_when_the_filter_names_a_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest("2026-09-14T09:00:00.000Z", Skill: "third-party", CostUsd: 0.07m),
            new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "grilling", CostUsd: 0.02m));

        var forGrilling = await studio.SkillAnswer("?skill=grilling");
        var forThirdParty = await studio.SkillAnswer("?skill=third-party");

        Assert.All(forGrilling.Days, day => Assert.Null(day.UnnamedSpend));
        Assert.All(forThirdParty.Days, day => Assert.Null(day.UnnamedSpend));
        Assert.Empty(forThirdParty.Skills);
    }
}
