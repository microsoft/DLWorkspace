using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using Microsoft.Practices.EnterpriseLibrary.TransientFaultHandling;
using System.Net;
using Microsoft.IdentityModel.Clients.ActiveDirectory;

namespace WebPortal.Helper
{
    // TODO: This is sample code that needs validation from the WAAD team!
    // based on existing detection strategies
    public class AdalDetectionStrategy : ITransientErrorDetectionStrategy
    {
        private static readonly WebExceptionStatus[] webExceptionStatus =
            new[]
            {
                WebExceptionStatus.ConnectionClosed,
                WebExceptionStatus.Timeout,
                WebExceptionStatus.RequestCanceled
            };

        private static readonly HttpStatusCode[] httpStatusCodes =
            new[]
            {
                HttpStatusCode.InternalServerError,
                HttpStatusCode.GatewayTimeout,
                HttpStatusCode.ServiceUnavailable,
                HttpStatusCode.RequestTimeout
            };

        public bool IsTransient(Exception ex)
        {
            var adalException = ex as AdalException;
            if (adalException == null)
            {
                return false;
            }

            if (adalException.ErrorCode == AdalError.ServiceUnavailable)
            {
                return true;
            }

            var innerWebException = adalException.InnerException as WebException;
            if (innerWebException != null)
            {
                if (webExceptionStatus.Contains(innerWebException.Status))
                {
                    return true;
                }

                if (innerWebException.Status == WebExceptionStatus.ProtocolError)
                {
                    var response = innerWebException.Response as HttpWebResponse;
                    return response != null && httpStatusCodes.Contains(response.StatusCode);
                }
            }

            return false;
        }
    }
}
