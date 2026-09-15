using System.Net.Http.Json;
using System.Text.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Counts_every_skill_activated_event_whatever_set_the_skill_off()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Trigger: "nested-skill"),
            new SkillActivated("grilling", "2026-09-14T09:15:00.000Z", Trigger: "agent-preload"),
            new SkillActivated("tdd", "2026-09-14T09:20:00.000Z", Trigger: "claude-proactive"));

        var skills = await studio.Skills();

        // A typed skill is use too, so an entry point never reads as a skill nobody runs.
        Assert.Equal(["grilling", "tdd"], skills.Select(skill => skill.Name));
        Assert.Equal([4, 1], skills.Select(skill => skill.Activations));
    }

    [Fact]
    public async Task Names_a_repository_by_its_owner_and_its_name()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Owner: "malcolmania", RepositoryName: "skillworks"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "acme", RepositoryName: "skillworks"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Owner: "acme", RepositoryName: "skillworks"));

        // Two organisations can each have a skillworks, and one name for both would merge them.
        Assert.Equal(["acme/skillworks", "malcolmania/skillworks"], (await studio.Skill("grilling")).Repositories);
    }

    [Fact]
    public async Task Counts_a_firing_that_names_no_repository_without_naming_one_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Owner: "acme"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", RepositoryName: "skillworks"));

        var grilling = await studio.Skill("grilling");

        // An older Claude Code, or a repository with no origin remote, still fired the skill.
        Assert.Equal(3, grilling.Activations);
        Assert.Empty(grilling.Repositories);
    }

    [Fact]
    public async Task Reports_nothing_when_no_skill_fired()
    {
        using var studio = new StudioHost();

        Assert.Empty(await studio.Skills());
    }

    [Fact]
    public async Task Reports_a_catalogue_skill_that_did_not_fire_in_the_lookback_with_a_zero()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        await studio.Push(
            new SkillActivated("probekit:probe-local", "2026-09-01T09:00:00.000Z"),
            new SkillActivated("probekit:probe-plugin", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("probekit:probe-plugin", "2026-09-14T09:05:00.000Z"));

        var skills = await studio.Skills();

        // probe-local last fired before the lookback, and its zero says its description may have stopped working.
        Assert.Equal(["probekit:probe-local", "probekit:probe-plugin"], skills.Select(skill => skill.Name));
        Assert.Equal([0, 2], skills.Select(skill => skill.Activations));
        Assert.Empty(skills[0].Repositories);
    }

    [Fact]
    public async Task Leaves_the_branch_out_of_the_answer()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"));

        using var response = await studio.AskForSkills("");
        var grilling = (await response.Content.ReadFromJsonAsync<JsonElement>()).GetProperty("skills")[0];

        // No telemetry event carries a branch, so a field for one would stay empty for good.
        Assert.Equal("grilling", grilling.GetProperty("name").GetString());
        Assert.False(grilling.TryGetProperty("branches", out _));
    }
}
