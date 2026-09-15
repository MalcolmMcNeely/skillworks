using Skillworks.Core.Gaps;

namespace Skillworks.Core.Arriving;

public sealed record AnswerEnd(Gap Gap) : ArrivingLine("end");
