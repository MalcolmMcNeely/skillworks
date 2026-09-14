namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    private const string ProjectFile = "<Project Sdk=\"Microsoft.NET.Sdk\" />\n";

    [Fact]
    public void A_namespace_that_is_the_project_name_then_the_folder_path_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Clock.cs", "namespace Skillworks.Studio;\n\npublic sealed class Clock;\n")
            .Write("src/Studio/Catalogue/Locators/CatalogueLocator.cs", """
                namespace Skillworks.Studio.Catalogue.Locators
                {
                    public sealed class CatalogueLocator;
                }
                """)
            .Write("src/Studio/Catalogue/CatalogueOptions.cs", """
                namespace Skillworks.Studio
                {
                    namespace Catalogue
                    {
                        public sealed class CatalogueOptions;
                    }
                }
                """)
            .Write("tests/Studio.Tests/Skillworks.Studio.Tests.csproj", ProjectFile)
            .Write("tests/Studio.Tests/Catalogue/Locators/CatalogueLocator.Tests.cs", """
                namespace Skillworks.Studio.Tests.Catalogue.Locators;

                public sealed class CatalogueLocatorTests;
                """);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("namespace Skillworks.Studio;\n\npublic sealed class CatalogueLocator;\n")]
    [InlineData("namespace Skillworks.Studio.Locators;\n\npublic sealed class CatalogueLocator;\n")]
    [InlineData("namespace Studio.Catalogue;\n\npublic sealed class CatalogueLocator;\n")]
    [InlineData("public sealed class CatalogueLocator;\n")]
    public void A_namespace_that_differs_from_its_folder_path_is_a_breach(string content)
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Catalogue/CatalogueLocator.cs", content);

        Assert.Equal([("namespace-follows-folder", "src/Studio/Catalogue/CatalogueLocator.cs")], tree.Breaches());
    }

    [Fact]
    public void The_nearest_project_above_a_file_names_its_namespace()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Skillworks.Plugins.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Loading/PluginLoader.cs", "namespace Skillworks.Plugins.Loading;\n\npublic sealed class PluginLoader;\n")
            .Write("src/Studio/Plugins/Loading/PluginCache.cs", "namespace Skillworks.Studio.Plugins.Loading;\n\npublic sealed class PluginCache;\n");

        Assert.Equal([("namespace-follows-folder", "src/Studio/Plugins/Loading/PluginCache.cs")], tree.Breaches());
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
}
