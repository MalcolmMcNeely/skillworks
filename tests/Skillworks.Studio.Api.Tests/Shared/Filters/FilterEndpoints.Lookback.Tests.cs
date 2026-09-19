using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Watch.Skills;

namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Reads_today_and_the_six_days_before_it_when_no_span_is_given()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(7), "23:59:59.999")),
            new SkillActivated("grilling", At(DaysBack(6), "00:00:00.000")),
            new SkillActivated("grilling", At(Today, "00:00:00.000")));

        var answer = await studio.SkillAnswer();

        // Named in the head, so a zero on screen says which week it is a zero for.
        Assert.Equal((From: DaysBack(6), To: Today, Lookback: true), SpanOf(answer));
        Assert.Equal(7, answer.Days.Count);
        Assert.Equal(1, Assert.Single(answer.Day(Today).Skills).Activations);
        Assert.Equal(1, Assert.Single(answer.Day(DaysBack(6)).Skills).Activations);
    }

    [Fact]
    public async Task Takes_the_length_of_the_lookback_from_configuration()
    {
        using var studio = new StudioHost(lookbackDays: 2);

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(2), "23:59:59.999")),
            new SkillActivated("grilling", At(Yesterday, "00:00:00.000")));

        var answer = await studio.SkillAnswer();

        Assert.Equal((From: Yesterday, To: Today, Lookback: true), SpanOf(answer));
        Assert.Equal(2, answer.Days.Count);
        Assert.Equal(1, Assert.Single(answer.Day(Yesterday).Skills).Activations);
    }

    [Fact]
    public async Task Covers_the_span_a_filter_names_in_place_of_the_lookback()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(12), "09:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000")));

        var answer = await studio.SkillAnswer(BothDays);

        Assert.Equal((From: DaysBack(14), To: DaysBack(10), Lookback: false), SpanOf(answer));
        Assert.Equal(1, answer.Skills.Sum(skill => skill.Activations));
        Assert.Equal(1, Assert.Single(answer.Day(DaysBack(12)).Skills).Activations);
    }

    [Fact]
    public async Task Covers_the_lookback_when_a_filter_names_only_a_repository_or_a_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(14), "09:00:00.000"), Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Owner: "acme", RepositoryName: "xi"));

        var inXi = await studio.SkillAnswer("?repository=acme/xi");
        var grilling = await studio.SkillAnswer("?skill=grilling");

        Assert.True(inXi.Head.Span.Lookback);
        Assert.Equal(1, inXi.Skills.Sum(skill => skill.Activations));
        Assert.True(grilling.Head.Span.Lookback);
        Assert.Equal(1, grilling.Skills.Sum(skill => skill.Activations));
    }

    [Fact]
    public async Task Runs_a_span_with_no_end_to_today_and_one_with_no_start_back_a_lookback()
    {
        using var studio = new StudioHost();

        Assert.Equal((From: DaysBack(5), To: Today, Lookback: false), SpanOf(await studio.SkillAnswer($"?from={Written(DaysBack(5))}")));
        Assert.Equal((From: DaysBack(16), To: DaysBack(10), Lookback: false), SpanOf(await studio.SkillAnswer($"?to={Written(DaysBack(10))}")));
    }

    private static (DateOnly From, DateOnly To, bool Lookback) SpanOf(SkillsAnswer answer) =>
        (answer.Head.Span.From, answer.Head.Span.To, answer.Head.Span.Lookback);
}
