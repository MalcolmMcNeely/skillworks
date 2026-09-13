namespace Skillworks.Core.Transcripts;

/// <summary>Where the session files are. The default is right on an ordinary machine.</summary>
public sealed class TranscriptOptions
{
    public const string SectionName = "Transcripts";

    /// <summary>
    /// Claude Code writes every session to <c>~/.claude/projects/&lt;slugged-cwd&gt;/&lt;session&gt;.jsonl</c>.
    /// Empty means that folder, so nothing has to be configured to read a real machine.
    /// </summary>
    public string Path { get; set; } = "";
}
