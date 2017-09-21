# Frequently Asked Questions (FAQ) for Authetnication

## I don't see the log in option for (Gmail, Live.com, etc..)

Please check if you have properly configured [authentication](../authentication/Readme.md), and include the authentication option in the [config.yaml](../configuration/Readme.md) file. 

## I am the administrator, and when I log in, I got the message "You are not an authorized user to this cluster!"

* Please check if you have logged into the intended account. You may have multiple Gmail/Live/Corp account, and the browser may have cached an account which is not the account you intend to use. You may need to open an [Edge (inprivate mode)](https://support.microsoft.com/en-us/help/4026200/windows-browse-inprivate-in-microsoft-edge) or [Chrome (incognito mode)](https://support.google.com/chrome/answer/95464?co=GENIE.Platform%3DAndroid&hl=en) to allow you to use the correct account. 
* Please check [authentication configuration](../authentication/Readme.md) and see if your account has been added as the administrator account for the deployed cluster. 
* Please note that when WinBind server is used, (i.e., WinbindServers is not []), you will need to specify WebUIregisterGroups, WebUIauthorizedGroups, WebUIadminGroups via numeric gid code which determines the users that will be authorized to use the cluster. Only when WinbindServers is [], you can use group membership relation to specify WebUIregisterGroups, WebUIauthorizedGroups, WebUIadminGroups. 

## I am an user, and when I log in, I got the message "You are not an authorized user to this cluster!"

* Please check if you have logged into the intended account. You may have multiple Gmail/Live/Corp account, and the browser may have cached an account which is not the account you intend to use. You may need to open an [Edge (inprivate mode)](https://support.microsoft.com/en-us/help/4026200/windows-browse-inprivate-in-microsoft-edge) or [Chrome (incognito mode)](https://support.google.com/chrome/answer/95464?co=GENIE.Platform%3DAndroid&hl=en) to allow you to use the correct account. 
* Please contact admin of the cluster, and asked him/her to add you as an authorized user to the cluster. 

## I clicked the link of a log in provider, but it doesn't do anything. 

* Sometime, the OpenID connect provider is not functioning. Please click the link again, to see if the log in works. 
 