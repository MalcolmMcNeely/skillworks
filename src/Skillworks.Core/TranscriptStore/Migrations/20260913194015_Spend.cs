using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace Skillworks.Core.TranscriptStore.Migrations
{
    /// <inheritdoc />
    public partial class Spend : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Effort",
                table: "Activations",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Model",
                table: "Activations",
                type: "TEXT",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "ModelPrices",
                columns: table => new
                {
                    Model = table.Column<string>(type: "TEXT", nullable: false),
                    InputPerMillion = table.Column<decimal>(type: "TEXT", nullable: false),
                    OutputPerMillion = table.Column<decimal>(type: "TEXT", nullable: false),
                    CacheReadPerMillion = table.Column<decimal>(type: "TEXT", nullable: false),
                    CacheWrite5mPerMillion = table.Column<decimal>(type: "TEXT", nullable: false),
                    CacheWrite1hPerMillion = table.Column<decimal>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ModelPrices", x => x.Model);
                });

            migrationBuilder.CreateTable(
                name: "Turns",
                columns: table => new
                {
                    RequestId = table.Column<string>(type: "TEXT", nullable: false),
                    SessionId = table.Column<string>(type: "TEXT", nullable: false),
                    SkillName = table.Column<string>(type: "TEXT", nullable: true),
                    Repository = table.Column<string>(type: "TEXT", nullable: true),
                    GitBranch = table.Column<string>(type: "TEXT", nullable: true),
                    TimestampUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    Model = table.Column<string>(type: "TEXT", nullable: false),
                    Effort = table.Column<string>(type: "TEXT", nullable: true),
                    InputTokens = table.Column<long>(type: "INTEGER", nullable: false),
                    OutputTokens = table.Column<long>(type: "INTEGER", nullable: false),
                    ThinkingTokens = table.Column<long>(type: "INTEGER", nullable: false),
                    CacheReadTokens = table.Column<long>(type: "INTEGER", nullable: false),
                    CacheWrite5mTokens = table.Column<long>(type: "INTEGER", nullable: false),
                    CacheWrite1hTokens = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Turns", x => x.RequestId);
                });

            migrationBuilder.InsertData(
                table: "ModelPrices",
                columns: new[] { "Model", "CacheReadPerMillion", "CacheWrite1hPerMillion", "CacheWrite5mPerMillion", "InputPerMillion", "OutputPerMillion" },
                values: new object[,]
                {
                    { "claude-haiku-4-5", 0.10m, 2m, 1.25m, 1m, 5m },
                    { "claude-opus-5", 1.50m, 30m, 18.75m, 15m, 75m },
                    { "claude-sonnet-5", 0.30m, 6m, 3.75m, 3m, 15m }
                });

            migrationBuilder.CreateIndex(
                name: "IX_Turns_SkillName",
                table: "Turns",
                column: "SkillName");

            // Spend is in lines already read, and the ingest never looks at a line twice. Dropping
            // the cursors is therefore the only way to cost the history already in the store, and
            // the activations go with them so the ones already counted pick up their model and
            // effort rather than staying blank for ever. Nothing is lost: both are keyed by an id
            // out of the transcript, so a re-read rebuilds them exactly.
            migrationBuilder.Sql("DELETE FROM Activations;");
            migrationBuilder.Sql("DELETE FROM IngestedTranscripts;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ModelPrices");

            migrationBuilder.DropTable(
                name: "Turns");

            migrationBuilder.DropColumn(
                name: "Effort",
                table: "Activations");

            migrationBuilder.DropColumn(
                name: "Model",
                table: "Activations");
        }
    }
}
