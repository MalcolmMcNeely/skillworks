using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;

namespace Skillworks.Core.Telemetry;

public sealed class TelemetryDbContext(DbContextOptions<TelemetryDbContext> options) : DbContext(options)
{
    /// <summary>
    /// SQLite has no date type, and EF will not translate a comparison over the text it writes for a
    /// DateTimeOffset, so a date range would have to be answered by reading the whole history back
    /// and sifting it in memory. Every one of these instants is already UTC, so dropping the offset
    /// loses nothing and leaves text SQLite can compare.
    /// </summary>
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

            // The two columns a filter narrows by, so asking about one week of a long history costs
            // a seek rather than a scan of all of it.
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
            // Where the fault is found is what identifies it, so reading the same line twice cannot
            // report it twice.
            fault.HasKey(f => new { f.Path, f.Line });

            // Stored the same way as the others. One database that writes an instant two ways is a
            // trap for whoever reads it next.
            fault.Property(f => f.NoticedUtc).HasConversion(AsUtc);
        });
    }
}
