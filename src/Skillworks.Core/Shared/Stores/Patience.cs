namespace Skillworks.Core.Shared.Stores;

public sealed class Patience
{
    // A request stalling and a whole read giving up arrive as the same silence, so the sentence names which ran out.
    public const string OneRequest = "one request";

    public const string AWholeSession = "a whole session";

    // A Patience of none would be spent before the request went out.
    private const int Floor = 1;

    // HttpClient keeps a wait of 100 seconds of its own, measured on the machine's clock, so a request Studio gives up on sooner leaves the Clock to answer.
    private const int InsideTheClientsWait = 90;

    private Patience(TimeSpan length) => Length = length;

    public TimeSpan Length { get; }

    public static Patience PerRequest(int seconds) =>
        new(TimeSpan.FromSeconds(Math.Clamp(seconds, Floor, InsideTheClientsWait)));

    // A read of hundreds of requests never meets the client's own wait, as each request inside it has already given up.
    public static Patience PerRead(int seconds) => new(TimeSpan.FromSeconds(Math.Max(Floor, seconds)));

    // Ended, because the Health page stands this beside details that are ended sentences too.
    public string RanOut(string subject, string over) =>
        $"{subject} did not answer inside the {Length.TotalSeconds:0} seconds Studio waits for {over}.";
}
