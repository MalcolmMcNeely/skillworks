using System.Net;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    private const string BothDays = "?from=2026-09-01&to=2026-09-05";

    [Fact]
    public async Task Counts_every_activation_inside_a_span_on_the_day_it_fired()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        var answer = await studio.SkillAnswer(BothDays);

        Assert.Equal(["grilling", "tdd", "unslop"], answer.Day("2026-09-05").Skills.Select(skill => skill.Name));
        Assert.Equal([1, 1, 1], answer.Day("2026-09-05").Skills.Select(skill => skill.Activations));
        Assert.Equal(["grilling", "unslop"], answer.Day("2026-09-01").Skills.Select(skill => skill.Name));
        Assert.Equal([1, 1], answer.Day("2026-09-01").Skills.Select(skill => skill.Activations));
        Assert.All(answer.Days.Skip(1).Take(3), day => Assert.Empty(day.Skills));
    }

    [Fact]
    public async Task Narrows_to_the_activations_inside_a_date_range()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        var answer = await studio.SkillAnswer("?from=2026-09-01&to=2026-09-01");

        // Only the nu firings fall in the range, so the xi firings are not in the answer at all.
        var day = Assert.Single(answer.Days);
        Assert.Equal(["grilling", "unslop"], day.Skills.Select(skill => skill.Name));
        Assert.Equal([1, 1], day.Skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Takes_in_the_whole_of_both_days_at_the_ends_of_a_range()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("before", "2026-09-04T23:59:59.999Z"),
            new SkillActivated("first", "2026-09-05T00:00:00.000Z"),
            new SkillActivated("last", "2026-09-05T23:59:59.999Z"),
            new SkillActivated("after", "2026-09-06T00:00:00.000Z"));

        var answer = await studio.SkillAnswer("?from=2026-09-05&to=2026-09-05");

        // A range ending at midnight on the 5th would drop the firing late that evening.
        Assert.Equal(["first", "last"], Assert.Single(answer.Days).Skills.Select(skill => skill.Name));
    }

    [Fact]
    public async Task Narrows_to_one_repository()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        var answer = await studio.SkillAnswer($"{BothDays}&repository=acme/xi");

        Assert.Equal(["grilling", "tdd", "unslop"], answer.Day("2026-09-05").Skills.Select(skill => skill.Name));
        Assert.Equal([1, 1, 1], answer.Day("2026-09-05").Skills.Select(skill => skill.Activations));
        Assert.Empty(answer.Day("2026-09-01").Skills);
    }

    [Fact]
    public async Task Leaves_out_a_firing_with_no_repository_when_a_repository_is_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:15:00.000Z", Owner: "acme"));

        // A firing with half a name might have been anywhere, so it is not an answer about acme/xi.
        Assert.Equal(1, (await studio.SkillOn("2026-09-14", "grilling", "?repository=acme/xi")).Activations);
        Assert.Empty((await studio.SkillAnswer("?repository=xi")).Skills);
    }

    [Fact]
    public async Task Tells_two_owners_repositories_of_the_same_name_apart()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "globex", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Owner: "globex", RepositoryName: "xi"));

        Assert.Equal(1, (await studio.SkillOn("2026-09-14", "grilling", "?repository=acme/xi")).Activations);
        Assert.Equal(2, (await studio.SkillOn("2026-09-14", "grilling", "?repository=globex/xi")).Activations);
    }

    [Fact]
    public async Task Narrows_to_one_skill()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        var answer = await studio.SkillAnswer($"{BothDays}&skill=grilling");

        Assert.Equal(["grilling"], answer.Day("2026-09-05").Skills.Select(skill => skill.Name));
        Assert.Equal(["grilling"], answer.Day("2026-09-01").Skills.Select(skill => skill.Name));
        Assert.Equal(2, answer.Skills.Sum(skill => skill.Activations));
    }

    [Fact]
    public async Task Narrows_by_the_date_the_repository_and_the_skill_at_once()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        var answer = await studio.SkillAnswer("?from=2026-09-05&to=2026-09-05&repository=acme/xi&skill=grilling");

        var grilling = Assert.Single(Assert.Single(answer.Days).Skills);
        Assert.Equal("grilling", grilling.Name);
        Assert.Equal(1, grilling.Activations);
    }

    [Fact]
    public async Task Answers_a_filter_that_matches_nothing_with_empty_days()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        using var response = await studio.AskForSkills("?from=2020-01-01&to=2020-01-02");

        // An empty week is an answer, and a failure would send the reader looking for a broken Studio.
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Empty((await studio.SkillAnswer("?from=2020-01-01&to=2020-01-02")).Skills);
    }

    [Fact]
    public async Task Answers_a_skill_nothing_has_ever_heard_of_with_empty_days()
    {
        using var studio = new StudioHost();
        await PushNuAndXi(studio);

        Assert.Empty((await studio.SkillAnswer($"{BothDays}&skill=no-such-skill")).Skills);
    }

    [Fact]
    public async Task Leaves_a_catalogue_skill_that_never_fired_out_of_a_narrowed_answer()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "acme", RepositoryName: "nu"));

        // A never-fired skill's zero belongs to the unfiltered answer; it did not happen there.
        Assert.Contains("probekit:probe-local", (await studio.SkillAnswer()).Head.CatalogueSkills);
        Assert.Empty((await studio.SkillAnswer("?repository=acme/nu")).Head.CatalogueSkills);
        Assert.Empty((await studio.SkillAnswer("?from=2026-09-14&to=2026-09-14")).Head.CatalogueSkills);
    }

    [Fact]
    public async Task Keeps_a_catalogue_skill_that_never_fired_when_it_is_the_skill_asked_for()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        var answer = await studio.SkillAnswer("?skill=probekit:probe-local");

        // Narrowing to one skill is narrowing the same list, not asking what happened somewhere.
        Assert.Equal(["probekit:probe-local"], answer.Head.CatalogueSkills);
    }

    private static Task PushNuAndXi(StudioHost studio) => studio.Push(
        new SkillActivated("grilling", "2026-09-01T10:00:00.000Z", Owner: "acme", RepositoryName: "nu"),
        new SkillActivated("unslop", "2026-09-01T10:05:00.000Z", Owner: "acme", RepositoryName: "nu"),
        new SkillActivated("grilling", "2026-09-05T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
        new SkillActivated("unslop", "2026-09-05T09:05:00.000Z", Owner: "acme", RepositoryName: "xi"),
        new SkillActivated("tdd", "2026-09-05T23:30:00.000Z", Owner: "acme", RepositoryName: "xi"));
}
