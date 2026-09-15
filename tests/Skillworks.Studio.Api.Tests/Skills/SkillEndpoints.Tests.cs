using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Reports_a_skill_that_fired_once_with_the_repository_and_branch_it_fired_in()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var grilling = await studio.Skill("grilling");

        Assert.Equal(1, grilling.Activations);
        Assert.Equal(["alpha"], grilling.Repositories);
        Assert.Equal(["main"], grilling.Branches);
    }

    [Fact]
    public async Task Reads_the_rest_of_a_transcript_that_holds_a_line_it_cannot_parse()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        // The ordinary fixture carries one truncated line. One bad line must not cost the file.
        Assert.Equal(1, await studio.ActivationsOf("grilling"));
    }

    [Fact]
    public async Task Counts_every_firing_in_a_session_as_its_own_activation()
    {
        using var studio = new StudioHost(StudioHost.Fixture("repeated"));

        Assert.Equal(3, await studio.ActivationsOf("unslop"));
    }

    [Fact]
    public async Task Reports_nothing_for_a_session_in_which_no_skill_fired()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        Assert.Empty(await studio.Skills());
    }

    [Fact]
    public async Task Reports_a_catalogue_skill_that_has_never_fired_with_no_activations()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), StudioHost.Catalogue());

        var never = await studio.Skill("probekit:probe-local");

        Assert.Equal(0, never.Activations);
        Assert.Empty(never.Repositories);
    }

    [Fact]
    public async Task Reports_a_catalogue_skill_that_has_fired_once_only()
    {
        using var studio = new StudioHost(StudioHost.Fixture("catalogue"), StudioHost.Catalogue());

        var skills = await studio.Skills();

        Assert.Equal(
            ["probekit:probe-local", "probekit:probe-plugin"],
            skills.Select(skill => skill.Name));
        Assert.Equal(2, await studio.ActivationsOf("probekit:probe-plugin"));
    }

    [Fact]
    public async Task Names_the_repository_a_session_ran_in_when_it_started_in_a_subfolder()
    {
        using var machine = new TemporaryFolder();

        // Started two folders down, where the working directory's leaf would answer "web" instead of "omega".
        machine.Subfolder("omega", ".git");
        var startedIn = machine.Subfolder("omega", "src", "web");

        var transcripts = machine.Subfolder("transcripts", "C--Projects-omega-src-web");
        var template = await File.ReadAllTextAsync(
            Path.Combine(StudioHost.Fixture("in-a-subfolder"), "template.jsonl.part"));

        await File.WriteAllTextAsync(
            Path.Combine(transcripts, "0a9f1c2e-0000-4000-8000-000000000006.jsonl"),
            template.Replace("__CWD__", startedIn.Replace("\\", "\\\\")));

        using var studio = new StudioHost(machine.Subfolder("transcripts"));

        Assert.Equal(["omega"], (await studio.Skill("comment-sweep")).Repositories);
    }
}
