#!/usr/bin/env python3

import sys
import argparse
import faulthandler
import signal
import logging
import smtplib
import yaml
import json
from email.parser import BytesParser

import pika

logger = logging.getLogger(__name__)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def load_smtp_config(path):
    with open(path) as f:
        content = yaml.full_load(f.read())["smtp"]

    return content["smtp_url"], content["smtp_from"], content[
        "smtp_auth_username"], content["smtp_auth_password"], content.get(
            "default_cc")


def gen_callback(smtp_config_path):
    smtp_url, smtp_from, smtp_user, smtp_pass, default_cc = load_smtp_config(
        smtp_config_path)
    parser = BytesParser()

    def callback(ch, method, properties, body):
        with smtplib.SMTP(smtp_url) as smtp_conn:
            smtp_conn.starttls()
            smtp_conn.login(smtp_user, smtp_pass)
            try:
                msg = parser.parsebytes(body)
            except Exception:
                logger.exception("error when parsing body %s, drop it", body)
                # drop malformed message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            try:
                smtp_conn.send_message(msg)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except smtplib.SMTPServerDisconnected:
                logger.error("failed to connect to smtp server, retain message")
            except Exception:
                logger.exception("error when sending email %s", body)

    return callback


def run(args):
    callback = gen_callback(args.smtp)

    credentials = pika.PlainCredentials(args.mq_user, args.mq_pass)

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=args.host,
                                          credentials=credentials))
            channel = connection.channel()

            channel.queue_declare(queue=args.queue, durable=True)
            logger.info("waiting for messages")

            channel.basic_qos(prefetch_count=500)
            channel.basic_consume(queue=args.queue,
                                  on_message_callback=callback)

            channel.start_consuming()
        except pika.exceptions.ProbableAuthenticationError:
            logger.error("authorization failed")
            return 1
        except Exception:
            logger.exception("catch exception when handling messages")


if __name__ == "__main__":
    register_stack_trace_dump()
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue",
                        help="queue name of rabbitmq",
                        default="email")
    parser.add_argument("--host", help="rabbitmq host", required=True)
    parser.add_argument("--mq_user", help="rabbitmq user", required=True)
    parser.add_argument("--mq_pass", help="rabbitmq pass", required=True)
    parser.add_argument("--smtp", help="path to smtp config", required=True)
    args = parser.parse_args()

    sys.exit(run(args))
