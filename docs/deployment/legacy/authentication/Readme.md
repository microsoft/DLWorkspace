# Authentication for DL workspace

DL Workspace authentication contains two part:

* Using OpenID, proves that you are a particular user (e.g., the login user is "a@microsoft.com" )
* Check out whether the particular user, e.g., "a@microsoft.com" can use the cluster. 

DL Workspace use [OpenID Connect]https://en.wikipedia.org/wiki/OpenID_Connect, and can use any provider that support OpenID connect. 

Please find configuration of a number of provides below. 

* [Microsoft Corporation](microsoft.md)
* [Gmail](gmail.md)
* [Live.com](live.md)

The “DeployAuthentications” section (first set in deploy.py, then overwritten by config.yaml), defines what OpenID authenication will be deployed on cluster. You can revise DeployAuthentications in config.yaml as:

```
DeployAuthentications: ["Scheme_A", "Scheme_B"]
```

DeployAuthentications : ["Corp"] turns on OpenID Connect authentication for Microsoft Corporate users. We have already setup OpenID Connect endpoint across most of Microsoft and Azure regions. Please contact the authors if you observe that OpenID Connect doesn't work for you.

["Live"] and ["Gmail"] turns on OpenID Connect authentication for Live.com sign-in and Gmail sign-in. You will Configure [Live.com](https://docs.microsoft.com/en-us/aspnet/core/security/authentication/social/microsoft-logins?tabs=aspnetcore2x) sign-in credential and [Gmail](https://docs.microsoft.com/en-us/aspnet/core/security/authentication/social/google-logins?tabs=aspnetcore2x) sign-in credential according to the link. Alternatively, you can contact the authors of DL Workspace to add your deployed endpoint to the existing sign-in credential. 


