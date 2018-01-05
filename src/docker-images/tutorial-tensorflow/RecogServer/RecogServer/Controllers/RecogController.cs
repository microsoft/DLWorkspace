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
        public async Task<IActionResult> UploadImage()
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
            _logger.LogInformation($"Upload image: {postdata}");

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
                        using (var stream = new FileStream(filename, FileMode.Create))
                        {
                            await file.CopyToAsync(stream);
                            totalUpload += stream.Length;
                            var logInfo = new { filename = filename, size = stream.Length };
                            _logger.LogInformation($"UploadImage: {logInfo}");

                        }
                    }
                }
                return Ok(new { url = ret });
            }
            catch (Exception ex)
            {
                var errorLog = new { exception = ex.ToString() };
                _logger.LogInformation("UploadImage: {0}", errorLog);
                return Ok(new { error = ex.ToString() });
            }
        }
    }
}
