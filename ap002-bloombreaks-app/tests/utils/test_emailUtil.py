"""Unit tests for application...infrastructure.utils.emailUtil.Email

No network is touched: smtplib.SMTP is patched, so every test asserts on the
calls the Email class *would* make against a real server.

Run from the repo root:
    python -m unittest discover -s tests -p 'test_*.py'
or just this file:
    python -m unittest tests.utils.test_emailUtil -v
"""

import os
import sys
import unittest
from email import message_from_string
from email.header import decode_header
from pathlib import Path
from unittest import mock

# The application package lives under src/main/python, which is not on sys.path
# when tests run from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src' / 'main' / 'python'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.consumer.core.facade.model.infrastructure.utils.emailUtil import (  # noqa: E402
    Email,
    EmailError,
)

import logging  # noqa: E402
import smtplib  # noqa: E402


def setUpModule():
    """Keep expected error traces out of the test output."""
    module_logger = logging.getLogger(
        'application.consumer.core.facade.model.infrastructure.utils.emailUtil'
    )
    module_logger.addHandler(logging.NullHandler())
    module_logger.propagate = False


SENDER = 'BloomsHobbyShop@gmail.com'
RECIPIENT = 'customer@example.com'
SUBJECT = 'Bloombreaks email validation'
BODY = '<p>hello</p>'


class EmailTestCase(unittest.TestCase):
    """Shared setup: a patched smtplib.SMTP plus a clean environment."""

    def setUp(self):
        env_patcher = mock.patch.dict(
            os.environ,
            {'SMTP_PASSWORD': 'app-password', 'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': '587'},
            clear=False,
        )
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        smtp_patcher = mock.patch('smtplib.SMTP')
        self.mock_smtp = smtp_patcher.start()
        self.addCleanup(smtp_patcher.stop)

        # `with smtplib.SMTP(...) as server:` yields __enter__'s return value.
        self.server = self.mock_smtp.return_value.__enter__.return_value

        self.email = Email(SENDER)

    def sent_message(self):
        """Parses the raw message string handed to server.sendmail()."""
        self.server.sendmail.assert_called_once()
        args, _ = self.server.sendmail.call_args
        return message_from_string(args[2])

    def html_part(self, msg):
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                return part.get_payload(decode=True).decode('utf-8')
        self.fail('No text/html part in the message')


