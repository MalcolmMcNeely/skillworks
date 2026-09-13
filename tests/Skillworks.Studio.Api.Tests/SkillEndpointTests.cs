using System.Text.Json;

namespace Skillworks.Studio.Api.Tests;

public sealed class SkillEndpointTests
{
    [Fact]
    public async Task Reports_a_skill_that_fired_once_with_the_repository_and_branch_it_fired_in()
    {
        using var studio = new Studio(Studio.Fixture("ordinary"));

        var skills = await studio.GetSkills();
        var grilling = Skill(skills, "grilling");

        Assert.Equal(1, grilling.GetProperty("activations").GetInt32());
        Assert.Equal(["alpha"], Strings(grilling, "repositories"));
        Assert.Equal(["main"], Strings(grilling, "branches"));
    }

    [Fact]
    public async Task Counts_every_firing_in_a_session_as_its_own_activation()
    {
        using var studio = new Studio(Studio.Fixture("repeated"));

        var skills = await studio.GetSkills();

        Assert.Equal(3, Skill(skills, "unslop").GetProperty("activations").GetInt32());
    }

    [Fact]
    public async Task Reports_nothing_for_a_session_in_which_no_skill_fired()
    {
        using var studio = new Studio(Studio.Fixture("quiet"));

        var skills = await studio.GetSkills();

        Assert.Empty(skills.EnumerateArray());
    }

    [Fact]
    public async Task Reports_a_catalogue_skill_that_has_never_fired_with_no_activations()
    {
        using var studio = new Studio(Studio.Fixture("quiet"), Studio.Catalogue());

        var skills = await studio.GetSkills();
        var never = Skill(skills, "probekit:probe-local");

        Assert.Equal(0, never.GetProperty("activations").GetInt32());
        Assert.Empty(never.GetProperty("repositories").EnumerateArray());
    }

    [Fact]
    public async Task Reports_a_catalogue_skill_that_has_fired_once_only()
    {
        using var studio = new Studio(Studio.Fixture("catalogue"), Studio.Catalogue());

        var skills = await studio.GetSkills();

        Assert.Equal(
            ["probekit:probe-local", "probekit:probe-plugin"],
            skills.EnumerateArray().Select(row => row.GetProperty("name").GetString()));
        Assert.Equal(2, Skill(skills, "probekit:probe-plugin").GetProperty("activations").GetInt32());
    }

    private static JsonElement Skill(JsonElement skills, string name) =>
        skills.EnumerateArray().Single(skill => skill.GetProperty("name").GetString() == name);

    private static string[] Strings(JsonElement skill, string property) =>
        [.. skill.GetProperty(property).EnumerateArray().Select(value => value.GetString()!)];
}
