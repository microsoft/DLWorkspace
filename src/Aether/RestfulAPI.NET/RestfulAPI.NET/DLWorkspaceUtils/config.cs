using System;
using System.Collections.Generic;
using System.Text;
using System.IO;
using Newtonsoft.Json;
using System.Xml.Linq;
using System.Runtime.Serialization;

namespace DLWorkspaceUtils
{
    [DataContract]
    class configItem
    {
        [DataMember]
        public string database_hostname;
        [DataMember]
        public string database_username;
        [DataMember]
        public string database_password;
        [DataMember]
        public string database_databasename;
        [DataMember]
        public string clusterId;

    }
    public class config
    {
        private static bool inited = false;
        private static object initLock = new object();
        private static configItem items;
        public static string database_hostname {
            get {
                config.Init();
                return items.database_hostname;
            }
        }

        public static string database_username
        {
            get
            {
                config.Init();
                return items.database_username;
            }
        }

        public static string database_password
        {
            get
            {
                config.Init();
                return items.database_password;
            }
        }

        public static string database_databasename
        {
            get
            {
                config.Init();
                return items.database_databasename;
            }
        }

        public static string clusterId
        {
            get
            {
                config.Init();
                return items.clusterId;
            }
        }

        private static void Init()
        {
            if (!config.inited)
            {
                lock (config.initLock)
                {
                    if (!config.inited)
                    {
                        if (File.Exists("config.json"))
                        {
                            using (StreamReader sr = new StreamReader(new FileStream("config.json", FileMode.Open)))
                            {
                                string configStr = sr.ReadToEnd();
                                sr.Dispose();
                                config.items = JsonConvert.DeserializeObject<configItem>(configStr);
                                config.inited = true;
                            }
                        }
                        else
                        {
                            throw new Exception("Cannot find configuation file: config.json!");
                        }
                    }
                }
            }
        }
    }
}
