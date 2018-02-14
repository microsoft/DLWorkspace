using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace RecogServer
{
    public class Program
    {
        public static void Main(string[] args)
        {
            BuildWebHost(args).Run();
        }

        public static IWebHost BuildWebHost(string[] args)
        {
            var config = new ConfigurationBuilder()
                .SetBasePath(Directory.GetCurrentDirectory())
                .AddJsonFile("hosting.json", optional: true)
                .AddCommandLine(args)
                .Build();

            return WebHost.CreateDefaultBuilder(args)
                .UseConfiguration(config)
                .CaptureStartupErrors(true)
                .UseKestrel(options =>
                {
                    /*
                    options.Listen(IPAddress.Any, 443, listenOptions =>
                    {
                        listenOptions.UseHttps("server.pfx");
                    });*/
                })
                .UseStartup<Startup>()
                .Build();
        }
    }
}
