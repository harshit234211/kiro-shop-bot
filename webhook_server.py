import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from config import BOT_TOKEN, DB_PATH
from logger import logger
import database as db
import gateway as gtw

def send_telegram_notification(telegram_id: int, message: str) -> bool:
    """Sends real-time Telegram message to user upon successful deposit credit."""
    if not BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN" in BOT_TOKEN:
        logger.warning("BOT_TOKEN not configured; skipping Telegram notification.")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logger.info(f"Telegram credit notification sent to user {telegram_id}.")
            return True
        else:
            logger.error(f"Telegram notification API returned status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

class TranzUPIWebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard HTTP request logs to keep terminal logs clean
        logger.info(f"Webhook HTTP {self.command} {self.path} - {args[0]}")

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "status": "ONLINE",
            "service": "Kiro Shop TranzUPI Webhook Server",
            "endpoint": "/webhook/tranzupi"
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        """Handles TranzUPI Webhook Callback notifications."""
        if self.path != "/webhook/tranzupi" and not self.path.startswith("/webhook"):
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        payload = {}
        try:
            if self.headers.get('Content-Type', '').startswith('application/json'):
                payload = json.loads(post_data)
            else:
                # Handle form urlencoded payloads
                from urllib.parse import parse_qs
                parsed = parse_qs(post_data)
                payload = {k: v[0] for k, v in parsed.items()}
        except Exception as e:
            logger.error(f"Failed to parse Webhook POST payload: {e}")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid payload format"}).encode("utf-8"))
            return

        logger.info(f"Received TranzUPI Webhook Payload for Order: {payload.get('order_id')}")

        # Process payment callback & execute atomic wallet transaction
        success, msg = gtw.process_tranzupi_webhook_payload(payload)

        if success:
            order_id = payload.get("order_id")
            dep = db.get_deposit_by_order_id(order_id)
            if dep:
                user_id = dep["telegram_user_id"]
                new_balance = db.get_user_balance(user_id)
                amount = dep["amount"]

                notification_msg = (
                    f"✅ *Deposit Successful!*\n\n"
                    f"💰 *Amount Credited:* ₹{amount:.2f}\n"
                    f"🆔 *Order ID:* `{order_id}`\n"
                    f"💼 *New Wallet Balance:* ₹{new_balance:.2f}\n\n"
                    f"Thank you for shopping at Kiro Shop! 🛍️"
                )
                send_telegram_notification(user_id, notification_msg)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "success": success,
            "message": msg
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

def run_webhook_server(port: int = 5000):
    db.init_db()
    server_address = ('', port)
    httpd = HTTPServer(server_address, TranzUPIWebhookHandler)
    logger.info(f"TranzUPI Webhook Listener Server running on port {port} at path /webhook/tranzupi")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Webhook Listener Server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", "5000"))
    run_webhook_server(port)
