import os
import datetime
from typing import Optional, Any
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, MIN_DEPOSIT_AMOUNT, is_admin, FEATURES
from logger import logger
import database as db
import gateway as gtw
import sensi_engine as sensi_eng

# --- KEYBOARD LAYOUTS ---

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns the primary ReplyKeyboardMarkup for Kiro Shop using FEATURES configuration."""
    buttons = []
    
    if FEATURES.get("wallet", True):
        buttons.append(KeyboardButton("💰 Wallet Balance"))
        buttons.append(KeyboardButton("💳 Deposit"))
    if FEATURES.get("tournament", True):
        buttons.append(KeyboardButton("🏆 Tournament App"))
    if FEATURES.get("sensi", True):
        buttons.append(KeyboardButton("🎯 Sensi Buy"))
    if FEATURES.get("panel", True):
        buttons.append(KeyboardButton("🛒 Panel Buy"))
    if FEATURES.get("gmail_recovery", True):
        buttons.append(KeyboardButton("📧 Gmail Recovery"))
    if FEATURES.get("profile", True):
        buttons.append(KeyboardButton("👤 Profile"))
    if FEATURES.get("spin", True):
        buttons.append(KeyboardButton("🎰 Daily Spin"))
    if FEATURES.get("support", True):
        buttons.append(KeyboardButton("🎧 Support"))
    if FEATURES.get("referral", True):
        buttons.append(KeyboardButton("🔗 Referral"))
    if FEATURES.get("dk_ai", True):
        buttons.append(KeyboardButton("🤖 DK AI Assistant"))
    if FEATURES.get("instagram", True):
        buttons.append(KeyboardButton("📸 @_x_harshit_66"))
        buttons.append(KeyboardButton("📸 @kiro_shop_66"))

    # Build 2 buttons per row layout
    keyboard = []
    row = []
    for btn in buttons:
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_inline_keyboard(back_target: str = "main") -> InlineKeyboardMarkup:
    """Returns inline back navigation button."""
    if back_target == "wallet":
        button_text = "⬅️ Wallet"
        callback_data = "nav_wallet"
    else:
        button_text = "⬅️ Main Menu"
        callback_data = "nav_main"
    return InlineKeyboardMarkup([[InlineKeyboardButton(button_text, callback_data=callback_data)]])

# --- HELPER FUNCTIONS ---

def format_date_str(date_input: Any) -> str:
    """Formats SQLite timestamp into human-readable string (e.g. 17 Aug 2026)."""
    if not date_input:
        return datetime.datetime.now().strftime("%d %b %Y")
    if isinstance(date_input, datetime.datetime):
        return date_input.strftime("%d %b %Y")
    try:
        dt = datetime.datetime.strptime(str(date_input).split(".")[0], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y")
    except Exception:
        return str(date_input)[:10]

# --- COMMAND & MESSAGE HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command, registers user, and shows Main Menu."""
    user = update.effective_user
    if not user:
        return

    # Clear pending state
    context.user_data.clear()

    # Register/retrieve user server-side
    user_record = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    balance = user_record.get("balance", 0.0)

    # Check for Referral deep link payload (/start ref_123456789)
    if context.args and len(context.args) > 0:
        arg_val = context.args[0]
        if arg_val.startswith("ref_"):
            try:
                referrer_id = int(arg_val.replace("ref_", ""))
                if db.record_referral(referrer_id=referrer_id, referred_user_id=user.id):
                    logger.info(f"🔗 [REFERRAL RECORDED] Referred User {user.id} joined via Referrer {referrer_id}")
            except ValueError:
                pass

    logger.info(f"👤 [USER START] User: {user.first_name} (@{user.username or 'N/A'}) | ID: {user.id} | Balance: ₹{balance:.2f}")

    welcome_msg = (
        f"🛍️ *Welcome to Kiro Shop*\n\n"
        f"👤 *User:* {user.first_name}\n"
        f"💰 *Wallet Balance:* ₹{balance:.2f}\n\n"
        f"Select an option from the menu below to get started."
    )

    await update.message.reply_text(
        text=welcome_msg,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

def get_deposit_options_keyboard() -> InlineKeyboardMarkup:
    """Returns quick deposit amount selection buttons including ₹10 option."""
    keyboard = [
        [
            InlineKeyboardButton("💰 ₹10", callback_data="dep_10"),
            InlineKeyboardButton("💰 ₹50", callback_data="dep_50"),
            InlineKeyboardButton("💰 ₹100", callback_data="dep_100")
        ],
        [
            InlineKeyboardButton("💰 ₹200", callback_data="dep_200"),
            InlineKeyboardButton("💰 ₹500", callback_data="dep_500"),
            InlineKeyboardButton("💰 ₹1000", callback_data="dep_1000")
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount Keypad 🔢", callback_data="dep_custom_keypad")
        ],
        [
            InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_numeric_keypad_keyboard(current_val: str = "0") -> InlineKeyboardMarkup:
    """Constructs an in-bot numeric keypad grid for custom amount entry without typing."""
    confirm_text = f"✅ Confirm ₹{current_val}" if current_val and current_val != "0" else "✅ Confirm"
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data="key_1"),
            InlineKeyboardButton("2️⃣", callback_data="key_2"),
            InlineKeyboardButton("3️⃣", callback_data="key_3")
        ],
        [
            InlineKeyboardButton("4️⃣", callback_data="key_4"),
            InlineKeyboardButton("5️⃣", callback_data="key_5"),
            InlineKeyboardButton("6️⃣", callback_data="key_6")
        ],
        [
            InlineKeyboardButton("7️⃣", callback_data="key_7"),
            InlineKeyboardButton("8️⃣", callback_data="key_8"),
            InlineKeyboardButton("9️⃣", callback_data="key_9")
        ],
        [
            InlineKeyboardButton("⌫ Clear", callback_data="key_clear"),
            InlineKeyboardButton("0️⃣", callback_data="key_0"),
            InlineKeyboardButton(confirm_text, callback_data="key_confirm")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Preset Amounts", callback_data="nav_deposit_presets")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_sensi_brands_keyboard() -> InlineKeyboardMarkup:
    """Returns all mobile brands in a single-screen 2-column compact grid with custom input option."""
    all_brands = db.get_sensi_brands()
    keyboard = [
        [InlineKeyboardButton("✏️ Type Custom Phone Name 📱", callback_data="sb_custom_input")]
    ]
    row = []
    for brand in all_brands:
        row.append(InlineKeyboardButton(f"📱 {brand}", callback_data=f"sb_b_{brand}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")])
    return InlineKeyboardMarkup(keyboard)

def get_sensi_models_keyboard(brand: str) -> InlineKeyboardMarkup:
    """Returns all phone models for chosen brand in a single-screen 2-column compact grid (No Pagination)."""
    models = db.get_sensi_models_by_brand(brand)
    keyboard = []
    row = []
    for model in models:
        row.append(InlineKeyboardButton(f"📱 {model}", callback_data=f"sb_m_{model}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Brands", callback_data="sb_b_back")])
    return InlineKeyboardMarkup(keyboard)

def get_sensi_variant_keyboard() -> InlineKeyboardMarkup:
    """Returns RAM + Storage variant selection grid."""
    variants = [
        "4GB + 64GB", "6GB + 128GB",
        "8GB + 128GB", "8GB + 256GB",
        "12GB + 256GB", "16GB + 512GB"
    ]
    keyboard = []
    row = []
    for v in variants:
        row.append(InlineKeyboardButton(f"💾 {v}", callback_data=f"sb_v_{v}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Brands", callback_data="sb_b_back")])
    return InlineKeyboardMarkup(keyboard)

def get_unified_payment_keyboard(order_id: str, price: float, back_callback: str = "nav_main") -> InlineKeyboardMarkup:
    """Returns TranzUPI payment option for all paid features."""
    keyboard = [
        [InlineKeyboardButton(f"🏦 Pay via TranzUPI (₹{price:.0f})", callback_data=f"pay_upi_{order_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=back_callback)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def render_unified_payment_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, item_name: str, price: float, back_callback: str = "nav_main") -> None:
    """Renders the Wallet Payment card across all paid features."""
    user = update.effective_user
    if not user:
        return

    user_rec = db.get_or_create_user(user.id, user.username, user.first_name)
    user_bal = float(user_rec.get("balance", 0.0))

    msg = (
        f"━━━━━━━━━━━━━━━━\n"
        f"💳 *WALLET PAYMENT*\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📦 *Item:* `{item_name}`\n"
        f"💰 *Price:* ₹{price:.0f}\n"
        f"🆔 *Order ID:* `{order_id}`\n\n"
        f"💰 *Your Wallet Balance:* ₹{user_bal:.2f}\n\n"
    )

    if user_bal >= price:
        msg += f"✅ *Sufficient Balance!* Tap *💰 Pay From Wallet* below to complete your order instantly."
        buttons = [
            [InlineKeyboardButton(f"💰 Pay From Wallet (₹{price:.0f})", callback_data=f"pay_wal_{order_id}")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data=back_callback)]
        ]
    else:
        diff = price - user_bal
        msg += f"❌ *Insufficient Wallet Balance!*\nRequired: ₹{price:.0f} | Shortage: ₹{diff:.2f}\n\nTap *💳 Add Funds to Wallet* below to deposit via TranzUPI!"
        buttons = [
            [InlineKeyboardButton("💳 Add Funds to Wallet", callback_data="nav_deposit_presets")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data=back_callback)]
        ]

    markup = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

def get_panel_catalog_keyboard() -> InlineKeyboardMarkup:
    """Returns all Panel Buy catalog items in a single-screen 2-column compact grid (No Pagination)."""
    items, _ = db.get_panel_catalog(page=0, per_page=100)
    keyboard = []
    row = []
    for item in items:
        p_name = item["product_name"]
        row.append(InlineKeyboardButton(f"🔥 {p_name}", callback_data=f"pb_m_{item['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")])
    return InlineKeyboardMarkup(keyboard)

    keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])
    return InlineKeyboardMarkup(keyboard)

