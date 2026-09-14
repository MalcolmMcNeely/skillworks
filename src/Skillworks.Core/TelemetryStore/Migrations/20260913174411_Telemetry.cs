using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Skillworks.Core.TelemetryStore.Migrations
{
    /// <inheritdoc />
    public partial class Telemetry : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Activations",
                columns: table => new
                {
                    ToolUseId = table.Column<string>(type: "TEXT", nullable: false),
                    SkillName = table.Column<string>(type: "TEXT", nullable: false),
                    SessionId = table.Column<string>(type: "TEXT", nullable: false),
                    Repository = table.Column<string>(type: "TEXT", nullable: true),
                    GitBranch = table.Column<string>(type: "TEXT", nullable: true),
                    TimestampUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Activations", x => x.ToolUseId);
                });

            migrationBuilder.CreateTable(
                name: "IngestedTranscripts",
                columns: table => new
                {
                    Path = table.Column<string>(type: "TEXT", nullable: false),
                    Offset = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IngestedTranscripts", x => x.Path);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Activations_SkillName",
                table: "Activations",
                column: "SkillName");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Activations");

            migrationBuilder.DropTable(
                name: "IngestedTranscripts");
        }
    }
}
