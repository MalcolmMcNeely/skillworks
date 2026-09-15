using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    [Fact]
    public async Task Counts_today_and_the_six_days_before_it_when_no_span_is_given()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-08T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-09T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-15T00:00:00.000Z"));

        var answer = await studio.SkillTable();

        // Named in the answer, so a zero on screen says which week it is a zero for.
        Assert.Equal(2, Assert.Single(answer.Skills).Activations);
        Assert.Equal(Span("2026-09-09", "2026-09-15", lookback: true), answer.Span);
    }

    [Fact]
    public async Task Takes_the_length_of_the_lookback_from_configuration()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), lookbackDays: 2);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-13T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-14T00:00:00.000Z"));

        var answer = await studio.SkillTable();

        Assert.Equal(1, Assert.Single(answer.Skills).Activations);
        Assert.Equal(Span("2026-09-14", "2026-09-15", lookback: true), answer.Span);
    }

    [Fact]
    public async Task Covers_the_span_a_filter_names_in_place_of_the_lookback()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-03T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"));

        var answer = await studio.SkillTable(BothDays);

        Assert.Equal(1, Assert.Single(answer.Skills).Activations);
        Assert.Equal(Span("2026-09-01", "2026-09-05", lookback: false), answer.Span);
    }

    [Fact]
    public async Task Covers_the_lookback_when_a_filter_names_only_a_repository_or_a_skill()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-01T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"));

        var inXi = await studio.SkillTable("?repository=acme/xi");

        Assert.Equal(1, Assert.Single(inXi.Skills).Activations);
        Assert.True(inXi.Span.Lookback);
        Assert.Equal(1, await studio.ActivationsOf("grilling", "?skill=grilling"));
    }

    [Fact]
    public async Task Runs_a_span_with_no_end_to_today_and_one_with_no_start_back_a_lookback()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        Assert.Equal(Span("2026-09-10", "2026-09-15", lookback: false), (await studio.SkillTable("?from=2026-09-10")).Span);
        Assert.Equal(Span("2026-08-30", "2026-09-05", lookback: false), (await studio.SkillTable("?to=2026-09-05")).Span);
    }

    private static SpanRow Span(string from, string to, bool lookback) => new()
    {
        From = DateOnly.Parse(from, CultureInfo.InvariantCulture),
        To = DateOnly.Parse(to, CultureInfo.InvariantCulture),
        Lookback = lookback,
    };
}
