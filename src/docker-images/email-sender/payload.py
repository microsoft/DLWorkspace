#!/usr/bin/env python3

import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.charset import Charset, BASE64
import logging
import base64

logger = logging.getLogger(__name__)

DEFAULT_ENCODING = "utf-8"


class Attachment(object):
    def __init__(self, content, content_type, content_subtype, filename):
        self.content = content # utf-8, base64 represented value, even if it's text
        self.content_type = content_type # main type of mime
        self.content_subtype = content_subtype # sub type of mime
        self.filename = filename # str

    @classmethod
    def deserialize(cls, json_obj):
        content = json_obj.get("Content")
        content_type = json_obj.get("ContentType")
        content_subtype = json_obj.get("ContentSubType")
        filename = json_obj.get("FileName")

        if content is None or content_type is None or \
                content_subtype is None or filename is None:
            raise RuntimeError("malformed attachment %s" % (json_obj))

        return cls(content, content_type, content_subtype, filename)

    def serialize(self):
        return {
            "Content": self.content,
            "ContentType": self.content_type,
            "ContentSubType": self.content_subtype,
            "FileName": self.filename
        }

    def to_email_message(self):
        att = MIMENonMultipart(self.content_type,
                               self.content_subtype,
                               charset=DEFAULT_ENCODING)
        att.add_header("Content-Disposition",
                       "attachment",
                       filename=self.filename)
        cs = Charset(DEFAULT_ENCODING)
        cs.body_type = BASE64
        att.set_payload(base64.b64decode(self.content.encode(DEFAULT_ENCODING)),
                        charset=cs)
        return att


class Payload(object):
    """ payload exchanged in queue and http """
    def __init__(self, to, cc, bcc, subject, body, body_type, attachments):
        self.to = to # , seperated list of receipt or None
        self.cc = cc # , seperated list of receipt or None
        self.bcc = bcc # , seperated list of receipt or None
        self.subject = subject # plain text
        self.body = body # plain or html text
        self.body_type = body_type # "plain" or "html"
        self.attachments = attachments # list of attachment

    def serialize(self):
        return json.dumps({
            "To": self.to,
            "CC": self.cc,
            "BCC": self.bcc,
            "Subject": self.subject,
            "Body": self.body,
            "BodyType": self.body_type,
            "Attachments": [a.serialize() for a in self.attachments],
        })

    @staticmethod
    def _is_empty(val):
        return val is None or len(val) == 0

    @classmethod
    def deserialize(cls, payload):
        to = payload.get("To")
        cc = payload.get("CC")
        bcc = payload.get("BCC")
        if Payload._is_empty(to) and Payload._is_empty(
                cc) and Payload._is_empty(bcc):
            raise RuntimeError("no To or CC or BCC provided %s" % (payload))

        subject = payload.get("Subject")
        body = payload.get("Body")
        body_type = payload.get("BodyType", "plain")
        if body_type not in {"plain", "html"}:
            raise RuntimeError("unknown body type %s" % (body_type))

        att = [
            Attachment.deserialize(a) for a in payload.get("Attachments", [])
        ]

        return cls(to, cc, bcc, subject, body, body_type, att)

    def to_email_message(self, smtp_from, default_cc):
        cc = self.cc or ""
        if default_cc is not None:
            cc += "," + default_cc

        msg = MIMEMultipart()
        msg["From"] = smtp_from
        if not Payload._is_empty(self.to):
            msg["To"] = self.to
        if not Payload._is_empty(self.cc):
            msg["CC"] = cc
        if not Payload._is_empty(self.bcc):
            msg["BCC"] = self.bcc
        msg["Subject"] = self.subject
        body = MIMEText(self.body.encode(DEFAULT_ENCODING),
                        self.body_type,
                        _charset=DEFAULT_ENCODING)
        msg.attach(body)

        for att in self.attachments:
            msg.attach(att.to_email_message())
        return msg
