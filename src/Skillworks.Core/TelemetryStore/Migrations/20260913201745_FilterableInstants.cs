using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Skillworks.Core.TelemetryStore.Migrations
{
    /// <inheritdoc />
    public partial class FilterableInstants : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // These instants were written as a DateTimeOffset, which SQLite stores as text with the
            // offset on the end and then refuses to compare. They are all UTC, so cutting "+00:00"
            // off leaves exactly the text the new mapping writes, and no transcript is read again.
            migrationBuilder.Sql("UPDATE Activations SET TimestampUtc = replace(TimestampUtc, '+00:00', '');");
            migrationBuilder.Sql("UPDATE Turns SET TimestampUtc = replace(TimestampUtc, '+00:00', '');");
            migrationBuilder.Sql("UPDATE TranscriptFaults SET NoticedUtc = replace(NoticedUtc, '+00:00', '');");

            migrationBuilder.CreateIndex(
                name: "IX_Turns_Repository",
                table: "Turns",
                column: "Repository");

            migrationBuilder.CreateIndex(
                name: "IX_Turns_TimestampUtc",
                table: "Turns",
                column: "TimestampUtc");

            migrationBuilder.CreateIndex(
                name: "IX_Activations_Repository",
                table: "Activations",
                column: "Repository");

            migrationBuilder.CreateIndex(
                name: "IX_Activations_TimestampUtc",
                table: "Activations",
                column: "TimestampUtc");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Turns_Repository",
                table: "Turns");

            migrationBuilder.DropIndex(
                name: "IX_Turns_TimestampUtc",
                table: "Turns");

            migrationBuilder.DropIndex(
                name: "IX_Activations_Repository",
                table: "Activations");

            migrationBuilder.DropIndex(
                name: "IX_Activations_TimestampUtc",
                table: "Activations");

            migrationBuilder.Sql(
                "UPDATE Activations SET TimestampUtc = TimestampUtc || '+00:00' WHERE TimestampUtc NOT LIKE '%+00:00';");
            migrationBuilder.Sql(
                "UPDATE Turns SET TimestampUtc = TimestampUtc || '+00:00' WHERE TimestampUtc NOT LIKE '%+00:00';");
            migrationBuilder.Sql(
                "UPDATE TranscriptFaults SET NoticedUtc = NoticedUtc || '+00:00' WHERE NoticedUtc NOT LIKE '%+00:00';");
        }
    }
}
