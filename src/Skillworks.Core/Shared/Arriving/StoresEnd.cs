using Skillworks.Core.Shared.Gaps;

namespace Skillworks.Core.Shared.Arriving;

// The events store and the trace store fall short apart from each other, so each names its own shortfall.
public sealed record StoresEnd(Gap Events, Gap Traces) : AnswerEnd;
