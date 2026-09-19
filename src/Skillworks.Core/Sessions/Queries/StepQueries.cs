using System.Globalization;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries(EventsStoreReader events, TimeProvider clock)
{
    private const string EventNameAttribute = "event.name";

    private const string SequenceAttribute = "event.sequence";

    private const string DurationAttribute = "duration_ms";

    private const string ToolAttribute = "tool_name";

    private const string SuccessAttribute = "success";

    private const string ErrorAttribute = "error_type";

    private const string DecisionAttribute = "decision";

    private const string SourceAttribute = "source";

    private const string CostAttribute = "cost_usd";

    private const string ModelAttribute = "model";

    private const string PromptEvent = "user_prompt";

    private const string AnswerEvent = "assistant_response";

    private const string ToolCallEvent = "tool_result";

    private const string DecisionEvent = "tool_decision";

    private const string ModelErrorEvent = "api_error";

    private const string TurnEvent = "api_request";

    private const string TitleSource = "generate_session_title";

    private const string Unsuccessful = "false";

    private const string Rejected = "reject";

    // A mark on a timeline carries a phrase, not a page, and the Step it opens carries the rest.
    private const int Opening = 200;

    // Every event of one run, as a timeline draws the run itself and not a total over it.
    public async Task<OpenedRun> OpenAsync(string id, DaySpan span, CancellationToken cancellationToken)
    {
        var read = await events.LinesAsync(
            new EventQuery(EventQuery.AnyEvent, span.FromUtc, span.UntilUtc) { Session = id },
            cancellationToken);

        if (read.Unreachable is not null || read.Lines.Count == 0)
        {
            return new OpenedRun(null, [], [], [], [], null, [], [], false, read);
        }

        var drawn = Stepped(read.Lines);
        var sent = Sent(read.Lines);

        return new OpenedRun(
            Run(id, read.Lines),
            drawn,
            Said(drawn),
            Fired(read.Lines),
            sent.Points,
            sent.Limit,
            Keys(drawn),
            Called(read.Lines),
            PromptsWithheld(read.Lines),
            read);
    }

    // Claude Code sends the Prompt with a marker in place of the words, so a withheld one is told from a missing one.
    private static bool PromptsWithheld(IReadOnlyList<EventLine> lines) =>
        lines.Any(line => Named(PromptEvent)(line) && line.Attribute(EventAttributes.Prompt) == EventAttributes.Withheld);

    private static IReadOnlyList<StepKey> Keys(IReadOnlyList<DrawnStep> drawn) =>
    [
        .. drawn
            .Select(each => Keyed(each.Line) is { } key ? new StepKey(each.Step.Id, key) : null)
            .OfType<StepKey>()
    ];

    private static string? Keyed(EventLine line) =>
        line.Attribute(StepKey.ToolUse) ?? line.Attribute(StepKey.Request);

    private Session Run(string id, IReadOnlyList<EventLine> lines)
    {
        var startedAt = lines[0].At;
        var lastEvent = lines[^1].At;
        var repository = MostlySaid(lines, line => line.Repository);
        var toolCalls = lines.Count(Named(ToolCallEvent));

        var faults =
            lines.Count(line => Named(ToolCallEvent)(line) && Failed(line)) +
            lines.Count(Named(ModelErrorEvent));

        var cost = lines.Where(Named(TurnEvent)).Sum(line => Number(line, CostAttribute));

        return new Session(
            id,
            startedAt,
            repository,
            MostlySaid(lines, line => line.Attribute(EventAttributes.Person)),
            SessionName.Of(Title(lines), FirstPrompt(lines), repository, startedAt),
            (long)(lastEvent - startedAt).TotalMilliseconds,
            RunningWindow.Covers(lastEvent, clock.GetUtcNow()),
            toolCalls,
            cost,
            faults,
            lines.Count(line => Named(DecisionEvent)(line) && Refused(line)));
    }

    // Paired with the event it came from, so an Exchange and a timeline band cover exactly one Spell.
    private static IReadOnlyList<DrawnStep> Stepped(IReadOnlyList<EventLine> lines) =>
        [
            .. lines
                .Select((line, place) => Stepped(line, Identity(line, place)) is { } step ? new DrawnStep(line, step) : null)
                .OfType<DrawnStep>()
        ];

    private static Step? Stepped(EventLine line, string id)
    {
        var length = (long)Number(line, DurationAttribute);
        var began = line.At.AddMilliseconds(-length);

        return line.Attribute(EventNameAttribute) switch
        {
            PromptEvent => new Step(id, StepKind.Prompt, line.At, 0, null, false, Words(line, EventAttributes.Prompt)),

            TurnEvent => new Step(id, StepKind.Turn, began, length, null, false, line.Attribute(ModelAttribute)),

            // The title is written by a request of Claude Code's own, so it is no part of what was said.
            AnswerEvent when line.Attribute(EventAttributes.QuerySource) != TitleSource =>
                new Step(id, StepKind.Answer, line.At, 0, null, false, Words(line, EventAttributes.Response)),

            ToolCallEvent => new Step(
                id,
                StepKind.Tool,
                began,
                length,
                line.Attribute(ToolAttribute),
                Failed(line),
                Failed(line) ? line.Attribute(ErrorAttribute) : null),

            DecisionEvent when Refused(line) =>
                new Step(id, StepKind.Refused, line.At, 0, line.Attribute(ToolAttribute), false, line.Attribute(SourceAttribute)),

            ModelErrorEvent => new Step(id, StepKind.Fault, began, length, null, true, line.Attribute(ErrorAttribute)),

            _ => null,
        };
    }

    // Claude Code numbers the events of a run, so a mark keeps its identity when a Running run is read again.
    private static string Identity(EventLine line, int place) =>
        line.Attribute(SequenceAttribute) ?? place.ToString(CultureInfo.InvariantCulture);

    private static Func<EventLine, bool> Named(string eventName) =>
        line => line.Attribute(EventNameAttribute) == eventName;

    private static bool Failed(EventLine line) => line.Attribute(SuccessAttribute) == Unsuccessful;

    private static bool Refused(EventLine line) => line.Attribute(DecisionAttribute) == Rejected;

    private static decimal Number(EventLine line, string attribute) =>
        decimal.TryParse(line.Attribute(attribute), NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : 0;

    private static string? Title(IReadOnlyList<EventLine> lines) =>
        lines
            .FirstOrDefault(line => Named(AnswerEvent)(line) && line.Attribute(EventAttributes.QuerySource) == TitleSource)
            ?.Attribute(EventAttributes.Response);

    private static string? FirstPrompt(IReadOnlyList<EventLine> lines) =>
        lines.FirstOrDefault(Named(PromptEvent))?.Attribute(EventAttributes.Prompt);

    // An older Claude Code puts the repository on no event, and a run with no origin remote has none.
    private static string? MostlySaid(IEnumerable<EventLine> lines, Func<EventLine, string?> said) =>
        lines.GroupBy(said)
            .Where(value => value.Key is not null)
            .OrderByDescending(value => value.Count())
            .ThenBy(value => value.Key, StringComparer.Ordinal)
            .Select(value => value.Key)
            .FirstOrDefault();

    private static string? Words(EventLine line, string attribute)
    {
        if (Recorded(line, attribute) is not { } said)
        {
            return null;
        }

        var phrase = string.Join(' ', said.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

        return phrase.Length > Opening ? phrase[..Opening] + '…' : phrase;
    }

}
