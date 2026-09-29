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
    string? AllowedBy);
