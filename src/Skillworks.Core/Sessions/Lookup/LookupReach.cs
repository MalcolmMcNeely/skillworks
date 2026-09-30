namespace Skillworks.Core.Sessions.Lookup;

public sealed class LookupReach(int days)
{
    // A reach of none would look nowhere.
    public DateTimeOffset StartBefore(DateTimeOffset asOf) => asOf - TimeSpan.FromDays(Math.Max(1, days));
}
