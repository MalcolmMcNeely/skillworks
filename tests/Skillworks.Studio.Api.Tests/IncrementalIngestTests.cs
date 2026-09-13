using System.Text.Json;

namespace Skillworks.Studio.Api.Tests;

public sealed class IncrementalIngestTests
{
    private const string Project = "C--Projects-delta";
    private const string Session = "0a9f1c2e-0000-4000-8000-000000000004.jsonl";

    [Fact]
    public async Task Picks_up_a_transcript_that_grew_without_counting_what_it_already_read()
    {
        var folder = Directory.CreateTempSubdirectory("skillworks-growing");

        try
        {
            var transcript = Plant(folder);
            using var studio = new Studio(folder.FullName);

            Assert.Equal(1, await Activations(studio, "implement"));

            await File.AppendAllTextAsync(transcript, Appendix());
            await studio.IngestAgain();

            Assert.Equal(1, await Activations(studio, "implement"));
            Assert.Equal(1, await Activations(studio, "code-review"));
        }
        finally
        {
            folder.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Reads_only_the_bytes_that_arrived_since_the_last_pass()
    {
        var folder = Directory.CreateTempSubdirectory("skillworks-growing");

        try
        {
            var transcript = Plant(folder);
            using var studio = new Studio(folder.FullName);

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

            Assert.Equal(0, await Activations(studio, "tampering"));
            Assert.Equal(1, await Activations(studio, "code-review"));
        }
        finally
        {
            folder.Delete(recursive: true);
        }
    }

    /// <summary>Puts the first half of the fixture where a locator will find it.</summary>
    private static string Plant(DirectoryInfo folder)
    {
        var project = folder.CreateSubdirectory(Project);
        var transcript = Path.Combine(project.FullName, Session);

        File.Copy(Path.Combine(Studio.Fixture("growing"), Project, Session), transcript);

        return transcript;
    }

    /// <summary>The second half, held back so a test can make the file grow.</summary>
    private static string Appendix() =>
        File.ReadAllText(Path.Combine(Studio.Fixture("growing"), "appendix.jsonl.part"));

    private static async Task<int> Activations(Studio studio, string skill)
    {
        var skills = await studio.GetSkills();

        return skills.EnumerateArray()
            .Where(row => row.GetProperty("name").GetString() == skill)
            .Select(row => row.GetProperty("activations").GetInt32())
            .SingleOrDefault();
    }
}
