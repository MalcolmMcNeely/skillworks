using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Details;

// Keyed by Step id, so a row that drew before this landed finds its details without a second read.
public sealed record DetailsPage(
    IReadOnlyDictionary<string, TurnDetails> Turns,
    IReadOnlyDictionary<string, ToolDetails> Tools,
    IReadOnlyDictionary<string, RefusalDetails> Refusals,
    IReadOnlyDictionary<string, FaultDetails> Faults) : ArrivingLine("details");
