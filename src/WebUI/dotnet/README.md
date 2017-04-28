# WebUI for DL Workspace

1. Development Requirement. 

  If you plan to do development, the following environment is recommended:

  1. Visual Studio 2017 (Install ASP.Net module)
  2. ASP.Net Core
  
  Please complete deployment of master node, through 
  
  ```
  ./deploy.py deploy
  ```
  
  Then, copy the WebUI setting file ./deploy/WebUI/appsettings.json to WebPortal. 
  
  We use Azure AD for authentication. You will need to make sure that the port you are running the WebPortal development is included in the Azure AD authentication. Please contact the author for help. 