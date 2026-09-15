using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Skillworks.Core.TranscriptStore;

// Only `dotnet ef migrations add` uses this, and it never opens the path; it only needs the provider.
internal sealed class TranscriptStoreDbContextFactory : IDesignTimeDbContextFactory<TranscriptStoreDbContext>
{
    public TranscriptStoreDbContext CreateDbContext(string[] args) =>
        new(new DbContextOptionsBuilder<TranscriptStoreDbContext>()
            .UseSqlite("Data Source=design-time.db")
            .Options);
}
