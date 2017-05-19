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
using System.Threading;

using Newtonsoft.Json.Linq; 

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
        private static Dictionary<string, object> _parsedConfiguration = null;

        // Asp.Net Core will restart service when configuration change, 
        // The current logic is temporarily turned off. 
        // If we need to provide continuous service when program configuration change, we may need to revisit this code. 
        private static long _lastUpdate = DateTime.MinValue.Ticks;
        // Configuration will be updated at this interval. 
        private static double _elapseTillUpdate = new TimeSpan(DateTime.UtcNow.Ticks - DateTime.MinValue.Ticks).TotalSeconds - 10.0;

        private static ILogger _logger;
        private static bool _first = true;

        private static object ExpandJToken(string entryname, JToken token)
        {
            JObject jobj = token as JObject;
            if (!Object.ReferenceEquals(jobj, null))
            {
                var retDic = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
                foreach (var pair in jobj)
                {
                    string name =  pair.Key;
                    JToken value = pair.Value;
                    retDic[name] = ExpandJToken(entryname + ":" + name, value);
                }

            }
            return null; 
        }

        public static void SetConfiguration(Dictionary<string, object> root, string key, string value )
        {
            string[] keys = key.Split(new char[] { ':' });
            int nKeys = keys.Count();

            JObject objValue = null;
            JArray arrValue = null; 
            /* Disable NewtonSoft parsing at this moment. 
            try
            {
                objValue = JObject.Parse(value);
                if ( !Object.ReferenceEquals(objValue, null) && _first )
                    _logger.LogInformation("JObject, parse {0} as {1}", value, objValue);
            }
            catch
            {

            }
            try
            {
                arrValue = JArray.Parse(value);
                if (!Object.ReferenceEquals(arrValue, null) && _first)
                    _logger.LogInformation("JArray, parse {0} as {1}", value, arrValue);
            }
            catch
            {

            } */



            for (int i = 0; i < nKeys && !Object.ReferenceEquals(root, null); i++)
            {
                string entry = keys[i];
                if (i < nKeys - 1)
                {
                    // Intermediate level. 
                    if (!root.ContainsKey(entry))
                    {
                        root[entry] = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
                    }
                    root = root[entry] as Dictionary<string, object>;
                    if (Object.ReferenceEquals(root, null))
                    {
                        if (_first)
                            _logger.LogError("Error in Configuration, Key = {0}, Value = {1}, conflict partial key exists... ", key, value);
                    }
                }
                else
                {
                    if (!Object.ReferenceEquals(objValue, null))
                    {
                        root[entry] = ExpandJToken(entry, objValue);
                    }
                    else if (!Object.ReferenceEquals(arrValue, null))
                    {
                        root[entry] = ExpandJToken(entry, arrValue);
                    }
                    else
                    { 
                        root[entry] = value;
                        if ( _first )
                            _logger.LogDebug("Configuration[{0}] = {1}", key, value);
                    }
                }
            }
        }

        public static object GetConfiguration(string key)
        {
            ParseConfigurationAgain();
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

        public static string[] GetConfigurationAsArray(string key)
        {
            var obj = GetConfiguration(key);
            var dicObj = obj as Dictionary<string, object>;
            if (!Object.ReferenceEquals(dicObj, null))
            {
                return dicObj.Values.Cast<string>().ToArray<string>();
            }
            else
            {
                var strObj = obj as string;
                if (String.IsNullOrEmpty(strObj))
                    return new string[] { };
                else
                    return new string[] { strObj };

            }
                
        }

        public static List<string> ParseConfigurationAsList(object obj)
        {
            var dicObj = obj as Dictionary<string, object>;
            if (!Object.ReferenceEquals(dicObj, null))
            {
                return dicObj.Values.Cast<string>().ToList<string>();
            }
            else
            {
                var strObj = obj as string;
                if (String.IsNullOrEmpty(strObj))
                    return new List<string>();
                else
                    return new List<string>() { strObj };
            }
        }

        public static List<string> GetConfigurationAsList(string key)
        {
            var obj = GetConfiguration(key);
            return ParseConfigurationAsList(obj);
        }

        public static void ParseConfigurationAgain()
        {
            bool bUpdate = false;
            long cur = DateTime.UtcNow.Ticks;
            var elapse = new TimeSpan(cur - _lastUpdate);
            if (elapse.TotalSeconds > _elapseTillUpdate)
            {
                // Double lock, use CAS to grab lock 
                long cur1 = DateTime.UtcNow.Ticks;
                long prevValue = _lastUpdate; 
                var elapse1 = new TimeSpan (cur1 - prevValue);
                if (elapse1.TotalSeconds > _elapseTillUpdate && 
                    Interlocked.CompareExchange( ref _lastUpdate, cur1, prevValue)==prevValue )
                {
                    bUpdate = true; 
                }
            }
            if (bUpdate)
            {
                // Configuration will be updated asynchronously, without locking. 
                var t = Task.Run(() => ParseConfigurationTask());
                if (_parsedConfiguration == null)
                {
                    t.Wait(); 
                }
            }
            while ( _parsedConfiguration==null )
            {
                // Wait for first population. 
                Thread.Sleep(1); 
            }
        }
            
        /// <summary>
        /// Parse a certain configuration 
        /// </summary>
        /// <param name="config"></param>
        public static void ParseConfigurationTask()
        {
            var newConfig = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);

            // The following code use reflection to travrese & parse configuration. 
            var configType = WindowsAuth.Startup.Configuration.GetType();
            BindingFlags bindFlags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;

            var info = configType.GetField("_providers", bindFlags);
            object obj = info.GetValue(WindowsAuth.Startup.Configuration);
            var objType = obj.GetType();
            var listProviders = obj as List<IConfigurationProvider>;
            // obj = info.GetValue(WindowsAuth.Startup.Configuration, null);


            int provider_index = 0; 
            foreach (var provider in listProviders)
            {
                provider_index++; 
                var jsonProvider = provider as JsonConfigurationProvider;
                if (!Object.ReferenceEquals(jsonProvider, null))
                {
                    var providerType = jsonProvider.GetType();
                    BindingFlags bdFlags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
                    var dataFieldInfo = providerType.GetProperty("Data", bdFlags);
                    if (Object.ReferenceEquals(dataFieldInfo, null))
                    {
                        _logger.LogError("Provider {0}, Class doesn't have a Data field ...  ", provider_index);
                    }
                    object dataField = dataFieldInfo.GetValue(jsonProvider);
                    if (Object.ReferenceEquals(dataField, null))
                    {
                        _logger.LogError("Provider {0}, Property Data doesn't exist ...  ", provider_index);
                    }
                    var dataFieldType = dataField.GetType();
                    var dataDic = dataField as SortedDictionary<string, string>;
                    if (Object.ReferenceEquals(dataDic, null))
                    {
                        var dic = dataField as Dictionary<string, string>;
                        if (Object.ReferenceEquals(dic, null))
                        {
                            _logger.LogError("Provider {0}, Data field is of type {1}, not SortedDictionary or Dictionary ...  ", provider_index, dataFieldType.ToString());
                        }
                        else
                        {
                            foreach (var pair in dataDic)
                            {
                                SetConfiguration(newConfig, pair.Key, pair.Value);
                            }
                        }
                    }
                    else
                    { 
                        foreach (var pair in dataDic)
                        {
                            if (Object.ReferenceEquals( pair.Key, null) || Object.ReferenceEquals(pair.Value, null) )
                            {
                                _logger.LogError("Null encountered at parsing .... ");
                                if (Object.ReferenceEquals(pair.Key, null))
                                {
                                    _logger.LogError("Key is null");
                                }
                                else
                                {
                                    _logger.LogError("Key is {0}", pair.Key);
                                }
                                if (Object.ReferenceEquals(pair.Value, null))
                                {
                                    _logger.LogError("Value is null");
                                }
                                else
                                {
                                    _logger.LogError("Value is {0}", pair.Value);
                                }
                            }
                            else
                            {
                                SetConfiguration(newConfig, pair.Key, pair.Value);
                            }
                        }
                    }
                }
                // string key = entry.Key;
                // var sec = WindowsAuth.Startup.Configuration.GetSection(key);
                // 
            }
            _parsedConfiguration = newConfig;
        }

        /// <summary>
        /// Parse a certain configuration 
        /// </summary>
        /// <param name="config"></param>
        public static void ParseConfiguration(ILoggerFactory logger)
        {
            _logger = logger.CreateLogger("ConfigurationParser");
            ParseConfigurationAgain(); 
            // _first = false; 
        }
    }


    
}
