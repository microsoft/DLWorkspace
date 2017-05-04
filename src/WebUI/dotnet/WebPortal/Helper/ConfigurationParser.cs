using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using WindowsAuth;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Configuration.Json;
using Microsoft.Extensions.Logging;
using System.Reflection;

namespace WebPortal.Helper
{
    /// <summary>
    /// A Class to aid parse configuration 
    /// </summary>
    public class ConfigurationParser
    {
        /// <summary>
        /// Storing parsed configuration for quick access
        /// </summary>
        private static Dictionary<string, object> _parsedConfiguration = new Dictionary<string, object>();
        private static ILogger _logger;
        private static bool _bParsed = false;

        public static void SetConfiguration(string key, string value )
        {
            string[] keys = key.Split(new char[] { ':' });
            int nKeys = keys.Count();
            var root = _parsedConfiguration;

            for (int i = 0; i < nKeys && !Object.ReferenceEquals(root, null); i++)
            {
                string entry = keys[i];
                if (i < nKeys - 1)
                {
                    // Intermediate level. 
                    if (!root.ContainsKey(entry))
                    {
                        root[entry] = new Dictionary<string, object>();
                    }
                    root = root[entry] as Dictionary<string, object>;
                    if (Object.ReferenceEquals(root, null))
                    {
                        _logger.LogError("Error in Configuration, Key = {0}, Value = {1}, conflict partial key exists... ", key, value);
                    }
                }
                else
                {
                    root[entry] = value;
                    _logger.LogInformation("Configuration[{0}] = {1}", key, value);
                }
            }
        }

        public static object GetConfiguration(string key)
        {
            string[] keys = key.Split(new char[] { ':' });
            int nKeys = keys.Count();
            var root = _parsedConfiguration;

            for (int i = 0; i < nKeys && !Object.ReferenceEquals(root, null); i++)
            {
                string entry = keys[i];
                if (i < nKeys - 1)
                {
                    // Intermediate level. 
                    if ( root.ContainsKey(entry))
                    {
                        root = root[entry] as Dictionary<string, object>;
                    }
                    else
                        root = null; 
                }
                else
                {
                    if (root.ContainsKey(entry))
                        return root[entry];
                    else
                        return null; 
                }
            }
            return null; 
        }


        /// <summary>
        /// Parse a certain configuration 
        /// </summary>
        /// <param name="config"></param>
        public static void ParseConfiguration(ILoggerFactory logger)
        {
            if (!_bParsed)
            {
                _logger = logger.CreateLogger("ConfigurationParser");

                // The following code use reflection to travrese & parse configuration. 
                var configType = WindowsAuth.Startup.Configuration.GetType();
                BindingFlags bindFlags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;
                
                var info = configType.GetField("_providers", bindFlags );
                object obj = info.GetValue(WindowsAuth.Startup.Configuration);
                var objType = obj.GetType();
                var listProviders = obj as List<IConfigurationProvider>;
                // obj = info.GetValue(WindowsAuth.Startup.Configuration, null);


                foreach (var provider in listProviders)
                {
                    var jsonProvider = provider as JsonConfigurationProvider;
                    if (!Object.ReferenceEquals(jsonProvider, null))
                    {
                        var providerType = jsonProvider.GetType();
                        BindingFlags bdFlags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
                        var dataFieldInfo = providerType.GetProperty("Data", bdFlags );
                        object dataField  = dataFieldInfo.GetValue(jsonProvider);
                        var dataFieldType = dataField.GetType(); 
                        var dataDic = dataField as SortedDictionary<string, string>;
                        foreach (var pair in dataDic)
                        {
                            SetConfiguration(pair.Key, pair.Value);
                        }
                    }
                    // string key = entry.Key;
                    // var sec = WindowsAuth.Startup.Configuration.GetSection(key);
                    // 


                }
                _bParsed = true;
            }
        }
    }
}
