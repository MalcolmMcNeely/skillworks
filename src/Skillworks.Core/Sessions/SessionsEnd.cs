using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Gaps;

namespace Skillworks.Core.Sessions;

// The next read starts at the oldest row's Latest, or at the date a quiet 30 days reached, as a quiet month is not the store's start.
public sealed record SessionsEnd(Gap Gap, DateTimeOffset? OldestLatestUtc, DateTimeOffset? QuietSinceUtc) : AnswerEnd;
