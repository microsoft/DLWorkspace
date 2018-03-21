using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using System.Text;

namespace WebUI.Utils
{
    public class ProcessUtils
    {

        public static async Task<Tuple<int, String, string>> RunProcessAsync(string fileName, string args)
        {
            using (var process = new Process
            {
                StartInfo =
                {
                    FileName = fileName, Arguments = args,
                    UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardOutput = true, RedirectStandardError = true
                },
                EnableRaisingEvents = true
            })
            {
                return await RunProcessAsync(process).ConfigureAwait(false);
            }
        }
        private static Task<Tuple<int, String, string>> RunProcessAsync(Process process)
        {
            var tcs = new TaskCompletionSource<Tuple<int, String, string>>();

            var sbOutput = new StringBuilder();
            var sbError = new StringBuilder();

            process.Exited += (s, ea) => tcs.SetResult(new Tuple<int, string, string>(process.ExitCode, sbOutput.ToString(), sbError.ToString()));
            process.OutputDataReceived += (s, ea) => { if (!String.IsNullOrEmpty(ea.Data)) { sbOutput.AppendLine(ea.Data); }; };
            process.ErrorDataReceived += (s, ea) => { if (!String.IsNullOrEmpty(ea.Data)) { sbError.AppendLine(ea.Data); }; };

            bool started = process.Start();
            if (!started)
            {
                //you may allow for the process to be re-used (started = false) 
                //but I'm not sure about the guarantees of the Exited event in such a case
                throw new InvalidOperationException("Could not start process: " + process);
            }

            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            return tcs.Task;
        }
    }
}
