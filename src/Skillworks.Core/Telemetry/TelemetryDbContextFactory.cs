using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Skillworks.Core.Telemetry;

// Only `dotnet ef migrations add` uses this, and it never opens the path; it only needs the provider.
internal sealed class TelemetryDbContextFactory : IDesignTimeDbContextFactory<TelemetryDbContext>
{
    public TelemetryDbContext CreateDbContext(string[] args) =>
        new(new DbContextOptionsBuilder<TelemetryDbContext>()
            .UseSqlite("Data Source=design-time.db")
            .Options);
}
