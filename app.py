import os
import sys
import threading
import logging
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [App]: %(message)s")

app = Flask(__name__)

bot_started = False
bot_lock = threading.Lock()

def start_bot_worker():
    global bot_started
    with bot_lock:
        if not bot_started:
            bot_started = True
            logging.info("🚀 Starting Telegram Bot polling thread in background...")
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                import bot
                bot.main()
            except Exception as e:
                logging.error(f"❌ Error in Telegram Bot thread: {e}", exc_info=e)

@app.route('/')
@app.route('/health')
def health_check():
    return jsonify({
        "status": "ONLINE",
        "service": "Kiro Shop Bot 24/7 Cloud Host",
        "bot_active": bot_started
    }), 200

@app.route('/webhook/tranzupi', methods=['GET', 'POST'])
def tranzupi_webhook():
    try:
        import gateway as gtw
        import database as db
        from webhook_server import send_telegram_notification

        if request.method == 'GET':
            return jsonify({"status": "ONLINE", "endpoint": "/webhook/tranzupi"}), 200

        payload = request.get_json(silent=True) or request.form.to_dict() or {}
        logging.info(f"Received TranzUPI Webhook Payload: {payload}")
        success, msg = gtw.process_tranzupi_webhook_payload(payload)

        if success:
            order_id = payload.get("order_id")
            dep = db.get_deposit_by_order_id(order_id)
            if dep:
                user_id = dep["telegram_user_id"]
                new_bal = db.get_user_balance(user_id)
                notification_msg = (
                    f"✅ *Deposit Successful!*\n\n"
                    f"💰 *Amount Credited:* ₹{dep['amount']:.2f}\n"
                    f"🆔 *Order ID:* `{order_id}`\n"
                    f"💼 *New Wallet Balance:* ₹{new_bal:.2f}\n\n"
                    f"Thank you for shopping at Kiro Shop! 🛍️"
                )
                send_telegram_notification(user_id, notification_msg)

        return jsonify({"success": success, "message": msg}), 200
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Start Bot thread upon application launch
t = threading.Thread(target=start_bot_worker, daemon=True)
t.start()

if __name__ == '__main__':
    port = int(os.getenv("PORT", "10000"))
    app.run(host='0.0.0.0', port=port)
