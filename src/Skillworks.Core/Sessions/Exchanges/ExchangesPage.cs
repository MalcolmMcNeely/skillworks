using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions.Exchanges;

public sealed record ExchangesPage(IReadOnlyList<Exchange> Exchanges) : ArrivingLine("exchanges");
