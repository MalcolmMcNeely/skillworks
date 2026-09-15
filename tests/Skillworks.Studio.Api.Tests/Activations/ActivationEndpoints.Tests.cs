using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    private const string Grilling = "toolu_01EAt7jnkYt1D63phjpVUBqL";

    [Fact]
    public async Task Opens_one_activation_by_the_id_the_list_gave_for_it()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var listed = Assert.Single(await studio.Activations());
        var opened = await studio.Activation(listed.Id);

        Assert.Equal(Grilling, listed.Id);
        Assert.Equal(listed.Id, opened.Id);
        Assert.Equal("grilling", opened.Skill);
    }

    [Fact]
    public async Task Reports_the_arguments_a_skill_was_called_with_as_the_transcript_recorded_them()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var opened = await studio.Activation(Grilling);

        // Read as recorded, so a firing can be judged and a new field never goes unnoticed.
        Assert.Equal(["skill", "args"], opened.Arguments.Select(argument => argument.Name));
        Assert.Equal(["grilling", "the rollout plan"], opened.Arguments.Select(argument => argument.Value));
    }

    [Fact]
    public async Task Reports_the_model_effort_repository_branch_and_moment_of_one_activation()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var opened = await studio.Activation(Grilling);

        Assert.Equal("claude-opus-5", opened.Model);
        Assert.Equal("xhigh", opened.Effort);
        Assert.Equal("alpha", opened.Repository);
        Assert.Equal("main", opened.Branch);
        Assert.Equal("0a9f1c2e-0000-4000-8000-000000000001", opened.SessionId);
        Assert.Equal(DateTimeOffset.Parse("2026-09-02T14:48:23.182Z"), opened.TimestampUtc);
    }

    [Fact]
    public async Task Reports_an_argument_that_was_not_recorded_as_an_absent_argument()
    {
        using var studio = new StudioHost(StudioHost.Fixture("repeated"));

        var opened = await studio.Activation((await studio.Activations()).First().Id);

        // The repeated fixture records only the skill, as a skill Claude picked up on its own does.
        Assert.Equal(["skill"], opened.Arguments.Select(argument => argument.Name));
    }

    [Fact]
    public async Task Lists_the_newest_activation_first()
    {
        using var studio = new StudioHost(StudioHost.Fixture("filtered"));

        var listed = await studio.Activations();

        // Newest first, because a reader opening a firing is nearly always looking for the last one.
        Assert.Equal(
            listed.Select(activation => activation.TimestampUtc).OrderDescending(),
            listed.Select(activation => activation.TimestampUtc));
    }

    [Fact]
    public async Task Narrows_the_list_by_the_date_the_repository_and_the_skill_at_once()
    {
        using var studio = new StudioHost(StudioHost.Fixture("filtered"));

        var listed = await studio.Activations("?from=2026-09-05&to=2026-09-05&repository=xi&skill=grilling");

        var only = Assert.Single(listed);
        Assert.Equal("grilling", only.Skill);
        Assert.Equal("xi", only.Repository);
        Assert.Equal("work", only.Branch);
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

        Assert.Equal("omega", Assert.Single(await studio.Activations("?skill=comment-sweep")).Repository);
    }

    [Fact]
    public async Task Answers_a_filter_that_matches_nothing_with_an_empty_list()
    {
        using var studio = new StudioHost(StudioHost.Fixture("filtered"));

        Assert.Empty(await studio.Activations("?from=2020-01-01&to=2020-01-02"));
    }

    [Fact]
    public async Task Answers_an_activation_it_has_never_read_with_a_not_found()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        using var response = await studio.AskForActivation("toolu_no_such_firing");

        // Missing, not empty: a blank page would read as a firing that happened and carried nothing.
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}
