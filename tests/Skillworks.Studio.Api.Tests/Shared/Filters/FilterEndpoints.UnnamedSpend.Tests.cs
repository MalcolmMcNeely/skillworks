using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Watch.Skills;

namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Counts_unnamed_spend_only_for_the_turns_inside_the_whole_days_a_span_names()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(DaysBack(11), "23:59:59.999"), Skill: "third-party", CostUsd: 0.01m),
            new ApiRequest(At(DaysBack(10), "00:00:00.000"), Skill: "third-party", CostUsd: 0.02m, OutputTokens: 200),
            new ApiRequest(At(DaysBack(10), "23:59:59.999"), Skill: "third-party", CostUsd: 0.04m, OutputTokens: 400),
            new ApiRequest(At(DaysBack(9), "00:00:00.000"), Skill: "third-party", CostUsd: 0.08m));

        var unnamed = Assert.Single((await studio.SkillAnswer($"?from={Written(DaysBack(10))}&to={Written(DaysBack(10))}")).Days).UnnamedSpend;

        Assert.Equal(0.06m, unnamed?.Cost);
        Assert.Equal(600, unnamed?.OutputTokens);
    }

    [Fact]
    public async Task Counts_unnamed_spend_only_for_the_turns_in_the_repository_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "third-party", CostUsd: 0.01m, Owner: "acme", RepositoryName: "nu"),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "third-party", CostUsd: 0.02m, Owner: "acme", RepositoryName: "xi"),
            new ApiRequest(At(Yesterday, "09:02:00.000"), Skill: "third-party", CostUsd: 0.04m));

        var everywhere = (await studio.SkillAnswer()).Day(Yesterday);
        var inNu = (await studio.SkillAnswer("?repository=acme/nu")).Day(Yesterday);

        Assert.Equal(0.07m, everywhere.UnnamedSpend?.Cost);
        Assert.Equal(0.01m, inNu.UnnamedSpend?.Cost);
    }

    [Fact]
    public async Task Leaves_unnamed_spend_out_when_the_filter_names_a_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new ApiRequest(At(Yesterday, "09:00:00.000"), Skill: "third-party", CostUsd: 0.07m),
            new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", CostUsd: 0.02m));

        var forGrilling = await studio.SkillAnswer("?skill=grilling");
        var forThirdParty = await studio.SkillAnswer("?skill=third-party");

        Assert.All(forGrilling.Days, day => Assert.Null(day.UnnamedSpend));
        Assert.All(forThirdParty.Days, day => Assert.Null(day.UnnamedSpend));
        Assert.Empty(forThirdParty.Skills);
    }
}
