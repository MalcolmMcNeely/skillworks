namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record ExchangeRow
{
    public required int Index { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long LengthMs { get; init; }

    public required string? Prompt { get; init; }

    public required int PromptLength { get; init; }

    public required string? Answer { get; init; }

    public required int AnswerLength { get; init; }

    public required int Turns { get; init; }

    public required int ToolCalls { get; init; }

    public required decimal Cost { get; init; }
}
