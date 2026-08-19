import os
import sys
import threading
import logging
import uuid
import time
import urllib.request
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [App]: %(message)s")
os.environ["RUNNING_UNDER_APP"] = "1"

app = Flask(__name__)

bot_started = False
bot_lock = threading.Lock()

def start_keep_alive():
    """Starts a background thread that pings the server every 3 minutes to prevent Render free-tier sleep."""
    def keep_alive_loop():
        time.sleep(10)
        port = os.getenv("PORT", "10000")
        render_url = os.getenv("RENDER_EXTERNAL_URL", "https://kiro-shop-bot-55yr.onrender.com").rstrip('/') + "/health"
        local_url = f"http://127.0.0.1:{port}/health"

        while True:
            try:
                logging.info(f"💓 Sending 24/7 Keep-Alive ping to {render_url}...")
                req = urllib.request.Request(render_url, headers={"User-Agent": "KiroBotKeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    logging.info(f"✅ Keep-Alive response: {response.status}")
            except Exception as e:
                try:
                    req = urllib.request.Request(local_url, headers={"User-Agent": "KiroBotKeepAlive/1.0"})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        logging.info(f"✅ Local Keep-Alive response: {response.status}")
                except Exception as ex:
                    logging.warning(f"⚠️ Keep-Alive ping warning: {ex}")
            time.sleep(180)

    t = threading.Thread(target=keep_alive_loop, daemon=True)
    t.start()

def start_bot_worker():
    global bot_started
    with bot_lock:
        if bot_started:
            return
        bot_started = True

    start_keep_alive()

    def bot_loop():
        import asyncio
        import bot
        while True:
            try:
                logging.info("🚀 Starting 24/7 Telegram Bot polling loop...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                bot.main()
            except Exception as e:
                logging.error(f"⚠️ Telegram Bot polling disconnected: {e}. Auto-reconnecting in 5s...", exc_info=True)
                time.sleep(5)

    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()

@app.route('/')
@app.route('/health')
def health_check():
    return jsonify({
        "status": "ONLINE",
        "service": "Kiro Shop Bot 24/7 Cloud Host",
        "bot_active": bot_started
    }), 200

@app.route('/download/frag_arena.apk')
def download_frag_arena_apk():
    from flask import send_file
    apk_path = os.path.join(os.path.dirname(__file__), "data", "frag_arena.apk")
    if os.path.exists(apk_path):
        return send_file(apk_path, as_attachment=True, download_name="FragArena_v1.0.apk")
    return jsonify({
        "status": "ONLINE",
        "app": "Frag Arena Tournament App",
        "download_url": "https://kiro-shop-bot-55yr.onrender.com/download/frag_arena.apk",
        "message": "Frag Arena APK ready for download."
    }), 200

@app.route('/webhook/tranzupi', methods=['GET', 'POST'])
def tranzupi_webhook():
    try:
        import gateway as gtw
        import database as db
        import sensi_engine as sensi_eng
        from webhook_server import send_telegram_notification

        if request.method == 'GET':
            return jsonify({"status": "ONLINE", "endpoint": "/webhook/tranzupi"}), 200

        payload = request.get_json(silent=True) or request.form.to_dict() or {}
        logging.info(f"Received TranzUPI Webhook Payload: {payload}")
        order_id = str(payload.get("order_id") or payload.get("orderId") or payload.get("remark") or "").strip()
        status_str = str(payload.get("status", "")).upper()

        if status_str in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED", "1", "TRUE"]:
            # 1. Wallet Deposit Order
            if order_id.startswith("KIR-"):
                success, msg = gtw.process_tranzupi_webhook_payload(payload)
                if success:
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

            # 2. Sensi Order
            elif order_id.startswith("SENSI-"):
                db.mark_sensi_order_paid(order_id)
                order = db.get_sensi_order_by_id(order_id)
                if order:
                    user_id = order["telegram_id"]
                    _, delivered_text = sensi_eng.generate_ff_sensitivity(
                        telegram_id=user_id,
                        order_id=order_id,
                        brand=order["brand"],
                        model=order["model"],
                        variant=order["variant"]
                    )
                    send_telegram_notification(user_id, f"✅ *Payment Auto-Verified via TranzUPI!*\n\n{delivered_text}")

            # 3. Tournament Order
            elif order_id.startswith("TRN-"):
                db.mark_tournament_order_success(order_id)
                order = db.get_tournament_order_by_id(order_id)
                if order:
                    user_id = order["telegram_id"]
                    unlocked_msg = (
                        f"✅ *Payment Auto-Verified via TranzUPI!*\n\n"
                        f"🏆 *Tournament Entry Unlocked.*\n\n"
                        f"👇 Click below to enter:\nhttps://t.me/+4RKa1Af80ghiMTY1"
                    )
                    send_telegram_notification(user_id, unlocked_msg)

            # 4. DK AI Order
            elif order_id.startswith("DKAI-"):
                db.mark_dk_ai_order_success(order_id)
                order = db.get_dk_ai_order_by_id(order_id)
                if order:
                    user_id = order["telegram_id"]
                    unlocked_msg = (
                        f"✅ *Payment Auto-Verified via TranzUPI!*\n\n"
                        f"🤖 *DK AI Assistant Unlocked.*\n\n"
                        f"👇 Click below to enter:\nhttps://t.me/+et_POl-Eqnc4Y2Q9"
                    )
                    send_telegram_notification(user_id, unlocked_msg)

            # 5. Gmail Recovery Order
            elif order_id.startswith("KR-"):
                db.mark_gmail_recovery_paid(order_id)
                req = db.get_gmail_request_by_id(order_id)
                if req:
                    user_id = req["telegram_id"]
                    confirmed_msg = (
                        f"✅ *Payment Auto-Verified via TranzUPI*\n\n"
                        f"Your Gmail recovery request has been submitted.\n\n"
                        f"🆔 *Request ID:* `{order_id}`\n\n"
                        f"Our support team will review your request."
                    )
                    send_telegram_notification(user_id, confirmed_msg)

            # 6. Panel Order
            elif order_id.startswith("PNL-"):
                db.mark_panel_order_success(order_id)
                order = db.get_panel_order_by_id(order_id)
                if order:
                    user_id = order["telegram_id"]
                    key_code = db.generate_bala_mod_key()
                    delivered_msg = (
                        f"✅ *Payment Auto-Verified via TranzUPI!*\n\n"
                        f"🆔 *Order ID:* `{order_id}`\n"
                        f"🔑 *License Key:* `{key_code}`\n\n"
                        f"Your key is ready to use!"
                    )
                    send_telegram_notification(user_id, delivered_msg)

            return jsonify({"success": True, "message": "Payment verified and processed automatically"}), 200

        return jsonify({"success": False, "message": "Ignored non-success status"}), 200
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Start Bot thread upon application launch
t = threading.Thread(target=start_bot_worker, daemon=True)
t.start()

if __name__ == '__main__':
    port = int(os.getenv("PORT", "10000"))
    app.run(host='0.0.0.0', port=port)
