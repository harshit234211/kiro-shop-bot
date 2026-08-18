import random
from typing import Dict, Any, Tuple
import database as db
from logger import logger

def generate_ff_sensitivity(telegram_id: int, order_id: str, brand: str, model: str, variant: str) -> Tuple[Dict[str, Any], str]:
    """
    Generates a unique random Free Fire sensitivity setup strictly within specified ranges.
    Saves the delivery record to the database and returns the data dict + formatted markdown string.
    """
    general = random.randint(85, 100)
    red_dot = random.randint(80, 100)
    scope_2x = random.randint(70, 95)
    scope_4x = random.randint(60, 90)
    sniper = random.randint(40, 70)
    free_look = random.randint(60, 100)
    fire_button = random.randint(38, 60)
    dpi = random.randint(420, 650)
    pointer_speed = random.randint(5, 10)

    # Save to database
    db.save_sensi_delivery(
        telegram_id=telegram_id,
        order_id=order_id,
        brand=brand,
        model=model,
        variant=variant,
        general=general,
        red_dot=red_dot,
        scope_2x=scope_2x,
        scope_4x=scope_4x,
        sniper=sniper,
        free_look=free_look,
        fire_button=fire_button,
        dpi=dpi,
        pointer_speed=pointer_speed
    )

    data = {
        "order_id": order_id,
        "brand": brand,
        "model": model,
        "variant": variant,
        "general": general,
        "red_dot": red_dot,
        "scope_2x": scope_2x,
        "scope_4x": scope_4x,
        "sniper": sniper,
        "free_look": free_look,
        "fire_button": fire_button,
        "dpi": dpi,
        "pointer_speed": pointer_speed
    }

    formatted_msg = (
        f"🎯 *Kiro Sensi Delivered*\n\n"
        f"📱 *Phone:*\n{model}\n\n"
        f"💾 *Variant:*\n{variant}\n\n"
        f"⚡ *General:* {general}\n"
        f"🔴 *Red Dot:* {red_dot}\n"
        f"🎯 *2x Scope:* {scope_2x}\n"
        f"🔭 *4x Scope:* {scope_4x}\n"
        f"🎯 *Sniper Scope:* {sniper}\n"
        f"👀 *Free Look:* {free_look}\n\n"
        f"🔥 *Fire Button Size:* {fire_button}%\n\n"
        f"📏 *DPI:* {dpi}\n\n"
        f"⚡ *Pointer Speed:* {pointer_speed}/10\n\n"
        f"🎮 *Play 3-5 matches for best results.*"
    )

    logger.info(f"Generated FF Sensitivity for Order {order_id} ({model} {variant})")
    return data, formatted_msg
