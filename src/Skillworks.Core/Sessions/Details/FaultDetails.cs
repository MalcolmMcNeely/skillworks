namespace Skillworks.Core.Sessions.Details;

public sealed record FaultDetails(
    string? Error,
    int? StatusCode,
    int? Attempt,
    string? Model,
    string? Effort,
    Purpose Purpose,
    SideRequest? Side,
    string? SentAs);
