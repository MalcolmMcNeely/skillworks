using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Gaps;

namespace Skillworks.Core.Sessions;

// The place of the oldest row read, so the next read starts where this one stopped.
public sealed record SessionsEnd(Gap Gap, DateTimeOffset? NextBeforeUtc) : AnswerEnd;
