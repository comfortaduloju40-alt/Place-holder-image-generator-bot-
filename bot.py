import os
import io
import logging
import random
from PIL import Image, ImageDraw, ImageFont
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN)

STYLES = {
    "Solid": {
        "desc": "Flat color with centered text",
    },
    "Gradient": {
        "desc": "Smooth gradient background",
    },
    "Checkerboard": {
        "desc": "Classic transparent-style checker",
    },
    "Diagonal": {
        "desc": "Diagonal stripe pattern",
    },
    "Noise": {
        "desc": "Subtle grainy texture",
    },
}

PALETTES = {
    "Gray":    [(180, 180, 180), (120, 120, 120)],
    "Blue":    [(99, 179, 237),  (44, 82, 130)],
    "Green":   [(72, 187, 120),  (22, 101, 52)],
    "Purple":  [(159, 122, 234), (76, 29, 149)],
    "Red":     [(252, 129, 129), (153, 27, 27)],
    "Orange":  [(251, 146, 60),  (154, 52, 18)],
    "Pink":    [(244, 114, 182), (131, 24, 67)],
    "Dark":    [(55, 65, 81),    (17, 24, 39)],
    "Random":  [],
}

user_sessions = {}


def get_palette(name):
    if name == "Random" or not name:
        r1 = tuple(random.randint(80, 220) for _ in range(3))
        r2 = tuple(max(0, c - 60) for c in r1)
        return [r1, r2]
    return PALETTES[name]


def load_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()


def draw_centered_text(draw, canvas_w, canvas_h, text, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (canvas_w - tw) // 2
    y = (canvas_h - th) // 2
    # shadow
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 80))
    draw.text((x, y), text, font=font, fill=color)


def make_solid(w, h, color1, color2):
    img = Image.new("RGB", (w, h), color1)
    return img


def make_gradient(w, h, color1, color2):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    for x in range(w):
        t = x / w
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(x, 0), (x, h)], fill=(r, g, b))
    return img


