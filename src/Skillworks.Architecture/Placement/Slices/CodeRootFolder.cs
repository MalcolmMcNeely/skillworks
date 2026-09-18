namespace Skillworks.Architecture.Placement.Slices;

internal sealed record CodeRootFolder(CodeRoot Root, string Folder, int Level)
{
    public string Name => Path.GetFileName(Folder);

    public string ParentName => Path.GetFileName(SourceTree.FolderOf(Folder));
}
