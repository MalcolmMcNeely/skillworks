using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Exchanges;

// The Turns before the first Prompt sit in no Exchange, so without them the Exchanges fall short of the Session's Cost.
public sealed record ExchangesPage(IReadOnlyList<Exchange> Exchanges, decimal BeforeFirstPrompt) : ArrivingLine("exchanges");
