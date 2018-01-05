using System;
using System.Collections.Generic;
using System.Text;
using System.IO;

namespace WebUI.Models
{
    public class WebUIConfig
    {
        static private string _configDirectory = null;
        public const string AzureConfigFile = "configAzure.json";
        public const string DatabaseConfigFile = "configDatabase.json";
        public const string GeneralConfigFile = "config.json";
        public const string AppInfoConfigFile = "configApp.json";
        public const string OrderConfigFile = "configOrder.json";
        public static string _configFolder = "RecogServer";

        static string ConfigDirectory
        {
            get
            {
                if (String.IsNullOrEmpty(_configDirectory))
                {
                    var currentDirectory = Directory.GetCurrentDirectory();
                    var parentDirectory = Directory.GetParent(currentDirectory);
                    _configDirectory = Path.Combine(parentDirectory.FullName, _configFolder);
                }
                return _configDirectory;
            }
        }

        public static string GetConfigFile(string filename)
        {
            return Path.Combine(ConfigDirectory, filename);
        }

    }
}
