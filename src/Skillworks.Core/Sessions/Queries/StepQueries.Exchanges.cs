using System.Globalization;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    public static ExchangesPage Exchanges(OpenedRun opened) => new(opened.Said, BeforeFirstPrompt(opened.Drawn));

    public static ExchangesPage Exchanges(OpenedRun opened, OpenedSpans traced) =>
        traced.Traced ? new(Said(opened.Drawn, traced.Agents), BeforeFirstPrompt(opened.Drawn)) : Exchanges(opened);

    private static decimal BeforeFirstPrompt(IReadOnlyList<DrawnStep> drawn) =>
        drawn.TakeWhile(each => each.Step.Kind != StepKind.Prompt)
            .Where(each => each.Step.Kind == StepKind.Turn)
            .Sum(each => Number(each.Line, CostAttribute));

    // Without the agents, which only a Span names, no Turn can be set apart as a Subagent's.
    private static IReadOnlyList<Exchange> Said(
        IReadOnlyList<DrawnStep> drawn,
        IReadOnlyDictionary<string, string>? agents = null)
    {
        var opened = new List<Underway>();

        foreach (var (line, step) in drawn)
        {
            if (step.Kind == StepKind.Prompt)
            {
                opened.Add(new Underway(opened.Count, line, agents));

                continue;
            }

            // Anything before the first Prompt belongs to no Exchange, as nobody had asked for it yet.
            if (opened.Count == 0)
            {
                continue;
            }

            opened[^1].Took(line, step);
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
    private sealed class Underway(int index, EventLine prompt, IReadOnlyDictionary<string, string>? agents)
    {
        // In the order each Subagent first spent, so the parts of a bar read in the order they ran.
        private readonly List<SubagentCost> _subagents = [];

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

        public void Took(EventLine line, Step step)
        {
            _reachedAt = line.At;

            switch (step.Kind)
            {
                case StepKind.Turn:
                    var cost = Number(line, CostAttribute);

                    _turns++;
                    _cost += cost;

                    if (agents?.GetValueOrDefault(step.Id) is { } agent)
                    {
                        Spent(agent, cost);
                    }

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
                _cost,
                agents is null ? null : _subagents);

        private void Spent(string agent, decimal cost)
        {
            var place = _subagents.FindIndex(each => each.Agent == agent);

            if (place < 0)
            {
                _subagents.Add(new SubagentCost(agent, cost));
            }
            else
            {
                _subagents[place] = _subagents[place] with { Cost = _subagents[place].Cost + cost };
            }
        }
    }
}
