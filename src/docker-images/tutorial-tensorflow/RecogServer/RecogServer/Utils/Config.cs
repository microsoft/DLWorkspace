using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.IO;
using Utils.Json;

namespace WebUI.Utils
{
    public class AuthenticationSetting
    {
        public static bool AllowLocal = false;
    }

    public class Config
    {
        public static JObject Current = null;
        public static JObject Set(Stream config)
        {
            Current = JsonUtils.Read(config);
            return Current;
        }
        public static JToken GetJToken(string entryname)
        {
            return JsonUtils.GetJToken(entryname, Current);
        }

    }
}
