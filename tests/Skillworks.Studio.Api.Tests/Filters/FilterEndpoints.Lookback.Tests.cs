using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Reads_today_and_the_six_days_before_it_when_no_span_is_given()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-08T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-09T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-15T00:00:00.000Z"));

        var answer = await studio.SkillAnswer();

        // Named in the head, so a zero on screen says which week it is a zero for.
        Assert.Equal(Span("2026-09-09", "2026-09-15", lookback: true), SpanOf(answer));
        Assert.Equal(7, answer.Days.Count);
        Assert.Equal(1, Assert.Single(answer.Day("2026-09-15").Skills).Activations);
        Assert.Equal(1, Assert.Single(answer.Day("2026-09-09").Skills).Activations);
    }

    [Fact]
    public async Task Takes_the_length_of_the_lookback_from_configuration()
    {
        using var studio = new StudioHost(lookbackDays: 2);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-13T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-14T00:00:00.000Z"));

        var answer = await studio.SkillAnswer();

        Assert.Equal(Span("2026-09-14", "2026-09-15", lookback: true), SpanOf(answer));
        Assert.Equal(2, answer.Days.Count);
        Assert.Equal(1, Assert.Single(answer.Day("2026-09-14").Skills).Activations);
    }

    [Fact]
    public async Task Covers_the_span_a_filter_names_in_place_of_the_lookback()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-03T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"));

        var answer = await studio.SkillAnswer(BothDays);

        Assert.Equal(Span("2026-09-01", "2026-09-05", lookback: false), SpanOf(answer));
        Assert.Equal(1, answer.Skills.Sum(skill => skill.Activations));
        Assert.Equal(1, Assert.Single(answer.Day("2026-09-03").Skills).Activations);
    }

    [Fact]
    public async Task Covers_the_lookback_when_a_filter_names_only_a_repository_or_a_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-01T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"));

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

        Assert.Equal(Span("2026-09-10", "2026-09-15", lookback: false), SpanOf(await studio.SkillAnswer("?from=2026-09-10")));
        Assert.Equal(Span("2026-08-30", "2026-09-05", lookback: false), SpanOf(await studio.SkillAnswer("?to=2026-09-05")));
    }

    private static (DateOnly From, DateOnly To, bool Lookback) Span(string from, string to, bool lookback) =>
        (DateOnly.Parse(from, CultureInfo.InvariantCulture), DateOnly.Parse(to, CultureInfo.InvariantCulture), lookback);

    private static (DateOnly From, DateOnly To, bool Lookback) SpanOf(SkillsAnswer answer) =>
        (answer.Head.Span.From, answer.Head.Span.To, answer.Head.Span.Lookback);
}
