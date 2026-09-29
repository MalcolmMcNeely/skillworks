using System.Globalization;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Details;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string OutputAttribute = "output_tokens";

    private const string FirstWordAttribute = "ttft_ms";

    private const string EffortAttribute = "effort";

    private const string SpeedAttribute = "speed";

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

    public static DetailsPage Details(OpenedRun opened)
    {
        // Read from every line and not the drawn Steps, as the title's Answer draws no Step and still has a Turn.
        var answers = opened.Read.Lines
            .Where(line => Named(AnswerEvent)(line) && line.Attribute(StepKey.Request) is not null)
            .GroupBy(line => line.Attribute(StepKey.Request)!, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Last(), StringComparer.Ordinal);

        return new(opened.Drawn
            .Where(each => each.Step.Kind == StepKind.Turn)
            .ToDictionary(each => each.Step.Id, each => TurnDetailsOf(each.Line, answers), StringComparer.Ordinal));
    }

    private static TurnDetails TurnDetailsOf(EventLine line, IReadOnlyDictionary<string, EventLine> answers)
    {
        var sentAs = line.Attribute(EventAttributes.QuerySource);
        var purpose = PurposeOf(sentAs);
        var answer = line.Attribute(StepKey.Request) is { } request ? answers.GetValueOrDefault(request) : null;

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
            answer is null ? null : Length(answer, EventAttributes.ResponseLength, EventAttributes.Response));
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
