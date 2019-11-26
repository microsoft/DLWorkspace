# user-synchronizer
Synchronize user information from Microsoft Graph / WinBind to database.

## Get Started

```shell
pipenv install
pipenv run start
```

## Configuration

It uses environment variables to configure the behavior of the service:

- `LOG_LEVEL`: Optional, log level of the logger, default `INFO`
- `LOG_FILE`: Optional, log file path of the logger
- `TENANT_ID`: Required, tenant id of Azure Active Directory
- `CLIENT_ID`: Required, application (client) id of the Azure Active Directory app.
- `CLIENT_SECRET`: Required, client secret of the Azure Active Directory app.
- `RESTFULAPI_URL`: Required, url of the restfulapi service, for example `http://restfulapi.com`
- `DOMAIN_OFFSET_FILE`: Optional, a yaml file record domain offset map, with the following format
    ```yaml
    '*': 900000000 # default offset
    domain.name: 100000000 # specific domain offset
    ```

`.env` is supported if you are using pipenv virtualenv mode.
