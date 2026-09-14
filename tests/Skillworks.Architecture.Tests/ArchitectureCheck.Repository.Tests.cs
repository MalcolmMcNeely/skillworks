namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void The_repository_meets_its_own_rules()
    {
        var result = ArchitectureCheck.Run(RepositoryRoot());

        // A check that scans nothing passes on any tree.
        Assert.NotEqual(0, result.SourceFilesScanned);
        Assert.True(result.Breaches.Count == 0, $"Fix each breach:\n{string.Join('\n', result.Breaches)}");
    }

    [Theory]
    [InlineData(".git/HEAD")]
    [InlineData(".git")]
    public void A_repository_inside_the_root_is_not_scanned(string gitEntry)
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write($".claude/worktrees/agent/{gitEntry}")
            .Write(".claude/worktrees/agent/src/App/utils/Clock.cs");

        var result = tree.Check();

        Assert.Empty(result.Breaches);
        Assert.Equal(1, result.SourceFilesScanned);
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
