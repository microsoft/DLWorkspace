# Authentication for Microsoft Corporation. 

When using DL Workspace for Microsoft groups, please use http://idwebelements/ to establish a number of security groups. Let's say 'aaa' and 'bbb' are security groups for authorized ordinary users of the cluster, and 'ccc' and 'ddd' are adminstrator users of the cluster. 

Within Microsoft, DLWorkspace uses OpenID Connect to establish the identity of the user, and then contacts a [WinBind](https://www.samba.org/samba/docs/man/Samba-HOWTO-Collection/winbind.html) server to check if the user is an administrator and/or authorized user. The reason we use a WinBind server is to share file between machine on the corporate domain and the DL Workspace cluster seamlessly. 

Please log onto the WinBind server, and check the gid for security groups 'aaa', 'bbb', 'ccc' and 'ddd'. Let's say that they are 'AAA', 'BBB', 'CCC', 'DDD',

please include the following information in the 'config.yaml' file:

```
WebUIauthorizedGroups : ['AAA@microsoft.com', 'BBB@microsoft.com' ]
WebUIadminGroups : ['CCC@microsoft.com','DDD@microsoft.com']
WebUIregisterGroups: [ 'MicrosoftUsers' ]
DeployAuthentications : ["Corp"]
```

If you are deploying on Azure, either in Azure Cluster mode or ACS mode, please set:

```
WinbindServers: []
```

DeployAuthentications : ["Corp"] turns on OpenID Connect authentication for Microsoft Corporate users. We have already setup OpenID Connect endpoint across most of Microsoft and Azure regions. Please contact the authors if you observe that OpenID Connect doesn't work for you. 

