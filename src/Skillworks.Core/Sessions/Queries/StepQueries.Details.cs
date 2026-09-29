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

    private const string DescriptionField = "description";

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

        return new(
            opened.Drawn
                .Where(each => each.Step.Kind == StepKind.Turn)
                .ToDictionary(each => each.Step.Id, each => TurnDetailsOf(each.Line, answers, requests), StringComparer.Ordinal),
            opened.Drawn
                .Where(each => each.Step.Kind == StepKind.Tool)
                .ToDictionary(each => each.Step.Id, each => ToolDetailsOf(each.Line), StringComparer.Ordinal));
    }

    private static ToolDetails ToolDetailsOf(EventLine line)
    {
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
            line.Attribute(AllowedByAttribute));
    }

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
