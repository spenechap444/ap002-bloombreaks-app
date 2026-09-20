"""Unit tests for Telnyx webhook redelivery handling in TextService.

Covers the two fixes:
  1. PROMO broadcasts run in the background, so the webhook returns right away.
  2. Each inbound event ID is claimed once, so a redelivery is a no-op.

No database or network is touched: the DB is a fake, and send_promotion is
patched wherever a test would otherwise call Telnyx.

Run from the repo root:
    python -m unittest discover -s tests -p 'test_*.py'
or just this file:
    python -m unittest tests.text.test_webhook_redelivery -v
"""

import logging
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src' / 'main' / 'python'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Text.py reads these at import / construction time.
os.environ.setdefault('TELNYX_API_KEY', 'test-key')
os.environ.setdefault('TELNYX_PHONE_NUMBER', '+15550000000')
os.environ.setdefault('TELNYX_PUBLIC_KEY', 'dGVzdA==')

from application.consumer.core.facade import Text  # noqa: E402
from application.consumer.core.facade.Text import TextService  # noqa: E402
from application.consumer.core.facade.model.infrastructure.repository.DB import (  # noqa: E402
    DatabaseOperationError,
)

ADMIN = '+15551112222'
PIN = '4321'


class FakeTextDB:
    """Stands in for textDB. The claimed-ID set behaves like the table's
    primary key: a second claim of the same ID returns False."""

    def __init__(self, admins=(ADMIN,), fail_store=False):
        self.claimed = set()
        self.released = []
        self.stored = []
        self.admins = list(admins)
        self.fail_store = fail_store

    def claim_webhook_event(self, event_id, event_type):
        if event_id in self.claimed:
            return False
        self.claimed.add(event_id)
        return True

    def release_webhook_event(self, event_id):
        self.claimed.discard(event_id)
        self.released.append(event_id)

    def store_sms_subscriber(self, subscriber):
        if self.fail_store:
            raise DatabaseOperationError('store failed')
        self.stored.append((subscriber.phone_number, subscriber.status_cd))
        return 0

    def fetch_sms_subscribers(self, status_cd='ACTIVE', admin_flag=None):
        return self.admins if admin_flag == 'Y' else ['+15553334444']


def inbound(event_id, text, sender=ADMIN):
    return {'data': {'event_type': 'message.received', 'id': event_id,
                     'occurred_at': '2026-09-19T22:00:00Z',
                     'payload': {'from': {'phone_number': sender},
                                 'text': text, 'direction': 'inbound'}}}


def drain_executor():
    """Block until every broadcast queued so far has finished. The executor
    has one worker, so a no-op submitted now runs after everything before it."""
    Text._broadcast_executor.submit(lambda: None).result(timeout=5)


def setUpModule():
    logging.getLogger('application.consumer.core.facade.Text').setLevel(logging.CRITICAL)


class TestIdempotency(unittest.TestCase):

    def setUp(self):
        self.db = FakeTextDB()
        self.svc = TextService(self.db)

    def test_first_delivery_is_processed(self):
        self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.assertEqual(self.db.stored, [(ADMIN, 'ACTIVE')])

    def test_redelivery_of_same_event_is_skipped(self):
        self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.assertEqual(len(self.db.stored), 1)

    def test_different_events_are_both_processed(self):
        self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.svc.handle_webhook(inbound('evt-2', 'STOP'))
        self.assertEqual(self.db.stored, [(ADMIN, 'ACTIVE'), (ADMIN, 'INACTIVE')])

    def test_failed_processing_releases_claim_so_retry_runs(self):
        self.db.fail_store = True
        with self.assertRaises(DatabaseOperationError):
            self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.assertEqual(self.db.released, ['evt-1'])

        # Telnyx retries after the 503; this time the DB is back.
        self.db.fail_store = False
        self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.assertEqual(self.db.stored, [(ADMIN, 'ACTIVE')])

    def test_claim_failure_propagates_for_503(self):
        self.db.claim_webhook_event = mock.Mock(side_effect=DatabaseOperationError('down'))
        with self.assertRaises(DatabaseOperationError):
            self.svc.handle_webhook(inbound('evt-1', 'START'))
        self.assertEqual(self.db.stored, [])

    def test_status_events_are_not_claimed(self):
        self.db.claim_webhook_event = mock.Mock()
        payload = {'data': {'event_type': 'message.finalized', 'id': 'evt-9',
                            'occurred_at': 'x',
                            'payload': {'to': [{'phone_number': '+1', 'status': 'delivered'}]}}}
        self.svc.handle_webhook(payload)
        self.db.claim_webhook_event.assert_not_called()


@mock.patch.dict(os.environ, {'ADMIN_SMS_PIN': PIN})
class TestBackgroundBroadcast(unittest.TestCase):

    def setUp(self):
        self.db = FakeTextDB()
        self.svc = TextService(self.db)

    def test_webhook_returns_before_broadcast_finishes(self):
        release = threading.Event()
        started = threading.Event()

        def slow_send(request):
            started.set()
            release.wait(timeout=5)
            return True, 'sent'

        with mock.patch.object(TextService, 'send_promotion', side_effect=slow_send) as send:
            t0 = time.monotonic()
            self.svc.handle_webhook(inbound('evt-p1', f'PROMO {PIN} Big sale tonight'))
            elapsed = time.monotonic() - t0

            self.assertTrue(started.wait(timeout=2), 'broadcast never started')
            self.assertLess(elapsed, 1.0, 'webhook waited on the broadcast')
            release.set()
            drain_executor()

        send.assert_called_once_with({'data': {'message': 'Big sale tonight'}})

    def test_redelivered_promo_broadcasts_once(self):
        with mock.patch.object(TextService, 'send_promotion', return_value=(True, 'sent')) as send:
            self.svc.handle_webhook(inbound('evt-p2', f'PROMO {PIN} Hello'))
            self.svc.handle_webhook(inbound('evt-p2', f'PROMO {PIN} Hello'))
            drain_executor()
        self.assertEqual(send.call_count, 1)

    def test_broadcast_crash_is_logged_not_raised(self):
        with mock.patch.object(TextService, 'send_promotion', side_effect=RuntimeError('boom')), \
             mock.patch.object(Text.logger, 'exception') as log_exc:
            self.svc.handle_webhook(inbound('evt-p3', f'PROMO {PIN} Hello'))
            drain_executor()
        log_exc.assert_called_once()

    def test_bad_pin_sends_nothing(self):
        with mock.patch.object(TextService, 'send_promotion') as send:
            self.svc.handle_webhook(inbound('evt-p4', 'PROMO 0000 Hello'))
            drain_executor()
        send.assert_not_called()

    def test_non_admin_sends_nothing(self):
        with mock.patch.object(TextService, 'send_promotion') as send:
            self.svc.handle_webhook(inbound('evt-p5', f'PROMO {PIN} Hello', sender='+15559999999'))
            drain_executor()
        send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
