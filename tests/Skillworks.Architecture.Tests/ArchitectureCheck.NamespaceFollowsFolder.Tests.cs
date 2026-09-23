namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    private const string ProjectFile = "<Project Sdk=\"Microsoft.NET.Sdk\" />\n";

    [Fact]
    public void A_namespace_that_is_the_root_namespace_then_the_folder_path_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Clock.cs", "namespace Skillworks.Studio;\n\npublic sealed class Clock;\n")
            .Write("src/Studio/Shared/Ledger/Locators/LedgerLocator.cs", """
                namespace Skillworks.Studio.Shared.Ledger.Locators
                {
                    public sealed class LedgerLocator;
                }
                """)
            .Write("src/Studio/Shared/Ledger/LedgerOptions.cs", """
                namespace Skillworks.Studio.Shared
                {
                    namespace Ledger
                    {
                        public sealed class LedgerOptions;
                    }
                }
                """)
            .Write("tests/Studio.Tests/Skillworks.Studio.Tests.csproj", ProjectFile)
            .Write("tests/Studio.Tests/Shared/Ledger/Locators/LedgerLocator.Tests.cs", """
                namespace Skillworks.Studio.Tests.Shared.Ledger.Locators;

                public sealed class LedgerLocatorTests;
                """);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("namespace Skillworks.Studio;\n\npublic sealed class LedgerLocator;\n")]
    [InlineData("namespace Skillworks.Studio.Locators;\n\npublic sealed class LedgerLocator;\n")]
    [InlineData("namespace Studio.Ledger;\n\npublic sealed class LedgerLocator;\n")]
    [InlineData("public sealed class LedgerLocator;\n")]
    public void A_namespace_that_differs_from_its_folder_path_is_a_breach(string content)
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Shared/Ledger/LedgerLocator.cs", content);

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Ledger/LedgerLocator.cs")],
            tree.Breaches());
    }

    [Fact]
    public void The_nearest_project_above_a_file_names_its_namespace()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Skillworks.Plugins.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Shared/Ledger/PluginLoader.cs", "namespace Skillworks.Plugins.Shared.Ledger;\n\npublic sealed class PluginLoader;\n")
            .Write("src/Studio/Plugins/Shared/Ledger/PluginCache.cs", "namespace Skillworks.Studio.Plugins.Shared.Ledger;\n\npublic sealed class PluginCache;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Plugins/Shared/Ledger/PluginCache.cs")],
            tree.Breaches());
    }

    [Fact]
    public void A_project_that_sets_a_root_namespace_names_its_namespaces_with_it()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFileWithRootNamespace("Acme.Studio"))
            .Write("src/Studio/Clock.cs", "namespace Acme.Studio;\n\npublic sealed class Clock;\n")
            .Write("src/Studio/Shared/Ledger/LedgerLocator.cs", "namespace Acme.Studio.Shared.Ledger;\n\npublic sealed class LedgerLocator;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_project_that_sets_a_root_namespace_breaches_a_namespace_named_for_the_project_file()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFileWithRootNamespace("Acme.Studio"))
            .Write("src/Studio/Shared/Ledger/LedgerLocator.cs", "namespace Skillworks.Studio.Shared.Ledger;\n\npublic sealed class LedgerLocator;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Ledger/LedgerLocator.cs")],
            tree.Breaches());
    }

    [Theory]
    [InlineData(ProjectFile)]
    [InlineData("<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <RootNamespace></RootNamespace>\n  </PropertyGroup>\n</Project>\n")]
    [InlineData("<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <RootNamespace>   </RootNamespace>\n  </PropertyGroup>\n</Project>\n")]
    [InlineData("<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <RootNamespace />\n  </PropertyGroup>\n</Project>\n")]
    public void A_project_with_no_root_namespace_names_its_namespaces_with_the_project_file_name(string projectFile)
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", projectFile)
            .Write("src/Studio/Shared/Ledger/LedgerLocator.cs", "namespace Skillworks.Studio.Shared.Ledger;\n\npublic sealed class LedgerLocator;\n")
            .Write("src/Studio/Shared/Ledger/LedgerOptions.cs", "namespace Ledger;\n\npublic sealed class LedgerOptions;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Ledger/LedgerOptions.cs")],
            tree.Breaches());
    }

    [Fact]
    public void A_file_in_no_project_has_no_namespace_to_follow()
    {
        using var tree = new RulesTree()
            .Write("scripts/Release.cs", "namespace Tools;\n\npublic sealed class Release;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Program_cs_with_top_level_statements_keeps_Program_in_no_namespace()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Program.cs", "WebApplication.Create(args).Run();\n\npublic partial class Program;\n");

        Assert.Empty(tree.Breaches());
    }

    private static string ProjectFileWithRootNamespace(string rootNamespace) => $"""
        <Project Sdk="Microsoft.NET.Sdk">
          <PropertyGroup>
            <RootNamespace>{rootNamespace}</RootNamespace>
          </PropertyGroup>
        </Project>
        """;
}
