# Authentication using Hotmail (or Live.com or Outlook.com) 

Hotmail or Live.com or Outlook.com account can be used as an OpenID Connect provider. 

Please follow the instruction in [setting up Azure AD Sign-In](https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-devquickstarts-openidconnect-nodejs) to Register an app. 

```
Tenant: __Your_Default_Directory_in_Azure__
Client ID: __Your_Application_ID_in_Azure__
Client secret: __Your_Client_Secret__
```

You will create a new Key, and when you save the created key, the secret will appear once. Please save the secret for use in the follows. 
Please put the following entry into the Reply URLs for your registered Web App:
```
http://dlws.yourcompany.com:port/*
```

Microsoft will allow you to use IP address, or localhost, or DNS name as Reply URLs. 

Please include the following information in the 'config.yaml' file:

```
UserGroups:
  DLWSAdmins:
    Allowed: [ "admin1@live.com", "admin2@hotmail.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"
  DLWSAllowed:
    Allowed: [ "user1@outlook.com", "user2@live.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"  
  DLWSRegister:
    Allowed: [ "@live.com", "@hotmail.com", "@outlook.com" ]
    uid : "aaaaa-bbbbb"
    gid : "ccccc"  

WebUIregisterGroups: [ "DLWSRegister"]
WebUIauthorizedGroups: [ "DLWSAllowed" ]
WebUIadminGroups: ["DLWSAdmins"]

Authentications: 
  MSFT:
    DisplayName: Live
    Tenant: __Your_Default_Directory_in_Azure__.onmicrosoft.com
    Client ID: __Your_Application_ID_in_Azure__
    ClientId: __Your_Client_ID__.apps.googleusercontent.com,
    ClientSecret: __Your_Client_Secret__
    AuthorityFormat: "https://login.microsoftonline.com/{0}"
    Domains: [ "live.com", "hotmail.com", "outlook.com" ]    

DeployAuthentications : ["MSFT"]

"WinbindServers": []
```

Value ccccc defines the gid of the users. Value aaaaa and bbbbb defines the ranges of the uid of the users. 

You will need to Azure portal to add user to your registered App to allow them to log in via Live.com authentication. 


