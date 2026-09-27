namespace Skillworks.Core.Sessions.Exchanges;

// Withheld words come back null with their true length beside them, so nothing reads as empty.
public sealed record Exchange(
    int Index,
    DateTimeOffset AtUtc,
    long LengthMs,
    string? Prompt,
    int PromptLength,
    string? Answer,
    int AnswerLength,
    int Turns,
    int ToolCalls,
    decimal Cost,
    // A part of Cost and never an addition to it. Null until a Span has named the agent behind each Turn.
    IReadOnlyList<SubagentCost>? Subagents);