class TestSmtpConversation(EmailTestCase):
    def test_connects_once_to_configured_host_and_port_with_timeout(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.mock_smtp.assert_called_once_with('smtp.gmail.com', 587, timeout=30)
        # A second connect() would tear down the port-587 socket and reopen on 25.
        self.server.connect.assert_not_called()

    def test_starttls_is_negotiated_and_ehlo_repeated_after_handshake(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.server.starttls.assert_called_once()
        self.assertEqual(self.server.ehlo.call_count, 2,
                         'ehlo must be re-sent after STARTTLS resets the session')

    def test_logs_in_with_credentials(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.server.login.assert_called_once_with(SENDER, 'app-password')

    def test_separate_smtp_username_overrides_sender_for_login(self):
        email = Email(SENDER, password='pw', username='relay-user')
        email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.server.login.assert_called_once_with('relay-user', 'pw')

    def test_without_password_it_warns_and_still_attempts_send(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            email = Email(SENDER)
            with self.assertLogs(
                'application.consumer.core.facade.model.infrastructure.utils.emailUtil',
                level='WARNING',
            ) as logs:
                email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.server.login.assert_not_called()
        self.assertIn('SMTP_PASSWORD', '\n'.join(logs.output))

    def test_connection_is_closed_via_context_manager(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.mock_smtp.return_value.__exit__.assert_called_once()

    def test_envelope_uses_sender_and_recipient_list(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        args, _ = self.server.sendmail.call_args
        self.assertEqual(args[0], SENDER)
        self.assertEqual(args[1], [RECIPIENT])

    def test_returns_true_on_success(self):
        self.assertTrue(self.email.send_mail(RECIPIENT, SUBJECT, BODY))


class TestMessageContent(EmailTestCase):
    def test_standard_headers_are_present(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)
        msg = self.sent_message()

        self.assertEqual(msg['From'], SENDER)
        self.assertEqual(msg['To'], RECIPIENT)
        self.assertEqual(msg['Subject'], SUBJECT)
        self.assertIsNotNone(msg['Date'])

    def test_body_is_wrapped_in_well_formed_html(self):
        self.email.send_mail(RECIPIENT, SUBJECT, BODY)
        html = self.html_part(self.sent_message())

        self.assertTrue(html.startswith('<html><body>'))
        self.assertTrue(html.endswith('</body></html>'))
        self.assertIn(BODY, html)

    def test_unicode_subject_is_encoded_and_round_trips(self):
        subject = 'Bloombreaks — vérification ✉'
        self.email.send_mail(RECIPIENT, subject, BODY)
        raw_subject = self.sent_message()['Subject']

        decoded, charset = decode_header(raw_subject)[0]
        self.assertEqual(decoded.decode(charset or 'utf-8'), subject)

    def test_multiple_recipients_are_joined_in_header_and_passed_as_list(self):
        recipients = ['a@example.com', 'b@example.com']
        self.email.send_mail(recipients, SUBJECT, BODY)

        args, _ = self.server.sendmail.call_args
        self.assertEqual(args[1], recipients)
        self.assertEqual(self.sent_message()['To'], 'a@example.com, b@example.com')

    def test_build_message_can_be_inspected_without_sending(self):
        recipients, msg = self.email.build_message(RECIPIENT, SUBJECT, BODY)

        self.assertEqual(recipients, [RECIPIENT])
        self.assertEqual(msg['To'], RECIPIENT)
        self.mock_smtp.assert_not_called()


class TestValidationMessage(EmailTestCase):
    def test_contains_the_security_code_and_headline(self):
        html = self.email.craft_validation_msg('123456')

        self.assertIn('123456', html)
        self.assertIn('Verify your email', html)

    def test_validation_code_survives_into_the_sent_email(self):
        body = self.email.craft_validation_msg('654321')
        self.email.send_mail(RECIPIENT, SUBJECT, body)

        self.assertIn('654321', self.html_part(self.sent_message()))


class TestInputValidation(EmailTestCase):
    def test_newline_in_recipient_is_rejected_before_connecting(self):
        with self.assertRaises(ValueError):
            self.email.send_mail('a@example.com\nBcc: attacker@evil.com', SUBJECT, BODY)

        self.mock_smtp.assert_not_called()

    def test_newline_in_subject_is_rejected(self):
        with self.assertRaises(ValueError):
            self.email.send_mail(RECIPIENT, 'Hi\r\nBcc: attacker@evil.com', BODY)

        self.mock_smtp.assert_not_called()

    def test_empty_recipient_is_rejected(self):
        for bad in ('', '   ', [], [None]):
            with self.subTest(recipient=bad):
                with self.assertRaises(ValueError):
                    self.email.send_mail(bad, SUBJECT, BODY)


class TestFailureHandling(EmailTestCase):
    def test_authentication_failure_is_wrapped_in_email_error(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'bad creds')

        with self.assertRaises(EmailError):
            self.email.send_mail(RECIPIENT, SUBJECT, BODY)

    def test_refused_recipient_is_wrapped_in_email_error(self):
        self.server.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
            {RECIPIENT: (550, b'No such user')}
        )

        with self.assertRaises(EmailError) as ctx:
            self.email.send_mail(RECIPIENT, SUBJECT, BODY)

        self.assertIn(RECIPIENT, str(ctx.exception))

    def test_socket_failure_is_wrapped_in_email_error(self):
        self.mock_smtp.side_effect = OSError('connection refused')

        with self.assertRaises(EmailError):
            self.email.send_mail(RECIPIENT, SUBJECT, BODY)


if __name__ == '__main__':
    unittest.main(verbosity=2)
