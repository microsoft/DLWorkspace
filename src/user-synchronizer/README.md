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
- `GROUPS_ID`: Required, id list of the groups, seperated by comma (`,`). 
- `WINBIND_URL`: Required, url of the winbind server, for example `http://example.com/domaininfo/GetUserId`
- `DATABASE_URL`: Required, [SQLAlchemy engine URL](https://docs.sqlalchemy.org/en/13/core/engines.html#sqlalchemy.create_engine) of the database.

`.env` is supported if you are using pipenv virtualenv mode.