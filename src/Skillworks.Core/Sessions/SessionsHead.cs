using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions;

// Nothing after this instant is read, so a later read that passes it back never moves a row already drawn.
public sealed record SessionsHead(DateTimeOffset AsOfUtc) : ArrivingLine("head");
