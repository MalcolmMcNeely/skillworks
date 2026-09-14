using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Ingest;

public sealed partial class IngestEndpointsTests
{
    [Fact]
    public async Task Picks_up_a_transcript_that_grew_without_counting_what_it_already_read()
    {
        using var machine = new TemporaryFolder();
        var transcript = Plant(machine);

        using var studio = new StudioHost(machine.Subfolder("transcripts"));

        Assert.Equal(1, await studio.ActivationsOf("implement"));

        await File.AppendAllTextAsync(transcript, Appendix());
        await studio.IngestAgain();

        Assert.Equal(1, await studio.ActivationsOf("implement"));
        Assert.Equal(1, await studio.ActivationsOf("code-review"));
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

        // Same length, so the stored offset still lands on the same line boundary. A pass that
        // reads the file again would find "tampering"; a pass that seeks past it cannot.
        Assert.Equal(alreadyRead.Length, tampered.Length);

        await File.WriteAllTextAsync(transcript, tampered + Appendix());
        await studio.IngestAgain();

        Assert.Equal(0, await studio.ActivationsOf("tampering"));
        Assert.Equal(1, await studio.ActivationsOf("code-review"));
    }

    private static string Appendix() =>
        File.ReadAllText(Path.Combine(StudioHost.Fixture("growing"), "appendix.jsonl.part"));
}
