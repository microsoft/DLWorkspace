using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Utils.Json;
using Newtonsoft.Json.Linq;
using System.IO;
using Microsoft.Extensions.Logging;
using WebUI.Models;

namespace Utils.Database
{
    public class DbConfig
    {
        private static ILogger logger = null;
        public static JObject Config = null;
        public static Dictionary<string, JToken> AllConfig = new Dictionary<string, JToken>();
        public static Dictionary<string, DbContext> All = new Dictionary<string, DbContext>();

        public static string FormConnectionString(JToken dbConfig)
        {
            var server = JsonUtils.GetString("host", dbConfig);
            var user = JsonUtils.GetString("user", dbConfig);
            var password = JsonUtils.GetString("password", dbConfig);
            var database = JsonUtils.GetString("database", dbConfig);
            var table = JsonUtils.GetString("table", dbConfig);
            var type = JsonUtils.GetString("type", dbConfig);

            switch (type)
            {
                case "MySQL":
                    // return $"Server={server};Database={database};Uid={user};Pwd={password};Trusted_Connection=True;";
                    return $"Server={server}; Database={database}; Uid={user}; Pwd={password}; ";
                default:
                    throw new ArgumentException($"Unsupported database type {type}");
            }
        }

        public static void Set(string configFileName = WebUIConfig.DatabaseConfigFile, ILogger thisLogger = null)
        {
            logger = thisLogger;
            var useConfigFilename = WebUIConfig.GetConfigFile(configFileName);
            if ( File.Exists(useConfigFilename)) { 
                using (var file = new FileStream(useConfigFilename, FileMode.Open))
                {
                    Config = JsonUtils.Read(file);
                    JToken configDatabase = JsonUtils.GetJToken("Database", Config);
                    foreach (var pair in JsonUtils.Iterate(configDatabase))
                    {
                        var dbName = pair.Key;
                        var dbConfig = pair.Value;
                        AllConfig[dbName] = dbConfig;
                    }
                }
            }
        }

        public static List<string> ConnectString<DbCtx>() where DbCtx : DbContext, new()
        {
            var optionBuilder = new DbContextOptionsBuilder<DbCtx>();
            var dbTypeName = typeof(DbCtx).Name;

            List<string> dbList = new List<string>();
            foreach (var pair in AllConfig)
            {
                var dbName = pair.Key;
                var dbConfig = AllConfig[dbName];

                var curDbTypeName = dbConfig.Value<string>("dbType");
                if (!String.IsNullOrEmpty(curDbTypeName) &&
                    dbTypeName.IndexOf(curDbTypeName, 0, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    if (!Object.ReferenceEquals(logger, null))
                        logger.LogInformation($"Database {dbName}, Configuration: {dbConfig}");
                    var connString = FormConnectionString(dbConfig);
                    if (!Object.ReferenceEquals(logger, null))
                        logger.LogInformation($"Connect with {connString}");
                    if (!String.IsNullOrEmpty(connString))
                        dbList.Add(connString);
                }
            }
            return dbList;
        }

        /* SQL
        public static List<DbCtx> Connect<DbCtx>() where DbCtx: DbContext, new()
        {
            var optionBuilder = new DbContextOptionsBuilder<DbCtx>();
            var dbTypeName = typeof(DbCtx).Name;

            List<DbCtx> dbList = new List<DbCtx>(); 
            foreach ( var pair in AllConfig)
            {
                var dbName = pair.Key;
                var dbConfig = AllConfig[dbName];

                var curDbTypeName = dbConfig.Value<string>("dbType");
                if ( !String.IsNullOrEmpty(curDbTypeName) &&
                    dbTypeName.IndexOf(curDbTypeName,0,StringComparison.OrdinalIgnoreCase)>=0 )
                { 
                    if (!Object.ReferenceEquals(logger, null))
                        logger.LogInformation($"Database {dbName}, Configuration: {dbConfig}");
                    var connString = FormConnectionString(dbConfig);
                    if (!Object.ReferenceEquals(logger, null))
                        logger.LogInformation($"Connect with {connString}");

                    var ctx = optionBuilder.UseSqlServer<DbCtx>(connString);
                    // db = new Dbctx(optionBuilder.Options); 
                    // see https://stackoverflow.com/questions/37570541/generic-constructor-with-new-type-constraint
                    var db = (DbCtx)Activator.CreateInstance(typeof(DbCtx), new[] { optionBuilder.Options });
                    All[dbName] = db;
                    dbList.Add(db);
                }
            }
            return dbList; 
        }
        */


    }
}
