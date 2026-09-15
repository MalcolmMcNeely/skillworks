using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Skillworks.Core.TranscriptStore.Migrations
{
    /// <inheritdoc />
    public partial class IngestFaults : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<long>(
                name: "Lines",
                table: "IngestedTranscripts",
                type: "INTEGER",
                nullable: false,
                defaultValue: 0L);

            migrationBuilder.CreateTable(
                name: "TranscriptFaults",
                columns: table => new
                {
                    Path = table.Column<string>(type: "TEXT", nullable: false),
                    Line = table.Column<long>(type: "INTEGER", nullable: false),
                    Reason = table.Column<string>(type: "TEXT", nullable: false),
                    NoticedUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_TranscriptFaults", x => new { x.Path, x.Line });
                });

            // A transcript already read has an offset but no line count, so a fault found in it
            // from here on would carry a line number an editor disagrees with. Dropping the cursors
            // costs one slow pass and buys line numbers that are right. Activations are keyed by
            // tool use id, so nothing is counted twice.
            migrationBuilder.Sql("DELETE FROM IngestedTranscripts;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "TranscriptFaults");

            migrationBuilder.DropColumn(
                name: "Lines",
                table: "IngestedTranscripts");
        }
    }
}
