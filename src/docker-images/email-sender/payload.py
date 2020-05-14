#!/usr/bin/env python3

import json
import email


class Payload(object):
    """ payload exchanged in queue and http """
    def __init__(self, to, cc, bcc, subject, body):
        self.to = to
        self.cc = cc
        self.bcc = bcc
        self.subject = subject
        self.body = body

    def serialize(self):
        return json.dumps({
            "To": self.to,
            "CC": self.cc,
            "BCC": self.bcc,
            "Subject": self.subject,
            "Body": self.body,
        })

    @classmethod
    def deserialize(cls, payload):
        to = payload.get("To")
        cc = payload.get("CC")
        bcc = payload.get("BCC")
        if to is None or cc is None:
            raise RuntimeError("no To or CC or BCC provided %s" % (payload))

        subject = payload.get("Subject")
        body = payload.get("Body")
        return cls(to, cc, bcc, subject, body)

    def to_email_message(self, smtp_from, default_cc):
        cc = self.cc or ""
        if default_cc is not None:
            cc += "," + default_cc

        msg = email.message.EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = self.to
        msg["CC"] = cc
        msg["BCC"] = self.bcc
        msg["Subject"] = self.subject
        msg.set_content(self.body)
        return msg
