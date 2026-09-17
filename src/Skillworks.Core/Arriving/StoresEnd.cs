using Skillworks.Core.Gaps;

namespace Skillworks.Core.Arriving;

// The events store and the trace store fall short apart from each other, so each names its own shortfall.
public sealed record StoresEnd(Gap Events, Gap Traces) : AnswerEnd;
