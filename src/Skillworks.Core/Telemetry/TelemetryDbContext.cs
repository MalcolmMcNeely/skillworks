using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

public sealed class TelemetryDbContext(DbContextOptions<TelemetryDbContext> options) : DbContext(options)
{
    public DbSet<Activation> Activations => Set<Activation>();

    public DbSet<IngestedTranscript> IngestedTranscripts => Set<IngestedTranscript>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<Activation>(activation =>
        {
            activation.HasKey(a => a.ToolUseId);
            activation.HasIndex(a => a.SkillName);
        });

        model.Entity<IngestedTranscript>().HasKey(t => t.Path);
    }
}