def make_checkerboard(w, h, color1, color2):
    img = Image.new("RGB", (w, h), color1)
    draw = ImageDraw.Draw(img)
    sq = max(20, min(w, h) // 10)
    for row in range(0, h, sq):
        for col in range(0, w, sq):
            if (row // sq + col // sq) % 2 == 0:
                draw.rectangle([(col, row), (col + sq, row + sq)], fill=color2)
    return img


def make_diagonal(w, h, color1, color2):
    img = Image.new("RGB", (w, h), color1)
    draw = ImageDraw.Draw(img)
    stripe = max(16, min(w, h) // 8)
    for i in range(-h, w + h, stripe * 2):
        draw.polygon(
            [(i, 0), (i + stripe, 0), (i + stripe + h, h), (i + h, h)],
            fill=color2,
        )
    return img


def make_noise(w, h, color1, color2):
    img = Image.new("RGB", (w, h), color1)
    pixels = img.load()
    r1, g1, b1 = color1
    for y in range(h):
        for x in range(w):
            noise = random.randint(-30, 30)
            pixels[x, y] = (
                max(0, min(255, r1 + noise)),
                max(0, min(255, g1 + noise)),
                max(0, min(255, b1 + noise)),
            )
    return img


RENDERERS = {
    "Solid": make_solid,
    "Gradient": make_gradient,
    "Checkerboard": make_checkerboard,
    "Diagonal": make_diagonal,
    "Noise": make_noise,
}


def make_placeholder(w, h, style, palette_name, label=None):
    color1, color2 = get_palette(palette_name)

    img = RENDERERS[style](w, h, color1, color2)
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Dimension text
    dim_text = f"{w} × {h}"
    font_size = max(16, min(w, h) // 8)
    font_size = min(font_size, 120)
    font = load_font(font_size)

    # Text color — auto contrast
    brightness = (color1[0] * 299 + color1[1] * 587 + color1[2] * 114) // 1000
    text_color = (255, 255, 255, 220) if brightness < 128 else (30, 30, 30, 220)

    if label:
        # Label above, dimensions below
        label_font_size = max(12, font_size // 2)
        label_font = load_font(label_font_size)
        # Draw label
        lb = draw.textbbox((0, 0), label, font=label_font)
        lw = lb[2] - lb[0]
        lh = lb[3] - lb[1]
        lx = (w - lw) // 2
        ly = h // 2 - lh - font_size // 2 - 8
        draw.text((lx + 2, ly + 2), label, font=label_font, fill=(0, 0, 0, 80))
        draw.text((lx, ly), label, font=label_font, fill=text_color)
        # Draw dims
        db = draw.textbbox((0, 0), dim_text, font=font)
        dw = db[2] - db[0]
        dh = db[3] - db[1]
        dx = (w - dw) // 2
        dy = h // 2 + 8
        draw.text((dx + 2, dy + 2), dim_text, font=font, fill=(0, 0, 0, 80))
        draw.text((dx, dy), dim_text, font=font, fill=text_color)
    else:
        draw_centered_text(draw, w, h, dim_text, font, text_color)

    # Border
    border_color = tuple(max(0, c - 40) for c in color1) + (180,)
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline=border_color, width=2)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return out.read()


# ---- Common presets ----
PRESETS = {
    "Twitter Header": (1500, 500),
    "Profile Avatar": (400, 400),
    "OG Image": (1200, 630),
    "Instagram Post": (1080, 1080),
    "Instagram Story": (1080, 1920),
    "YouTube Thumbnail": (1280, 720),
    "Facebook Cover": (851, 315),
    "Custom Size": None,
}


def send_preset_picker(cid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(name, callback_data=f"preset:{name}")
        for name in PRESETS
    ]
    markup.add(*buttons)
    bot.send_message(
        cid,
        "📐 *Step 1 — Choose a size preset:*",
        parse_mode="Markdown",
        reply_markup=markup,
    )


def send_style_picker(cid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⬜ Solid", callback_data="style:Solid"),
        types.InlineKeyboardButton("🌈 Gradient", callback_data="style:Gradient"),
        types.InlineKeyboardButton("▦ Checkerboard", callback_data="style:Checkerboard"),
        types.InlineKeyboardButton("⟋ Diagonal", callback_data="style:Diagonal"),
        types.InlineKeyboardButton("🌫 Noise", callback_data="style:Noise"),
    )
    bot.send_message(
        cid,
        "🎨 *Step 2 — Choose a style:*",
        parse_mode="Markdown",
        reply_markup=markup,
    )


def send_palette_picker(cid):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("⬜ Gray", callback_data="palette:Gray"),
        types.InlineKeyboardButton("🔵 Blue", callback_data="palette:Blue"),
        types.InlineKeyboardButton("🟢 Green", callback_data="palette:Green"),
        types.InlineKeyboardButton("🟣 Purple", callback_data="palette:Purple"),
        types.InlineKeyboardButton("🔴 Red", callback_data="palette:Red"),
        types.InlineKeyboardButton("🟠 Orange", callback_data="palette:Orange"),
        types.InlineKeyboardButton("🩷 Pink", callback_data="palette:Pink"),
        types.InlineKeyboardButton("⬛ Dark", callback_data="palette:Dark"),
        types.InlineKeyboardButton("🎲 Random", callback_data="palette:Random"),
    )
    bot.send_message(
        cid,
        "🖌 *Step 3 — Choose a color palette:*",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    cid = message.chat.id
    bot.send_message(
        cid,
        "👋 *Placeholder Image Generator*\n\n"
        "I generate placeholder images for your designs, mockups, and projects!\n\n"
        "📐 Pick a size, style, and color — get a PNG instantly.\n\n"
        "Send /make to start\n"
        "Send /quick for a fast one-line command\n"
        "Send /help for usage info",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["make"])
def cmd_make(message):
    cid = message.chat.id
    user_sessions[cid] = {"step": "preset"}
    send_preset_picker(cid)


@bot.message_handler(commands=["quick"])
def cmd_quick(message):
    cid = message.chat.id
    bot.send_message(
        cid,
        "⚡ *Quick mode*\n\n"
        "Send a message in this format:\n"
        "`/gen WIDTHxHEIGHT`\n\n"
        "Examples:\n"
        "`/gen 800x600`\n"
        "`/gen 1200x630 Blue Gradient My Banner`\n\n"
        "Format: `/gen WxH [palette] [style] [label]`\n"
        "Palette options: Gray, Blue, Green, Purple, Red, Orange, Pink, Dark, Random\n"
        "Style options: Solid, Gradient, Checkerboard, Diagonal, Noise",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["gen"])
def cmd_gen(message):
    cid = message.chat.id
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(cid, "Usage: `/gen WIDTHxHEIGHT [palette] [style] [label]`", parse_mode="Markdown")
        return

    size_str = parts[1].lower().replace(" ", "")
    try:
        if "x" in size_str:
            w, h = size_str.split("x")
            w, h = int(w), int(h)
        else:
            bot.send_message(cid, "❌ Size format: `800x600`", parse_mode="Markdown")
            return
    except ValueError:
        bot.send_message(cid, "❌ Invalid size. Example: `/gen 800x600`", parse_mode="Markdown")
        return

    # Cap size
    w = max(10, min(w, 4000))
    h = max(10, min(h, 4000))

    palette = "Gray"
    style = "Gradient"
    label = None

    remaining = parts[2:]
    if remaining:
        if remaining[0].capitalize() in PALETTES:
            palette = remaining[0].capitalize()
            remaining = remaining[1:]
    if remaining:
        if remaining[0].capitalize() in STYLES:
            style = remaining[0].capitalize()
            remaining = remaining[1:]
    if remaining:
        label = " ".join(remaining)

    try:
        result = make_placeholder(w, h, style, palette, label)
        bot.send_photo(
            cid,
            result,
            caption=f"✅ `{w}×{h}` — {style} / {palette}" + (f" / _{label}_" if label else ""),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("Quick gen error")
        bot.send_message(cid, f"❌ Error: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("preset:"))
def handle_preset(call):
    cid = call.message.chat.id
    preset_name = call.data.split(":", 1)[1]
    session = user_sessions.setdefault(cid, {})
    session["preset_name"] = preset_name

    bot.answer_callback_query(call.id, f"{preset_name} selected!")

    if preset_name == "Custom Size":
        bot.edit_message_text(
            "✅ Custom size selected.\n\n📏 *Send your size as:* `WIDTHxHEIGHT`\nExample: `1200x630`",
            cid,
            call.message.message_id,
            parse_mode="Markdown",
        )
        session["step"] = "custom_size"
    else:
        w, h = PRESETS[preset_name]
        session["width"] = w
        session["height"] = h
        bot.edit_message_text(
            f"✅ Size: *{preset_name}* ({w}×{h})",
            cid,
            call.message.message_id,
            parse_mode="Markdown",
        )
        session["step"] = "style"
        send_style_picker(cid)


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "custom_size")
def handle_custom_size(message):
    cid = message.chat.id
    session = user_sessions.get(cid, {})
    try:
        size_str = message.text.strip().lower().replace(" ", "")
        w, h = size_str.split("x")
        w, h = int(w), int(h)
        w = max(10, min(w, 4000))
        h = max(10, min(h, 4000))
        session["width"] = w
        session["height"] = h
        session["step"] = "style"
        bot.send_message(cid, f"✅ Size set to *{w}×{h}*", parse_mode="Markdown")
        send_style_picker(cid)
    except Exception:
        bot.send_message(cid, "❌ Invalid format. Send like: `1200x630`", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("style:"))
def handle_style(call):
    cid = call.message.chat.id
    style = call.data.split(":")[1]
    session = user_sessions.setdefault(cid, {})
    session["style"] = style
    session["step"] = "palette"
    bot.answer_callback_query(call.id, f"{style} selected!")
    bot.edit_message_text(
        f"✅ Style: *{style}*",
        cid,
        call.message.message_id,
        parse_mode="Markdown",
    )
    send_palette_picker(cid)


@bot.callback_query_handler(func=lambda call: call.data.startswith("palette:"))
def handle_palette(call):
    cid = call.message.chat.id
    palette = call.data.split(":")[1]
    session = user_sessions.setdefault(cid, {})
    session["palette"] = palette
    session["step"] = "label"
    bot.answer_callback_query(call.id, f"{palette} selected!")
    bot.edit_message_text(
        f"✅ Palette: *{palette}*",
        cid,
        call.message.message_id,
        parse_mode="Markdown",
    )
    bot.send_message(
        cid,
        "🏷 *Step 4 — Add a label?*\n\nSend any text to add a label on the image.\nSend /skip to show only the dimensions.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "label")
def handle_label(message):
    cid = message.chat.id
    session = user_sessions.get(cid, {})
    label = None if message.text.strip() == "/skip" else message.text.strip()
    session["label"] = label
    session["step"] = "done"
    generate_image(cid)


def generate_image(cid):
    session = user_sessions.get(cid, {})
    w = session.get("width", 800)
    h = session.get("height", 600)
    style = session.get("style", "Gradient")
    palette = session.get("palette", "Gray")
    label = session.get("label")

    msg = bot.send_message(cid, "⏳ Generating your placeholder…")
    try:
        result = make_placeholder(w, h, style, palette, label)
        caption = (
            f"✅ *{w}×{h}* placeholder ready!\n"
            f"Style: {style} · Palette: {palette}"
        )
        if label:
            caption += f" · Label: _{label}_"
        caption += "\n\nSend /make for another or /quick for fast mode."
        bot.send_photo(cid, result, caption=caption, parse_mode="Markdown")
        bot.delete_message(cid, msg.message_id)
    except Exception as e:
        logger.exception("Generate error")
        bot.send_message(cid, f"❌ Failed: {e}")


@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    cid = message.chat.id
    user_sessions.pop(cid, None)
    bot.send_message(cid, "❌ Cancelled. Send /make to start over.")


if __name__ == "__main__":
    logger.info("Placeholder bot starting…")
    bot.infinity_polling()
