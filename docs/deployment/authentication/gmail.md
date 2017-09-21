# Authentication using Gmail 

Google Sign-In can be used as an OpenID Connect provider. Due to restriction of Google Sign-In, the deployed DL Workspace cluster needed to end with a public top-level domain (such as .com or .org). This restriction is placed by [Google](https://console.developers.google.com/) when you try to put the 
Authorized redirect URIs in the Google Sign-In page. 

Please follow the instruction in [setting up Google Sign-In](https://developers.google.com/identity/protocols/OpenIDConnect) to obtain a OAuth 2.0 Credential for Web Application __dlws-auth__ from Google. You will need the following information in the subsequent setup. 

```
Client ID: __Your_Client_ID__.apps.googleusercontent.com 
Client secret: __Your_Client_Secret__
```

Let's assume that the web portal of DL Workspace cluster will run at DNS 'dlws.yourcompany.com:port'. Please put the following entry into the Authorized redirect URIs in Google's development console:
```
http://dlws.yourcompany.com:port/signin-Gmail
```

You will find that Google required that the redirect URIs ends with a public top-level domain, hence the restriction. 

Please include the following information in the 'config.yaml' file:

```
UserGroups:
  DLWSAdmins:
    Allowed: [ "admin1@gmail.com", "admin2@gmail.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"
  DLWSAllowed:
    Allowed: [ "user1@gmail.com", "user2@gmail.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"  
  DLWSRegister:
    Allowed: [ "@gmail.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"  

WebUIregisterGroups: [ "DLWSRegister"]
WebUIauthorizedGroups: [ "DLWSAllowed" ]
WebUIadminGroups: ["DLWSAdmins"]

Authentications: 
  Google:
    DisplayName: Google
    Tenant: __dlws-auth__ (this must match the Web Application registered)
    ClientId: __Your_Client_ID__.apps.googleusercontent.com
    ClientSecret: __Your_Client_Secret__
    AuthorityFormat: https://accounts.google.com
    Scope: "openid email"
    Domains: [ "gmail.com" ]    

DeployAuthentications : ["Google"]

WinbindServers: []
```

Value ccccc defines the gid of the users. Value aaaaa and bbbbb defines the ranges of the uid of the users. 

For this setup, any user with a gmail account can log on to the cluster. They will first appear as unauthorized user. The administrator of the cluster can log in, and use the "Manage User" function to promote an unauthorized user to authorized user or to an administrator. 

If you need help, please contact the maintainers of DL Workspace. If you are just trying to setup a small cluster, we may be able to add your cluster endpoint in our OpenID connect account for the time being for you to quickly start. 
