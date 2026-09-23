using System.Globalization;

namespace Skillworks.Studio.Api.Tests.Shared.Harness;

// As scripts/session-watch.mjs posts it: Claude Code's own shape, under a scope of the hook's own.
public sealed record HookRecord(string Session, string EventName, string HookEventName, string At)
{
    internal const string Scope = "skillworks.session-watch";

    public string? Owner { get; init; }

    public string? RepositoryName { get; init; }

    public string? FilePath { get; init; }

    public string? LoadReason { get; init; }

    public string? Source { get; init; }

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("event.name", EventName),
        ("session.id", Session),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
        ("session_id", Session),
        ("transcript_path", $"C:/Users/ada/.claude/projects/skillworks/{Session}.jsonl"),
        ("cwd", "C:/Projects/skillworks"),
        ("hook_event_name", HookEventName),
        ("file_path", FilePath),
        ("memory_type", FilePath is null ? null : "Project"),
        ("load_reason", LoadReason),
        ("source", Source),
    ];

    internal static HookRecord Loaded(string session, string at, string reason = "session_start") =>
        new(session, "instructions_loaded", "InstructionsLoaded", at)
        {
            FilePath = "C:/Projects/skillworks/CLAUDE.md",
            LoadReason = reason,
        };

    internal static HookRecord Started(string session, string at, string source = "startup") =>
        new(session, "session_start", "SessionStart", at) { Source = source };
}
