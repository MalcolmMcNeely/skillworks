using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Ingest;

public sealed partial class IngestEndpointsTests
{
    [Fact]
    public async Task Counts_the_transcripts_it_set_out_to_read_and_the_ones_it_has_reached()
    {
        using var studio = new StudioHost(StudioHost.Fixture("malformed"));

        await studio.WaitForIngestPasses(1);
        var status = await studio.Status();

        Assert.Equal(3, status.TranscriptsTotal);
        Assert.Equal(3, status.TranscriptsSeen);
        Assert.Equal(3, status.TranscriptsRead);
    }

    [Fact]
    public async Task Says_nothing_has_been_read_yet_when_it_is_pointed_at_no_transcripts()
    {
        using var machine = new TemporaryFolder();
        using var studio = new StudioHost(machine.Subfolder("no-transcripts"));

        await studio.WaitForIngestPasses(1);
        var status = await studio.Status();

        Assert.Equal(0, status.TranscriptsTotal);
        Assert.Equal(0, status.ActivationsAdded);
    }

    [Fact]
    public async Task Reports_when_the_data_on_screen_was_last_refreshed()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.WaitForIngestPasses(1);
        var refreshed = (await studio.Status()).LastRefreshUtc;

        Assert.NotNull(refreshed);
        Assert.InRange(refreshed.Value, PinnedClock.Today, studio.Now);
    }

    [Fact]
    public async Task Reports_a_finished_pass_as_finished_rather_than_as_still_running()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.WaitForIngestPasses(1);
        var status = await studio.Status();

        Assert.False(status.Running);
        Assert.False(status.LastPassWasFull);
    }

    [Fact]
    public async Task Reads_a_repaired_transcript_again_when_asked_to_read_everything()
    {
        using var machine = new TemporaryFolder();
        var transcript = Plant(machine);

        using var studio = new StudioHost(machine.Subfolder("transcripts"));

        Assert.Equal(1, await studio.ActivationsAdded());

        // The changed bytes were already read, so only a full re-ingest can see this repair.
        await File.WriteAllTextAsync(
            transcript,
            (await File.ReadAllTextAsync(transcript)).Replace("\"skill\":\"implement\"", "\"skill\":\"repaired\""));

        await studio.IngestAgain();
        Assert.Equal(0, await studio.ActivationsAdded());

        await studio.FullIngest();

        Assert.Equal(1, await studio.ActivationsAdded());
    }

    [Fact]
    public async Task Says_the_pass_that_just_finished_read_everything()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.FullIngest();
        var status = await studio.Status();

        Assert.True(status.LastPassWasFull);
        Assert.False(status.Running);
        Assert.Equal(2, status.CompletedPasses);
    }

    [Fact]
    public async Task Counts_a_skill_once_when_everything_is_read_again()
    {
        using var studio = new StudioHost(StudioHost.Fixture("repeated"));

        await studio.FullIngest();

        // The repeated fixture fires unslop three times.
        Assert.Equal(3, await studio.ActivationsAdded());
    }

    [Fact]
    public async Task Reads_the_other_transcripts_when_one_of_them_holds_a_line_it_cannot_parse()
    {
        using var studio = new StudioHost(StudioHost.Fixture("malformed"));

        // One firing in each: kappa and mu are whole, and lambda has a truncated line above its firing.
        Assert.Equal(3, await studio.ActivationsAdded());
    }

    [Fact]
    public async Task Names_the_file_and_the_line_it_could_not_parse()
    {
        using var studio = new StudioHost(StudioHost.Fixture("malformed"));

        var fault = Assert.Single(await studio.Faults());

        Assert.EndsWith("0a9f1c2e-0000-4000-8000-000000000008.jsonl", fault.Path);
        Assert.Equal(2, fault.Line);
        Assert.NotEmpty(fault.Reason);
        Assert.Equal(1, (await studio.Status()).Faults);
    }

    [Fact]
    public async Task Keeps_counting_a_skipped_line_once_however_many_passes_run()
    {
        using var studio = new StudioHost(StudioHost.Fixture("malformed"));

        await studio.IngestAgain();
        await studio.FullIngest();

        Assert.Equal(1, (await studio.Status()).Faults);
    }

    [Fact]
    public async Task Reads_the_other_transcripts_when_one_of_them_will_not_open()
    {
        using var machine = new TemporaryFolder();
        var transcripts = machine.Subfolder("transcripts");

        foreach (var project in Directory.EnumerateDirectories(StudioHost.Fixture("malformed")))
        {
            CopyInto(project, transcripts);
        }

        var shut = Directory.EnumerateFiles(transcripts, "*.jsonl", SearchOption.AllDirectories)
            .Single(path => path.Contains("kappa"));

        // Windows honours the refusal to share, so one transcript is made unreadable without changing it for good.
        using (new FileStream(shut, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            using var studio = new StudioHost(transcripts);

            // research in mu and unslop in lambda; tdd in kappa is shut.
            Assert.Equal(2, await studio.ActivationsAdded());

            var whole = (await studio.Faults()).Single(fault => fault.Line == 0);
            Assert.Equal(shut, whole.Path);
        }
    }

    [Fact]
    public async Task Reads_a_transcript_that_would_not_open_once_it_opens_again()
    {
        using var machine = new TemporaryFolder();
        var transcripts = machine.Subfolder("transcripts");
        CopyInto(Path.Combine(StudioHost.Fixture("malformed"), "C--Projects-kappa"), transcripts);

        var shut = Directory.EnumerateFiles(transcripts, "*.jsonl", SearchOption.AllDirectories).Single();

        // Closed by hand halfway through, and again on the way out so a failed assertion leaves no folder locked.
        using var handle = new FileStream(shut, FileMode.Open, FileAccess.Read, FileShare.None);

        using var studio = new StudioHost(transcripts);

        Assert.Equal(0, await studio.ActivationsAdded());
        Assert.Single(await studio.Faults());

        handle.Dispose();
        await studio.IngestAgain();

        Assert.Equal(1, await studio.ActivationsAdded());
        Assert.Empty(await studio.Faults());
    }

    [Fact]
    public async Task Keeps_the_line_it_skipped_when_a_transcript_that_would_not_open_opens_again()
    {
        using var machine = new TemporaryFolder();
        var transcripts = machine.Subfolder("transcripts");
        var transcript = Path.Combine(
            machine.Subfolder("transcripts", "C--Projects-lambda"),
            "0a9f1c2e-0000-4000-8000-000000000008.jsonl");

        var lines = await File.ReadAllLinesAsync(Path.Combine(
            StudioHost.Fixture("malformed"),
            "C--Projects-lambda",
            "0a9f1c2e-0000-4000-8000-000000000008.jsonl"));

        // The good line and the truncated one below it. The rest is held back.
        await File.WriteAllLinesAsync(transcript, lines[..2]);

        using var studio = new StudioHost(transcripts);

        Assert.Equal(2, (await studio.Faults()).Single().Line);

        await File.AppendAllLinesAsync(transcript, lines[2..]);

        using (new FileStream(transcript, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            await studio.IngestAgain();
            Assert.Equal(2, (await studio.Status()).Faults);
        }

        await studio.IngestAgain();

        Assert.Equal(1, await studio.ActivationsAdded());

        // Reopening clears only the "would not open" fault; the unparsed line is never re-read, so it stays.
        Assert.Equal(2, (await studio.Faults()).Single().Line);
    }

    [Fact]
    public async Task Reports_a_pass_that_has_been_asked_for_as_running_before_it_starts()
    {
        using var machine = new TemporaryFolder();
        var project = machine.Subfolder("transcripts", "C--Projects-many");
        var source = Path.Combine(
            StudioHost.Fixture("repeated"),
            "C--Projects-beta",
            "0a9f1c2e-0000-4000-8000-000000000002.jsonl");

        // Enough files that a pass cannot finish between the request being queued and the reply being written.
        for (var session = 0; session < 200; session++)
        {
            File.Copy(source, Path.Combine(project, $"0a9f1c2e-0000-4000-8000-{session:D12}.jsonl"));
        }

        using var studio = new StudioHost(machine.Subfolder("transcripts"));

        // Reporting this as idle is what lets a developer click a 678 MB re-read a second time.
        Assert.True((await studio.Ask("/api/ingest/full")).Running);
    }

    [Fact]
    public async Task Picks_up_a_session_written_while_it_is_running_without_being_asked()
    {
        using var machine = new TemporaryFolder();
        var transcripts = machine.Subfolder("transcripts");

        using var studio = new StudioHost(transcripts, sweepSeconds: 1);
        await studio.WaitForIngestPasses(1);

        CopyInto(Path.Combine(StudioHost.Fixture("malformed"), "C--Projects-mu"), transcripts);

        await studio.WaitForActivationsAdded();
    }

    private static string Plant(TemporaryFolder machine)
    {
        const string Project = "C--Projects-delta";
        const string Session = "0a9f1c2e-0000-4000-8000-000000000004.jsonl";

        var transcript = Path.Combine(machine.Subfolder("transcripts", Project), Session);
        File.Copy(Path.Combine(StudioHost.Fixture("growing"), Project, Session), transcript);

        return transcript;
    }

    private static void CopyInto(string project, string transcripts)
    {
        var landing = Directory.CreateDirectory(
            Path.Combine(transcripts, new DirectoryInfo(project).Name));

        foreach (var session in Directory.EnumerateFiles(project, "*.jsonl"))
        {
            File.Copy(session, Path.Combine(landing.FullName, Path.GetFileName(session)));
        }
    }
}
