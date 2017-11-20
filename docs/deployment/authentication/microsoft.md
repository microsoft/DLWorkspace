# Authentication for Microsoft Corporation.

Deploy.py defines “UserGroups” which will allow all Microsoft employees to access the cluster, find the section below in deploy.py:

```
"UserGroups": {
        # Group name
        "CCSAdmins": {
            ...
        },
        "MicrosoftUsers": {
            ...
        },
        "Live": {
            ...
        },
            "Gmail": {
            ...
        },
    },

    "WebUIregisterGroups": [ "MicrosoftUsers", "Live", "Gmail" ],
    "WebUIauthorizedGroups": [], # [ "MicrosoftUsers", "Live", "Gmail" ],
    "WebUIadminGroups" : [ "CCSAdmins" ],

    "DeployAuthentications" : ...,
    # You should remove WinBindServers if you will use
    # UserGroups for authentication.
    "WinbindServers": ...
```

You can override the default settings by defining your own UserGroups in config.yaml, for example,

```

UserGroups:
  DLWSAdmins:
    Allowed: [ “a@microsoft.com”, “b@microsoft.com” ]
    uid : "10000-10002"
    gid : "1000"


WebUIauthorizedGroups: [ "DLWSAdmins" ]
WebUIadminGroups: [ "DLWSAdmins" ]
DeployAuthentications : ["Corp"]
WinbindServers: []
```

If you are deploying on prem, then aside from UserGroups setting, you have another option -- use http://idwebelements/ to establish a number of security groups. Let's say 'aaa' and 'bbb' are security groups for authorized ordinary users of the cluster, and 'ccc' and 'ddd' are adminstrator users of the cluster.

Within Microsoft, DLWorkspace uses OpenID Connect to establish the identity of the user, and then contacts a [WinBind](https://www.samba.org/samba/docs/man/Samba-HOWTO-Collection/winbind.html) server to check if the user is an administrator and/or authorized user. The reason we use a WinBind server is to share file between machine on the corporate domain and the DL Workspace cluster seamlessly.

Please log onto the WinBind server, and check the gid for security groups 'aaa', 'bbb', 'ccc' and 'ddd'. Let's say that they are 'AAA', 'BBB', 'CCC', 'DDD',

please include the following information in the 'config.yaml' file:

```
WebUIauthorizedGroups : ['aaa', 'bbb' ] # (These are numerical number of the gid returned by the WinBind Server)
WebUIadminGroups : ['ccc','ddd']
WebUIregisterGroups: [ 'MicrosoftUsers' ]
DeployAuthentications : ["Corp"]
```


