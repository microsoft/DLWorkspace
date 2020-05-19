#!/usr/bin/env python3

import argparse
import sys
import json
import logging
import smtpd
import asyncore

import pika

logger = logging.getLogger(__name__)


def get_pika_connection(host, credentials):
    return pika.BlockingConnection(
        pika.ConnectionParameters(host=host, credentials=credentials))


def put_message(host, credentials, queue, payload):
    connection = get_pika_connection(host, credentials)
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)

    channel.basic_publish(
        exchange='',
        routing_key='email',
        body=payload,
        properties=pika.BasicProperties(
            delivery_mode=2, # make message persistent
        ))
    logger.info("put %r" % payload)
    connection.close()


class CustomSMTPServer(smtpd.SMTPServer):
    def __init__(self, local_addr, remote_addr, queue_host, queue_cred,
                 queue_name):
        smtpd.SMTPServer.__init__(self, local_addr, remote_addr)
        self.queue_host = queue_host
        self.queue_cred = queue_cred
        self.queue_name = queue_name

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        try:
            put_message(self.queue_host, self.queue_cred, self.queue_name, data)
        except Exception:
            logger.exception("failed to handle email %s", data)


def serve(args):
    credentials = pika.PlainCredentials(args.mq_user, args.mq_pass)

    try:
        get_pika_connection(args.mq_host, credentials)
    except pika.exceptions.ProbableAuthenticationError:
        logger.error("authorization failed")
        return 1

    server = CustomSMTPServer((args.host, args.port), None, args.mq_host,
                              credentials, args.queue)
    asyncore.loop()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue",
                        help="queue name of rabbitmq",
                        default="email")
    parser.add_argument("--mq_host", help="rabbitmq host", required=True)
    parser.add_argument("--mq_user", help="rabbitmq user", required=True)
    parser.add_argument("--mq_pass", help="rabbitmq pass", required=True)
    parser.add_argument("--host", help="host to listen", required=True)
    parser.add_argument("--port", help="port to listen", type=int, default=9095)
    args = parser.parse_args()

    sys.exit(serve(args))
