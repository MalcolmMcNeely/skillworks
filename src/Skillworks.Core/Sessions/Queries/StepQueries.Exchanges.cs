using System.Globalization;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.Steps;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private static IReadOnlyList<Exchange> Said(IReadOnlyList<Drawn> drawn)
    {
        var opened = new List<Underway>();

        foreach (var (line, step) in drawn)
        {
            if (step.Kind == StepKind.Prompt)
            {
                opened.Add(new Underway(opened.Count, line));

                continue;
            }

            // Anything before the first Prompt belongs to no Exchange, as nobody had asked for it yet.
            if (opened.Count == 0)
            {
                continue;
            }

            opened[^1].Took(line, step.Kind);
        }

        return [.. opened.Select(open => open.Closed())];
    }

    private static string? Recorded(EventLine line, string attribute) =>
        line.Attribute(attribute) is { } said && said != EventAttributes.Withheld ? said : null;

    // The length is recorded even where the words are not, so a reader sees how much was said.
    private static int Length(EventLine line, string lengthAttribute, string attribute) =>
        int.TryParse(line.Attribute(lengthAttribute), NumberStyles.Integer, CultureInfo.InvariantCulture, out var length)
            ? length
            : Recorded(line, attribute)?.Length ?? 0;

    // No figure of an Exchange is known until its last event has arrived, so they gather here first.
    private sealed class Underway(int index, EventLine prompt)
    {
        private readonly DateTimeOffset _at = prompt.At;
        private readonly string? _prompt = Recorded(prompt, EventAttributes.Prompt);
        private readonly int _promptLength = Length(prompt, EventAttributes.PromptLength, EventAttributes.Prompt);

        private DateTimeOffset _reachedAt = prompt.At;
        private DateTimeOffset? _answeredAt;
        private string? _answer;
        private int _answerLength;
        private int _turns;
        private int _toolCalls;
        private decimal _cost;

        public void Took(EventLine line, StepKind kind)
        {
            _reachedAt = line.At;

            switch (kind)
            {
                case StepKind.Turn:
                    _turns++;
                    _cost += Number(line, CostAttribute);

                    break;

                case StepKind.Tool:
                    _toolCalls++;

                    break;

                case StepKind.Answer:
                    _answeredAt = line.At;
                    _answer = Recorded(line, EventAttributes.Response);
                    _answerLength = Length(line, EventAttributes.ResponseLength, EventAttributes.Response);

                    break;
            }
        }

        public Exchange Closed() =>
            new(
                index,
                _at,
                (long)((_answeredAt ?? _reachedAt) - _at).TotalMilliseconds,
                _prompt,
                _promptLength,
                _answer,
                _answerLength,
                _turns,
                _toolCalls,
                _cost);
    }
}
