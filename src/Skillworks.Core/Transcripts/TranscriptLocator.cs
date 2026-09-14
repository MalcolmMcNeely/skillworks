using Microsoft.Extensions.Options;

namespace Skillworks.Core.Transcripts;

public sealed class TranscriptLocator(IOptions<TranscriptOptions> options)
{
    public TranscriptLocation Locate()
    {
        var path = Folder();
        return new TranscriptLocation(path, Directory.Exists(path));
    }

    // Every subfolder too, so subagent sidechains are read along with their sessions.
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
