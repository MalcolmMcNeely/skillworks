using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Theory]
    [InlineData(PlacementFile)]
    [InlineData(CommentsFile)]
    [InlineData(WordsFile)]
    [InlineData(DeterminismFile)]
    [InlineData(ContextMapFile)]
    public void A_missing_rules_file_is_a_breach(string file)
    {
        using var tree = new RulesTree().Delete(file);

        Assert.Equal([("rules-file", file)], tree.Breaches());
    }

    [Theory]
    [InlineData(PlacementFile)]
    [InlineData(CommentsFile)]
    [InlineData(WordsFile)]
    [InlineData(DeterminismFile)]
    [InlineData(ContextMapFile)]
    public void A_rules_file_with_no_yaml_block_is_a_breach(string file)
    {
        using var tree = new RulesTree().Write(file, "# Rules\n\nThe text for Claude, and no settings.\n");

        Assert.Equal([("rules-file", file)], tree.Breaches());
    }

    [Theory]
    [InlineData(PlacementFile, "slices")]
    [InlineData(PlacementFile, "concerns")]
    [InlineData(PlacementFile, "max-types-per-folder")]
    [InlineData(PlacementFile, "source-files")]
    [InlineData(PlacementFile, "test-files")]
    [InlineData(PlacementFile, "skip-folders")]
    [InlineData(PlacementFile, "banned-folder-names")]
    [InlineData(PlacementFile, "name-map")]
    [InlineData(CommentsFile, "doc-comments")]
    [InlineData(WordsFile, "banned-words")]
    [InlineData(WordsFile, "skip-folders")]
    [InlineData(DeterminismFile, "clock")]
    [InlineData(DeterminismFile, "contexts")]
    public void A_rules_file_that_lacks_a_key_is_a_breach_that_names_the_key(string file, string key)
    {
        using var tree = new RulesTree().Remove(file, key);

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("rules-file", file), (breach.Rule, breach.Path));
        Assert.Contains($"`{key}`", breach.Message);
    }

    [Theory]
    [InlineData(PlacementFile, "slices", "Watch")]
    [InlineData(PlacementFile, "concerns", "{api: api}")]
    [InlineData(PlacementFile, "max-types-per-folder", "many")]
    [InlineData(PlacementFile, "max-types-per-folder", "0")]
    [InlineData(PlacementFile, "skip-folders", "bin")]
    [InlineData(PlacementFile, "name-map", "[Queries]")]
    [InlineData(PlacementFile, "name-map", "{Queries: Queries}")]
    [InlineData(PlacementFile, "name-map", "{\"Que*ries\": Queries}")]
    [InlineData(PlacementFile, "name-map", "{\"*Queries*\": Queries}")]
    [InlineData(CommentsFile, "doc-comments", "sometimes")]
    [InlineData(WordsFile, "banned-words", "Widget")]
    [InlineData(WordsFile, "banned-words", "[Widget]")]
    [InlineData(WordsFile, "banned-words", "{Widget: Gadget}")]
    [InlineData(WordsFile, "skip-folders", "sketches")]
    [InlineData(DeterminismFile, "clock", "[TimeProvider]")]
    [InlineData(DeterminismFile, "contexts", "app")]
    public void A_setting_of_the_wrong_shape_is_a_breach_that_names_the_key(string file, string key, string value)
    {
        using var tree = new RulesTree().Set(file, key, value);

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("rules-file", file), (breach.Rule, breach.Path));
        Assert.Contains($"`{key}`", breach.Message);
    }

    [Theory]
    [InlineData("max-types-per-folder: [10")]
    [InlineData("- a list\n- of names")]
    public void A_yaml_block_that_is_not_a_set_of_keys_is_a_breach(string yaml)
    {
        using var tree = new RulesTree().Write(PlacementFile, $"# Rules\n\n```yaml\n{yaml}\n```\n");

        Assert.Equal([("rules-file", PlacementFile)], tree.Breaches());
    }

    [Fact]
    public void A_rules_file_with_two_yaml_blocks_is_a_breach()
    {
        using var tree = new RulesTree().Write(
            CommentsFile,
            "# Rules\n\n```yaml\ndoc-comments: false\n```\n\nMore text.\n\n```yaml\ndoc-comments: true\n```\n");

        Assert.Equal([("rules-file", CommentsFile)], tree.Breaches());
    }

    [Fact]
    public void Rules_files_that_hold_every_key_are_not_a_breach()
    {
        using var tree = new RulesTree();

        Assert.Empty(tree.Breaches());
    }
}
