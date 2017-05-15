using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WebPortal.Helper
{
    public class Constants
    {
        public static string AdminConsentKey = "isAzureAdSignUpForTenant";
        public static string TenantNameKey = "TenantSignUpName";
        public static string True = "True";
        public static string False = "False";
        public static string TenantIdClaimType = "http://schemas.microsoft.com/identity/claims/tenantid";
        public static string ObjectIdClaimType = "http://schemas.microsoft.com/identity/claims/objectidentifier";
        public static string Common = "common";
        public static string AdminConsent = "admin_consent";
        public static string Issuer = "iss";
    }
}
