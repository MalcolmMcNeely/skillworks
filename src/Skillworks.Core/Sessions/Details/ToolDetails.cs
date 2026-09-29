namespace Skillworks.Core.Sessions.Details;

// Input is null where Claude Code kept it back, and InputBytes still says how large it was.
public sealed record ToolDetails(
    string? Tool,
    bool Passed,
    string? Error,
    string? Input,
    long? InputBytes,
    string? Parameters,
    string? Command,
    string? Description,
    long? ResultBytes,
    string? AllowedBy,
    // Without a Span the output and timings are not known, not empty; with one, no output means Claude Code kept it back.
    bool Traced,
    string? Output,
    string? Diff,
    long? WaitedMs,
    long? RanMs);
