namespace Skillworks.Core.Transcripts;

/// <summary>
/// Names the repository a session ran in. A transcript records the working directory, which is
/// often a folder inside the repository rather than its root, so the leaf of that path is the wrong
/// answer: a session started in <c>skillworks\src\Skillworks.Studio.Web</c> belongs to skillworks.
/// The answer is cached, because a history holds far more activations than distinct folders.
/// </summary>
public sealed class RepositoryNames
{
    private readonly Dictionary<string, string?> _known = new(StringComparer.OrdinalIgnoreCase);

    public string? Of(string? workingDirectory)
    {
        if (string.IsNullOrWhiteSpace(workingDirectory))
        {
            return null;
        }

        lock (_known)
        {
            if (!_known.TryGetValue(workingDirectory, out var name))
            {
                name = Resolve(workingDirectory);
                _known[workingDirectory] = name;
            }

            return name;
        }
    }

    private static string? Resolve(string workingDirectory)
    {
        for (var folder = Open(workingDirectory); folder is not null; folder = folder.Parent)
        {
            var git = Path.Combine(folder.FullName, ".git");

            // A worktree and a submodule write .git as a file, not a folder.
            if (Directory.Exists(git) || File.Exists(git))
            {
                return folder.Name;
            }
        }

        // The folder has been deleted, or was never in a repository. Its own name is the best left.
        return Leaf(workingDirectory);
    }

    private static DirectoryInfo? Open(string path)
    {
        try
        {
            var folder = new DirectoryInfo(path);
            return folder.Exists ? folder : null;
        }
        catch (Exception unusable) when (unusable is ArgumentException or PathTooLongException)
        {
            return null;
        }
    }

    /// <summary>
    /// Split by hand rather than with Path, because a Windows transcript read on Linux still has to
    /// yield "alpha" from "C:\Projects\alpha".
    /// </summary>
    private static string? Leaf(string path) =>
        path.TrimEnd('\\', '/').Split('\\', '/') is [.., var leaf] && leaf.Length > 0 ? leaf : null;
}
