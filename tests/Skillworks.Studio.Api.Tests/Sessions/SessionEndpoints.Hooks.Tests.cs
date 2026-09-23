using Skillworks.Core.Sessions;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // The Loki tests below push HookRecord.Scope, so this is what ties the reader's filter to the script.
    [Fact]
    public async Task Pushes_hook_records_under_the_scope_the_session_watch_hook_writes()
    {
        var script = await File.ReadAllTextAsync(Path.Combine(RepositoryRoot(), "scripts", "session-watch.mjs"));

        Assert.Contains($"scope: {{ name: \"{HookRecord.Scope}\" }}", script, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Keeps_a_sessions_start_and_length_when_hook_records_sit_around_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            HookRecord.Started(Morning, At(Yesterday, "08:59:58.000")),
            HookRecord.Loaded(Morning, At(Yesterday, "08:59:59.000")),
            HookRecord.Loaded(Morning, At(Yesterday, "09:30:00.000"), "compact"));

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")));

        var row = Assert.Single(await studio.SessionsIn());
        var run = (await studio.StepAnswer(Morning)).Run;

        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), row.StartedUtc);
        Assert.Equal((long)TimeSpan.FromMinutes(1).TotalMilliseconds, row.LengthMs);
        Assert.NotNull(run);
        Assert.Equal(row.StartedUtc, run.StartedUtc);
        Assert.Equal(row.LengthMs, run.LengthMs);
    }

    [Fact]
    public async Task Leaves_a_finished_session_unmarked_when_a_compaction_loads_its_rules_again()
    {
        using var studio = new StudioHost();

        var lastEvent = Now - RunningWindow.Length - TimeSpan.FromMinutes(1);

        await studio.Push(
            SessionEvent.Titled(Morning, Stamped(lastEvent - TimeSpan.FromMinutes(10)), "The finished run"),
            new SessionEvent(Morning, "tool_result", Stamped(lastEvent)));

        await studio.Push(
            HookRecord.Started(Morning, Stamped(Now - TimeSpan.FromMinutes(1)), "compact"),
            HookRecord.Loaded(Morning, Stamped(Now - TimeSpan.FromMinutes(1)), "compact"));

        Assert.False(Assert.Single(await studio.SessionsIn()).Running);
        Assert.False((await studio.StepAnswer(Morning)).Run?.Running);
    }

    [Fact]
    public async Task Leaves_hook_records_out_of_the_vote_on_where_a_session_ran()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build") with
            {
                Owner = "acme",
                RepositoryName = "xi",
            });

        HookRecord Elsewhere(HookRecord record) => record with { Owner = "acme", RepositoryName = "hooks" };

        await studio.Push(
            Elsewhere(HookRecord.Started(Morning, At(Yesterday, "08:59:58.000"))),
            Elsewhere(HookRecord.Loaded(Morning, At(Yesterday, "08:59:59.000"))),
            Elsewhere(HookRecord.Loaded(Morning, At(Yesterday, "09:00:30.000"), "path_glob_match")),
            HookRecord.Loaded(Morning, At(Yesterday, "09:00:40.000"), "nested_traversal"));

        Assert.Equal("acme/xi", Assert.Single(await studio.SessionsIn()).Repository);
        Assert.Equal("acme/xi", (await studio.StepAnswer(Morning)).Run?.Repository);
    }

    [Fact]
    public async Task Lists_no_session_for_hook_records_alone()
    {
        using var studio = new StudioHost();

        await studio.Push(
            HookRecord.Started(Afternoon, At(Yesterday, "14:00:00.000")),
            HookRecord.Loaded(Afternoon, At(Yesterday, "14:00:01.000")));

        Assert.Empty(await studio.SessionsIn());
    }

    [Fact]
    public async Task Draws_no_step_for_a_hook_record()
    {
        using var studio = new StudioHost();

        await studio.Push(
            HookRecord.Started(Morning, At(Yesterday, "08:59:58.000")),
            HookRecord.Loaded(Morning, At(Yesterday, "08:59:59.000")),
            HookRecord.Loaded(Morning, At(Yesterday, "09:00:15.000"), "compact"));

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:20.000"), "Bash", 4_000));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal(["prompt", "tool"], steps.Select(step => step.Kind));
    }

    private static string RepositoryRoot()
    {
        var folder = new DirectoryInfo(AppContext.BaseDirectory);
        while (folder is not null && !File.Exists(Path.Combine(folder.FullName, "Skillworks.slnx")))
            folder = folder.Parent;

        return folder?.FullName ?? throw new InvalidOperationException(
            $"No folder above {AppContext.BaseDirectory} holds Skillworks.slnx.");
    }
}
