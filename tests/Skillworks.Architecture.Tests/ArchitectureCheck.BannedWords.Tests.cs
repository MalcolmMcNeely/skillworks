using System.Text.RegularExpressions;
using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_banned_word_in_a_csharp_file_is_a_breach_that_names_the_word()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", "// The Widget ticks.\npublic sealed class Clock;\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("banned-words", "src/App/Clock.cs"), (breach.Rule, breach.Path));
        Assert.Equal("Widget", WordIn(breach.Message));
    }

    [Theory]
    [InlineData("web/src/clock/format.ts")]
    [InlineData("web/src/clock/Clock.tsx")]
    public void A_banned_word_in_a_front_end_file_is_a_breach(string file)
    {
        using var tree = new RulesTree().Write(file, "export const widget = 1;\n");

        Assert.Equal([("banned-words", file)], tree.Breaches());
    }

    [Fact]
    public void A_banned_word_in_a_test_file_is_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write("tests/App.Tests/Clock.Tests.cs", "// The Widget ticks.\npublic sealed partial class ClockTests;\n");

        Assert.Equal([("banned-words", "tests/App.Tests/Clock.Tests.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("WIDGET")]
    [InlineData("widget")]
    [InlineData("wIdGeT")]
    public void A_banned_word_is_a_breach_in_any_letter_case(string word)
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", $"// The {word} ticks.\npublic sealed class Clock;\n");

        Assert.Equal([("banned-words", "src/App/Clock.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("gadget box")]
    [InlineData("GadgetBox")]
    [InlineData("gadgetBox")]
    [InlineData("gadget_box")]
    [InlineData("gadget-box")]
    [InlineData("GADGET_BOX")]
    public void A_banned_word_is_a_breach_however_its_parts_are_joined(string word)
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", $"// The {word} ticks.\npublic sealed class Clock;\n");

        Assert.Equal([("banned-words", "src/App/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_word_that_only_holds_a_banned_word_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", "// Widgets, a widgeon, a gadget and a box.\npublic sealed class Clock;\n");

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("// Pass the gadget, box and lever.")]
    [InlineData("// The gadget.\n// Box it up.")]
    [InlineData("// A gadget\n// box.")]
    [InlineData("// The gadget  box.")]
    public void Words_a_mark_holds_apart_are_not_one_banned_word(string line)
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", $"{line}\npublic sealed class Clock;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Two_names_that_sit_side_by_side_are_not_one_banned_word()
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", """
            public sealed class Clock
            {
                public (int Gadget, int Box) Pair => (1, 2);
            }
            """);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Two_banned_words_in_one_file_are_two_breaches()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", "// The Widget sits in the gadget box.\npublic sealed class Clock;\n");

        Assert.Equal(
            [("src/App/Clock.cs", "Widget"), ("src/App/Clock.cs", "Gadget box")],
            tree.Check().Breaches.Select(breach => (breach.Path, WordIn(breach.Message))));
    }

    [Fact]
    public void One_banned_word_twice_in_one_file_is_one_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", "// The Widget ticks. The widget tocks.\npublic sealed class Clock;\n");

        Assert.Equal([("banned-words", "src/App/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_banned_word_in_a_skipped_folder_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write("src/App/obj/Clock.g.cs", "// The Widget ticks.\npublic sealed class Clock;\n")
            .Write("web/node_modules/left-pad/index.ts", "export const widget = 1;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_banned_word_in_a_folder_the_words_file_skips_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/sketches/clock/ClockSketch.cs", "// The Widget ticks.\npublic sealed class ClockSketch;\n")
            .Write("src/sketches/clock/clockSketch.ts", "export const widget = 1;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_folder_the_words_file_skips_is_still_judged_on_where_its_code_sits()
    {
        using var tree = new RulesTree()
            .Write("src/sketches/clock/utils/ClockSketch.cs", "// The Widget ticks.\npublic sealed class ClockSketch;\n");

        Assert.Equal([("banned-folder-names", "src/sketches/clock/utils")], tree.Breaches());
    }

    [Fact]
    public void The_skipped_folders_come_from_the_words_file()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "skip-folders", "[drafts]")
            .Write("src/drafts/Clock.cs", "// The Widget ticks.\npublic sealed class Clock;\n")
            .Write("src/sketches/Clock.cs", "// The Widget ticks.\npublic sealed class Clock;\n");

        Assert.Equal([("banned-words", "src/sketches/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void The_banned_words_come_from_the_words_file()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "banned-words", "{app: [Sprocket], check: []}")
            .Write("src/App/Clock.cs", "// A Widget and a Sprocket.\npublic sealed class Clock;\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal("Sprocket", WordIn(breach.Message));
    }

    [Fact]
    public void An_empty_list_of_banned_words_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "banned-words", "{app: [], check: []}")
            .Write("src/App/Clock.cs", "// The Widget sits in the gadget box.\npublic sealed class Clock;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_file_is_judged_by_the_words_of_the_context_that_claims_it()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "banned-words", "{app: [Widget], check: [Sprocket]}")
            .Write("src/App/Clock.cs", "// The Sprocket ticks.\npublic sealed class Clock;\n")
            .Write("tools/Check/Timer.cs", "// The Sprocket ticks.\npublic sealed class Timer;\n");

        Assert.Equal([("banned-words", "tools/Check/Timer.cs")], tree.Breaches());
    }

    [Fact]
    public void A_file_no_context_claims_is_judged_by_no_banned_words()
    {
        using var tree = new RulesTree()
            .Write("elsewhere/Clock.cs", "// The Widget sits in the gadget box.\npublic sealed class Clock;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_context_with_an_empty_list_judges_nothing()
    {
        using var tree = new RulesTree()
            .Write("tools/Check/Timer.cs", "// The Widget sits in the gadget box.\npublic sealed class Timer;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_list_under_a_name_no_context_carries_is_a_breach()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "banned-words", "{app: [Widget], check: [], ghost: [Sprocket]}");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("banned-words", WordsFile), (breach.Rule, breach.Path));
        Assert.Contains("`ghost`", breach.Message);
    }

    [Fact]
    public void A_context_with_no_list_of_its_own_is_a_breach()
    {
        using var tree = new RulesTree()
            .Set(WordsFile, "banned-words", "{app: [Widget]}")
            .Write("tools/Check/Timer.cs", "// The Widget sits in the gadget box.\npublic sealed class Timer;\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("banned-words", WordsFile), (breach.Rule, breach.Path));
        Assert.Contains("`check`", breach.Message);
    }

    [Fact]
    public void A_renamed_context_does_not_quietly_disarm_its_words()
    {
        using var tree = new RulesTree()
            .SetContext("studio", "CONTEXT.md", slices: true, "src", "tests", "web")
            .RemoveContext("app")
            .Write("src/App/Clock.cs", "// The Widget ticks.\npublic sealed class Clock;\n");

        Assert.Equal(
            [("banned-words", WordsFile), ("banned-words", WordsFile)],
            tree.Breaches());
    }

    [Fact]
    public void A_breach_names_the_glossary_of_the_context_that_claims_the_file()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", "// The Widget ticks.\npublic sealed class Clock;\n");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("`CONTEXT.md`", breach.Message);
    }

    private static string WordIn(string message) => Regex.Match(message, "`([^`]+)`").Groups[1].Value;
}
