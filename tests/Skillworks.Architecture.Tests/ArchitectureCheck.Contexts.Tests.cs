using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void Contexts_that_claim_paths_of_their_own_are_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write("tools/Check/Timer.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_path_two_contexts_claim_is_a_breach()
    {
        using var tree = new RulesTree().SetContext("check", "tools/Check/CONTEXT.md", slices: false, "src");

        Assert.Equal([("contexts", "src")], tree.Breaches());
    }

    [Fact]
    public void A_path_inside_another_contexts_path_is_a_breach()
    {
        using var tree = new RulesTree().SetContext("check", "tools/Check/CONTEXT.md", slices: false, "src/App");

        Assert.Equal([("contexts", "src/App")], tree.Breaches());
    }

    [Fact]
    public void A_breach_over_one_path_names_both_contexts()
    {
        using var tree = new RulesTree().SetContext("check", "tools/Check/CONTEXT.md", slices: false, "src/App");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("`app`", breach.Message);
        Assert.Contains("`check`", breach.Message);
    }

    [Fact]
    public void A_path_that_only_starts_with_another_path_is_not_a_breach()
    {
        using var tree = new RulesTree().SetContext("check", "tools/Check/CONTEXT.md", slices: false, "srcery");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_glossary_that_is_not_there_is_a_breach()
    {
        using var tree = new RulesTree().SetContext("check", "tools/Check/WORDS.md", slices: false, "tools/Check");

        Assert.Equal([("contexts", "tools/Check/WORDS.md")], tree.Breaches());
    }

    [Fact]
    public void One_context_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .RemoveContext("check")
            .Set(WordsFile, "banned-words", "{app: [Widget]}")
            .Write("src/App/Clock.cs");

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("glossary", "    slices: true\n    code:\n      - src")]
    [InlineData("slices", "    glossary: CONTEXT.md\n    code:\n      - src")]
    [InlineData("code", "    glossary: CONTEXT.md\n    slices: true")]
    public void A_context_that_lacks_a_field_is_a_breach_that_names_it(string field, string fields)
    {
        using var tree = new RulesTree().Write(
            ContextMapFile,
            $"# Context Map\n\n```yaml\ncontexts:\n  app:\n{fields}\n```\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("rules-file", ContextMapFile), (breach.Rule, breach.Path));
        Assert.Contains($"`{field}`", breach.Message);
        Assert.Contains("`app`", breach.Message);
    }

    [Fact]
    public void A_map_that_lacks_the_contexts_key_is_a_breach_that_names_it()
    {
        using var tree = new RulesTree().Write(ContextMapFile, "# Context Map\n\n```yaml\nareas: []\n```\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("rules-file", ContextMapFile), (breach.Rule, breach.Path));
        Assert.Contains("`contexts`", breach.Message);
    }

    [Theory]
    [InlineData("contexts: [app]")]
    [InlineData("contexts: app")]
    [InlineData("contexts:\n  app: CONTEXT.md")]
    public void A_contexts_setting_of_the_wrong_shape_is_a_breach(string yaml)
    {
        using var tree = new RulesTree().Write(ContextMapFile, $"# Context Map\n\n```yaml\n{yaml}\n```\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("rules-file", ContextMapFile), (breach.Rule, breach.Path));
        Assert.Contains("`contexts`", breach.Message);
    }
}
