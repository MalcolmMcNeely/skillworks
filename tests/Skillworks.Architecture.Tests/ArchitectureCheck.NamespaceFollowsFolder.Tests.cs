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
            .Write("src/Studio/Shared/Catalogue/Locators/CatalogueLocator.cs", """
                namespace Skillworks.Studio.Shared.Catalogue.Locators
                {
                    public sealed class CatalogueLocator;
                }
                """)
            .Write("src/Studio/Shared/Catalogue/CatalogueOptions.cs", """
                namespace Skillworks.Studio.Shared
                {
                    namespace Catalogue
                    {
                        public sealed class CatalogueOptions;
                    }
                }
                """)
            .Write("tests/Studio.Tests/Skillworks.Studio.Tests.csproj", ProjectFile)
            .Write("tests/Studio.Tests/Shared/Catalogue/Locators/CatalogueLocator.Tests.cs", """
                namespace Skillworks.Studio.Tests.Shared.Catalogue.Locators;

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
            .Write("src/Studio/Shared/Catalogue/CatalogueLocator.cs", content);

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Catalogue/CatalogueLocator.cs")],
            tree.Breaches());
    }

    [Fact]
    public void The_nearest_project_above_a_file_names_its_namespace()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Skillworks.Plugins.csproj", ProjectFile)
            .Write("src/Studio/Plugins/Shared/Catalogue/PluginLoader.cs", "namespace Skillworks.Plugins.Shared.Catalogue;\n\npublic sealed class PluginLoader;\n")
            .Write("src/Studio/Plugins/Shared/Catalogue/PluginCache.cs", "namespace Skillworks.Studio.Plugins.Shared.Catalogue;\n\npublic sealed class PluginCache;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Plugins/Shared/Catalogue/PluginCache.cs")],
            tree.Breaches());
    }

    [Fact]
    public void A_project_that_sets_a_root_namespace_names_its_namespaces_with_it()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFileWithRootNamespace("Acme.Studio"))
            .Write("src/Studio/Clock.cs", "namespace Acme.Studio;\n\npublic sealed class Clock;\n")
            .Write("src/Studio/Shared/Catalogue/CatalogueLocator.cs", "namespace Acme.Studio.Shared.Catalogue;\n\npublic sealed class CatalogueLocator;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_project_that_sets_a_root_namespace_breaches_a_namespace_named_for_the_project_file()
    {
        using var tree = new RulesTree()
            .Write("src/Studio/Skillworks.Studio.csproj", ProjectFileWithRootNamespace("Acme.Studio"))
            .Write("src/Studio/Shared/Catalogue/CatalogueLocator.cs", "namespace Skillworks.Studio.Shared.Catalogue;\n\npublic sealed class CatalogueLocator;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Catalogue/CatalogueLocator.cs")],
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
            .Write("src/Studio/Shared/Catalogue/CatalogueLocator.cs", "namespace Skillworks.Studio.Shared.Catalogue;\n\npublic sealed class CatalogueLocator;\n")
            .Write("src/Studio/Shared/Catalogue/CatalogueOptions.cs", "namespace Catalogue;\n\npublic sealed class CatalogueOptions;\n");

        Assert.Equal(
            [("namespace-follows-folder", "src/Studio/Shared/Catalogue/CatalogueOptions.cs")],
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
