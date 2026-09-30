using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Gaps;

namespace Skillworks.Core.Sessions;

// The next read starts at the oldest row's Latest, or at the date a quiet 30 days reached, as a quiet month is not the store's start.
// A Lookup's end carries the start of its reach and no Latest, so the page says how far it looked and offers no more.
public sealed record SessionsEnd(Gap Gap, DateTimeOffset? OldestLatestUtc, DateTimeOffset? LookedBackToUtc) : AnswerEnd;
