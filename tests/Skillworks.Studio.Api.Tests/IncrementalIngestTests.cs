namespace Skillworks.Studio.Api.Tests;

public sealed class IncrementalIngestTests
{
    private const string Project = "C--Projects-delta";
    private const string Session = "0a9f1c2e-0000-4000-8000-000000000004.jsonl";

    [Fact]
    public async Task Picks_up_a_transcript_that_grew_without_counting_what_it_already_read()
    {
        using var folder = new TemporaryFolder();
        var transcript = Plant(folder);

        using var studio = new Studio(folder.Path);

        Assert.Equal(1, await studio.ActivationsOf("implement"));

        await File.AppendAllTextAsync(transcript, Appendix());
        await studio.IngestAgain();

        Assert.Equal(1, await studio.ActivationsOf("implement"));
        Assert.Equal(1, await studio.ActivationsOf("code-review"));
    }

    [Fact]
    public async Task Reads_only_the_bytes_that_arrived_since_the_last_pass()
    {
        using var folder = new TemporaryFolder();
        var transcript = Plant(folder);

        using var studio = new Studio(folder.Path);
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

    /// <summary>Puts the first half of the fixture where a locator will find it.</summary>
    private static string Plant(TemporaryFolder folder)
    {
        var transcript = Path.Combine(folder.Subfolder(Project), Session);

        File.Copy(Path.Combine(Studio.Fixture("growing"), Project, Session), transcript);

        return transcript;
    }

    /// <summary>The second half, held back so a test can make the file grow.</summary>
    private static string Appendix() =>
        File.ReadAllText(Path.Combine(Studio.Fixture("growing"), "appendix.jsonl.part"));
}