def get_panel_checkout_keyboard(order_id: str, price: Optional[float]) -> InlineKeyboardMarkup:
    """Returns payment options or Coming Soon status button for Panel checkout."""
    if price is None or price <= 0:
        keyboard = [
            [InlineKeyboardButton("⏳ Price Not Set / Coming Soon", callback_data="ignore")],
            [InlineKeyboardButton("⬅️ Back to Panel Catalog", callback_data="pb_p_0")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(f"💰 Pay via Wallet Balance (₹{price:.0f})", callback_data=f"pb_wal_{order_id}")],
            [InlineKeyboardButton(f"🏦 Pay via UPI / Gateway (₹{price:.0f})", callback_data=f"pb_upi_{order_id}")],
            [InlineKeyboardButton("⬅️ Back to Panel Catalog", callback_data="pb_p_0")]
        ]
    return InlineKeyboardMarkup(keyboard)

async def handle_deposit_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles click on 💳 Deposit button."""
    user = update.effective_user
    if not user:
        return

    user_record = db.get_or_create_user(user.id, user.username, user.first_name)
    balance = user_record.get("balance", 0.0)

    logger.info(f"💳 [USER ACTION] User: {user.first_name} ({user.id}) opened Deposit Menu")

    msg = (
        f"💳 *Kiro Shop Deposit*\n\n"
        f"👤 *User:* {user.first_name}\n"
        f"💰 *Current Balance:* ₹{balance:.2f}\n\n"
        f"👇 Select a deposit amount below to generate your payment QR Code:"
    )

    await update.message.reply_text(
        text=msg,
        parse_mode="Markdown",
        reply_markup=get_deposit_options_keyboard()
    )

async def handle_deposit_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles click on 📜 Deposit History button."""
    user = update.effective_user
    if not user:
        return

    logger.info(f"📜 [USER ACTION] User: {user.first_name} ({user.id}) viewed Deposit History")
    db.get_or_create_user(user.id, user.username, user.first_name)
    history = db.get_user_deposit_history(telegram_user_id=user.id, limit=10)

    if not history:
        msg = "📜 *Deposit History*\n\nNo deposits found."
    else:
        msg_lines = ["📜 *Deposit History*\n"]
        for record in history:
            formatted_date = format_date_str(record.get("created_at"))
            status_emoji = "📌"
            if record["status"] == "SUCCESS":
                status_emoji = "✅"
            elif record["status"] in ["FAILED", "EXPIRED"]:
                status_emoji = "❌"

            msg_lines.append(
                f"💰 ₹{record['amount']:.0f}\n"
                f"🆔 {record['order_id']}\n"
                f"{status_emoji} {record['status']}\n"
                f"🕐 {formatted_date}\n"
            )
        msg = "\n".join(msg_lines).strip()

    reply_markup = get_back_inline_keyboard("wallet")
    if update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_coming_soon(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str) -> None:
    """Generic handler for features marked as Coming Soon."""
    user = update.effective_user
    if user:
        logger.info(f"🚀 [USER ACTION] User: {user.first_name} ({user.id}) tapped Coming Soon feature '{title}'")

    msg = (
        f"{title}\n\n"
        f"🚀 *Coming Soon*\n\n"
        f"This feature will be available soon."
    )
    await update.message.reply_text(
        text=msg,
        parse_mode="Markdown",
        reply_markup=get_back_inline_keyboard("main")
    )

async def handle_deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    """Validates deposit input and creates pending deposit record."""
    user = update.effective_user
    if not user:
        return

    # Parse and validate amount input
    cleaned_text = user_text.replace("₹", "").replace(",", "").strip()
    try:
        amount = float(cleaned_text)
    except ValueError:
        await update.message.reply_text(
            text="❌ *Invalid Amount*\n\nPlease enter a valid number (e.g. 100).",
            parse_mode="Markdown",
            reply_markup=get_back_inline_keyboard("main")
        )
        return

    if amount < MIN_DEPOSIT_AMOUNT:
        await update.message.reply_text(
            text=f"❌ *Invalid Amount*\n\nMinimum deposit amount is ₹{MIN_DEPOSIT_AMOUNT:.0f}.",
            parse_mode="Markdown",
            reply_markup=get_back_inline_keyboard("main")
        )
        return

