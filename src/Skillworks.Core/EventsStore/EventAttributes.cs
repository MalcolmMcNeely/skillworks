namespace Skillworks.Core.EventsStore;

// Spelled as Claude Code sends them, on every event.
public static class EventAttributes
{
    public const string Skill = "skill.name";

    public const string Owner = "vcs.owner.name";

    public const string RepositoryName = "vcs.repository.name";

    // Loki gives OTLP attributes with their dots turned into underscores.
    internal static string LabelOf(string attribute) => attribute.Replace('.', '_');

    // An event missing either half has no Repository, or a half-known one would read as a real repository.
    internal static string? RepositoryOf(string? owner, string? name) =>
        owner is { Length: > 0 } && name is { Length: > 0 } ? $"{owner}/{name}" : null;

    // Split at the last slash, as an owner can be a group path and a repository name holds no slash.
    internal static (string Owner, string Name) OwnerAndName(string repository)
    {
        var cut = repository.LastIndexOf('/');

        return (cut < 0 ? "" : repository[..cut], repository[(cut + 1)..]);
    }
}
