using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc.Infrastructure;
using Microsoft.Extensions.Logging;
using Microsoft.AspNetCore.Mvc;
using Newtonsoft.Json.Linq;
using Microsoft.Extensions.Primitives;
using System.IO;
using WebUI.Utils;

namespace RecogServer.Controllers
{
    public class RecogController : Controller
    {
        private readonly IActionDescriptorCollectionProvider _provider = null;
        private readonly ILogger _logger = null;
        public RecogController(IActionDescriptorCollectionProvider provider,
            ILoggerFactory logger)
        {
            _provider = provider;
            _logger = logger.CreateLogger("OrderController");
        }

        [HttpPost]
        public async Task<IActionResult> RecogImage()
        {
            var forms = Request.Form;
            var postdata = new JObject();
            foreach (var key in forms.Keys)
            {
                forms.TryGetValue(key, out StringValues values);
                if (!String.IsNullOrEmpty(values[0]))
                {
                    postdata[key] = values[0];
                }
            }
            // _logger.LogInformation($"Recog image: {postdata}");

            Int64 totalUpload = 0L;
            var files = Request.Form.Files;
            JObject ret = new JObject();

            try
            {
                
                foreach (var file in files)
                {
                    if (file.Length > 0)
                    {
                        var filename = file.Name;
                        var ext = Path.GetExtension(filename);
                        var imagename = Guid.NewGuid().ToString() + ext;
                        using (var stream = new FileStream(imagename, FileMode.Create))
                        {
                            await file.CopyToAsync(stream);
                            totalUpload += stream.Length;
                            var logInfo = new { filename = filename, size = stream.Length };
                            _logger.LogInformation($"ReogImage: {logInfo}");
                            var recogprog = "/tensorflow/tensorflow/examples/label_image/label_image.py";
                            var recoggraph = "/tensorflow/tensorflow/examples/label_image/data/inception_v3_2016_08_28_frozen.pb";
                            var label = "/tensorflow/tensorflow/examples/label_image/data/imagenet_slim_labels.txt";
                            var command = $"{recogprog} --graph {recoggraph} --image {imagename} --labels {label}";

                            var tuple = await ProcessUtils.RunProcessAsync("/usr/bin/python3", command);
                            var thisResult = new JObject();
                            thisResult["code"] = tuple.Item1;
                            thisResult["output"] = tuple.Item2;
                            thisResult["error"] = tuple.Item3;
                            ret[filename] = thisResult;
                        }
                    }
                }
                return Ok(new { result = ret });
            }
            catch (Exception ex)
            {
                var errorLog = new { exception = ex.ToString() };
                _logger.LogInformation("ReogImage: {0}", errorLog);
                return Ok(new { error = ex.ToString(), result = ret });
            }
        }
    }
}
