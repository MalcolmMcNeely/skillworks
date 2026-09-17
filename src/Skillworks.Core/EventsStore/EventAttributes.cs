namespace Skillworks.Core.EventsStore;

// Spelled as Claude Code sends them, on every event.
public static class EventAttributes
{
    public const string Skill = "skill.name";

    public const string Owner = "vcs.owner.name";

    public const string RepositoryName = "vcs.repository.name";

    public const string Session = "session.id";

    // The signed-in address, on every event and with no switch of its own to leave it off.
    public const string Person = "user.email";

    public const string Prompt = "prompt";

    public const string Response = "response";

    public const string QuerySource = "query_source";

    public const string ToolInput = "tool_input";

    public const string PromptLength = "prompt_length";

    public const string ResponseLength = "response_length";

    // Claude Code writes this in place of the words when the prompt and response switches are off.
    public const string Withheld = "<REDACTED>";

    // Sent in place of any skill from a plugin outside Anthropic's marketplaces, so it names no one skill.
    public const string Unnamed = "third-party";

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
