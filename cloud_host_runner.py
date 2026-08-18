import os
import sys
import time
import logging
import traceback

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [CloudRunner]: %(message)s")

def run_bot_cloud():
    """Cloud keep-alive supervisor process for 24/7 uptime."""
    logging.info("Starting Kiro Shop Bot Cloud Runner (24/7 Keep-Alive mode)...")

    while True:
        try:
            logging.info("Launching bot main entrypoint...")
            import bot
            bot.main()
            logging.warning("Bot main() finished. Restarting in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Cloud Runner stopped by user.")
            break
        except Exception as e:
            logging.error(f"Error in Cloud Runner loop: {e}\n{traceback.format_exc()}")
            logging.info("Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_bot_cloud()
