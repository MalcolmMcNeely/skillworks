namespace Skillworks.Core.Catalogue;

/// <summary>Where the catalogue is, and whether anything is actually there.</summary>
/// <param name="Path">The resolved absolute path.</param>
/// <param name="Exists">False means the path is configured but the folder is missing.</param>
public sealed record CatalogueLocation(string Path, bool Exists);
