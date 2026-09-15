using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using Skillworks.Core.Activations;
using Skillworks.Core.Ingest;
using Skillworks.Core.Spend;

namespace Skillworks.Core.TranscriptStore;

public sealed class TranscriptStoreDbContext(DbContextOptions<TranscriptStoreDbContext> options) : DbContext(options)
{
    // EF can't compare DateTimeOffset text on SQLite; every instant is UTC, so dropping the offset is safe.
    private static readonly ValueConverter<DateTimeOffset, DateTime> AsUtc = new(
        moment => moment.UtcDateTime,
        stored => new DateTimeOffset(DateTime.SpecifyKind(stored, DateTimeKind.Utc), TimeSpan.Zero));

    public DbSet<Activation> Activations => Set<Activation>();

    public DbSet<Turn> Turns => Set<Turn>();

    public DbSet<ModelPrice> ModelPrices => Set<ModelPrice>();

    public DbSet<IngestedTranscript> IngestedTranscripts => Set<IngestedTranscript>();

    public DbSet<TranscriptFault> TranscriptFaults => Set<TranscriptFault>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<Activation>(activation =>
        {
            activation.HasKey(a => a.ToolUseId);
            activation.HasIndex(a => a.SkillName);

            // The two columns a filter narrows by, so one week of a long history is a seek, not a scan.
            activation.HasIndex(a => a.TimestampUtc);
            activation.HasIndex(a => a.Repository);
            activation.Property(a => a.TimestampUtc).HasConversion(AsUtc);
        });

        model.Entity<Turn>(turn =>
        {
            turn.HasKey(t => t.RequestId);
            turn.HasIndex(t => t.SkillName);
            turn.HasIndex(t => t.TimestampUtc);
            turn.HasIndex(t => t.Repository);
            turn.Property(t => t.TimestampUtc).HasConversion(AsUtc);
        });

        model.Entity<ModelPrice>(price =>
        {
            price.HasKey(p => p.Model);
            price.HasData(SeededPrices.All);
        });

        model.Entity<IngestedTranscript>().HasKey(t => t.Path);

        model.Entity<TranscriptFault>(fault =>
        {
            // Reading the same line twice must not report the fault twice.
            fault.HasKey(f => new { f.Path, f.Line });

            // A database that stores instants two ways is a trap for whoever reads it next.
            fault.Property(f => f.NoticedUtc).HasConversion(AsUtc);
        });
    }
}
