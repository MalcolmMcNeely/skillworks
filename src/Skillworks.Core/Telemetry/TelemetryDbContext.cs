using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

public sealed class TelemetryDbContext(DbContextOptions<TelemetryDbContext> options) : DbContext(options)
{
    public DbSet<Activation> Activations => Set<Activation>();

    public DbSet<IngestedTranscript> IngestedTranscripts => Set<IngestedTranscript>();

    public DbSet<TranscriptFault> TranscriptFaults => Set<TranscriptFault>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<Activation>(activation =>
        {
            activation.HasKey(a => a.ToolUseId);
            activation.HasIndex(a => a.SkillName);
        });

        model.Entity<IngestedTranscript>().HasKey(t => t.Path);

        // Where the fault is found is what identifies it, so reading the same line twice cannot
        // report it twice.
        model.Entity<TranscriptFault>().HasKey(f => new { f.Path, f.Line });
    }
}
