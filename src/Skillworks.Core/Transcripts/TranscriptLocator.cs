using Microsoft.Extensions.Options;

namespace Skillworks.Core.Transcripts;

/// <summary>Where the transcripts are, and whether anything is actually there.</summary>
/// <param name="Path">The resolved absolute path.</param>
/// <param name="Exists">False means Studio has nothing to read, which explains an empty screen.</param>
public sealed record TranscriptLocation(string Path, bool Exists);

/// <summary>Finds the session files. Configuration may override the folder; nothing has to.</summary>
public sealed class TranscriptLocator(IOptions<TranscriptOptions> options)
{
    public TranscriptLocation Locate()
    {
        var path = Folder();
        return new TranscriptLocation(path, Directory.Exists(path));
    }

    /// <summary>Every transcript under the folder, including subagent sidechains.</summary>
    public IReadOnlyList<string> Transcripts()
    {
        var location = Locate();

        return location.Exists
            ? [.. Directory.EnumerateFiles(location.Path, "*.jsonl", SearchOption.AllDirectories).Order()]
            : [];
    }

    private string Folder() => string.IsNullOrWhiteSpace(options.Value.Path)
        ? System.IO.Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".claude",
            "projects")
        : System.IO.Path.GetFullPath(options.Value.Path);
}
