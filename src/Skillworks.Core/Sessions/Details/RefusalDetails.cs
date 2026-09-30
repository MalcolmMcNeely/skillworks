namespace Skillworks.Core.Sessions.Details;

// The same fields a Tool call asks with, so a refused call reads what it wanted to do by the same rule.
public sealed record RefusalDetails(
    string? Tool,
    string? Input,
    long? InputBytes,
    string? Parameters,
    string? Command,
    string? Description,
    string? RefusedBy);
