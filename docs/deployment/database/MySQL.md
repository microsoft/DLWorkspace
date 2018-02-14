To use MySQL database in DLWorkspace, please use the following config options:

```
mysql_password: [mysql password (root)]
datasource: MySQL
```

To enable mysql service in infra nodes:
```
./deploy.py kubernetes start mysql
```

[optional] You may also use your own MySQL server in DLWorkspace. To use your own server, use the following config options:
```
mysql_password: [mysql password (root)]
datasource: MySQL
mysql_port: [mysql port]
mysql_username: [username, e.g. root]
mysql_node: [address of your mysql server, e.g. mysql.mydomain.com]
```
