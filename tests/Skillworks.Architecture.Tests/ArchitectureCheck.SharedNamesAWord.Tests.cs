namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_folder_in_Shared_that_names_no_glossary_word_is_a_breach()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Health")
            .Project("src/App")
            .Write("src/App/Shared/Plumbing/Pipe.cs");

        Assert.Equal([("shared-names-a-word", "src/App/Shared/Plumbing")], tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_in_Shared_that_names_a_glossary_word_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Health")
            .Project("src/App")
            .Write("src/App/Shared/Health/Lamp.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_named_for_a_two_word_headword_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Events store")
            .Project("src/App")
            .Write("src/App/Shared/EventsStore/Reader.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_that_only_holds_a_glossary_word_is_a_breach()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Health")
            .Project("src/App")
            .Write("src/App/Shared/HealthReport/Report.cs");

        Assert.Equal([("shared-names-a-word", "src/App/Shared/HealthReport")], tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_in_the_front_end_Shared_is_judged_by_the_same_words()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Events store")
            .FrontEnd("web")
            .Write("web/src/shared/events-store/reader.ts")
            .Write("web/src/shared/plumbing/pipe.ts");

        Assert.Equal([("shared-names-a-word", "web/src/shared/plumbing")], tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_file_directly_in_Shared_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Shared/Pipe.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_beneath_a_folder_in_Shared_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Health")
            .Project("src/App")
            .Write("src/App/Shared/Health/Lamps/Lamp.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_in_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Plumbing/Pipe.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void The_glossary_is_the_one_the_context_map_names_for_that_context()
    {
        using var tree = new RulesTree()
            .Glossary("app", "Health")
            .Glossary("check", "Rule")
            .Project("src/App")
            .Write("src/App/Shared/Rule/Line.cs")
            .Project("tools/Check")
            .Write("tools/Check/Shared/Health/Lamp.cs");

        Assert.Equal(
            [
                ("shared-names-a-word", "src/App/Shared/Rule"),
                ("shared-names-a-word", "tools/Check/Shared/Health"),
            ],
            tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_no_context_claims_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("lib/App")
            .Write("lib/App/Shared/Plumbing/Pipe.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_shared_names_a_word_breach_names_the_folder_the_glossary_and_what_to_do()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Shared/Plumbing/Pipe.cs");

        var breach = Assert.Single(tree.Check("shared-names-a-word").Breaches);

        Assert.Contains("`Plumbing`", breach.Message);
        Assert.Contains("`CONTEXT.md`", breach.Message);
        Assert.Contains("Rename", breach.Message);
    }

    [Fact]
    public void The_shared_names_a_word_check_is_not_in_the_run()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Shared/Plumbing/Pipe.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_glossary_written_with_windows_line_endings_is_read_the_same()
    {
        using var tree = new RulesTree()
            .Write("CONTEXT.md", "# Glossary\r\n\r\n**Events store**:\r\nWhat this context means by it.\r\n")
            .Project("src/App")
            .Write("src/App/Shared/EventsStore/Reader.cs");

        Assert.Empty(tree.Breaches("shared-names-a-word"));
    }

    [Fact]
    public void A_folder_whose_glossary_is_missing_is_left_to_the_contexts_rule()
    {
        using var tree = new RulesTree()
            .Delete("CONTEXT.md")
            .Project("src/App")
            .Write("src/App/Shared/Plumbing/Pipe.cs");

        Assert.Equal([("contexts", "CONTEXT.md")], tree.Breaches("shared-names-a-word"));
    }
}
