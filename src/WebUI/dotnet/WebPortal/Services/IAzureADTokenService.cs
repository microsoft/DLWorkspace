using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WindowsAuth.Services
{
    public interface IAzureAdTokenService
    {
        Task<string> GetAccessTokenForAadGraph();
        Task RedeemAuthCodeForAadGraph(string code, string redirect_uri);
        void Clear();
    }
}
