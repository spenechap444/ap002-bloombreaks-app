"""
Sends a signed 'YES' (subscribe) or 'STOP' (unsubscribe) webhook to
/text/webhook, mimicking Telnyx.

Telnyx signs "{timestamp}|{raw_body}" with Ed25519, and TextConsumer verifies
it before processing - so a plain curl always gets a 401. This script uses a
local test keypair instead of Telnyx's real key.

First run auto-generates a keypair and prints a TELNYX_PUBLIC_KEY line -
put it in src/main/python/.env and restart the app, then run again.
(Restore the real Telnyx key in .env when you're done testing.)

Usage:
    python signed_subscribe_curl.py                  # subscribe (YES)
    python signed_subscribe_curl.py --text STOP      # unsubscribe
    python signed_subscribe_curl.py --url http://localhost:8000/text/webhook
"""
import argparse
import base64
import json
import os
import subprocess
import time

from nacl.signing import SigningKey

KEY_FILE = os.path.join(os.path.dirname(__file__), '.test_signing_key')


def load_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return SigningKey(base64.b64decode(f.read())), False

    sk = SigningKey.generate()
    with open(KEY_FILE, 'wb') as f:
        f.write(base64.b64encode(sk.encode()))
    return sk, True


def build_payload(from_number, text, to_number):
    return {
        "data": {
            "event_type": "message.received",
            "id": "b301ed3f-1490-491f-995f-6e64e69674d4",
            "occurred_at": "2024-01-15T20:16:07.588+00:00",
            "payload": {
                "direction": "inbound",
                "from": {"carrier": "T-Mobile USA", "line_type": "long_code",
                         "phone_number": from_number},
                "id": "84cca175-9755-4859-b67f-4730d7f58aa3",
                "record_type": "message",
                "text": text,
                "to": [{"carrier": "Telnyx", "line_type": "Wireless",
                        "phone_number": to_number, "status": "webhook_delivered"}],
                "type": "SMS"
            },
            "record_type": "event"
        },
        "meta": {"attempt": 1, "delivered_to": "http://localhost:8000/text/webhook"}
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='https://sinner-booted-unpainted.ngrok-free.dev/text/webhook')
    p.add_argument('--from-number', default='+18609495474')
    p.add_argument('--to-number', default='+14012508015')
    p.add_argument('--text', default='YES', help='YES to subscribe, STOP to unsubscribe')
    args = p.parse_args()

    sk, created = load_or_create_key()
    pub_line = f'TELNYX_PUBLIC_KEY={base64.b64encode(sk.verify_key.encode()).decode()}'
    if created:
        print('Generated new test keypair ->', KEY_FILE)
        print('Put this line in src/main/python/.env, restart the app, then rerun me:')
        print(pub_line)
        return
    # Reminder on every run - a 401 below usually means .env still has a different key.
    print(f'(app .env must contain: {pub_line})')

    # Sign the exact bytes we send - any re-serialization breaks verification.
    body = json.dumps(build_payload(args.from_number, args.text, args.to_number))
    timestamp = str(int(time.time()))
    signature = base64.b64encode(
        sk.sign(f'{timestamp}|{body}'.encode('utf-8')).signature).decode()

    print(f'POST {args.url} text={args.text}')
    subprocess.run([
        'curl', '-s', '-X', 'POST', args.url,
        '-H', 'Content-Type: application/json',
        '-H', f'telnyx-signature-ed25519: {signature}',
        '-H', f'telnyx-timestamp: {timestamp}',
        '--data-binary', body,
    ])
    print()


if __name__ == '__main__':
    main()
