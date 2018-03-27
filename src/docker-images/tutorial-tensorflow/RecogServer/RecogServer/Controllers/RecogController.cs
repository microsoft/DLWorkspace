using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
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
        private static int nWait = 0;
        private static int maxWait = 10;
        private static SemaphoreSlim sem = new SemaphoreSlim(1);
        private static Tuple<String, String> model = null; 


        private readonly IActionDescriptorCollectionProvider _provider = null;
        private readonly ILogger _logger = null;

        private static Tuple<String,String> Model
        {
            get
            {
                if ( !Object.ReferenceEquals(model,null))
                {
                    return model; 
                } else
                {
                    var customdir = "/custom/model";
                    var filesInDir = Directory.GetFiles(customdir);
                    var models = new Dictionary<String, Tuple<String, String>>(StringComparer.OrdinalIgnoreCase);
                    foreach (var onefile in filesInDir)
                    {
                        Console.WriteLine($"Examine {onefile} .");
                        string extModels = Path.GetExtension(onefile);
                        string fname = Path.GetFileName(onefile);
                        char[] splitchars = new char[] { '_', '-' };
                        string baseModels = fname.Split(splitchars)[0];
                        var tuple = new Tuple<String, String>(null, null);
                        if (models.TryGetValue(baseModels, out var tuple1))
                        {
                            tuple = tuple1;
                        }
                        if (String.Compare(extModels, ".pb", true) == 0)
                        {
                            Console.WriteLine($"Find pb file {onefile} .");
                            tuple = new Tuple<String, String>(onefile, tuple.Item2);
                        }
                        if (String.Compare(extModels, ".txt", true) == 0)
                        {
                            Console.WriteLine($"Find label file {onefile} .");
                            tuple = new Tuple<String, String>(tuple.Item1, onefile);
                        }
                        models[baseModels] = tuple;
                    }
                    Tuple<String, String> useModel = null;
                    foreach (var pair in models)
                    {
                        var tuple = pair.Value;
                        if (!String.IsNullOrEmpty(tuple.Item1) && !String.IsNullOrEmpty(tuple.Item2))
                        {
                            useModel = tuple;
                        }
                    }
                    if ( Object.ReferenceEquals(useModel,null))
                    {
                        // No need to search again next time. 
                        model = new Tuple<string, string>(null, null);
                    }
                    else
                    {
                        var modelName = useModel.Item1;
                        var labelName = useModel.Item2;
                        model = new Tuple<String,String>(modelName, labelName);
                        Console.WriteLine($"Use TF model {model.Item1}, {model.Item2}");
                    }
                    return model; 
                }
            }
        }


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
                            int nWait = Interlocked.Increment ( ref RecogController.nWait);
                            var thisResult = new JObject();
                            if ( nWait < RecogController.maxWait)
                            {
                                try {
                                    await sem.WaitAsync();
                                    var tuple = await ProcessUtils.RunProcessAsync("/usr/bin/python3", command);
                                    sem.Release();
                                    thisResult["code"] = tuple.Item1;
                                    thisResult["output"] = tuple.Item2;
                                    thisResult["error"] = tuple.Item3;
                                    _logger.LogInformation($"Image Recog, code=={tuple.Item1}, output=={tuple.Item2}, error = {tuple.Item3}");
                                } catch (Exception )
                                {}
                            } else 
                            {
                                thisResult["error"] = $"Too many recognition items: {nWait}, not waiting. ";
                            }
                            Interlocked.Decrement(ref RecogController.nWait);

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

        [HttpPost]
        public async Task<IActionResult> CustomRecog()
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
                            _logger.LogInformation($"CustomRecog: {logInfo}");
                            var recogprog = "/tensorflow/tensorflow/examples/label_image/label_image.py";
                            var thisResult = new JObject();
                            var useModel = RecogController.Model;
                            if ( String.IsNullOrEmpty(useModel.Item1) || String.IsNullOrEmpty(useModel.Item2) )
                            {
                                thisResult["output"] = "Customized model hasn't been loaded. ";
                                
                            }
                            else {
                                var recoggraph = useModel.Item1;
                                var label = useModel.Item2;

                                var command = $"{recogprog} --graph {recoggraph} --image {imagename} --labels {label} --input_layer=Mul --output_layer=final_result --input_mean=128 --input_std=128";
                                int nWait = Interlocked.Increment(ref RecogController.nWait);
                                
                                if (nWait < RecogController.maxWait)
                                {
                                    try
                                    {
                                        await sem.WaitAsync();
                                        var tuple = await ProcessUtils.RunProcessAsync("/usr/bin/python3", command);
                                        sem.Release();
                                        thisResult["code"] = tuple.Item1;
                                        thisResult["output"] = tuple.Item2;
                                        thisResult["error"] = tuple.Item3;
                                        _logger.LogInformation($"Custom Recog, code=={tuple.Item1}, output=={tuple.Item2}, error = {tuple.Item3}");
                                    }
                                    catch (Exception)
                                    { }
                                }
                                else
                                {
                                    thisResult["output"] = $"Too many recognition items: {nWait}. Please wait and resubmit request.";
                                }
                                Interlocked.Decrement(ref RecogController.nWait);
                            }
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


        [HttpPost]
        public async Task<IActionResult> Detectron()
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
                var foldername = Guid.NewGuid().ToString();
                var imageFolder = Path.Combine("/var/www/html/image", foldername);
                var outputFolder = Path.Combine("/var/www/html/output", foldername);
                Directory.CreateDirectory(imageFolder);
                Directory.CreateDirectory(outputFolder);

                var ext = ".jpg";

                var result = new JObject(); 

                foreach (var file in files)
                {
                    if (file.Length > 0)
                    {
                        var filename = Path.Combine(imageFolder, file.Name);
                        var targetname = Path.Combine("output", foldername, file.Name);

                        var extused = Path.GetExtension(filename);
                        if ( String.IsNullOrEmpty(extused))
                        {
                            extused = ".jpg";
                            ext = ".jpg";
                            filename += extused;
                            targetname += extused + ".pdf";
                        }
                        else
                        {
                            targetname += ".pdf";
                        }
                        using (var stream = new FileStream(filename, FileMode.Create))
                        {
                            await file.CopyToAsync(stream);
                            totalUpload += stream.Length;
                            result[targetname] = filename;
                        }
                    }
                }
                ret["result"] = result; 
                var ext1 = ext.Substring(1);
                            
                var recogprog = "/detectron/tools/infer_simple.py";
                
                var command = $"{recogprog}  --cfg /detectron/configs/12_2017_baselines/e2e_mask_rcnn_R-101-FPN_2x.yaml --output-dir {outputFolder} --image-ext {ext1} --wts /detectron/tools/model_final.pkl {imageFolder}";
                int nWait = Interlocked.Increment(ref RecogController.nWait);

                if (nWait < RecogController.maxWait)
                {
                    try
                    {
                        await sem.WaitAsync();
                        _logger.LogInformation(command);
                        var tuple = await ProcessUtils.RunProcessAsync("/usr/bin/python2", command);
                        sem.Release();
                        ret["code"] = tuple.Item1;
                        ret["output"] = tuple.Item2;
                        ret["error"] = tuple.Item3;
                        _logger.LogInformation($"Detectron, code=={tuple.Item1}, output=={tuple.Item2}, error = {tuple.Item3}");
                        var tuple1 = await ProcessUtils.RunProcessAsync("apache2ctl", "restart");
                    }
                    catch (Exception)
                    { }
                }
                else
                {
                    ret["output"] = $"Too many recognition process running: {nWait}. Please wait and resubmit request.";
                }
                Interlocked.Decrement(ref RecogController.nWait);
                            
                return Ok(new { result = ret });
            }
            catch (Exception ex)
            {
                var errorLog = new { exception = ex.ToString() };
                _logger.LogInformation("Detectron: {0}", errorLog);
                return Ok(new { error = ex.ToString(), result = ret });
            }
        }
    }
}
