using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Ingest;

public sealed partial class IngestEndpointsTests
{
    [Fact]
    public async Task Picks_up_a_transcript_that_grew_without_counting_what_it_already_read()
    {
        using var machine = new TemporaryFolder();
        var transcript = Plant(machine);

        using var studio = new StudioHost(machine.Subfolder("transcripts"));

        Assert.Equal(1, await studio.ActivationsAdded());

        await File.AppendAllTextAsync(transcript, Appendix());
        await studio.IngestAgain();

        // code-review from the appendix, and not implement a second time.
        Assert.Equal(1, await studio.ActivationsAdded());
    }

    [Fact]
    public async Task Reads_only_the_bytes_that_arrived_since_the_last_pass()
    {
        using var machine = new TemporaryFolder();
        var transcript = Plant(machine);

        using var studio = new StudioHost(machine.Subfolder("transcripts"));
        await studio.WaitForIngestPasses(1);

        var alreadyRead = await File.ReadAllTextAsync(transcript);
        var tampered = alreadyRead
            .Replace("\"skill\":\"implement\"", "\"skill\":\"tampering\"")
            .Replace("toolu_04EAt7jnkYt1D63phjpVUB01", "toolu_04EAt7jnkYt1D63phjpVUB99");

        // Same length, so the stored offset still lands on a line boundary and only a re-read would find "tampering".
        Assert.Equal(alreadyRead.Length, tampered.Length);

        await File.WriteAllTextAsync(transcript, tampered + Appendix());
        await studio.IngestAgain();

        // code-review from the appendix alone; a re-read would add "tampering" too.
        Assert.Equal(1, await studio.ActivationsAdded());
    }

    private static string Appendix() =>
        File.ReadAllText(Path.Combine(StudioHost.Fixture("growing"), "appendix.jsonl.part"));
}
