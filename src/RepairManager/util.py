import smtplib
import logging

def smtp_send_email(smtp_url, login, password, sender, receiver, subject, body):
    message = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (sender, receiver, subject, body)

    try:
        with smtplib.SMTP(smtp_url) as server:
            server.starttls()
            server.login(login, password)
            server.sendmail(sender, receiver, message)
        logging.info('Email Sent')
    except smtplib.SMTPAuthenticationError:
        logging.warning('The server didn\'t accept the user\\password combination.')
    except smtplib.SMTPServerDisconnected:
        logging.warning('Server unexpectedly disconnected')
    except smtplib.SMTPException as e:
        logging.exception('SMTP error occurred: ' + str(e))