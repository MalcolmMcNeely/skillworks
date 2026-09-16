using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions;

public sealed record SessionsPage(IReadOnlyList<Session> Sessions) : ArrivingLine("sessions");
