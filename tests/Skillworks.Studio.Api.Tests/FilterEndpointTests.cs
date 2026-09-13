using System.Net;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// What the filtered fixture holds, so the assertions below read as arithmetic rather than as magic.
/// Two sessions in two repositories, four days apart:
/// <list type="bullet">
/// <item><c>nu</c> on 1 September: grilling fires once and owns one sonnet request; unslop fires
/// once and owns one haiku request.</item>
/// <item><c>xi</c> on 5 September: grilling fires once and owns one sonnet request; unslop fires
/// once and owns nothing; tdd fires at half past eleven at night and owns nothing.</item>
/// </list>
/// </summary>
public sealed class FilterEndpointTests
{
    /// <summary>grilling's one request in nu, at the seeded claude-sonnet-5 rates.</summary>
    private const decimal GrillingInNu =
        (1_000m * 3m) / 1_000_000m +
        (2_000m * 15m) / 1_000_000m;

    /// <summary>grilling's one request in xi, at the same rates on half the tokens.</summary>
    private const decimal GrillingInXi =
        (500m * 3m) / 1_000_000m +
        (1_000m * 15m) / 1_000_000m;

    [Fact]
    public async Task Counts_every_activation_when_nothing_is_narrowed()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var skills = await studio.Skills();

        Assert.Equal(["grilling", "tdd", "unslop"], skills.Select(skill => skill.Name));
        Assert.Equal([2, 1, 2], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Narrows_to_the_activations_inside_a_date_range()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var skills = await studio.Skills("?from=2026-09-01&to=2026-09-01");

        // Only the nu session falls in the range, so the xi firings are not in the answer at all.
        Assert.Equal(["grilling", "unslop"], skills.Select(skill => skill.Name));
        Assert.Equal([1, 1], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Takes_in_the_whole_of_the_last_day_of_a_range()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        // tdd fired at 23:30 on the 5th. A range that ended at midnight on the 5th would drop it,
        // which is not what a reader asking about the 5th meant.
        Assert.Equal(1, await studio.ActivationsOf("tdd", "?from=2026-09-05&to=2026-09-05"));
    }

    [Fact]
    public async Task Narrows_to_one_repository()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var skills = await studio.Skills("?repository=xi");

        Assert.Equal(["grilling", "tdd", "unslop"], skills.Select(skill => skill.Name));
        Assert.Equal([1, 1, 1], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Narrows_to_one_skill()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var skills = await studio.Skills("?skill=grilling");

        Assert.Equal(["grilling"], skills.Select(skill => skill.Name));
        Assert.Equal(2, skills.Single().Activations);
    }

    [Fact]
    public async Task Narrows_by_the_date_the_repository_and_the_skill_at_once()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var skills = await studio.Skills("?from=2026-09-05&to=2026-09-05&repository=xi&skill=grilling");

        Assert.Equal(["grilling"], skills.Select(skill => skill.Name));
        Assert.Equal(1, skills.Single().Activations);
    }

    [Fact]
    public async Task Charges_a_skill_only_for_what_it_spent_inside_the_filter()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        var everywhere = await studio.Skill("grilling");
        var inNu = await studio.Skill("grilling", "?repository=nu");

        // The cost has to narrow with the count. A filtered count beside an all-time cost would read
        // as a skill that cost a fortune for one firing.
        Assert.Equal(GrillingInNu + GrillingInXi, everywhere.Spend.Cost);
        Assert.Equal(GrillingInNu, inNu.Spend.Cost);
        Assert.Equal(1_000, inNu.Spend.InputTokens);
    }

    [Fact]
    public async Task Reports_the_branches_a_skill_fired_on_inside_the_filter_only()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        Assert.Equal(["main", "work"], (await studio.Skill("grilling")).Branches);
        Assert.Equal(["work"], (await studio.Skill("grilling", "?repository=xi")).Branches);
    }

    [Fact]
    public async Task Answers_a_filter_that_matches_nothing_with_an_empty_list()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        using var response = await studio.AskForSkills("?from=2020-01-01&to=2020-01-02");

        // An empty answer is an answer. Reporting "nothing happened that week" as a failure would
        // send the reader looking for a broken Studio instead of reading the fact.
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Empty(await studio.Skills("?from=2020-01-01&to=2020-01-02"));
    }

    [Fact]
    public async Task Answers_a_skill_nothing_has_ever_heard_of_with_an_empty_list()
    {
        using var studio = new Studio(Studio.Fixture("filtered"));

        Assert.Empty(await studio.Skills("?skill=no-such-skill"));
    }

    [Fact]
    public async Task Leaves_a_catalogue_skill_that_never_fired_out_of_a_narrowed_answer()
    {
        using var studio = new Studio(Studio.Fixture("filtered"), Studio.Catalogue());

        // A skill that never fired belongs to the all-time, everywhere answer, where a zero says the
        // description may be broken. Asking what happened in nu is asking what happened there, and a
        // skill that did not happen there is not a zero in that answer.
        Assert.Contains("probekit:probe-local", (await studio.Skills()).Select(skill => skill.Name));
        Assert.DoesNotContain(
            "probekit:probe-local",
            (await studio.Skills("?repository=nu")).Select(skill => skill.Name));
    }

    [Fact]
    public async Task Keeps_a_catalogue_skill_that_never_fired_when_it_is_the_skill_asked_for()
    {
        using var studio = new Studio(Studio.Fixture("filtered"), Studio.Catalogue());

        var never = await studio.Skill("probekit:probe-local", "?skill=probekit:probe-local");

        // Narrowing to one skill is narrowing the same list, not asking what happened somewhere.
        Assert.Equal(0, never.Activations);
    }

    [Fact]
    public async Task Offers_the_repositories_and_skills_a_filter_can_name()
    {
        using var studio = new Studio(Studio.Fixture("filtered"), Studio.Catalogue());

        var choices = await studio.Filters();

        Assert.Equal(["nu", "xi"], choices.Repositories);
        Assert.Equal(["grilling", "probekit:probe-local", "probekit:probe-plugin", "tdd", "unslop"], choices.Skills);
    }
}
