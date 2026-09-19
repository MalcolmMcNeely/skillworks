using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Watch.Skills;

namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public sealed partial class FilterEndpointsTests
{
    // More days than the test Loki lets one query cover.
    private static readonly string TenDays = $"?from={Written(DaysBack(14))}&to={Written(DaysBack(5))}";

    [Fact]
    public async Task Reads_every_day_of_a_span_longer_than_one_query_may_cover()
    {
        using var studio = new StudioHost();

        // At both ends of the span, so no one query could hold both.
        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(14), "09:00:00.000"), Trigger: "claude-proactive", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", At(DaysBack(5), "09:00:00.000"), Trigger: "user-slash", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", At(DaysBack(5), "09:05:00.000"), Trigger: "user-slash", Owner: "acme", RepositoryName: "xi"));

        var answer = await studio.SkillAnswer(TenDays);
        var newest = Assert.Single(answer.Day(DaysBack(5)).Skills);
        var oldest = Assert.Single(answer.Day(DaysBack(14)).Skills);

        Assert.Equal("complete", answer.Gap.Kind);
        Assert.Equal(10, answer.Days.Count);
        Assert.Equal(2, newest.Activations);
        Assert.Equal(["acme/xi"], newest.Repositories);
        Assert.Equal(["user-slash"], newest.Origins.Select(origin => origin.Trigger));
        Assert.Equal(1, oldest.Activations);
        Assert.Equal(["acme/nu"], oldest.Repositories);
        Assert.Equal(["claude-proactive"], oldest.Origins.Select(origin => origin.Trigger));
    }

    [Fact]
    public async Task Reads_spend_on_every_day_of_a_span_longer_than_one_query_may_cover()
    {
        using var studio = new StudioHost();

        // At both ends of the span, so no one query could hold both.
        await studio.Push(
            new ApiRequest(At(DaysBack(14), "09:00:00.000"), Skill: "grilling", Model: "claude-opus-5[1m]", CostUsd: 0.1m, OutputTokens: 100),
            new ApiRequest(At(DaysBack(5), "09:00:00.000"), Skill: "grilling", Model: "claude-sonnet-5", CostUsd: 0.2m, OutputTokens: 200),
            new ApiRequest(At(DaysBack(5), "09:05:00.000"), Skill: "grilling", Model: "claude-sonnet-5", CostUsd: 0.4m, OutputTokens: 400));

        var answer = await studio.SkillAnswer(TenDays);
        var newest = Assert.Single(answer.Day(DaysBack(5)).Skills);
        var oldest = Assert.Single(answer.Day(DaysBack(14)).Skills);

        Assert.Equal(0.6m, newest.Spend?.Cost);
        Assert.Equal(600, newest.Spend?.OutputTokens);
        Assert.Equal(["claude-sonnet-5"], newest.Models!);
        Assert.Equal(0.1m, oldest.Spend?.Cost);
        Assert.Equal(100, oldest.Spend?.OutputTokens);
        Assert.Equal(["claude-opus-5[1m]"], oldest.Models!);
    }

    [Fact]
    public async Task Counts_an_activation_at_midnight_once_on_the_day_it_starts()
    {
        using var studio = new StudioHost();

        // One at every midnight, so every cut between days has an Activation on it.
        await studio.Push(SkillActivated.AtEveryMidnight("grilling", DaysBack(15), DaysBack(4)));

        var answer = await studio.SkillAnswer(TenDays);

        Assert.Equal(10, answer.Days.Count);
        Assert.All(answer.Days, day => Assert.Equal(1, Assert.Single(day.Skills).Activations));
    }
}
