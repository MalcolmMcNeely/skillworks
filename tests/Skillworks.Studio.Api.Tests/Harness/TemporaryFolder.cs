namespace Skillworks.Studio.Api.Tests.Harness;

public sealed class TemporaryFolder : IDisposable
{
    private readonly DirectoryInfo _folder = Directory.CreateTempSubdirectory("skillworks-test");

    public string Path => _folder.FullName;

    public string Subfolder(params string[] parts) =>
        Directory.CreateDirectory(System.IO.Path.Combine([Path, .. parts])).FullName;

    public void Dispose() => _folder.Delete(recursive: true);
}
