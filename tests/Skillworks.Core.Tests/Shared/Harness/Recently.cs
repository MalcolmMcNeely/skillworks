using System.Globalization;

namespace Skillworks.Core.Tests.Shared.Harness;

// A fixture dated long ago sits in no Batch a period reads.
public static class Recently
{
    // One moment for the whole run, or a fixture and the clock a host reads could land on different days.
    public static readonly DateTimeOffset Now = DateTimeOffset.UtcNow;

    public static readonly DateOnly Today = DateOnly.FromDateTime(Now.UtcDateTime);

    public static readonly DateOnly Yesterday = Today.AddDays(-1);

    public static readonly DateOnly Tomorrow = Today.AddDays(1);

    public static DateOnly DaysBack(int days) => Today.AddDays(-days);

    public static string At(DateOnly day, string time) => $"{Written(day)}T{time}Z";

    public static string Written(DateOnly day) => day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
}
