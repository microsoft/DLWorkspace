# Frequently Asked Questions (FAQ) for ACS Deployment. 

{% include_relative "../Azure/CommonFAQ.md" %}

## The deployment script returns with error 

    ```
    Deployment failed. {
    "error": {
        "code": "BadRequest",
        "message": "The credentials in ServicePrincipalProfile were invalid...
    ```

    It seems that ACS creation fails from time to time. Please try to rerun the script. If things repeat, please consider to use [Azure Cluster](../Azure/Readme.md) deployment first till we investigate and fix the issue. 