#!/usr/bin/env python3

import argparse
import sys
import json
import logging

import payload

import pika

import flask
from flask import Flask
from flask import request
from flask import Response
from flask_cors import CORS

logger = logging.getLogger(__name__)


def put_message(host, queue, payload):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
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


def serve(args):
    app = Flask(__name__)
    CORS(app)

    @app.route("/put_email", methods=["POST"])
    def put_email():
        params = request.get_json(force=True)

        try:
            data = payload.Payload.deserialize(params)
            put_message(args.host, args.queue, data.serialize())
        except Exception as e:
            logger.exception("failed to process %s", params)
            return Response(str(e), status=400)

        return Response("ok", status=201)

    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue",
                        help="queue name of rabbitmq",
                        default="email")
    parser.add_argument("--host", help="rabbitmq host", required=True)
    parser.add_argument("--port", help="port to listen", type=int, default=9095)
    args = parser.parse_args()

    serve(args)
