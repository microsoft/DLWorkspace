#!/usr/bin/env python3

import logging
import os
import sys

import mysql.connector

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from config import config

logger = logging.getLogger(__name__)

db = "DLWSCluster-%s" % config["clusterId"]
host = config["mysql"]["hostname"]
username = config["mysql"]["username"]
password = config["mysql"]["password"]

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
    level=logging.INFO)

conn = mysql.connector.connect(user=username, password=password, host=host)
sql = """
CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET 'utf8'
""" % (db)

cursor = conn.cursor()
cursor.execute(sql)

logger.info("created db %s if not exist", db)

conn.commit()
conn.close()

conn = mysql.connector.connect(user=username,
                               password=password,
                               host=host,
                               database=db)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS `jobs`
(
    `id`                 INT           NOT NULL AUTO_INCREMENT,
    `jobid`              VARCHAR(50)   NOT NULL,
    `familytoken`        VARCHAR(50)   NOT NULL,
    `isparent`           INT           NOT NULL,
    `jobname`            VARCHAR(1024) NOT NULL,
    `username`           VARCHAR(255)  NOT NULL,
    `vcname`             VARCHAR(255)  NOT NULL,
    `jobstatus`          VARCHAR(255)  NOT NULL DEFAULT 'unapproved',
    `jobstatusdetail`    LONGTEXT      NULL,
    `jobtype`            VARCHAR(255)  NOT NULL,
    `jobdescriptionpath` TEXT          NULL,
    `jobdescription`     LONGTEXT      NULL,
    `jobtime`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `endpoints`          LONGTEXT      NULL,
    `errormsg`           LONGTEXT      NULL,
    `jobparams`          LONGTEXT      NOT NULL,
    `jobmeta`            LONGTEXT      NULL,
    `joblog`             LONGTEXT      NULL,
    `joblogcursor`       LONGTEXT      NULL,
    `retries`            INT           NULL     DEFAULT 0,
    `lastupdated`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `priority`           INT           NOT NULL DEFAULT 100,
    `insight`            LONGTEXT      NULL,
    `repairMessage`      LONGTEXT      NULL,
    PRIMARY KEY (`id`),
    UNIQUE (`jobid`),
    INDEX  (`username`),
    INDEX  (`vcname`),
    INDEX  (`jobtime`),
    INDEX  (`jobid`),
    INDEX  (`jobstatus`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `clusterstatus`
(
    `id`     INT      NOT NULL AUTO_INCREMENT,
    `status` LONGTEXT NOT NULL,
    `time`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX(`time`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `storage`
(
    `id`               INT          NOT NULL AUTO_INCREMENT,
    `storagetype`      VARCHAR(255) NOT NULL,
    `url`              VARCHAR(255) NOT NULL,
    `metadata`         TEXT         NOT NULL,
    `vcname`           VARCHAR(255) NOT NULL,
    `defaultmountpath` VARCHAR(255) NOT NULL,
    `time`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT vc_url       UNIQUE(`vcname`, `url`),
    CONSTRAINT vc_mountpath UNIQUE(`vcname`, `defaultmountpath`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `vc`
(
    `id`               INT          NOT     NULL              AUTO_INCREMENT,
    `vcname`           VARCHAR(255) NOT     NULL              UNIQUE,
    `parent`           VARCHAR(255) DEFAULT NULL,
    `quota`            VARCHAR(255) NOT     NULL,
    `metadata`         TEXT         NOT     NULL,
    `resourcequota`    TEXT         NOT     NULL,
    `resourcemetadata` TEXT         NOT     NULL,
    `time`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT `hierarchy` FOREIGN KEY (`parent`) REFERENCES `vc` (`vcname`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `identity`
(
    `id`           INT          NOT NULL AUTO_INCREMENT,
    `identityname` VARCHAR(255) NOT NULL UNIQUE,
    `uid`          INT          NOT NULL,
    `gid`          INT          NOT NULL,
    `groups`       mediumtext   NOT NULL,
    `public_key`   TEXT         NOT NULL,
    `private_key`  TEXT         NOT NULL,
    `time`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE(`identityname`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `acl`
(
    `id`           INT          NOT NULL AUTO_INCREMENT,
    `identityname` VARCHAR(255) NOT NULL,
    `identityid`   INT          NOT NULL,
    `resource`     VARCHAR(255) NOT NULL,
    `permissions`  INT          NOT NULL,
    `isdeny`       INT          NOT NULL,
    `time`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT identityname_resource UNIQUE(`identityname`,`resource`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `templates`
(
    `id`    INT          NOT NULL AUTO_INCREMENT,
    `name`  VARCHAR(255) NOT NULL,
    `scope` VARCHAR(255) NOT NULL COMMENT '"master", "vc:vcname" or "user:username"',
    `json`  TEXT         NOT NULL,
    `time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT name_scope UNIQUE(`name`, `scope`)
);
""")

cursor.close()
conn.commit()

logger.info("created all tables from db %s if not exist", db)

conn.close()
