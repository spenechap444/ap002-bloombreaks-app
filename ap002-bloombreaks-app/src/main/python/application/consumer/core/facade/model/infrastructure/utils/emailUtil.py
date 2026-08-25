from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from email.header import Header
import smtplib
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_SMTP_HOST = 'smtp.gmail.com'
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_TIMEOUT = 30


class EmailError(Exception):
    """Raised when an outbound email could not be delivered to the SMTP server."""


class Email:
    """Sends transactional email over SMTP + STARTTLS.

    Credentials come from the environment so nothing secret lives in code:
        SMTP_PASSWORD  - required by Gmail (use an App Password, not the account password)
        SMTP_USERNAME  - optional, defaults to the sender address
        SMTP_HOST      - optional, defaults to smtp.gmail.com
        SMTP_PORT      - optional, defaults to 587
        SMTP_TIMEOUT   - optional, defaults to 30 seconds
    """

    def __init__(self, sender, password=None, username=None,
                 host=None, port=None, timeout=None):
        self.__sender = sender
        self.__password = password if password is not None else os.environ.get('SMTP_PASSWORD')
        self.__username = username or os.environ.get('SMTP_USERNAME') or sender
        self.__host = host or os.environ.get('SMTP_HOST', DEFAULT_SMTP_HOST)
        self.__port = int(port or os.environ.get('SMTP_PORT', DEFAULT_SMTP_PORT))
        self.__timeout = int(timeout or os.environ.get('SMTP_TIMEOUT', DEFAULT_SMTP_TIMEOUT))

    @property
    def sender(self):
        return self.__sender

    @staticmethod
    def _reject_header_injection(value, field):
        if '\r' in value or '\n' in value:
            raise ValueError(f'Illegal newline in {field} header: {value!r}')

    @staticmethod
    def _encode_subject(p_subject_i):
        # Only RFC-2047 encode when we have to - plain ASCII subjects stay readable.
        try:
            p_subject_i.encode('ascii')
        except UnicodeEncodeError:
            return Header(p_subject_i, 'utf-8')
        return p_subject_i

    @staticmethod
    def _normalise_recipients(p_recip_i):
        if isinstance(p_recip_i, str):
            recipients = [p_recip_i]
        else:
            recipients = [r for r in p_recip_i]
        recipients = [r.strip() for r in recipients if r and r.strip()]
        if not recipients:
            raise ValueError('At least one recipient is required')
        return recipients

    def build_message(self, p_recip_i, p_subject_i, p_msgbody_i):
        """Builds the MIME message. Split out from send_mail so it can be inspected/tested."""
        recipients = self._normalise_recipients(p_recip_i)
        for recipient in recipients:
            self._reject_header_injection(recipient, 'To')
        self._reject_header_injection(p_subject_i, 'Subject')

        msg = MIMEMultipart('alternative')
        msg['From'] = self.__sender
        msg['To'] = ', '.join(recipients)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = self._encode_subject(p_subject_i)

        html = f'<html><body>{p_msgbody_i}</body></html>'
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        return recipients, msg

    def send_mail(self, p_recip_i, p_subject_i, p_msgbody_i):
        recipients, msg = self.build_message(p_recip_i, p_subject_i, p_msgbody_i)

        try:
            # SMTP(host, port) already opens the connection - calling connect()
            # again would drop this socket and reconnect on the default port 25.
            with smtplib.SMTP(self.__host, self.__port, timeout=self.__timeout) as server:
                server.ehlo()      # identify the client
                server.starttls()  # secure the connection using TLS
                server.ehlo()      # re-identify: the TLS handshake resets the session
                if self.__password:
                    server.login(self.__username, self.__password)
                else:
                    logger.warning(
                        'SMTP_PASSWORD is not set - sending unauthenticated. '
                        'Gmail will reject this with "530 Authentication Required".'
                    )
                server.sendmail(self.__sender, recipients, msg.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception('Failed to send mail to %s', recipients)
            raise EmailError(f'Failed to send mail to {recipients}: {exc}') from exc

        logger.info('Sent "%s" to %s', p_subject_i, recipients)
        return True

    def craft_validation_msg(self, p_sec_cd_i) -> str:
        # prepare the html body
        html = '<h1 style="font-size: 24px; font-weight: bold;"> Verify your email</h1>'
        html += '''<p> Thank you for creating an account with Bloom breaks! </p>
                  <p> Please enter this code in the Bloombreaks app to continue! </p>'''
        html += f'<h2 style="font-size: 20px; font-weight: bold;"> {p_sec_cd_i}</h2>'

        return html
