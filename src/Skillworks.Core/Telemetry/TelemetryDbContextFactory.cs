using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Only `dotnet ef migrations add` uses this. The path is never opened, so it does not matter what
/// it is; the tool needs a provider to know it is writing SQLite.
/// </summary>
internal sealed class TelemetryDbContextFactory : IDesignTimeDbContextFactory<TelemetryDbContext>
{
    public TelemetryDbContext CreateDbContext(string[] args) =>
        new(new DbContextOptionsBuilder<TelemetryDbContext>()
            .UseSqlite("Data Source=design-time.db")
            .Options);
}
