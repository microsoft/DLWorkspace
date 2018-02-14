using Microsoft.EntityFrameworkCore.Migrations;
using System;
using System.Collections.Generic;

namespace WebApplication1.Migrations
{
    public partial class Version14 : Migration
    {
        /// <summary>
        /// 4000: Maximum column size supported by Sql, we don't use max as it is unsure MySQL supported nvarchar(max)
        /// </summary>
        /// <param name="migrationBuilder"></param>
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Template",
                columns: table => new
                {
                    Template = table.Column<string>(type: "nvarchar(450)", nullable: false),
                    Json = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    Type = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    Username = table.Column<string>(type: "nvarchar(4000)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Template", x => x.Template);
                });

            migrationBuilder.CreateTable(
                name: "User",
                columns: table => new
                {
                    Email = table.Column<string>(type: "nvarchar(450)", nullable: false),
                    Alias = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    Config = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    ConfigSecret = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    Other = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    Password = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    gid = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    isAdmin = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    isAuthorized = table.Column<string>(type: "nvarchar(4000)", nullable: true),
                    uid = table.Column<string>(type: "nvarchar(4000)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_User", x => x.Email);
                });
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Template");

            migrationBuilder.DropTable(
                name: "User");
        }
    }
}
