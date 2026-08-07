"""
Sends a promotion broadcast by POSTing to /text/promotion, mimicking the
producer app that kicks off an outbound SMS blast.

Unlike signed_subscribe_curl.py (which fakes an INBOUND Telnyx webhook to
subscribe/unsubscribe a number), this script exercises the OUTBOUND send path:
TextService.send_promotion() -> Telnyx client -> a real SMS to every ACTIVE
subscriber in the database.

Auth: /text/promotion has no Telnyx signature - instead it authenticates the
same way a logged-in user does, so data.email / data.userPassword must be a
real user that exists in the DB (AuthService.login() checks the hash).

  *** This sends REAL text messages to REAL subscribers via Telnyx. ***
  The app must be running with a valid TELNYX_API_KEY and TELNYX_PHONE_NUMBER,
  and there must be at least one ACTIVE subscriber, or nothing goes out.

Usage:
    python send_promotion_curl.py --email you@example.com --password secret
    python send_promotion_curl.py --email you@example.com --password secret \
        --message "Spring sale - 20% off all bookings this week!"
    python send_promotion_curl.py --email ... --password ... \
        --url http://localhost:8000/text/promotion
"""
import argparse
import json
import subprocess
import time
import uuid


def build_payload(message, email, password):
    # Shape dictated by the 'promotionRequest' contract in
    # templates/textContracts.json - requestId/timestamp/requestAction/data/
    # metadata are all required, and data needs message + email + userPassword.
    return {
        "requestId": str(uuid.uuid4()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "requestAction": "sendPromotion",
        "data": {
            "message": message,
            "email": email,
            "userPassword": password,
        },
        "metadata": {
            "source": "send_promotion_curl.py",
            "version": "1.0",
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='https://sinner-booted-unpainted.ngrok-free.dev/text/promotion')
    p.add_argument('--email', default='bloomshobbyshop@gmail.com', help='Login email (must exist in the DB)')
    p.add_argument('--password', default='Wolfpack#55', help='Login password for that user')
    p.add_argument('--message', default='Test promotional message... it is beginning...',
                   help='The SMS body sent to every active subscriber')
    args = p.parse_args()

    body = json.dumps(build_payload(args.message, args.email, args.password))

    print(f'POST {args.url}')
    print(f'  message: {args.message!r}')
    print('  (this triggers a real Telnyx send to all active subscribers)')
    subprocess.run([
        'curl', '-sS', '-X', 'POST', args.url,
        '-H', 'Content-Type: application/json',
        '-w', '\nHTTP %{http_code}\n',
        '--data-binary', body,
    ])


if __name__ == '__main__':
    main()
