import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from configparser import ConfigParser

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')


def send_mail(subject, text,
              send_from=config.get('EMAIL', 'FROM'),
              send_to=[e.strip() for e in config.get('EMAIL', 'TO').split(',')],
              cc_to=[e.strip() for e in config.get('EMAIL', 'CC').split(',')] if config.has_option('EMAIL', 'CC') else '',
              bcc_to=[e.strip() for e in config.get('EMAIL', 'BCC').split(',')] if config.has_option('EMAIL', 'BCC') else '',
              files=None,
              server=config.get('EMAIL', 'SERVER') if config.has_option('EMAIL', 'SERVER') else 'localhost'):
    # based on: https://stackoverflow.com/questions/3362600/how-to-send-email-attachments

    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['CC'] = COMMASPACE.join(cc_to)
    msg['BCC'] = COMMASPACE.join(bcc_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    try:
        smtp = smtplib.SMTP(server)
        smtp.sendmail(send_from, send_to+cc_to+bcc_to, msg.as_string())
        smtp.close()
    except Exception as e:
        code, msg = e.args
        print("Failed to send email!")
        print("Error code = {}".format(code))
        print(msg)
