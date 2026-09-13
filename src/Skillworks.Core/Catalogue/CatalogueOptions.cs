namespace Skillworks.Core.Catalogue;

/// <summary>Where to look for the catalogue. ADR 0003: the path is configuration, never assumed.</summary>
public sealed class CatalogueOptions
{
    public const string SectionName = "Catalogue";

    /// <summary>Absolute, or relative to the process working directory.</summary>
    public string Path { get; set; } = "plugins";
}
