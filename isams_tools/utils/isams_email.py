import logging
import smtplib
import sys
from email.mime.text import MIMEText

from settings import EMAIL, EMAIL_LOGIN, EMAIL_SSL

logger = logging.getLogger('root')


class ISAMSEmail:
    """Creates an email object in order to send it, named so to prevent clashes, it doesn't do anything special"""
    email = None

    def __init__(self, subject, message, to, email_from, cc=None, bcc=None):
        """Contructor for an ISAMSEmail object

        :param subject: email subject
        :param message: email message
        :param to: recipients, command separated
        :param email_from: email sender address
        :param bcc: email BCC recipients
        """
        self.email = MIMEText(message)
        self.email['To'] = to
        self.email['From'] = email_from
        if cc:
            self.email['Cc'] = cc
        else:
            self.email['Cc'] = ''

        if bcc:
            self.bcc_list = EMAIL['bcc'] + bcc
        else:
            self.bcc_list = EMAIL['bcc']

        self.email['Subject'] = subject

        logger.info(
            "Preparing email with the following data: From: {1} To: {0} CC: {4} BCC: {2} Subject: {3}: ".format(
                self.email['To'], self.email['From'], self.bcc_list, self.email['Subject'], self.email['Cc']
            ))

    def send(self):
        """Try to connect to the mail server and send the email"""
        if EMAIL_SSL:
            s = smtplib.SMTP_SSL(EMAIL['server'], EMAIL['port'])
        else:
            s = smtplib.SMTP(EMAIL['server'], EMAIL['port'])

        try:
            if EMAIL_LOGIN:
                s.login(EMAIL['username'], EMAIL['password'])

            # put together recipients - BCC are just recipients not specified in To or CC
            recipients = []
            if self.email['To']:
                recipients = recipients + self.email['To'].split(', ')

            if self.email['Cc']:
                recipients = recipients + self.email['Cc'].split(', ')

            if self.bcc_list:
                recipients = recipients + self.bcc_list.split(', ')

            s.sendmail(self.email['From'], recipients, self.email.as_string())
            s.quit()
            logger.info("Email sent successfully")
        except Exception as exc:
            logger.critical("Mail error: " + str(exc))
            sys.exit(1)

    def __str__(self):
        return str(self.email)