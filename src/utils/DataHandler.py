from config import config

if "datasource" in config and config["datasource"] == "MySQL":
    from MySQLDataHandler import DataHandler
else:
    from SQLDataHandler import DataHandler

