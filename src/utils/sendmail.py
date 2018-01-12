import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendmail(email, subject, message, message_html = None):
    server = smtplib.SMTP('smtp-mail.outlook.com', 587)
    server.starttls()
    #Next, log in to the server
    server.login("dlworkspace-notice@outlook.com", "")

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = "DLWorkspace Notice <dlworkspace-notice@outlook.com>"
    msg['To'] = email

    part1 = MIMEText(message, 'plain')
    msg.attach(part1)


    if message_html is not None:
        part2 = MIMEText(message_html, 'html')
        msg.attach(part2)

    #Send the mail
    server.sendmail("dlworkspace-notice@outlook.com", email, msg.as_string())

if __name__ == '__main__':
    sendmail("hongzhi.li@microsoft.com","DLWorkspace Notice", "test!")