async def process_deposit_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user, amount: float) -> None:
    """Core function to create deposit entry and send payment details."""
    db.get_or_create_user(user.id, user.username, user.first_name)
    order_id = gtw.generate_order_id()
    deposit = db.create_deposit(
        telegram_user_id=user.id,
        amount=amount,
        order_id=order_id,
        gateway="TranzUPI"
    )
    logger.info(f"🎉 [DEPOSIT CREATED] User: {user.first_name} ({user.id}) | Order: {order_id} | Amount: ₹{amount:.2f} | Status: PENDING")

    pay_details = gtw.create_tranzupi_payment_link(
        order_id=order_id,
        amount=amount,
        user_name=user.first_name or "Customer"
    )

    msg = (
        f"💳 *Kiro Shop Deposit Initiated*\n\n"
        f"💰 *Amount:* ₹{amount:.2f}\n"
        f"🆔 *Order ID:* `{order_id}`\n"
        f"📌 *Status:* {deposit['status']}\n"
        f"🏦 *Gateway:* TranzUPI (Live)\n\n"
        f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
        f"⚠️ *Instructions:*\n"
        f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to complete payment in Paytm / PhonePe / GPay.\n"
        f"2️⃣ After payment, tap *🔄 Check Payment Status* to instantly credit your wallet balance!"
    )

    pay_url = pay_details.get("payment_url") or f"https://upiqr.in/api/qr?name={urllib.parse.quote(MERCHANT_NAME)}&vpa={TRANZUPI_UPI_ID}&amount={amount:.2f}&note={order_id}"
    buttons = [
        [InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)],
        [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"chk_status_{order_id}")],
        [InlineKeyboardButton("📜 View History", callback_data="view_history")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=msg,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        elif update.message:
            await update.message.reply_text(
                text=msg,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error sending deposit text message: {e}")

async def handle_deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    """Validates deposit input and creates pending deposit record."""
    user = update.effective_user
    if not user:
        return

    # Parse and validate amount input
    cleaned_text = user_text.replace("₹", "").replace(",", "").strip()
    try:
        amount = float(cleaned_text)
    except ValueError:
        await update.message.reply_text(
            text="❌ *Invalid Amount*\n\nPlease enter a valid number (e.g. 100).",
            parse_mode="Markdown",
            reply_markup=get_back_inline_keyboard("main")
        )
        return

    if amount < MIN_DEPOSIT_AMOUNT:
        await update.message.reply_text(
            text=f"❌ *Invalid Amount*\n\nMinimum deposit amount is ₹{MIN_DEPOSIT_AMOUNT:.0f}.",
            parse_mode="Markdown",
            reply_markup=get_back_inline_keyboard("main")
        )
        return

    # Clear awaiting state
    context.user_data["awaiting_deposit_amount"] = False
    await process_deposit_creation(update, context, user, amount)

async def handle_sensi_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiates the Sensi Buy mobile brand selection wizard."""
    user = update.effective_user
    if not user:
        return
    db.get_or_create_user(user.id, user.username, user.first_name)
    price = db.get_sensi_price()
    
    msg = (
        f"🎯 *Kiro Free Fire Sensi Buy*\n\n"
        f"Get a custom high-performance Free Fire sensitivity profile tailored specifically to your device model!\n\n"
        f"🏷️ *Price:* ₹{price:.0f}\n"
        f"📱 *Step 1:* Select your mobile phone brand below:"
    )
    
    markup = get_sensi_brands_keyboard()
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            await context.bot.send_message(chat_id=user.id, text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_sensi_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays user's recent sensitivity purchases."""
    user = update.effective_user
    if not user:
        return
    
    deliveries = db.get_user_sensi_history(user.id, limit=10)
    if not deliveries:
        msg = "📜 *Sensi History*\n\nYou haven't purchased any Sensi setups yet."
        if update.callback_query:
            await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        elif update.message:
            await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        return

    msg = f"📜 *Your Purchased Sensi History ({len(deliveries)} setups)*\n\n"
    for idx, d in enumerate(deliveries, 1):
        date_str = format_date_str(d["created_at"])
        msg += (
            f"*{idx}. {d['model']} ({d['variant']})*\n"
            f"📅 Date: `{date_str}` | Order: `{d['order_id']}`\n"
            f"⚡ Gen: `{d['general']}` | 🔴 RedDot: `{d['red_dot']}` | 🎯 2x: `{d['scope_2x']}` | 🔭 4x: `{d['scope_4x']}`\n"
            f"🎯 Sniper: `{d['sniper']}` | 👀 FreeLook: `{d['free_look']}`\n"
            f"🔥 Fire: `{d['fire_button']}%` | 📏 DPI: `{d['dpi']}` | ⚡ Speed: `{d['pointer_speed']}/10`\n"
            f"-----------------------------------------\n"
        )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

def get_gmail_problem_options_keyboard() -> InlineKeyboardMarkup:
    """Returns interactive inline buttons for selecting Gmail account issue."""
    keyboard = [
        [InlineKeyboardButton("📱 Lost Recovery Phone / 2FA Access", callback_data="gr_prob_Lost Recovery Phone / 2FA Access")],
        [InlineKeyboardButton("🔑 Forgot Password & Recovery Email", callback_data="gr_prob_Forgot Password & Recovery Email")],
        [InlineKeyboardButton("🚨 Hacked Account / Password Changed", callback_data="gr_prob_Hacked Account / Password Changed")],
        [InlineKeyboardButton("🔒 Account Disabled / Security Lock", callback_data="gr_prob_Account Disabled / Security Lock")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_gmail_recovery_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the Gmail Recovery initial warning and confirmation card."""
    user = update.effective_user
    if not user:
        return
    db.get_or_create_user(user.id, user.username, user.first_name)
    fee = db.get_gmail_fee()

    msg = (
        f"📧 *Gmail Recovery*\n\n"
        f"We can help you with a legitimate Gmail recovery request.\n\n"
        f"⚠️ *Never send your Gmail password, OTP, recovery code, cookie, or authentication token.*\n\n"
        f"💰 *Service Fee:* ₹{fee:.0f}\n\n"
        f"Continue?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Continue", callback_data="gr_start_continue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nav_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_gmail_recovery_issue_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays interactive problem selection options after user taps Continue."""
    user = update.effective_user
    if not user:
        return
    fee = db.get_gmail_fee()

    msg = (
        f"📧 *Gmail Recovery Request*\n\n"
        f"Get professional support for recovering your lost or compromised Gmail account.\n\n"
        f"💰 *Service Fee:* ₹{fee:.0f}\n\n"
        f"👇 *Step 1:* Select your account issue from the options below:"
    )
    markup = get_gmail_problem_options_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_profile_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the 👤 Profile card."""
    user = update.effective_user
    if not user:
        return

    db.get_or_create_user(user.id, user.username, user.first_name)
    stats = db.get_user_profile_stats(user.id)

    uname_str = f"@{stats['username']}" if stats['username'] else "Not Set"

    msg = (
        f"👤 *Kiro Shop Profile*\n\n"
        f"🆔 *User ID:* `{stats['telegram_id']}`\n"
        f"👤 *Username:* {uname_str}\n"
        f"💰 *Wallet Balance:* ₹{stats['balance']:.2f}\n"
        f"💳 *Total Deposited:* ₹{stats['total_deposited']:.2f}\n"
        f"🛒 *Total Purchases:* ₹{stats['total_purchases']:.2f}\n"
        f"📊 *Total Orders:* {stats['total_orders']}\n"
        f"📅 *Joined:* {stats['joined_date']}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

async def handle_spin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the 🎰 Daily Spin menu card (Set to Coming Soon)."""
    user = update.effective_user
    if not user:
        return
    db.get_or_create_user(user.id, user.username, user.first_name)

    msg = (
        f"🎰 *Kiro Shop Daily Spin*\n\n"
        f"⏳ *COMING SOON!* 🚀\n\n"
        f"The Daily Spin feature is currently undergoing a major reward upgrade!\n\n"
        f"🎁 Exciting new spin rewards, wallet cashbacks, and bonus points will be unlocked soon.\n\n"
        f"👉 Stay tuned!"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_support_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the 🎧 Support card with direct WhatsApp links."""
    user = update.effective_user
    if not user:
        return

    msg = (
        f"🎧 *Kiro Shop Support*\n\n"
        f"For assistance, contact us on WhatsApp:\n\n"
        f"📱 *7017022966*\n"
        f"📱 *8791984082*\n\n"
        f"Tap a number below:"
    )

    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp 1", url="https://wa.me/917017022966")],
        [InlineKeyboardButton("💬 WhatsApp 2", url="https://wa.me/918791984082")],
        [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_referral_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the 🔗 Referral tracking link card."""
    user = update.effective_user
    if not user:
        return

    db.get_or_create_user(user.id, user.username, user.first_name)
    ref_count = db.get_user_referral_count(user.id)

    bot_username = context.bot.username if context.bot and context.bot.username else "KiroShop_Bot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    msg = (
        f"🔗 *Referral*\n\n"
        f"*Your Referral Link:*\n"
        f"`{ref_link}`\n\n"
        f"👥 *Total Referrals:* {ref_count}\n\n"
        f"ℹ️ *Referral rewards are currently unavailable.*"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

def get_dk_ai_checkout_keyboard(order_id: str, price: float = 99.0) -> InlineKeyboardMarkup:
    """Returns payment options for DK AI Assistant purchase."""
    keyboard = [
        [InlineKeyboardButton(f"💰 Pay From Wallet (₹{price:.0f})", callback_data=f"dk_wal_{order_id}")],
        [InlineKeyboardButton(f"🏦 Pay With UPI (₹{price:.0f})", callback_data=f"dk_upi_{order_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tournament_checkout_keyboard(order_id: str, price: float = 99.0) -> InlineKeyboardMarkup:
    """Returns payment options for Tournament App Entry purchase."""
    keyboard = [
        [InlineKeyboardButton(f"💰 Pay From Wallet (₹{price:.0f})", callback_data=f"tr_wal_{order_id}")],
        [InlineKeyboardButton(f"🏦 Pay With UPI (₹{price:.0f})", callback_data=f"tr_upi_{order_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_tournament_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles 🏆 Tournament App entry (Direct Telegram Group Access)."""
    user = update.effective_user
    if not user:
        return

    db.get_or_create_user(user.id, user.username, user.first_name)

    group_url = "https://t.me/+4RKa1Af80ghiMTY1"

    unlocked_msg = (
        f"🏆 *Kiro Free Fire Tournament App*\n\n"
        f"🎉 *100% Free Access!* Join our official tournament community for daily matches, custom rooms, and prizes!\n\n"
        f"👇 Tap below to enter:"
    )
    keyboard = [
        [InlineKeyboardButton("🏆 JOIN TOURNAMENT 🚀", url=group_url)],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try:
                await context.bot.send_message(chat_id=user.id, text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)
            except Exception as e:
                logger.error(f"Error sending tournament app msg: {e}")
    elif update.message:
        try:
            await update.message.reply_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            await context.bot.send_message(chat_id=user.id, text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)

async def handle_dk_ai_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles 🤖 DK AI Assistant feature access and ₹99 payment unlock."""
    user = update.effective_user
    if not user:
        return

    db.get_or_create_user(user.id, user.username, user.first_name)

    # Check if user has already unlocked access previously
    if db.has_user_unlocked_dk_ai(user.id):
        unlocked_msg = (
            f"✅ *DK AI Assistant Already Unlocked*\n\n"
            f"🤖 *DK AI Assistant*\n\n"
            f"👇 Click below to enter:"
        )
        keyboard = [
            [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
            [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=markup)
        return

    # Not unlocked yet -> Create pending order and show ₹99 payment screen
    order_id = gtw.generate_order_id().replace("KIR-", "DKAI-")
    db.create_dk_ai_order(telegram_id=user.id, price=99.0, order_id=order_id, payment_method="PENDING")

    await render_unified_payment_screen(
        update=update,
        context=context,
        order_id=order_id,
        item_name="DK AI Assistant Access",
        price=99.0,
        back_callback="nav_main"
    )

async def handle_instagram_click(update: Update, context: ContextTypes.DEFAULT_TYPE, handle: str) -> None:
    """Handles Instagram profile link button clicks."""
    user = update.effective_user
    if not user:
        return

    if "_x_harshit_66" in handle:
        url = "https://instagram.com/_x_harshit_66"
        label = "📸 @_x_harshit_66"
    else:
        url = "https://instagram.com/kiro_shop_66"
        label = "📸 @kiro_shop_66"

    msg = (
        f"📸 *Kiro Shop Instagram*\n\n"
        f"Follow us on Instagram for updates, giveaways, and announcements:\n\n"
        f"👉 *{label}*"
    )

    keyboard = [
        [InlineKeyboardButton(label, url=url)],
        [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiates the Panel Buy catalog browser."""
    user = update.effective_user
    if not user:
        return
    db.get_or_create_user(user.id, user.username, user.first_name)

    msg = (
        f"🛒 *Kiro Panel Buy Catalog*\n\n"
        f"Browse premium game cheats, proxy clients, root mods, and certificate panels.\n\n"
        f"👇 Select a panel product below to view details and purchase:"
    )

    markup = get_panel_catalog_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=markup)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main routing function for incoming user text messages."""
    user = update.effective_user
    text = update.message.text.strip() if update.message and update.message.text else ""

    # Check if user was in deposit input flow
    if context.user_data.get("awaiting_deposit_amount"):
        if text.startswith("⬅️") or text in ["💳 Deposit", "📜 Deposit History", "📜 Sensi History", "💰 Wallet Balance"]:
            context.user_data["awaiting_deposit_amount"] = False
        else:
            await handle_deposit_amount_input(update, context, text)
            return

    # Check if user is in Gmail email input flow
    if context.user_data.get("awaiting_gmail_email"):
        if text.startswith("⬅️") or text in ["💳 Deposit", "📜 Deposit History", "💰 Wallet Balance"]:
            context.user_data["awaiting_gmail_email"] = False
        else:
            if "@" not in text or "." not in text:
                await update.message.reply_text("❌ *Invalid Email Address*\n\nPlease enter a valid email address (e.g. `example@gmail.com`).", parse_mode="Markdown")
                return
            email = text.strip()
            context.user_data["awaiting_gmail_email"] = False
            order_id = context.user_data.get("gmail_order_id")

            if order_id:
                db.update_gmail_recovery_email(order_id, email)
                req = db.get_gmail_request_by_id(order_id)
                problem = req["problem_description"] if req else "Account Recovery"
                fee = req["amount"] if req else 299.0
            else:
                problem = context.user_data.get("gmail_problem", "Account Recovery")
                fee = 299.0
                order_id = gtw.generate_order_id().replace("KIR-", "KR-")
                db.create_gmail_recovery_request(
                    telegram_id=user.id,
                    email=email,
                    problem_description=problem,
                    order_id=order_id,
                    payment_method="WALLET",
                    amount=fee
                )
                db.mark_gmail_recovery_paid(order_id)

            msg = (
                f"🎉 *Gmail Recovery Request Submitted!*\n\n"
                f"📧 *Target Email:* `{email}`\n"
                f"📝 *Account Issue:* {problem}\n"
                f"💰 *Fee Paid:* ₹{fee:.0f} (Wallet)\n"
                f"🆔 *Request ID:* `{order_id}`\n\n"
                f"Our technical support team has received your request and will start the recovery process shortly!"
            )
            await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

    # Check if user is in custom Sensi phone input flow
    if context.user_data.get("awaiting_sensi_phone"):
        if text.startswith("⬅️") or text in ["💳 Deposit", "📜 Deposit History", "💰 Wallet Balance"]:
            context.user_data["awaiting_sensi_phone"] = False
        else:
            phone_name = text.strip()
            context.user_data["awaiting_sensi_phone"] = False
            price = db.get_sensi_price()
            order_id = gtw.generate_order_id().replace("KIR-", "SENSI-")
            db.create_sensi_order(
                telegram_id=user.id,
                brand="Custom Phone",
                model=phone_name,
                ram="Standard",
                storage="Standard",
                payment_method="PENDING",
                price=price,
                order_id=order_id
            )
            await render_unified_payment_screen(
                update=update,
                context=context,
                order_id=order_id,
                item_name=f"Free Fire Sensi ({phone_name})",
                price=price,
                back_callback="nav_main"
            )
            return

    # Handle main navigation buttons
    if text == "💳 Deposit":
        await handle_deposit_click(update, context)
    elif text == "📜 Deposit History":
        await handle_deposit_history(update, context)
    elif text == "💰 Wallet Balance":
        user_rec = db.get_or_create_user(user.id, user.username, user.first_name)
        bal = user_rec.get("balance", 0.0)
        msg = f"💰 *Your Kiro Shop Wallet Balance:* ₹{bal:.2f}\n\nTap 💳 Deposit below to add funds."
        await update.message.reply_text(text=msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
    elif text == "📜 Sensi History":
        await handle_sensi_history(update, context)
    elif text == "🎯 Sensi Buy":
        await handle_sensi_start(update, context)
    elif text == "📧 Gmail Recovery":
        await handle_gmail_recovery_start(update, context)
    elif text == "🏆 Tournament App":
        await handle_tournament_app(update, context)
    elif text == "🛒 Panel Buy":
        await handle_panel_start(update, context)
    elif text == "👤 Profile":
        await handle_profile_click(update, context)
    elif text == "🎰 Daily Spin":
        await handle_spin_start(update, context)
    elif text == "🎧 Support":
        await handle_support_click(update, context)
    elif text == "🔗 Referral":
        await handle_referral_click(update, context)
    elif text == "🤖 DK AI Assistant":
        await handle_dk_ai_assistant(update, context)
    elif text == "📸 @_x_harshit_66":
        await handle_instagram_click(update, context, "_x_harshit_66")
    elif text == "📸 @kiro_shop_66":
        await handle_instagram_click(update, context, "kiro_shop_66")
    elif text in ["⬅️ Wallet", "⬅️ Main Menu"]:
        await start_command(update, context)
    else:
        # Fallback response for unhandled text inputs
        await start_command(update, context)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline keyboard interactions safely."""
    query = update.callback_query
    if not query:
        return

    try:
        await query.answer()
    except Exception as e:
        logger.debug(f"Ignored expired callback query answer: {e}")

    data = query.data
    user = query.from_user
    logger.info(f"🔘 [BUTTON PRESS] User: {user.first_name} ({user.id}) pressed button '{data}'")

    if data == "nav_main" or data == "nav_wallet":
        context.user_data.clear()
        user_record = db.get_or_create_user(user.id, user.username, user.first_name)
        balance = user_record.get("balance", 0.0)

        welcome_msg = (
            f"🛍️ *Welcome to Kiro Shop*\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Wallet Balance:* ₹{balance:.2f}\n\n"
            f"Select an option from the menu below to get started."
        )
        if query.message and query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=user.id,
                text=welcome_msg,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            try:
                await query.edit_message_text(text=welcome_msg, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=welcome_msg,
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
    elif data == "view_history":
        await handle_deposit_history(update, context)
    elif data in ["nav_tournament", "btn_tournament"]:
        await handle_tournament_app(update, context)
    elif data == "nav_deposit_presets":
        user_record = db.get_or_create_user(user.id, user.username, user.first_name)
        balance = user_record.get("balance", 0.0)
        msg = (
            f"💳 *Kiro Shop Deposit*\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Current Balance:* ₹{balance:.2f}\n\n"
            f"👇 Select a deposit amount below to generate your payment QR Code:"
        )
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_deposit_options_keyboard())
    elif data == "dep_custom_keypad":
        context.user_data["keypad_val"] = "0"
        msg = (
            f"✏️ *Custom Deposit Amount Keypad*\n\n"
            f"💰 *Entered Amount:* ₹0\n\n"
            f"Tap numbers below to construct your custom deposit amount (Minimum ₹{MIN_DEPOSIT_AMOUNT:.0f}):"
        )
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_numeric_keypad_keyboard("0"))
    elif data.startswith("key_"):
        key = data.replace("key_", "")
        current = context.user_data.get("keypad_val", "0")
        if key == "clear":
            current = "0"
        elif key == "confirm":
            try:
                amt = float(current)
            except ValueError:
                amt = 0.0
            if amt < MIN_DEPOSIT_AMOUNT:
                try:
                    await query.answer(f"❌ Minimum deposit amount is ₹{MIN_DEPOSIT_AMOUNT:.0f}", show_alert=True)
                except Exception:
                    pass
                return
            else:
                context.user_data["keypad_val"] = "0"
                await process_deposit_creation(update, context, user, amt)
                return
        else:
            if current == "0":
                current = key
            else:
                if len(current) < 6:
                    current += key
        
        context.user_data["keypad_val"] = current
        msg = (
            f"✏️ *Custom Deposit Amount Keypad*\n\n"
            f"💰 *Entered Amount:* ₹{current}\n\n"
            f"Tap numbers below to construct your custom deposit amount (Minimum ₹{MIN_DEPOSIT_AMOUNT:.0f}):"
        )
        try:
            await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_numeric_keypad_keyboard(current))
        except Exception:
            pass
    elif data == "nav_deposit_presets":
        user_record = db.get_or_create_user(user.id, user.username, user.first_name)
        balance = user_record.get("balance", 0.0)
        msg = (
            f"💳 *Kiro Shop Wallet Deposit*\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Current Balance:* ₹{balance:.2f}\n\n"
            f"👇 Select a deposit amount below to add funds via TranzUPI:"
        )
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_deposit_options_keyboard())

    elif data.startswith("chk_status_"):
        target_order = data.replace("chk_status_", "")
        dep = db.get_deposit_by_order_id(target_order)
        if not dep:
            await query.answer("❌ Deposit record not found.", show_alert=True)
            return

        if dep["status"] == "SUCCESS":
            new_bal = db.sync_user_balance_integrity(user.id)
            await query.answer(f"✅ Payment already verified! Wallet Balance: ₹{new_bal:.2f}", show_alert=True)
            return

        # Query TranzUPI live API status
        res = gtw.check_tranzupi_order_status(target_order)
        payment_status = str(res.get("payment_status", "PENDING")).upper()
        
        logger.info(f"Manual Check Status for Order {target_order}: Parsed Payment Status={payment_status} | Raw={res}")

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            success, msg = db.credit_wallet_transaction(
                order_id=target_order,
                transaction_id=res.get("txn_id") or "TXN-MANUAL",
                payment_reference=res.get("utr") or "UTR-VERIFIED",
                verified_amount=float(dep["amount"])
            )
            new_bal = db.sync_user_balance_integrity(user.id)
            await query.answer("🎉 Payment Verified! Wallet credited successfully.", show_alert=True)
            updated_msg = (
                f"✅ *Kiro Shop Deposit Successful!*\n\n"
                f"💰 *Amount Credited:* ₹{float(dep['amount']):.2f}\n"
                f"🆔 *Order ID:* `{target_order}`\n"
                f"💼 *New Wallet Balance:* ₹{new_bal:.2f}\n\n"
                f"Your wallet balance has been updated."
            )
            try:
                await query.edit_message_text(text=updated_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
            except Exception:
                pass
        else:
            await query.answer("⌛ Payment not completed yet! Please complete payment via UPI app first, then tap Check Payment Status.", show_alert=True)

    elif data.startswith("sb_regen_"):
        brand = data.replace("sb_regen_", "")
        new_order_id = gtw.generate_order_id().replace("KIR-", "SENSI-")
        data_dict, delivered_text = sensi_eng.generate_ff_sensitivity(
            telegram_id=user.id,
            order_id=new_order_id,
            brand=brand,
            model=brand,
            variant="Standard"
        )
        await query.answer("🔄 Generated new balanced profile!", show_alert=True)
        buttons = [
            [InlineKeyboardButton("🔄 Generate Again", callback_data=f"sb_regen_{brand}")],
            [InlineKeyboardButton("💾 Save Profile", callback_data=f"sb_save_{data_dict['profile_id']}"), InlineKeyboardButton("📤 Share", callback_data=f"sb_share_{data_dict['profile_id']}")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")]
        ]
        await query.edit_message_text(text=delivered_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("sb_save_"):
        profile_id = data.replace("sb_save_", "")
        await query.answer(f"💾 Profile [{profile_id}] saved to your account!", show_alert=True)

    elif data.startswith("sb_share_"):
        profile_id = data.replace("sb_share_", "")
        bot_uname = context.bot.username or "KiroShopBot"
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_uname}&text=Check%20out%20my%20Free%20Fire%20Sensi%20Profile%20[{profile_id}]%20on%20Kiro%20Shop!"
        await query.answer("📤 Share link ready!", show_alert=True)
        keyboard = [
            [InlineKeyboardButton("📲 Share to Telegram Friends", url=share_url)],
            [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
        ]
        await query.edit_message_text(text=f"📤 *Share Profile [{profile_id}]*\n\nTap below to share your custom profile with friends!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "sb_custom_input":
        context.user_data["awaiting_sensi_phone"] = True
        msg = (
            f"✏️ *Custom Phone / Device Name*\n\n"
            f"Please type your exact Phone Model or Device Name below:\n\n"
            f"Example: `Vivo T4x 5G` or `iPhone 15 Pro Max`"
        )
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
    elif data == "sb_b_back":
        await handle_sensi_start(update, context)
    elif data == "sb_m_back":
        brand = context.user_data.get("sensi_brand", "Mobile")
        msg = f"🎯 *Kiro Free Fire Sensi Buy*\n\n📱 *Brand:* {brand}\n📲 *Step 2:* Select your phone model below:"
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_sensi_models_keyboard(brand=brand))
    elif data.startswith("sb_b_"):
        brand = data.replace("sb_b_", "")
        price = db.get_sensi_price()
        order_id = gtw.generate_order_id().replace("KIR-", "SENSI-")

        db.create_sensi_order(
            telegram_id=user.id,
            brand=brand,
            model=f"{brand} Phone",
            ram="Standard",
            storage="Standard",
            payment_method="PENDING",
            price=price,
            order_id=order_id
        )

        await render_unified_payment_screen(
            update=update,
            context=context,
            order_id=order_id,
            item_name=f"Free Fire Sensi ({brand})",
            price=price,
            back_callback="nav_main"
        )
    elif data.startswith("sb_m_"):
        model = data.replace("sb_m_", "")
        price = db.get_sensi_price()
        order_id = gtw.generate_order_id().replace("KIR-", "SENSI-")
        db.create_sensi_order(
            telegram_id=user.id,
            brand="Phone",
            model=model,
            ram="Standard",
            storage="Standard",
            payment_method="PENDING",
            price=price,
            order_id=order_id
        )
        await render_unified_payment_screen(
            update=update,
            context=context,
            order_id=order_id,
            item_name=f"Free Fire Sensi ({model})",
            price=price,
            back_callback="nav_main"
        )

    elif data.startswith("sp_wal_"):
        order_id = data.replace("sp_wal_", "")
        order = db.get_sensi_order_by_id(order_id)
        if not order:
            await query.answer("❌ Sensi order not found.", show_alert=True)
            return

        success, msg = db.process_wallet_sensi_payment(order_id)
        if success:
            await query.answer("🎉 Payment Successful! Delivering sensitivity...", show_alert=True)
            variant = f"{order['ram']} + {order['storage']}"
            _, delivered_text = sensi_eng.generate_ff_sensitivity(
                telegram_id=user.id,
                order_id=order_id,
                brand=order["brand"],
                model=order["model"],
                variant=variant
            )
            await query.edit_message_text(text=delivered_text, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data.startswith("sp_upi_"):
        order_id = data.replace("sp_upi_", "")
        order = db.get_sensi_order_by_id(order_id)
        if not order:
            await query.answer("❌ Sensi order not found.", show_alert=True)
            return

        price = float(order["price"])
        pay_details = gtw.create_tranzupi_payment_link(order_id, price, user.first_name or "Customer")

        msg = (
            f"💳 *Kiro Sensi Gateway Payment*\n\n"
            f"📱 *Device:* {order['model']} ({order['ram']} + {order['storage']})\n"
            f"💰 *Amount:* ₹{price:.0f}\n"
            f"🆔 *Order ID:* `{order_id}`\n"
            f"🏦 *Gateway:* TranzUPI (Live)\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status & Deliver Sensi*!"
        )

        buttons = []
        pay_url = pay_details.get("payment_url")
        if pay_url and (pay_url.startswith("http://") or pay_url.startswith("https://")):
            buttons.append([InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)])

        buttons.append([InlineKeyboardButton("🔄 Check Payment Status & Deliver Sensi", callback_data=f"sp_chk_{order_id}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("sp_chk_"):
        order_id = data.replace("sp_chk_", "")
        order = db.get_sensi_order_by_id(order_id)
        if not order:
            await query.answer("❌ Sensi order not found.", show_alert=True)
            return

        if order["status"] == "SUCCESS":
            await query.answer("✅ Sensi order already completed!", show_alert=True)
            return

        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            db.mark_sensi_order_success(order_id)
            await query.answer("🎉 Payment Verified! Delivering sensitivity...", show_alert=True)
            variant = f"{order['ram']} + {order['storage']}"
            _, delivered_text = sensi_eng.generate_ff_sensitivity(
                telegram_id=user.id,
                order_id=order_id,
                brand=order["brand"],
                model=order["model"],
                variant=variant
            )
            await query.edit_message_text(text=delivered_text, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI and tap again.", show_alert=True)

    # --- GMAIL RECOVERY CALLBACK HANDLERS ---
    elif data == "gr_start_continue":
        await handle_gmail_recovery_issue_selection(update, context)

    elif data == "spin_now":
        await query.answer("⏳ Daily Spin is COMING SOON!", show_alert=True)
        return

        user_rec = db.get_or_create_user(user.id)
        current_bal = float(user_rec.get("balance", 0.0))

        if is_special:
            await query.answer(f"🎉 SPECIAL RESULT 20 ⭐! ₹{reward_amt:.0f} credited to wallet!", show_alert=True)
            special_msg = (
                f"🎉 *SPECIAL RESULT!*\n\n"
                f"You got: *20* ⭐\n\n"
                f"💰 *Reward Credited:* ₹{reward_amt:.2f}\n"
                f"💳 *New Wallet Balance:* ₹{current_bal:.2f}\n\n"
                f"Come back after 24 hours for your next spin."
            )
            await query.edit_message_text(text=special_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer(f"🎉 Spin Win! ₹{reward_amt:.0f} credited to wallet!", show_alert=True)
            normal_msg = (
                f"🎉 *Daily Spin Winner!*\n\n"
                f"You got: *{result}*\n\n"
                f"💰 *Reward Credited:* ₹{reward_amt:.2f}\n"
                f"💳 *New Wallet Balance:* ₹{current_bal:.2f}\n\n"
                f"Come back after 24 hours for your next spin."
            )
            await query.edit_message_text(text=normal_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

    # --- UNIFIED REUSABLE PAYMENT CALLBACK HANDLERS ---
    elif data.startswith("pay_wal_"):
        order_id = data.replace("pay_wal_", "")

        # 1. Sensi Order
        if order_id.startswith("SENSI-"):
            success, msg_or_key = db.process_wallet_sensi_payment(order_id)
            if not success:
                if msg_or_key.startswith("INSUFFICIENT_BALANCE|"):
                    details = msg_or_key.split("|", 1)[1]
                    await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
                else:
                    await query.answer(msg_or_key, show_alert=True)
                return

            await query.answer("🎉 Payment Successful! Generating Sensitivity...", show_alert=True)
            order = db.get_sensi_order_by_id(order_id)
            brand_name = order["brand"] if (order and "brand" in order) else "Mobile"
            model_name = order["model"] if (order and "model" in order) else brand_name
            data, delivered_text = sensi_eng.generate_ff_sensitivity(
                telegram_id=user.id,
                order_id=order_id,
                brand=brand_name,
                model=model_name,
                variant="Standard"
            )
            buttons = [
                [InlineKeyboardButton("🔄 Generate Again", callback_data=f"sb_regen_{brand_name}")],
                [InlineKeyboardButton("💾 Save Profile", callback_data=f"sb_save_{data['profile_id']}"), InlineKeyboardButton("📤 Share", callback_data=f"sb_share_{data['profile_id']}")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")]
            ]
            try:
                await query.edit_message_text(text=delivered_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as err:
                logger.warning(f"Markdown delivery fallback: {err}")
                await query.edit_message_text(text=delivered_text.replace("`", "").replace("*", ""), reply_markup=InlineKeyboardMarkup(buttons))

        # 2. Tournament Order
        elif order_id.startswith("TRN-"):
            success, res_msg = db.process_wallet_tournament_payment(order_id)
            if not success:
                if res_msg.startswith("INSUFFICIENT_BALANCE|"):
                    details = res_msg.split("|", 1)[1]
                    await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
                else:
                    await query.answer(res_msg, show_alert=True)
                return

            await query.answer("🎉 Payment Verified! Tournament Entry Unlocked.", show_alert=True)
            unlocked_msg = (
                f"✅ *Payment Successful!*\n\n"
                f"🏆 *Tournament Entry Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🏆 JOIN TOURNAMENT", url="https://t.me/+4RKa1Af80ghiMTY1")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        # 3. DK AI Order
        elif order_id.startswith("DKAI-"):
            success, res_msg = db.process_wallet_dk_ai_payment(order_id)
            if not success:
                if res_msg.startswith("INSUFFICIENT_BALANCE|"):
                    details = res_msg.split("|", 1)[1]
                    await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
                else:
                    await query.answer(res_msg, show_alert=True)
                return

            await query.answer("🎉 Payment Verified! DK AI Unlocked.", show_alert=True)
            unlocked_msg = (
                f"✅ *Payment Successful!*\n\n"
                f"🤖 *DK AI Assistant Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        # 4. Gmail Recovery Order
        elif order_id.startswith("KR-"):
            success, msg_res = db.process_wallet_gmail_recovery_payment(order_id)
            if success:
                await query.answer("🎉 Payment Successful (₹299)! Please type your Gmail address.", show_alert=True)
                context.user_data["awaiting_gmail_email"] = True
                context.user_data["gmail_order_id"] = order_id
                send_gmail_msg = (
                    f"✅ *Payment Successful (₹299)*\n\n"
                    f"📧 *Step 2: Enter Target Gmail Address*\n\n"
                    f"Please type your Target Gmail Address below:\n\n"
                    f"Example: `target@gmail.com`"
                )
                await query.edit_message_text(text=send_gmail_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
            else:
                if msg_res.startswith("INSUFFICIENT_BALANCE|"):
                    details = msg_res.split("|", 1)[1]
                    await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
                else:
                    await query.answer(f"❌ {msg_res}", show_alert=True)

        # 5. Panel Buy Order
        elif order_id.startswith("PNL-"):
            if "VAR_" in order_id:
                success, res = db.process_wallet_panel_variant_payment(order_id)
            else:
                success, res = db.process_wallet_panel_payment(order_id)

            if not success:
                if res.startswith("INSUFFICIENT_BALANCE|"):
                    details = res.split("|", 1)[1]
                    await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
                else:
                    await query.answer(res, show_alert=True)
                return

            key_code = res if res.startswith("KEY-") else "KEY-ACTIVATED"
            await query.answer("🎉 Purchase Successful!", show_alert=True)
            delivered_msg = (
                f"✅ *Purchase Successful!*\n\n"
                f"🆔 *Order ID:* `{order_id}`\n"
                f"🔑 *License Key:* `{key_code}`\n\n"
                f"Your key is ready to use!"
            )
            await query.edit_message_text(text=delivered_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

    elif data.startswith("pay_upi_"):
        order_id = data.replace("pay_upi_", "")

        # Determine amount and product name server-side
        amount = 59.0
        item_name = "Product"
        if order_id.startswith("SENSI-"):
            amount = db.get_sensi_price()
            item_name = "Free Fire Sensitivity Profile"
        elif order_id.startswith("TRN-"):
            amount = 99.0
            item_name = "Tournament App Entry"
        elif order_id.startswith("DKAI-"):
            amount = 99.0
            item_name = "DK AI Assistant Access"
        elif order_id.startswith("KR-"):
            amount = db.get_gmail_fee()
            item_name = "Gmail Recovery Request"
        elif order_id.startswith("PNL-"):
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT product_name, price FROM panel_orders WHERE order_id = ?", (order_id,))
            p_row = cursor.fetchone()
            conn.close()
            if p_row:
                item_name = p_row["product_name"]
                amount = float(p_row["price"])

        pay_details = gtw.create_tranzupi_payment_order(
            amount=amount,
            order_id=order_id,
            customer_name=user.first_name or "Kiro User",
            customer_email=f"user_{user.id}@kiroshop.bot",
            customer_mobile="9999999999"
        )

        msg = (
            f"━━━━━━━━━━━━━━━━\n"
            f"💳 *UPI PAYMENT*\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"📦 *Item:* `{item_name}`\n"
            f"💰 *Amount:* ₹{amount:.0f}\n"
            f"🆔 *Order ID:* `{order_id}`\n"
            f"🏦 *Gateway:* TranzUPI (Live)\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status*!"
        )

        pay_url = pay_details.get("payment_url") or f"https://upiqr.in/api/qr?name={urllib.parse.quote(MERCHANT_NAME)}&vpa={TRANZUPI_UPI_ID}&amount={amount:.2f}&note={order_id}"
        buttons = [
            [InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)],
            [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"pay_chk_{order_id}")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")]
        ]

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("pay_chk_"):
        order_id = data.replace("pay_chk_", "")

        # Verify status with gateway
        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            if order_id.startswith("SENSI-"):
                db.mark_sensi_order_paid(order_id)
                data, delivered_text = sensi_eng.generate_ff_sensitivity(
                    telegram_id=user.id,
                    order_id=order_id,
                    brand=order["brand"],
                    model=order["model"],
                    variant=order["variant"]
                )
                await query.answer("🎉 Payment Verified! Sensi profile generated.", show_alert=True)
                buttons = [
                    [InlineKeyboardButton("🔄 Generate Again", callback_data=f"sb_regen_{order['brand']}")],
                    [InlineKeyboardButton("💾 Save Profile", callback_data=f"sb_save_{data['profile_id']}"), InlineKeyboardButton("📤 Share", callback_data=f"sb_share_{data['profile_id']}")],
                    [InlineKeyboardButton("⬅️ Back to Menu", callback_data="nav_main")]
                ]
                await query.edit_message_text(text=delivered_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

            elif order_id.startswith("TRN-"):
                db.mark_tournament_order_success(order_id)
                await query.answer("🎉 Payment Verified! Tournament Entry Unlocked.", show_alert=True)
                unlocked_msg = (
                    f"✅ *Payment Verified!*\n\n"
                    f"🏆 *Tournament Entry Unlocked.*\n\n"
                    f"👇 Click below to enter:"
                )
                keyboard = [
                    [InlineKeyboardButton("🏆 JOIN TOURNAMENT", url="https://t.me/+4RKa1Af80ghiMTY1")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
                ]
                await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

            elif order_id.startswith("DKAI-"):
                db.mark_dk_ai_order_success(order_id)
                await query.answer("🎉 Payment Verified! DK AI Unlocked.", show_alert=True)
                unlocked_msg = (
                    f"✅ *Payment Verified!*\n\n"
                    f"🤖 *DK AI Assistant Unlocked.*\n\n"
                    f"👇 Click below to enter:"
                )
                keyboard = [
                    [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
                ]
                await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

            elif order_id.startswith("KR-"):
                db.mark_gmail_recovery_paid(order_id)
                await query.answer("🎉 Payment Verified! Request submitted.", show_alert=True)
                confirmed_msg = (
                    f"✅ *Payment Verified*\n\n"
                    f"Your recovery request has been submitted.\n\n"
                    f"🆔 *Request ID:* `{order_id}`\n\n"
                    f"Our support team will review your request."
                )
                await query.edit_message_text(text=confirmed_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

            elif order_id.startswith("PNL-"):
                db.mark_panel_order_success(order_id)
                await query.answer("🎉 Payment Verified! Key generated.", show_alert=True)
                delivered_msg = (
                    f"✅ *Payment Verified!*\n\n"
                    f"🆔 *Order ID:* `{order_id}`\n"
                    f"🔑 *License Key:* `KEY-{uuid.uuid4().hex[:12].upper()}`\n\n"
                    f"Your key is ready to use!"
                )
                await query.edit_message_text(text=delivered_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI and tap again.", show_alert=True)

    # --- DK AI ASSISTANT CALLBACK HANDLERS ---
    elif data.startswith("dk_wal_"):
        order_id = data.replace("dk_wal_", "")
        success, res_msg = db.process_wallet_dk_ai_payment(order_id)
        if not success:
            if res_msg.startswith("INSUFFICIENT_BALANCE|"):
                details = res_msg.split("|", 1)[1]
                alert_text = f"❌ Insufficient Balance\n\n{details}"
                await query.answer(alert_text, show_alert=True)
            else:
                await query.answer(res_msg, show_alert=True)
            return

        await query.answer("🎉 Payment Successful! DK AI Assistant Unlocked.", show_alert=True)
        unlocked_msg = (
            f"✅ *Payment Successful!*\n\n"
            f"🤖 *DK AI Assistant Unlocked.*\n\n"
            f"👇 Click below to enter:"
        )
        keyboard = [
            [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
            [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
        ]
        await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("dk_upi_"):
        order_id = data.replace("dk_upi_", "")
        order = db.get_dk_ai_order_by_id(order_id)
        if not order:
            await query.answer("❌ Order not found.", show_alert=True)
            return

        pay_details = gtw.create_tranzupi_payment_order(
            amount=99.0,
            order_id=order_id,
            customer_name=user.first_name or "Kiro User",
            customer_email=f"user_{user.id}@kiroshop.bot",
            customer_mobile="9999999999"
        )

        msg = (
            f"🏦 *TranzUPI Payment Gateway*\n\n"
            f"🤖 *Product:* DK AI Assistant Access\n"
            f"💰 *Amount:* ₹99.00\n"
            f"🆔 *Order ID:* `{order_id}`\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status & Unlock DK AI*!"
        )

        buttons = []
        pay_url = pay_details.get("payment_url")
        if pay_url and (pay_url.startswith("http://") or pay_url.startswith("https://")):
            buttons.append([InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)])

        buttons.append([InlineKeyboardButton("🔄 Check Payment Status & Unlock DK AI", callback_data=f"dk_chk_{order_id}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("dk_chk_"):
        order_id = data.replace("dk_chk_", "")
        order = db.get_dk_ai_order_by_id(order_id)
        if not order:
            await query.answer("❌ DK AI order not found.", show_alert=True)
            return

        if order["status"] == "SUCCESS":
            await query.answer("✅ Order already completed!", show_alert=True)
            unlocked_msg = (
                f"✅ *DK AI Assistant Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            db.mark_dk_ai_order_success(order_id)
            await query.answer("🎉 Payment Verified! DK AI Assistant Unlocked.", show_alert=True)
            unlocked_msg = (
                f"✅ *Payment Successful!*\n\n"
                f"🤖 *DK AI Assistant Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🤖 JOIN DK AI ASSISTANT", url="https://t.me/+et_POl-Eqnc4Y2Q9")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI app first.", show_alert=True)

    elif data.startswith("gr_prob_"):
        problem_choice = data.replace("gr_prob_", "")
        context.user_data["gmail_problem"] = problem_choice

        fee = db.get_gmail_fee()
        order_id = gtw.generate_order_id().replace("KIR-", "KR-")
        db.create_gmail_recovery_request(
            telegram_id=user.id,
            email="AWAITING_INPUT",
            problem_description=problem_choice,
            order_id=order_id,
            payment_method="WALLET",
            amount=fee
        )

        await render_unified_payment_screen(
            update=update,
            context=context,
            order_id=order_id,
            item_name=f"Gmail Recovery ({problem_choice})",
            price=fee,
            back_callback="nav_main"
        )

    elif data.startswith("gr_wal_"):
        order_id = data.replace("gr_wal_", "")
        req = db.get_gmail_request_by_id(order_id)
        if not req:
            await query.answer("❌ Gmail Recovery request not found.", show_alert=True)
            return

        success, msg = db.process_wallet_gmail_recovery_payment(order_id)
        if success:
            await query.answer("🎉 Payment Successful! Request submitted.", show_alert=True)
            confirmed_msg = (
                f"✅ *Payment Successful*\n\n"
                f"Your recovery request has been submitted.\n\n"
                f"🆔 *Request ID:* `{order_id}`\n\n"
                f"Our support team will review your request."
            )
            await query.edit_message_text(text=confirmed_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data.startswith("gr_upi_"):
        order_id = data.replace("gr_upi_", "")
        req = db.get_gmail_request_by_id(order_id)
        if not req:
            await query.answer("❌ Gmail Recovery request not found.", show_alert=True)
            return

        amount = float(req["amount"])
        pay_details = gtw.create_tranzupi_payment_link(order_id, amount, user.first_name or "Customer")

        msg = (
            f"💳 *Gmail Recovery Payment*\n\n"
            f"📧 *Email:* `{req['email']}`\n"
            f"💰 *Amount:* ₹{amount:.0f}\n"
            f"🆔 *Order ID:* `{order_id}`\n"
            f"🏦 *Gateway:* TranzUPI (Live)\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status & Submit Request*!"
        )

        buttons = []
        pay_url = pay_details.get("payment_url")
        if pay_url and (pay_url.startswith("http://") or pay_url.startswith("https://")):
            buttons.append([InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)])

        buttons.append([InlineKeyboardButton("🔄 Check Payment Status & Submit Request", callback_data=f"gr_chk_{order_id}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("gr_chk_"):
        order_id = data.replace("gr_chk_", "")
        req = db.get_gmail_request_by_id(order_id)
        if not req:
            await query.answer("❌ Gmail Recovery request not found.", show_alert=True)
            return

        if req["status"] in ["PAID", "UNDER_REVIEW", "COMPLETED"]:
            await query.answer("✅ Request already submitted & under review!", show_alert=True)
            return

        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            db.mark_gmail_recovery_paid(order_id)
            await query.answer("🎉 Payment Verified! Request submitted.", show_alert=True)
            confirmed_msg = (
                f"✅ *Payment Successful*\n\n"
                f"Your recovery request has been submitted.\n\n"
                f"🆔 *Request ID:* `{order_id}`\n\n"
                f"Our support team will review your request."
            )
            await query.edit_message_text(text=confirmed_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI and tap again.", show_alert=True)

    # --- PANEL BUY CALLBACK HANDLERS ---
    elif data.startswith("pb_p_"):
        try:
            page = int(data.replace("pb_p_", ""))
            msg = (
                f"🛒 *Kiro Panel Buy Catalog*\n\n"
                f"Browse premium game cheats, proxy clients, root mods, and certificate panels.\n\n"
                f"👇 Select a panel product below to view details and purchase:"
            )
            await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_panel_catalog_keyboard())
        except ValueError:
            pass

    elif data.startswith("pb_m_"):
        try:
            item_id = int(data.replace("pb_m_", ""))
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM panel_catalog WHERE id = ?", (item_id,))
            item_row = cursor.fetchone()
            conn.close()

            if not item_row:
                await query.answer("❌ Panel product not found.", show_alert=True)
                return

            item = dict(item_row)
            p_name = item["product_name"]

            variants = db.get_panel_variants(p_name)

            msg = (
                f"🔥 *{p_name}*\n\n"
                f"Select Duration:"
            )

            buttons = []
            if variants:
                for v in variants:
                    dur = v["duration"]
                    price = v["price"]
                    stock = v["is_in_stock"]
                    icon = "⏱️" if ("Hour" in dur) else "📅"
                    if stock == 1 and price is not None:
                        btn_label = f"{icon} {dur} — ₹{float(price):.0f}"
                        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"pb_v_{v['id']}")])
                    else:
                        btn_label = f"❌ {dur} — OUT OF STOCK"
                        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"pb_oos_{v['id']}")])
            else:
                buttons.append([InlineKeyboardButton("❌ OUT OF STOCK", callback_data="pb_oos_0")])

            buttons.append([InlineKeyboardButton("⬅️ Back to Shop", callback_data="nav_panel_shop")])
            await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            logger.error(f"Error handling panel product click: {e}")

    elif data == "nav_panel_shop":
        msg = (
            f"🛒 *Kiro Panel Buy Catalog*\n\n"
            f"Browse premium game cheats, proxy clients, root mods, and certificate panels.\n\n"
            f"👇 Select a panel product below to view details and purchase:"
        )
        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=get_panel_catalog_keyboard())

    elif data.startswith("pb_oos_"):
        await query.answer("❌ OUT OF STOCK", show_alert=True)

    elif data.startswith("pb_v_"):
        variant_id = int(data.replace("pb_v_", ""))
        v = db.get_panel_variant_by_id(variant_id)
        if not v or v["is_in_stock"] == 0 or v["price"] is None:
            await query.answer("❌ OUT OF STOCK", show_alert=True)
            return

        price = float(v["price"])
        order_id = gtw.generate_order_id().replace("KIR-", "PNL-")
        db.create_panel_variant_order(telegram_id=user.id, variant_id=variant_id, price=price, order_id=order_id, payment_method="PENDING")

        await render_unified_payment_screen(
            update=update,
            context=context,
            order_id=order_id,
            item_name=f"{v['product_name']} ({v['duration']})",
            price=price,
            back_callback="nav_panel_shop"
        )

    elif data.startswith("pb_vwal_"):
        order_id = data.replace("pb_vwal_", "")
        success, res = db.process_wallet_panel_variant_payment(order_id)
        if not success:
            if res.startswith("INSUFFICIENT_BALANCE|"):
                details = res.split("|", 1)[1]
                await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
            else:
                await query.answer(res, show_alert=True)
            return

        key_code = res
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_orders WHERE order_id = ?", (order_id,))
        order_info = dict(cursor.fetchone())
        conn.close()

        await query.answer("🎉 Purchase Successful!", show_alert=True)
        delivered_msg = (
            f"✅ *Purchase Successful!*\n\n"
            f"🎮 *Product:* `{order_info['product_name']}`\n"
            f"💰 *Paid:* ₹{order_info['price']:.0f}\n"
            f"🔑 *License Key:* `{key_code}`\n\n"
            f"Your key is ready to use!"
        )
        await query.edit_message_text(text=delivered_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))

    # --- TOURNAMENT APP CALLBACK HANDLERS ---
    elif data.startswith("tr_wal_"):
        order_id = data.replace("tr_wal_", "")
        success, res_msg = db.process_wallet_tournament_payment(order_id)
        if not success:
            if res_msg.startswith("INSUFFICIENT_BALANCE|"):
                details = res_msg.split("|", 1)[1]
                await query.answer(f"❌ Insufficient Balance\n\n{details}", show_alert=True)
            else:
                await query.answer(res_msg, show_alert=True)
            return

        await query.answer("🎉 Payment Verified! Tournament Entry Unlocked.", show_alert=True)
        unlocked_msg = (
            f"✅ *Payment Successful!*\n\n"
            f"🏆 *Tournament Entry Unlocked.*\n\n"
            f"👇 Click below to enter:"
        )
        keyboard = [
            [InlineKeyboardButton("🏆 JOIN TOURNAMENT", url="https://t.me/+4RKa1Af80ghiMTY1")],
            [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
        ]
        await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("tr_upi_"):
        order_id = data.replace("tr_upi_", "")
        order = db.get_tournament_order_by_id(order_id)
        if not order:
            await query.answer("❌ Order not found.", show_alert=True)
            return

        pay_details = gtw.create_tranzupi_payment_order(
            amount=99.0,
            order_id=order_id,
            customer_name=user.first_name or "Kiro User",
            customer_email=f"user_{user.id}@kiroshop.bot",
            customer_mobile="9999999999"
        )

        msg = (
            f"🏦 *TranzUPI Payment Gateway*\n\n"
            f"🏆 *Product:* Tournament App Entry\n"
            f"💰 *Amount:* ₹99.00\n"
            f"🆔 *Order ID:* `{order_id}`\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status & Unlock Entry*!"
        )

        buttons = []
        pay_url = pay_details.get("payment_url")
        if pay_url and (pay_url.startswith("http://") or pay_url.startswith("https://")):
            buttons.append([InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)])

        buttons.append([InlineKeyboardButton("🔄 Check Payment Status & Unlock Entry", callback_data=f"tr_chk_{order_id}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("tr_chk_"):
        order_id = data.replace("tr_chk_", "")
        order = db.get_tournament_order_by_id(order_id)
        if not order:
            await query.answer("❌ Order not found.", show_alert=True)
            return

        if order["status"] == "SUCCESS":
            await query.answer("✅ Order already completed!", show_alert=True)
            unlocked_msg = (
                f"✅ *Tournament Entry Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🏆 JOIN TOURNAMENT", url="https://t.me/+4RKa1Af80ghiMTY1")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            db.mark_tournament_order_success(order_id)
            await query.answer("🎉 Payment Verified! Tournament Entry Unlocked.", show_alert=True)
            unlocked_msg = (
                f"✅ *Payment Successful!*\n\n"
                f"🏆 *Tournament Entry Unlocked.*\n\n"
                f"👇 Click below to enter:"
            )
            keyboard = [
                [InlineKeyboardButton("🏆 JOIN TOURNAMENT", url="https://t.me/+4RKa1Af80ghiMTY1")],
                [InlineKeyboardButton("⬅️ Back", callback_data="nav_main")]
            ]
            await query.edit_message_text(text=unlocked_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI app first.", show_alert=True)

    elif data.startswith("pb_wal_"):
        order_id = data.replace("pb_wal_", "")
        order = db.get_panel_order_by_id(order_id)
        if not order:
            await query.answer("❌ Panel order not found.", show_alert=True)
            return

        success, msg = db.process_wallet_panel_payment(order_id)
        if success:
            await query.answer("🎉 Payment Successful! Panel key generated.", show_alert=True)
            confirmed_msg = (
                f"✅ *Payment Successful*\n\n"
                f"Your purchase for *{order['product_name']}* has been processed.\n\n"
                f"🆔 *Order ID:* `{order_id}`\n"
                f"💰 *Amount Paid:* ₹{float(order['price']):.0f}\n\n"
                f"🔑 *Key / Access Link:* Your activation code has been issued. Contact Support with your Order ID for instant setup instructions!"
            )
            await query.edit_message_text(text=confirmed_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data.startswith("pb_upi_"):
        order_id = data.replace("pb_upi_", "")
        order = db.get_panel_order_by_id(order_id)
        if not order:
            await query.answer("❌ Panel order not found.", show_alert=True)
            return

        price = float(order["price"])
        pay_details = gtw.create_tranzupi_payment_link(order_id, price, user.first_name or "Customer")

        msg = (
            f"💳 *Panel Checkout Payment*\n\n"
            f"📦 *Product:* `{order['product_name']}`\n"
            f"💰 *Amount:* ₹{price:.0f}\n"
            f"🆔 *Order ID:* `{order_id}`\n"
            f"🏦 *Gateway:* TranzUPI (Live)\n\n"
            f"📲 *UPI Payment String:*\n`{pay_details['upi_intent']}`\n\n"
            f"⚠️ *Instructions:*\n"
            f"1️⃣ Tap *💳 Pay Now via UPI 📲* button below to pay via Paytm/PhonePe/GPay.\n"
            f"2️⃣ After payment, tap *🔄 Check Payment Status & Confirm Order*!"
        )

        buttons = []
        pay_url = pay_details.get("payment_url")
        if pay_url and (pay_url.startswith("http://") or pay_url.startswith("https://")):
            buttons.append([InlineKeyboardButton("💳 Pay Now via UPI 📲", url=pay_url)])

        buttons.append([InlineKeyboardButton("🔄 Check Payment Status & Confirm Order", callback_data=f"pb_chk_{order_id}")])
        buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="nav_main")])

        await query.edit_message_text(text=msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("pb_chk_"):
        order_id = data.replace("pb_chk_", "")
        order = db.get_panel_order_by_id(order_id)
        if not order:
            await query.answer("❌ Panel order not found.", show_alert=True)
            return

        if order["status"] == "SUCCESS":
            await query.answer("✅ Order already completed!", show_alert=True)
            return

        res = gtw.check_tranzupi_order_status(order_id)
        payment_status = str(res.get("payment_status", "PENDING")).upper()

        if payment_status in ["SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"]:
            db.mark_panel_order_success(order_id)
            await query.answer("🎉 Payment Verified! Order completed.", show_alert=True)
            confirmed_msg = (
                f"✅ *Payment Successful*\n\n"
                f"Your purchase for *{order['product_name']}* has been verified.\n\n"
                f"🆔 *Order ID:* `{order_id}`\n"
                f"💰 *Amount Paid:* ₹{float(order['price']):.0f}\n\n"
                f"🔑 *Key / Access Link:* Your activation code has been issued. Contact Support with your Order ID for instant setup instructions!"
            )
            await query.edit_message_text(text=confirmed_msg, parse_mode="Markdown", reply_markup=get_back_inline_keyboard("main"))
        else:
            await query.answer("⌛ Payment not completed yet! Please pay via UPI and tap again.", show_alert=True)

    elif data.startswith("dep_"):
        try:
            preset_amount = float(data.replace("dep_", ""))
            context.user_data["awaiting_deposit_amount"] = False
            await process_deposit_creation(update, context, user, preset_amount)
        except ValueError:
            logger.error(f"Invalid deposit callback data: {data}")
    else:
        logger.warning(f"Unhandled callback query data: {data}")

# --- ADMIN COMMAND HANDLERS ---

async def admin_sensi_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to update Sensi purchase price: /sensiprice 29"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return
    if not context.args:
        price = db.get_sensi_price()
        await update.message.reply_text(f"💡 Current Sensi price is ₹{price:.2f}.\nUsage: `/sensiprice 49`", parse_mode="Markdown")
        return
    try:
        new_price = float(context.args[0])
        db.set_sensi_price(new_price)
        await update.message.reply_text(f"✅ Sensi price updated to ₹{new_price:.2f} successfully!", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid price format. Example: `/sensiprice 49`", parse_mode="Markdown")

async def admin_add_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add a new phone model: /addmodel Vivo | Vivo X100 Pro"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return
    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        await update.message.reply_text("💡 Usage: `/addmodel Brand | Model Name` (e.g. `/addmodel Vivo | Vivo X100 Pro`)", parse_mode="Markdown")
        return
    parts = raw_text.split("|", 1)
    brand = parts[0].strip()
    model = parts[1].strip()
    if db.add_sensi_catalog_model(brand, model):
        await update.message.reply_text(f"✅ Model *{model}* added under brand *{brand}*!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Failed to add model.", parse_mode="Markdown")

async def admin_sensi_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view Sensi sales summary: /sensisales"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return
    sales = db.get_sensi_sales_summary()
    msg = (
        f"📊 *Kiro Sensi Sales Report*\n\n"
        f"🛍️ *Total Orders:* {sales['total_orders']}\n"
        f"💰 *Total Revenue:* ₹{sales['total_revenue']:.2f}\n\n"
        f"🔥 *Top Brands:*\n"
    )
    for b in sales["top_brands"]:
        msg += f"• {b['brand']}: {b['count']} sales\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_gmail_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to list pending Gmail recovery requests: /gmailrequests"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    requests_list = db.get_all_gmail_recovery_requests(limit=15)
    if not requests_list:
        await update.message.reply_text("📥 *No Gmail Recovery Requests Found.*", parse_mode="Markdown")
        return

    msg = f"📋 *Gmail Recovery Requests ({len(requests_list)})*\n\n"
    for r in requests_list:
        msg += (
            f"🆔 *{r['order_id']}* | Status: `{r['status']}`\n"
            f"👤 User: `{r['telegram_id']}` | Email: `{r['email']}`\n"
            f"📝 Problem: {r['problem_description']}\n"
            f"💰 Amount: ₹{float(r['amount']):.0f} ({r['payment_method']})\n"
            f"-----------------------------------------\n"
        )
    msg += "\n💡 Admin command to update status:\n`/setgmailstatus KR-XXXXXXXX COMPLETED`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_set_gmail_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to update status: /setgmailstatus KR-XXXXXXXX COMPLETED"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    if len(context.args) < 2:
        await update.message.reply_text("💡 Usage: `/setgmailstatus KR-XXXXXXXX COMPLETED` (Statuses: UNDER_REVIEW, COMPLETED, REJECTED)", parse_mode="Markdown")
        return

    order_id = context.args[0].strip()
    new_status = context.args[1].strip().upper()

    if db.update_gmail_recovery_status(order_id, new_status):
        await update.message.reply_text(f"✅ Request `{order_id}` status updated to *{new_status}*!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Failed to update request status.", parse_mode="Markdown")

async def admin_set_panel_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set price for a panel product: /setpanelprice BALA MOD MAIN ID | 499"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        await update.message.reply_text("💡 Usage: `/setpanelprice Product Name | Price` (e.g. `/setpanelprice BALA MOD MAIN ID | 499`)", parse_mode="Markdown")
        return

    parts = raw_text.split("|", 1)
    p_name = parts[0].strip()
    try:
        price = float(parts[1].strip())
        if db.set_panel_price(p_name, price):
            await update.message.reply_text(f"✅ Price for panel *{p_name}* updated to ₹{price:.0f}!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Panel product *{p_name}* not found in catalog.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid price number. Example: `/setpanelprice BALA MOD MAIN ID | 499`", parse_mode="Markdown")

async def admin_panel_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view Panel Buy sales report: /panelsales"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    sales = db.get_panel_sales_summary()
    msg = (
        f"📊 *Kiro Panel Buy Sales Report*\n\n"
        f"🛍️ *Total Orders:* {sales['total_orders']}\n"
        f"💰 *Total Revenue:* ₹{sales['total_revenue']:.2f}\n\n"
        f"🔥 *Top Selling Panels:*\n"
    )
    for p in sales.get("top_products", []):
        msg += f"• {p['product_name']}: {p['count']} sales\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_dashboard_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view complete system stats dashboard: /stats or /admin"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    stats = db.get_admin_dashboard_stats()
    msg = (
        f"📊 *Kiro Shop Admin Dashboard*\n\n"
        f"👥 *Total Users:* {stats['total_users']}\n"
        f"💳 *Completed Deposits:* {stats['total_deposits_count']} (₹{stats['total_deposits_sum']:.2f})\n"
        f"🎯 *Sensi Orders:* {stats['sensi_orders_count']}\n"
        f"🛒 *Panel Orders:* {stats['panel_orders_count']}\n"
        f"📧 *Gmail Requests:* {stats['gmail_requests_count']}\n"
        f"🎰 *Total Spins Executed:* {stats['total_spins_count']}\n"
        f"🔗 *Total Registered Referrals:* {stats['total_referrals_count']}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_set_panel_price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set panel variant price: /setpanelprice BR MOD ROOT | 1 Day | 70"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text("💡 Usage: `/setpanelprice Panel Name | Duration | Price`", parse_mode="Markdown")
        return

    parts = [x.strip() for x in raw.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("💡 Usage: `/setpanelprice Panel Name | Duration | Price`", parse_mode="Markdown")
        return

    p_name, duration, price_str = parts[0], parts[1], parts[2]
    try:
        price_val = float(price_str)
    except ValueError:
        await update.message.reply_text("❌ Invalid price number.", parse_mode="Markdown")
        return

    if db.admin_set_panel_variant_price(p_name, duration, price_val):
        await update.message.reply_text(f"✅ Price for *{p_name} ({duration})* set to *₹{price_val:.0f}* and marked In Stock!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Failed to update price.", parse_mode="Markdown")

async def admin_toggle_panel_stock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to toggle panel variant stock: /togglepanelstock BR MOD ROOT | 1 Day | 0"""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ *Unauthorized Access*", parse_mode="Markdown")
        return

    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text("💡 Usage: `/togglepanelstock Panel Name | Duration | 0` (0=Out of Stock, 1=In Stock)", parse_mode="Markdown")
        return

    parts = [x.strip() for x in raw.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("💡 Usage: `/togglepanelstock Panel Name | Duration | 0`", parse_mode="Markdown")
        return

    p_name, duration, stock_str = parts[0], parts[1], parts[2]
    stock_int = 1 if stock_str in ["1", "in", "instock", "true"] else 0

    if db.admin_toggle_panel_variant_stock(p_name, duration, stock_int):
        status_lbl = "✅ IN STOCK" if stock_int == 1 else "❌ OUT OF STOCK"
        await update.message.reply_text(f"✅ Stock for *{p_name} ({duration})* set to *{status_lbl}*!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Failed to update stock.", parse_mode="Markdown")

async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for uncaught exceptions."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

import threading
from webhook_server import run_webhook_server

def main() -> None:
    """Bot launcher."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    logger.info("Initializing database...")
    db.init_db()

    # Start Webhook Listener Server in background thread
    port = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "5000")))
    webhook_thread = threading.Thread(target=run_webhook_server, args=(port,), daemon=True)
    webhook_thread.start()
    logger.info(f"Background TranzUPI Webhook Server thread started on port {port}.")

    logger.info("Starting Kiro Shop Telegram Bot...")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning("BOT_TOKEN is not configured in .env. Bot runner in standby mode.")
        print("\n[CONFIG NOTICE] BOT_TOKEN is missing or set to placeholder in .env.")
        print("Please configure BOT_TOKEN in .env file to launch live polling.\n")
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_dashboard_stats))
    application.add_handler(CommandHandler("stats", admin_dashboard_stats))
    application.add_handler(CommandHandler("sensiprice", admin_sensi_price))
    application.add_handler(CommandHandler("addmodel", admin_add_model))
    application.add_handler(CommandHandler("sensisales", admin_sensi_sales))
    application.add_handler(CommandHandler("gmailrequests", admin_gmail_requests))
    application.add_handler(CommandHandler("setgmailstatus", admin_set_gmail_status))
    application.add_handler(CommandHandler("setpanelprice", admin_set_panel_price_cmd))
    application.add_handler(CommandHandler("togglepanelstock", admin_toggle_panel_stock_cmd))
    application.add_handler(CommandHandler("panelsales", admin_panel_sales))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_error_handler(error_handler)

    logger.info("Kiro Shop Bot started polling...")
    try:
        application.run_polling(drop_pending_updates=True, stop_signals=None)
    except Exception as e:
        logger.error(f"Error in run_polling: {e}", exc_info=e)

if __name__ == "__main__":
    main()

