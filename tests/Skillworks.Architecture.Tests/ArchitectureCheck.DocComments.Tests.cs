using System.Text.RegularExpressions;
using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Theory]
    [InlineData("namespace App;\n\n/// <summary>Tells the time.</summary>\npublic sealed class Clock;\n")]
    [InlineData("namespace App;\n\n/** <summary>Tells the time.</summary> */\npublic sealed class Clock;\n")]
    public void A_csharp_doc_comment_is_a_breach(string content)
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", content);

        Assert.Equal([("doc-comments", "src/App/Clock.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("web/src/format.ts")]
    [InlineData("web/src/Clock.tsx")]
    public void A_typescript_doc_block_is_a_breach(string file)
    {
        using var tree = new RulesTree()
            .Write(file, """
                /**
                 * Formats a moment.
                 */
                export const format = (moment: Date) => moment.toISOString();
                """);

        Assert.Equal([("doc-comments", file)], tree.Breaches());
    }

    [Fact]
    public void A_file_is_one_breach_that_names_the_line_of_each_doc_comment()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", """
                namespace App;

                /// <summary>
                /// Tells the time.
                /// </summary>
                public sealed class Clock
                {
                    /// <summary>Now.</summary>
                    public DateTimeOffset Now => DateTimeOffset.UtcNow;
                }
                """)
            .Write("web/src/format.ts", """
                import { clock } from './clock';

                /**
                 * Formats a moment.
                 */
                export const format = (moment: Date) => moment.toISOString();

                /** Now. */
                export const now = () => clock.now();
                """);

        var breaches = tree.Check().Breaches;

        Assert.Equal(
            [
                ("doc-comments", "src/App/Clock.cs", "lines 3, 8"),
                ("doc-comments", "web/src/format.ts", "lines 3, 8"),
            ],
            breaches.Select(breach => (breach.Rule, breach.Path, LinesIn(breach.Message))));
    }

    [Fact]
    public void Ordinary_comments_and_strings_that_look_like_doc_comments_are_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", """
                namespace App;

                // An ordinary comment.
                /* A block comment. */
                //// A banner made of slashes.
                public sealed class Clock
                {
                    public const string Root = "///";
                }
                """)
            .Write("web/src/format.ts", """
                // An ordinary comment.
                /* A block comment. */
                /**/
                export const tests = [
                  'src/**/*.test.ts',
                  'src/**',
                  `${root}/**`,
                ];
                // A closing mark: */
                """);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_doc_comment_in_a_code_file_is_not_a_breach_when_doc_comments_are_allowed()
    {
        using var tree = new RulesTree()
            .Set(CommentsFile, "doc-comments", "true")
            .Write("src/App/Clock.cs", "/// <summary>Tells the time.</summary>\npublic sealed class Clock;\n")
            .Write("web/src/format.ts", "/** Formats a moment. */\nexport const format = 1;\n")
            .Write("tests/App.Tests/Clock.Tests.cs")
            .Write("tests/App.Tests/Hosts/AppHost.cs", "/// <summary>Hosts the app.</summary>\npublic sealed class AppHost;\n")
            .Write("web/src/format.test.ts")
            .Write("web/src/fakeClock.ts", "/** Stands in for the clock. */\nexport const fakeClock = 1;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_doc_comment_in_a_test_file_is_a_breach_when_doc_comments_are_allowed()
    {
        using var tree = new RulesTree()
            .Set(CommentsFile, "doc-comments", "true")
            .Write("tests/App.Tests/Clock.Tests.cs", "/// <summary>Tells the time.</summary>\npublic sealed class ClockTests;\n")
            .Write("web/src/format.ts")
            .Write("web/src/format.test.ts", "/** Formats a moment. */\nit('formats', () => {});\n")
            .Write("web/src/Clock.tsx")
            .Write("web/src/Clock.test.tsx", "/** Renders the time. */\nit('renders', () => {});\n");

        Assert.Equal(
            [
                ("doc-comments", "tests/App.Tests/Clock.Tests.cs"),
                ("doc-comments", "web/src/Clock.test.tsx"),
                ("doc-comments", "web/src/format.test.ts"),
            ],
            tree.Breaches());
    }

    [Fact]
    public void The_test_files_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(CommentsFile, "doc-comments", "true")
            .Set(PlacementFile, "test-files", "[\"*Spec.cs\"]")
            .Write("tests/App.Tests/ClockSpec.cs", "/// <summary>Tells the time.</summary>\npublic sealed class ClockTests;\n")
            .Write("tests/App.Tests/Clock.Tests.cs", "/// <summary>Tells the time.</summary>\npublic sealed partial class Clock;\n");

        Assert.Equal([("doc-comments", "tests/App.Tests/ClockSpec.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("/** The count. */\nexport const count = 1;\n")]
    [InlineData("export interface Row {\n  count: number;\n  /** Null when idle. */\n  since: Date | null;\n}\n")]
    public void A_block_mark_that_begins_its_line_is_a_breach(string content)
    {
        using var tree = new RulesTree().Write("web/src/row.ts", content);

        Assert.Equal([("doc-comments", "web/src/row.ts")], tree.Breaches());
    }

    [Theory]
    [InlineData("export const banner = ' /** The count. */ ';\n")]
    [InlineData("// Was: /** The count. */\nexport const count = 1;\n")]
    [InlineData("export const count = /** The count. */ 1;\n")]
    [InlineData("export interface Row { count: number; /** Null when idle. */ }\n")]
    public void A_block_mark_that_does_not_begin_its_line_is_not_a_breach(string content)
    {
        using var tree = new RulesTree().Write("web/src/row.ts", content);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("/** @type {number} */ export const count = /** The count. */ 1;\n")]
    [InlineData("/**\n * @type {number}\n */ export const count = /** The count. */ 1;\n")]
    public void A_block_mark_after_the_close_of_a_block_on_its_line_is_not_a_breach(string content)
    {
        using var tree = new RulesTree().Write("web/src/row.ts", content);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("export default /** @type {import('vite').UserConfig} */ ({});\n")]
    [InlineData("/** @type {import('vite').UserConfig} */\nexport default {};\n")]
    [InlineData("/** @vitest-environment jsdom */\nit('renders', () => {});\n")]
    [InlineData("/** @typedef {{ skill: string, count: number }} Row */\nexport {};\n")]
    [InlineData("/**\n * @param {string} moment\n *\n * @returns {Date}\n */\nexport const parse = (moment) => new Date(moment);\n")]
    [InlineData("/** @deprecated Use b instead. */\nexport const a = 1;\n")]
    [InlineData("/** @description The config Vite reads. */\nexport default {};\n")]
    [InlineData("/**\n * @param moment The moment to parse.\n */\nexport const parse = (moment) => new Date(moment);\n")]
    [InlineData("/**\r\n * @param {string} moment\r\n *\r\n */\r\nexport const parse = (moment) => new Date(moment);\r\n")]
    public void A_block_that_holds_only_tags_is_not_a_breach(string content)
    {
        using var tree = new RulesTree().Write("web/src/config.ts", content);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("/**\n * @type {import('vite').UserConfig}\n * The config Vite reads.\n */\nexport default {};\n")]
    [InlineData("/**\n * @deprecated\n * Use b instead.\n */\nexport const a = 1;\n")]
    public void A_block_with_a_line_that_does_not_start_with_a_tag_is_a_breach(string content)
    {
        using var tree = new RulesTree().Write("web/src/config.ts", content);

        Assert.Equal([("doc-comments", "web/src/config.ts")], tree.Breaches());
    }

    private static string LinesIn(string message) => Regex.Match(message, @"lines? [\d, ]*\d").Value;
}
