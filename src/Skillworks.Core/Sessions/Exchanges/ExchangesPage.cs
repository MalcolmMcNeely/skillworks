using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Exchanges;

public sealed record ExchangesPage(IReadOnlyList<Exchange> Exchanges) : ArrivingLine("exchanges");
