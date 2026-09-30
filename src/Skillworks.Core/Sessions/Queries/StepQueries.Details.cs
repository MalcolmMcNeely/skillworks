using System.Globalization;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Details;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string OutputAttribute = "output_tokens";

    private const string FirstWordAttribute = "ttft_ms";

    private const string EffortAttribute = "effort";

    private const string SpeedAttribute = "speed";

    private const string StopReasonAttribute = "stop_reason";

    private const string AttemptAttribute = "attempt";

    // Sent only with the tool details setting on, as is the input.
    private const string ParametersAttribute = "tool_parameters";

    // Sent whatever the settings, so a kept-back input still has a size.
    private const string InputBytesAttribute = "tool_input_size_bytes";

    private const string ResultBytesAttribute = "tool_result_size_bytes";

    private const string AllowedByAttribute = "decision_source";

    // The whole message, sent only with the tool details setting on, where error_type is the kind alone.
    private const string ErrorTextAttribute = "error";

    // The parameters hold the command whole, where the input cuts each value at 512 characters.
    private const string FullCommandField = "full_command";

    private const string CommandField = "command";

    private const string ToolSpan = "claude_code.tool";

    private const string WaitSpan = "claude_code.tool.blocked_on_user";

    private const string RunSpan = "claude_code.tool.execution";

    // Sent only with the tool content setting on, and never on an Agent call.
    private const string OutputEvent = "tool.output";

    private const string OutputField = "output";

    // A Read's output is the file it read, and an edit's is its diff.
    private const string ContentField = "content";

    private const string DiffField = "diff";

    private const string DescriptionField = "description";

    private const string HookRunEvent = "hook_execution_complete";

    // Claude Code writes the tool after the hook's event, as in `PreToolUse:Bash`.
    private const string HookNameAttribute = "hook_name";

    private const string BeforeTool = "PreToolUse:";

    private const string AfterTool = "PostToolUse:";

    private const string HookCountAttribute = "num_hooks";

    private const string HooksLengthAttribute = "total_duration_ms";

    // An older Claude Code names no source on a Turn, and a Turn that names none is the main agent's.
    private const string MainAgent = "main";

    // Claude Code writes the output style after it, as in `:outputStyle:custom`, so only the start is matched.
    private const string InteractiveMainAgent = "repl_main_thread";

    private const string HeadlessMainAgent = "sdk";

    // Claude Code writes the agent's type after it, as in `agent:custom`.
    private const string SubagentWork = "agent:";

    private static readonly Dictionary<string, SideRequest> SideRequests = new(StringComparer.Ordinal)
    {
        ["away_summary"] = SideRequest.AwaySummary,
        ["prompt_suggestion"] = SideRequest.PromptSuggestion,
        [TitleSource] = SideRequest.SessionTitle,
        ["compact"] = SideRequest.Compaction,
        ["agent_summary"] = SideRequest.SubagentSummary,
        ["web_fetch_apply"] = SideRequest.WebPageRead,
        ["web_search_tool"] = SideRequest.WebSearch,
    };

    public static DetailsPage Details(OpenedRun opened, OpenedSpans traced)
    {
        var requests = traced.Read.Spans
            .Where(span => span.Name == StepKey.TurnSpan && span.Attributes.GetValueOrDefault(StepKey.Request) is { Length: > 0 })
            .GroupBy(span => span.Attributes[StepKey.Request], StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Last(), StringComparer.Ordinal);

        // Read from every line and not the drawn Steps, as the title's Answer draws no Step and still has a Turn.
        var answers = opened.Read.Lines
            .Where(line => Named(AnswerEvent)(line) && line.Attribute(StepKey.Request) is not null)
            .GroupBy(line => line.Attribute(StepKey.Request)!, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Last(), StringComparer.Ordinal);

        var uses = traced.Read.Spans
            .Where(span => span.Name == ToolSpan && span.Attributes.GetValueOrDefault(StepKey.ToolUse) is { Length: > 0 })
            .GroupBy(span => span.Attributes[StepKey.ToolUse], StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Last(), StringComparer.Ordinal);

        // A Subagent's Spans repeat its Agent call's tool use id, so a wait and a run are matched by their parent Span.
        var within = traced.Read.Spans
            .Where(span => span.ParentSpanId is not null)
            .ToLookup(span => (span.TraceId, span.ParentSpanId!));

        var calls = opened.Read.Lines
            .Where(line => Named(ToolCallEvent)(line) && line.Attribute(ToolAttribute) is not null && SequenceOf(line) is not null)
            .ToLookup(line => line.Attribute(ToolAttribute)!, StringComparer.Ordinal);

        var before = HooksAround(opened.Read.Lines, calls, BeforeTool, -1);
        var after = HooksAround(opened.Read.Lines, calls, AfterTool, 1);

        return new(
            opened.Drawn
                .Where(each => each.Step.Kind == StepKind.Turn)
                .ToDictionary(each => each.Step.Id, each => TurnDetailsOf(each.Line, answers, requests), StringComparer.Ordinal),
            opened.Drawn
                .Where(each => each.Step.Kind == StepKind.Tool)
                .ToDictionary(each => each.Step.Id, each => ToolDetailsOf(each.Line, uses, within, before, after), StringComparer.Ordinal));
    }

    private static ToolDetails ToolDetailsOf(
        EventLine line,
        IReadOnlyDictionary<string, Span> uses,
        ILookup<(string, string), Span> within,
        IReadOnlyDictionary<EventLine, HookRun> before,
        IReadOnlyDictionary<EventLine, HookRun> after)
    {
        var use = line.Attribute(StepKey.ToolUse);
        var span = use is null ? null : uses.GetValueOrDefault(use);
        var said = span?.Events.LastOrDefault(each => each.Name == OutputEvent)?.Attributes;
        var inside = span is null ? [] : within[(span.TraceId, span.SpanId)];

        var input = Recorded(line, EventAttributes.ToolInput);
        var parameters = Recorded(line, ParametersAttribute);
        var asked = ToolInput.Fields(input);
        var named = ToolInput.Fields(parameters);

        return new ToolDetails(
            line.Attribute(ToolAttribute),
            !Failed(line),
            Failed(line) ? line.Attribute(ErrorTextAttribute) ?? line.Attribute(ErrorAttribute) : null,
            input,
            Bytes(line, InputBytesAttribute),
            parameters,
            ToolInput.Text(named, FullCommandField) ?? ToolInput.Text(asked, CommandField),
            ToolInput.Text(named, DescriptionField) ?? ToolInput.Text(asked, DescriptionField),
            Bytes(line, ResultBytesAttribute),
            line.Attribute(AllowedByAttribute),
            span is not null,
            Said(said, OutputField) ?? Said(said, ContentField),
            Said(said, DiffField),
            LengthOf(inside, WaitSpan),
            LengthOf(inside, RunSpan),
            before.GetValueOrDefault(line),
            after.GetValueOrDefault(line));
    }

    // A failed call runs no PostToolUse, so a run binds only to its nearest call and never to that call's neighbour.
    private static Dictionary<EventLine, HookRun> HooksAround(
        IReadOnlyList<EventLine> lines,
        ILookup<string, EventLine> calls,
        string hookEvent,
        int side) =>
        lines
            .Where(line => Named(HookRunEvent)(line)
                && SequenceOf(line) is not null
                && line.Attribute(HookNameAttribute) is { } name
                && name.StartsWith(hookEvent, StringComparison.Ordinal))
            .Select(run => (Run: run, Call: Nearest(calls[run.Attribute(HookNameAttribute)![hookEvent.Length..]], run, side)))
            .Where(each => each.Call is not null)
            .GroupBy(each => each.Call!)
            .ToDictionary(group => group.Key, group => HookRunOf(Nearest(group.Select(each => each.Run), group.Key, -side)!));

    private static HookRun HookRunOf(EventLine run) =>
        new((int)Number(run, HookCountAttribute), (long)Number(run, HooksLengthAttribute));

    // Claude Code counts its events again from the start when it restarts, so a number two lines share goes to the nearer in time.
    private static EventLine? Nearest(IEnumerable<EventLine> candidates, EventLine from, int side) =>
        candidates
            .Select(line => (Line: line, Apart: (SequenceOf(from)!.Value - SequenceOf(line)!.Value) * side))
            .Where(each => each.Apart > 0)
            .OrderBy(each => each.Apart)
            .ThenBy(each => (from.At - each.Line.At).Duration())
            .Select(each => each.Line)
            .FirstOrDefault();

    private static long? SequenceOf(EventLine line) =>
        long.TryParse(line.Attribute(SequenceAttribute), NumberStyles.Integer, CultureInfo.InvariantCulture, out var sequence)
            ? sequence
            : null;

    private static string? Said(IReadOnlyDictionary<string, string>? said, string field) =>
        said?.GetValueOrDefault(field) is { } text && text != EventAttributes.Withheld ? text : null;

    private static long? LengthOf(IEnumerable<Span> inside, string name) =>
        inside.LastOrDefault(span => span.Name == name) is { } found
            ? (long)(found.Ended - found.Started).TotalMilliseconds
            : null;

    private static long? Bytes(EventLine line, string attribute) =>
        long.TryParse(line.Attribute(attribute), NumberStyles.Integer, CultureInfo.InvariantCulture, out var bytes)
            ? bytes
            : null;

    private static TurnDetails TurnDetailsOf(
        EventLine line,
        IReadOnlyDictionary<string, EventLine> answers,
        IReadOnlyDictionary<string, Span> requests)
    {
        var sentAs = line.Attribute(EventAttributes.QuerySource);
        var purpose = PurposeOf(sentAs);
        var request = line.Attribute(StepKey.Request);
        var answer = request is null ? null : answers.GetValueOrDefault(request);
        var asked = request is null ? null : requests.GetValueOrDefault(request);

        return new TurnDetails(
            purpose,
            purpose == Purpose.Side ? SideRequests.GetValueOrDefault(sentAs!, SideRequest.Other) : null,
            sentAs,
            line.Attribute(ModelAttribute),
            line.Attribute(EffortAttribute),
            line.Attribute(SpeedAttribute),
            Number(line, CostAttribute),
            (long)Number(line, DurationAttribute),
            long.TryParse(line.Attribute(FirstWordAttribute), NumberStyles.Integer, CultureInfo.InvariantCulture, out var wait)
                ? wait
                : null,
            (long)Number(line, CacheReadAttribute),
            (long)Number(line, CacheCreationAttribute),
            (long)Number(line, InputAttribute),
            (long)Number(line, OutputAttribute),
            answer is null ? null : Recorded(answer, EventAttributes.Response),
            answer is null ? null : Length(answer, EventAttributes.ResponseLength, EventAttributes.Response),
            asked?.Attributes.GetValueOrDefault(StopReasonAttribute) is { Length: > 0 } stopped ? stopped : null,
            int.TryParse(asked?.Attributes.GetValueOrDefault(AttemptAttribute), NumberStyles.Integer, CultureInfo.InvariantCulture, out var attempt)
                ? attempt
                : null);
    }

    // The Time breakdown sets Side requests apart by this too, so the two never disagree.
    private static Purpose PurposeOf(string? sentAs) => sentAs switch
    {
        null or "" or MainAgent or HeadlessMainAgent => Purpose.Work,
        _ when sentAs.StartsWith(InteractiveMainAgent, StringComparison.Ordinal) => Purpose.Work,
        _ when sentAs.StartsWith(SubagentWork, StringComparison.Ordinal) => Purpose.Subagent,
        _ => Purpose.Side,
    };
}
