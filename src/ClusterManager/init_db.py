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
    `jobId`              VARCHAR(50)   NOT NULL,
    `familyToken`        VARCHAR(50)   NOT NULL,
    `isParent`           INT           NOT NULL,
    `jobName`            VARCHAR(1024) NOT NULL,
    `userName`           VARCHAR(255)  NOT NULL,
    `vcName`             VARCHAR(255)  NOT NULL,
    `jobStatus`          VARCHAR(255)  NOT NULL DEFAULT 'unapproved',
    `jobStatusDetail`    LONGTEXT      NULL,
    `jobType`            VARCHAR(255)  NOT NULL,
    `jobDescriptionPath` TEXT          NULL,
    `jobDescription`     LONGTEXT      NULL,
    `jobTime`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `endpoints`          LONGTEXT      NULL,
    `errorMsg`           LONGTEXT      NULL,
    `jobParams`          LONGTEXT      NOT NULL,
    `jobMeta`            LONGTEXT      NULL,
    `jobLog`             LONGTEXT      NULL,
    `jobLogCursor`       LONGTEXT      NULL,
    `retries`            INT           NULL     DEFAULT 0,
    `lastUpdated`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `priority`           INT           NOT NULL DEFAULT 100,
    `insight`            LONGTEXT      NULL,
    `repairMessage`      LONGTEXT      NULL,
    PRIMARY KEY (`id`),
    UNIQUE (`jobId`),
    INDEX  (`userName`),
    INDEX  (`vcName`),
    INDEX  (`jobTime`),
    INDEX  (`jobId`),
    INDEX  (`jobStatus`)
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
    `storageType`      VARCHAR(255) NOT NULL,
    `url`              VARCHAR(255) NOT NULL,
    `metadata`         TEXT         NOT NULL,
    `vcName`           VARCHAR(255) NOT NULL,
    `defaultMountPath` VARCHAR(255) NOT NULL,
    `time`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT vc_url       UNIQUE(`vcName`, `url`),
    CONSTRAINT vc_mountPath UNIQUE(`vcName`, `defaultMountPath`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `vc`
(
    `id`               INT          NOT     NULL              AUTO_INCREMENT,
    `vcName`           VARCHAR(255) NOT     NULL              UNIQUE,
    `parent`           VARCHAR(255) DEFAULT NULL,
    `quota`            VARCHAR(255) NOT     NULL,
    `metadata`         TEXT         NOT     NULL,
    `resourceQuota`    TEXT         NOT     NULL,
    `resourceMetadata` TEXT         NOT     NULL,
    `time`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT `hierarchy` FOREIGN KEY (`parent`) REFERENCES `vc` (`vcName`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `identity`
(
    `id`           INT          NOT NULL AUTO_INCREMENT,
    `identityName` VARCHAR(255) NOT NULL UNIQUE,
    `uid`          INT          NOT NULL,
    `gid`          INT          NOT NULL,
    `groups`       mediumtext   NOT NULL,
    `public_key`   TEXT         NOT NULL,
    `private_key`  TEXT         NOT NULL,
    `time`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE(`identityName`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS  `acl`
(
    `id`           INT          NOT NULL AUTO_INCREMENT,
    `identityName` VARCHAR(255) NOT NULL,
    `identityId`   INT          NOT NULL,
    `resource`     VARCHAR(255) NOT NULL,
    `permissions`  INT          NOT NULL,
    `isDeny`       INT          NOT NULL,
    `time`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT identityname_resource UNIQUE(`identityName`, `resource`)
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
