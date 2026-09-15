using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Skillworks.Core.TranscriptStore.Migrations
{
    /// <inheritdoc />
    public partial class ActivationArguments : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Nullable rather than backfilled: the arguments are in the transcripts and nowhere
            // else, so a firing already read shows none until a full re-ingest reads it again.
            migrationBuilder.AddColumn<string>(
                name: "Arguments",
                table: "Activations",
                type: "TEXT",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Arguments",
                table: "Activations");
        }
    }
}
