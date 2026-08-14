import io
import os
import re
import textwrap
from pathlib import Path

import qrcode
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageFilter
from dotenv import load_dotenv
from openai import OpenAI

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ============================================================
# A.R.I.A. SMART POSTER ENGINE V2
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
FONT_DIR = ASSET_DIR / "fonts"
TEMPLATE_DIR = ASSET_DIR / "templates"
FONT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

st.set_page_config(
    page_title="A.R.I.A. Smart Poster Engine V2",
    layout="wide",
    page_icon="🎨",
)

# ============================================================
# CONSTANTS
# ============================================================

GOOGLE_FONTS_RAW = "https://raw.githubusercontent.com/google/fonts/main"

FONT_CATALOG = {
    "Poppins (Modern/Bold)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/poppins/Poppins%5Bwght%5D.ttf",
    },
    "Playfair Display (Elegant)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    },
    "Fredoka (Playful)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/fredoka/Fredoka%5Bwght%5D.ttf",
    },
    "Roboto (Clean)": {
        "url": f"{GOOGLE_FONTS_RAW}/apache/roboto/Roboto%5Bwght%5D.ttf",
    },
    "Oswald (Strong)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/oswald/Oswald%5Bwght%5D.ttf",
    },
    "Lobster (Decorative)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/lobster/Lobster-Regular.ttf",
    },
    "Bebas Neue (Impact)": {
        "url": f"{GOOGLE_FONTS_RAW}/ofl/bebasneue/BebasNeue-Regular.ttf",
    },
}

STYLE_CONFIGS = {
    "Bold & Modern": {
        "font": "Poppins (Modern/Bold)",
        "headline": "#FFFFFF",
        "subtext": "#FDE68A",
        "brand": "#FFFFFF",
        "accent": "#22C55E",
        "outline": "#000000",
        "shadow": "#000000",
        "overlay": (0, 0, 0, 105),
    },
    "Elegant & Traditional": {
        "font": "Playfair Display (Elegant)",
        "headline": "#FFFDF5",
        "subtext": "#FCD34D",
        "brand": "#FFFDF5",
        "accent": "#B45309",
        "outline": "#172033",
        "shadow": "#000000",
        "overlay": (0, 0, 0, 90),
    },
    "Fun & Playful": {
        "font": "Fredoka (Playful)",
        "headline": "#FFFFFF",
        "subtext": "#FECACA",
        "brand": "#FFFFFF",
        "accent": "#EF4444",
        "outline": "#7F1D1D",
        "shadow": "#000000",
        "overlay": (0, 0, 0, 90),
    },
    "Minimal & Clean": {
        "font": "Roboto (Clean)",
        "headline": "#FFFFFF",
        "subtext": "#E5E7EB",
        "brand": "#FFFFFF",
        "accent": "#2563EB",
        "outline": "#111827",
        "shadow": "#000000",
        "overlay": (0, 0, 0, 80),
    },
    "Strong & Impact": {
        "font": "Bebas Neue (Impact)",
        "headline": "#FFFFFF",
        "subtext": "#FBBF24",
        "brand": "#FFFFFF",
        "accent": "#F59E0B",
        "outline": "#000000",
        "shadow": "#000000",
        "overlay": (0, 0, 0, 115),
    },
}

POSTER_SIZES = {
    "Instagram Square — 1080 × 1080": (1080, 1080),
    "Instagram Portrait — 1080 × 1350": (1080, 1350),
    "Instagram Story — 1080 × 1920": (1080, 1920),
    "Facebook Post — 1080 × 1080": (1080, 1080),
    "WhatsApp Status — 1080 × 1920": (1080, 1920),
    "A4 Print — 2480 × 3508": (2480, 3508),
}

CTA_OPTIONS = [
    "ORDER NOW",
    "SHOP NOW",
    "BOOK NOW",
    "CALL NOW",
    "DM US",
    "VISIT US",
    "LEARN MORE",
    "NO CTA",
]

# ============================================================
# HELPERS
# ============================================================

def safe_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return value.strip("_") or "aria_poster"


@st.cache_resource(show_spinner=False)
def _download_font_cached(font_name: str, font_url: str):
    """Download a Google Font and cache the path.

    Only successful downloads are cached (st.cache_resource caches
    whatever is returned, including None) — a transient network error
    must not be memorized as "this font can never be downloaded" for
    the rest of the app's process lifetime.
    """
    safe_name = safe_filename(font_name) + ".ttf"
    font_path = FONT_DIR / safe_name

    if font_path.exists() and font_path.stat().st_size > 1000:
        return str(font_path)

    response = requests.get(font_url, timeout=20)
    response.raise_for_status()
    font_path.write_bytes(response.content)
    return str(font_path)


def download_font(font_name: str, font_url: str):
    """Public wrapper: returns a font path, or None on failure, without
    poisoning the cache with the failure itself."""
    try:
        return _download_font_cached(font_name, font_url)
    except Exception:
        return None


def load_font(font_path, size):
    """Load the selected font; use a system/default fallback."""
    if font_path and Path(font_path).exists():
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    for system_font in [
        "arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(system_font, size)
        except Exception:
            continue

    return ImageFont.load_default()


def fit_font(text, font_path, max_width, start_size, min_size=24, stroke_width=0):
    """Automatically reduce font size until text fits max_width.

    stroke_width must match what will actually be used to render the text
    (draw_block_top_aligned draws an outline), otherwise the outlined
    text can overflow max_width even though the bare glyph fit.
    """
    text = str(text).strip()
    if not text:
        return load_font(font_path, min_size)

    for size in range(start_size, min_size - 1, -2):
        font = load_font(font_path, size)
        bbox = font.getbbox(text, stroke_width=stroke_width)
        if (bbox[2] - bbox[0]) <= max_width:
            return font

    return load_font(font_path, min_size)


def get_text_size(draw, text, font, stroke_width=0):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text_to_width(draw, text, font, max_width):
    """Word-wrap using actual rendered pixel width.

    A word that is wider than max_width all by itself (a long URL, a
    compound word, etc.) cannot be fixed by shrinking the font alone —
    fit_font has a min_size floor for readability, and even below that
    a single very long word could still overflow. So here we hard-break
    any such word into character chunks that each fit max_width.
    """
    words = str(text).split()
    if not words:
        return []

    lines = []
    current = ""

    for word in words:
        word_width, _ = get_text_size(draw, word, font, 0)

        if word_width > max_width:
            # Flush whatever we were building, then hard-break this word.
            if current:
                lines.append(current)
                current = ""

            chunk = ""
            for ch in word:
                candidate = chunk + ch
                cw, _ = get_text_size(draw, candidate, font, 0)
                if cw <= max_width or not chunk:
                    chunk = candidate
                else:
                    lines.append(chunk)
                    chunk = ch
            current = chunk
            continue

        candidate = f"{current} {word}".strip()
        width, _ = get_text_size(draw, candidate, font, 0)

        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def rects_overlap(a, b, pad=0):
    """a, b are (x1, y1, x2, y2). True if they intersect, with an
    optional padding buffer treated as part of each rect."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ax1, ay1, ax2, ay2 = ax1 - pad, ay1 - pad, ax2 + pad, ay2 + pad
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


def measure_block(draw, text, font, max_width, stroke_width, line_spacing):
    """Wrap text and measure its total rendered height without drawing."""
    lines = wrap_text_to_width(draw, text, font, max_width)
    if not lines:
        return [], [], 0
    heights = [get_text_size(draw, line, font, stroke_width)[1] for line in lines]
    total_h = sum(heights) + line_spacing * (len(lines) - 1)
    return lines, heights, total_h


def draw_block_top_aligned(
    image, draw, lines, heights, top_y, font, fill, outline,
    stroke_width=4, line_spacing=12,
):
    """Draw a pre-wrapped, pre-measured text block starting at top_y.
    Returns the y-coordinate of the block's bottom edge."""
    y = top_y
    for line, line_h in zip(lines, heights):
        text_w, _ = get_text_size(draw, line, font, stroke_width)
        x = (image.width - text_w) / 2

        draw.text(
            (x + 5, y + 6), line, font=font,
            fill="#000000", stroke_width=stroke_width + 2, stroke_fill="#000000",
        )
        draw.text(
            (x, y), line, font=font,
            fill=fill, stroke_width=stroke_width, stroke_fill=outline,
        )
        y += line_h + line_spacing

    return y - line_spacing if lines else top_y


def add_gradient_overlay(image, direction="bottom", strength=120):
    """Add a transparent black gradient for readable text.

    Fully vectorized with NumPy: the alpha ramp is built as one 2D array
    in C, with no Python-level loop over rows or pixels at all. Falls
    back to a 1D-loop-plus-resize approach if NumPy isn't installed
    (still far faster than the original per-pixel Python loop, just not
    quite as fast as the NumPy path).
    """
    image = image.convert("RGBA")
    w, h = image.size

    if strength <= 0:
        return image

    if _HAS_NUMPY:
        rows = np.arange(h, dtype=np.float32) / max(1, h - 1)
        if direction != "bottom":
            rows = 1 - rows
        alpha_row = np.clip(rows * strength, 0, 255).astype(np.uint8)
        alpha_2d = np.broadcast_to(alpha_row[:, None], (h, w))
        alpha = Image.fromarray(alpha_2d, mode="L")
    else:
        ramp = []
        for y in range(h):
            factor = y / max(1, h - 1)
            if direction != "bottom":
                factor = 1 - factor
            ramp.append(int(max(0, min(255, factor * strength))))
        alpha_col = Image.new("L", (1, h))
        alpha_col.putdata(ramp)
        alpha = alpha_col.resize((w, h))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay.putalpha(alpha)

    return Image.alpha_composite(image, overlay)


def analyze_background_brightness(image, region="bottom"):
    """Average grayscale brightness (0-255) of the region where text
    will actually sit, so overlay strength can respond to the real
    photo instead of using one fixed value for every background."""
    gray = image.convert("L")

    if _HAS_NUMPY:
        arr = np.array(gray)
        h = arr.shape[0]
        if region == "bottom":
            sample = arr[int(h * 0.35):, :]
        elif region == "top":
            sample = arr[: int(h * 0.35), :]
        else:
            sample = arr
        return float(sample.mean())

    # Fallback without numpy: histogram-weighted average over the
    # full image (region cropping skipped for simplicity).
    hist = gray.histogram()
    total = sum(hist)
    if not total:
        return 128.0
    return sum(i * c for i, c in enumerate(hist)) / total


def recommended_gradient_strength(brightness):
    """Map background brightness to a sensible overlay strength.
    Darker backgrounds need little to no darkening; bright ones need
    a stronger overlay to keep white/light text readable."""
    if brightness < 60:
        return 40
    elif brightness < 110:
        return 90
    elif brightness < 170:
        return 135
    else:
        return 175


def crop_to_fill(image, size):
    """Crop image to target aspect ratio without distortion."""
    target_w, target_h = size
    image = image.convert("RGB")

    src_w, src_h = image.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        image = image.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        image = image.crop((0, top, src_w, top + new_h))

    return image.resize(size, Image.Resampling.LANCZOS)


def apply_upload_darkening(image, amount=0.82):
    return ImageEnhance.Brightness(image).enhance(amount)


def compute_logo_rect(image_size, logo, position="Top Right", max_width_frac=0.22, max_height_frac=0.14, margin=55):
    """Compute the logo's placement rect, sized by its own aspect ratio.

    A fixed width percentage (e.g. "18% of canvas width") looks fine for
    a roughly-square logo, but blows up visually for a wide horizontal
    logo and eats too much vertical space for a tall one. Instead this
    caps BOTH the width and the height the logo may occupy, and picks
    whichever constraint yields the smaller box — so a wide logo gets
    capped by width, a tall logo gets capped by height, and either way
    it fits comfortably in its corner.
    """
    if logo is None:
        return None

    iw, ih = image_size
    aspect = logo.width / max(1, logo.height)

    max_w = iw * max_width_frac
    max_h = ih * max_height_frac

    # Candidate size if width is the binding constraint, and vice versa.
    w_by_width, h_by_width = max_w, max_w / aspect
    w_by_height, h_by_height = max_h * aspect, max_h

    if h_by_width <= max_h:
        target_w, target_h = w_by_width, h_by_width
    else:
        target_w, target_h = w_by_height, h_by_height

    target_w = max(60, int(target_w))
    target_h = max(40, int(target_h))

    if position == "Top Left":
        x, y = margin, margin
    elif position == "Bottom Left":
        x, y = margin, ih - target_h - margin
    elif position == "Bottom Right":
        x, y = iw - target_w - margin, ih - target_h - margin
    else:
        x, y = iw - target_w - margin, margin

    return (x, y, x + target_w, y + target_h)


def add_logo(image, logo, rect):
    """Place a logo with transparency at a precomputed rect."""
    if logo is None or rect is None:
        return image

    x, y, x2, y2 = rect
    logo = logo.convert("RGBA").resize((x2 - x, y2 - y), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, (x, y))
    return image


def compute_cta_layout(image_width, text, font_path):
    """Compute the CTA pill's font, size, line(s) and horizontal position.
    Does not depend on y, so this can be called early for layout math.

    fit_font tries to shrink the font to fit max_width, but has a
    min_size floor for readability — a long CTA phrase can still be
    wider than max_width even at min_size. Rather than let the pill
    silently overflow the canvas edge, wrap onto a second line if one
    line still doesn't fit.
    """
    if text == "NO CTA":
        return None

    max_text_w = int(image_width * 0.42)
    font = fit_font(text, font_path, max_text_w, 58, 28)

    tmp = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(tmp)
    text_w, text_h = get_text_size(draw, text, font)

    lines = [text]
    if text_w > max_text_w:
        wrapped = wrap_text_to_width(draw, text, font, max_text_w)
        if len(wrapped) > 1:
            lines = wrapped[:2]  # cap at 2 lines — a pill isn't a paragraph
            line_sizes = [get_text_size(draw, ln, font) for ln in lines]
            text_w = max(w for w, _ in line_sizes)
            text_h = sum(h for _, h in line_sizes) + int(text_h * 0.25)
        # Hard clamp as a last resort so the pill can never exceed the
        # canvas regardless of wrapping.
        text_w = min(text_w, max_text_w)

    pad_x = int(image_width * 0.045)
    pad_y = int(image_width * 0.018)
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2
    x = (image_width - box_w) // 2

    return {
        "font": font, "lines": lines, "text_w": text_w, "text_h": text_h,
        "box_w": box_w, "box_h": box_h, "x": x,
    }


def cta_rect_for_y(layout, y):
    if layout is None:
        return None
    return (layout["x"], y, layout["x"] + layout["box_w"], y + layout["box_h"])


def draw_cta(image, text, accent, layout, y):
    """Draw a rounded CTA pill at a precomputed layout and explicit y."""
    if text == "NO CTA" or layout is None:
        return image

    font = layout["font"]
    lines = layout["lines"]
    box_w, box_h = layout["box_w"], layout["box_h"]
    x = layout["x"]

    # Shadow — rendered on a small padded crop around the pill only,
    # then blurred and composited back, instead of blurring the full
    # canvas (slow at large poster sizes like A4 print).
    blur_pad = 24
    shadow = Image.new("RGBA", (box_w + blur_pad * 2, box_h + blur_pad * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (blur_pad + 8, blur_pad + 10, blur_pad + box_w + 8, blur_pad + box_h + 10),
        radius=min(box_h, 90) // 2,
        fill=(0, 0, 0, 100),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    image.alpha_composite(shadow, (x - blur_pad, int(y) - blur_pad))

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (x, y, x + box_w, y + box_h),
        radius=min(box_h, 90) // 2,
        fill=accent,
    )

    line_sizes = [get_text_size(draw, ln, font) for ln in lines]
    total_text_h = sum(h for _, h in line_sizes) + int(4 * len(lines))
    ty = y + (box_h - total_text_h) / 2
    for line, (lw, lh) in zip(lines, line_sizes):
        tx = x + (box_w - lw) / 2
        draw.text((tx, ty), line, font=font, fill="#FFFFFF")
        ty += lh + 4

    return image


def compute_qr_rect(image_size, position="Bottom Right", size_ratio=0.16, margin=45):
    """Estimate the QR backing's placement rect (square, so this is
    exact once size_ratio/margin are fixed — no need to render the QR
    itself first)."""
    iw, ih = image_size
    target = int(iw * size_ratio)
    pad = max(12, int(target * 0.08))
    side = target + pad * 2

    if position == "Bottom Left":
        x, y = margin, ih - side - margin
    elif position == "Top Left":
        x, y = margin, margin
    elif position == "Top Right":
        x, y = iw - side - margin, margin
    else:
        x, y = iw - side - margin, ih - side - margin

    return (x, y, x + side, y + side)


def nudge_rect_away(rect, avoid_rects, position, image_size, gap=20):
    """If rect overlaps anything in avoid_rects, slide it further along
    its own edge (up if it's a bottom-corner element, down if top;
    inward slightly if that's not enough) until clear, or give up after
    a few tries and leave it at the last attempted spot."""
    iw, ih = image_size
    x1, y1, x2, y2 = rect
    is_bottom = position.startswith("Bottom")

    for _ in range(6):
        blocked = next((r for r in avoid_rects if r and rects_overlap((x1, y1, x2, y2), r, pad=gap)), None)
        if blocked is None:
            break
        if is_bottom:
            shift = blocked[1] - y2 - gap  # move up above the blocker
            y1 += shift
            y2 += shift
        else:
            shift = blocked[3] - y1 + gap  # move down below the blocker
            y1 += shift
            y2 += shift
        # keep on-canvas
        if y1 < 0:
            y1, y2 = 0, y2 - y1
        if y2 > ih:
            y1, y2 = y1 - (y2 - ih), ih

    return (x1, y1, x2, y2)


def draw_qr_code(image, data, rect):
    """Generate and place a QR code inside a precomputed rect."""
    if not data.strip():
        return image

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data.strip())
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    x1, y1, x2, y2 = rect
    side = x2 - x1
    pad = max(12, int(side * 0.08 / 1.16))  # matches compute_qr_rect's padding ratio
    inner = side - pad * 2
    qr_img = qr_img.resize((max(1, inner), max(1, inner)), Image.Resampling.LANCZOS)

    backing = Image.new("RGBA", (side, side), "white")
    backing.alpha_composite(qr_img, (pad, pad))

    image.alpha_composite(backing, (int(x1), int(y1)))
    return image


def validate_layout(image_size, rects):
    """Check a finished layout for problems.

    rects: dict of name -> (x1,y1,x2,y2) or None, e.g.
      {"headline": ..., "subtext": ..., "contact": ..., "brand": ...,
       "logo": ..., "cta": ..., "qr": ...}

    Returns a list of human-readable issue strings (empty = all clear).
    Every named rect is checked against canvas bounds, and every pair
    of rects is checked against each other for overlap.
    """
    iw, ih = image_size
    issues = []
    named = {k: v for k, v in rects.items() if v is not None}

    for name, (x1, y1, x2, y2) in named.items():
        if x1 < -1 or y1 < -1 or x2 > iw + 1 or y2 > ih + 1:
            issues.append(f"{name} extends outside the canvas ({(x1, y1, x2, y2)})")

    names = list(named.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if rects_overlap(named[a], named[b]):
                issues.append(f"{a} overlaps {b}")

    return issues


def compute_text_stack_layout(image, font_path, scale, content_top, content_height,
                               headline, subtext, contact_line, business_name):
    """Fit fonts, wrap, and stack headline/subtext/contact/brand inside
    [content_top, content_top + content_height], auto-shrinking fonts
    (in that priority order) when the nominal sizes don't fit, instead
    of silently overlapping or overflowing.

    Returns a dict with each block's font/lines/heights, the gaps to
    use between them, the starting y, and a `fits` flag.
    """
    draw = ImageDraw.Draw(image)

    headline_max_w = int(image.width * 0.86)
    subtext_max_w = int(image.width * 0.80)
    contact_max_w = int(image.width * 0.78)
    brand_max_w = int(image.width * 0.72)

    strokes = {
        "headline": max(2, int(5 * scale)),
        "subtext": max(2, int(3 * scale)),
        "contact": max(2, int(2 * scale)),
        "brand": max(2, int(3 * scale)),
    }
    line_spacings = {
        "headline": max(8, int(14 * scale)),
        "subtext": max(6, int(10 * scale)),
        "contact": max(4, int(6 * scale)),
        "brand": max(5, int(8 * scale)),
    }
    max_widths = {
        "headline": headline_max_w, "subtext": subtext_max_w,
        "contact": contact_max_w, "brand": brand_max_w,
    }
    texts = {
        "headline": headline.upper(), "subtext": subtext,
        "contact": contact_line, "brand": business_name.upper(),
    }
    has_contact = bool(contact_line.strip())

    start_sizes = {
        "headline": int(128 * scale), "subtext": int(54 * scale),
        "contact": int(34 * scale), "brand": int(44 * scale),
    }
    min_sizes = {
        "headline": max(28, int(32 * scale)), "subtext": max(16, int(18 * scale)),
        "contact": max(12, int(14 * scale)), "brand": max(14, int(16 * scale)),
    }
    shrink_step = max(2, int(4 * scale))
    # Priority order per the requested cascade: headline first, then
    # subtext, then contact, then brand.
    order = ["headline", "subtext", "contact", "brand"]

    current_sizes = dict(start_sizes)
    fonts, lines_map, heights_map, totals = {}, {}, {}, {}

    def refit_and_measure():
        for name in order:
            if name == "contact" and not has_contact:
                fonts[name], lines_map[name], heights_map[name], totals[name] = None, [], [], 0
                continue
            font = fit_font(
                texts[name], font_path, max_widths[name],
                current_sizes[name], min_sizes[name], stroke_width=strokes[name],
            )
            fonts[name] = font
            lines_map[name], heights_map[name], totals[name] = measure_block(
                draw, texts[name], font, max_widths[name], strokes[name], line_spacings[name],
            )

    refit_and_measure()

    min_gap = max(4, int(8 * scale))
    for _ in range(40):
        blocks_total = sum(totals.values())
        n_gaps = 3 if has_contact else 2
        if blocks_total + n_gaps * min_gap <= content_height:
            break
        shrank = False
        for name in order:
            if name == "contact" and not has_contact:
                continue
            if current_sizes[name] > min_sizes[name]:
                current_sizes[name] = max(min_sizes[name], current_sizes[name] - shrink_step)
                shrank = True
                break
        if not shrank:
            break  # everything is already at its floor
        refit_and_measure()

    blocks_total = sum(totals.values())
    n_gaps = 3 if has_contact else 2
    fits = blocks_total + n_gaps * min_gap <= content_height

    nominal_gaps = {
        "h_s": max(20, int(40 * scale)),
        "s_c": max(14, int(26 * scale)) if has_contact else 0,
        "c_b": max(14, int(26 * scale)) if has_contact else max(18, int(34 * scale)),
    }
    nominal_gap_total = sum(nominal_gaps.values())
    available_for_gaps = content_height - blocks_total

    if available_for_gaps >= nominal_gap_total:
        gaps = dict(nominal_gaps)
        y = content_top + (available_for_gaps - nominal_gap_total) / 2
    elif available_for_gaps > 0:
        ratio = available_for_gaps / nominal_gap_total if nominal_gap_total else 0
        gaps = {k: (int(v * ratio) if v else 0) for k, v in nominal_gaps.items()}
        y = content_top
    else:
        gaps = {"h_s": min_gap if not fits else 0, "s_c": 0, "c_b": min_gap if not fits else 0}
        y = content_top

    return {
        "fonts": fonts, "lines": lines_map, "heights": heights_map,
        "totals": totals, "gaps": gaps, "start_y": y, "fits": fits,
        "strokes": strokes, "line_spacings": line_spacings,
    }


def find_best_qr_position(image_size, preferred_position, avoid_rects,
                           size_ratio=0.15, margin=45, min_ratio=0.09):
    """Smart QR placement: try the preferred corner, then the other
    three corners at the normal size; only if every corner collides
    does it start shrinking the QR (still trying all four corners at
    each smaller size) before finally falling back to a nudge.
    """
    all_positions = ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
    order = [preferred_position] + [p for p in all_positions if p != preferred_position]
    avoid = [r for r in avoid_rects if r]

    ratio = size_ratio
    while ratio >= min_ratio:
        for pos in order:
            rect = compute_qr_rect(image_size, pos, ratio, margin)
            if not any(rects_overlap(rect, r) for r in avoid):
                return rect, ratio, False  # False = no fallback needed
        ratio -= 0.015

    # Nothing fit even at the smallest size — last resort: place at
    # the preferred corner, smallest size, and nudge away from the
    # single worst offender.
    rect = compute_qr_rect(image_size, preferred_position, min_ratio, margin)
    rect = nudge_rect_away(rect, avoid, preferred_position, image_size)
    return rect, min_ratio, True


def create_smart_poster(
    base_image,
    headline,
    subtext,
    business_name,
    style_name,
    size,
    font_path,
    logo=None,
    logo_position="Top Right",
    cta="NO CTA",
    cta_position="Bottom",
    qr_data="",
    qr_position="Bottom Right",
    gradient_strength=115,
    darken_background=True,
    contact_line="",
):
    """Main V3 rendering engine — layout-driven and self-correcting.

    1. Reserves top/bottom bands based on the actual size of the logo
       and CTA (if positioned there).
    2. Fits and stacks headline/subtext/contact/brand inside whatever
       space remains, auto-shrinking fonts (headline -> subtext ->
       contact -> brand) if the nominal sizes don't fit.
    3. Validates the resulting layout (validate_layout) and, if it
       still finds a text/logo or text/CTA overlap, widens the
       reserved band and re-runs the stack fit — up to a few tries.
    4. Places the QR last, trying all four corners (avoiding logo,
       CTA, AND every text block) before shrinking it as a last resort.
    """
    config = STYLE_CONFIGS[style_name]

    image = crop_to_fill(base_image, size).convert("RGBA")

    if darken_background:
        image = apply_upload_darkening(image, 0.82)

    if gradient_strength == "auto" or gradient_strength is None:
        brightness = analyze_background_brightness(image, region="bottom")
        gradient_strength = recommended_gradient_strength(brightness)

    image = add_gradient_overlay(image, direction="bottom", strength=gradient_strength)

    scale = image.width / 1080
    outer_margin = max(40, int(50 * scale))

    logo_rect = compute_logo_rect((image.width, image.height), logo, logo_position)
    cta_layout = compute_cta_layout(image.width, cta, font_path)

    # --- Reserve bands + fit the text stack, with a bounded number of
    # corrective retries if validation still finds an overlap ------------
    top_pad_extra = 0
    bottom_pad_extra = 0
    stack = None
    headline_rect = subtext_rect = contact_rect = brand_rect = None

    for attempt in range(3):
        top_reserved = outer_margin + top_pad_extra
        bottom_reserved = outer_margin + bottom_pad_extra

        if logo_rect is not None:
            if logo_position.startswith("Top"):
                top_reserved = max(top_reserved, (logo_rect[3]) + outer_margin)
            else:
                bottom_reserved = max(bottom_reserved, (image.height - logo_rect[1]) + outer_margin)

        cta_y = None
        cta_rect = None
        if cta_layout is not None:
            if cta_position == "Top":
                cta_y = top_reserved
                cta_rect = cta_rect_for_y(cta_layout, cta_y)
                top_reserved = max(top_reserved, cta_rect[3] + outer_margin)
            else:
                cta_y = image.height - bottom_reserved - cta_layout["box_h"]
                cta_rect = cta_rect_for_y(cta_layout, cta_y)
                bottom_reserved = max(bottom_reserved, (image.height - cta_rect[1]) + outer_margin)

        content_top = top_reserved
        content_bottom = image.height - bottom_reserved
        content_height = max(80, content_bottom - content_top)

        stack = compute_text_stack_layout(
            image, font_path, scale, content_top, content_height,
            headline, subtext, contact_line, business_name,
        )

        # Compute the resulting bounding rect of each text block (for
        # validation and later QR-avoidance) without drawing yet.
        def block_rect(name, top_y):
            lines = stack["lines"][name]
            if not lines:
                return None, top_y
            heights = stack["heights"][name]
            font = stack["fonts"][name]
            stroke = stack["strokes"][name]
            spacing = stack["line_spacings"][name]
            tmp_draw = ImageDraw.Draw(image)
            max_w = max(get_text_size(tmp_draw, ln, font, stroke)[0] for ln in lines)
            total_h = sum(heights) + spacing * (len(lines) - 1)
            x1 = (image.width - max_w) / 2
            rect = (x1, top_y, x1 + max_w, top_y + total_h)
            return rect, top_y + total_h

        y = stack["start_y"]
        headline_rect, y = block_rect("headline", y)
        y += stack["gaps"]["h_s"]
        subtext_rect, y = block_rect("subtext", y)
        if stack["totals"]["contact"]:
            y += stack["gaps"]["s_c"]
            contact_rect, y = block_rect("contact", y)
        else:
            contact_rect = None
        y += stack["gaps"]["c_b"]
        brand_rect, _ = block_rect("brand", y)

        issues = validate_layout(
            (image.width, image.height),
            {
                "headline": headline_rect, "subtext": subtext_rect,
                "contact": contact_rect, "brand": brand_rect,
                "logo": logo_rect, "cta": cta_rect,
            },
        )

        # Only text-vs-(logo/cta) overlaps are worth retrying for —
        # those mean our reserved band was too small. Anything else
        # (e.g. a genuinely tiny canvas) won't be fixed by more margin.
        text_names = {"headline", "subtext", "contact", "brand"}
        band_issues = [
            i for i in issues
            if ("logo" in i or "cta" in i) and any(t in i for t in text_names)
        ]
        if not band_issues or attempt == 2:
            break

        # Widen whichever band is implicated and try again.
        if any("logo" in i for i in band_issues) and logo_rect is not None:
            if logo_position.startswith("Top"):
                top_pad_extra += max(20, int(30 * scale))
            else:
                bottom_pad_extra += max(20, int(30 * scale))
        if any("cta" in i for i in band_issues) and cta_layout is not None:
            if cta_position == "Top":
                top_pad_extra += max(20, int(30 * scale))
            else:
                bottom_pad_extra += max(20, int(30 * scale))

    # --- Draw the text stack ---------------------------------------------
    draw = ImageDraw.Draw(image)
    y = stack["start_y"]
    y = draw_block_top_aligned(
        image, draw, stack["lines"]["headline"], stack["heights"]["headline"], y,
        stack["fonts"]["headline"], config["headline"], config["outline"],
        stroke_width=stack["strokes"]["headline"], line_spacing=stack["line_spacings"]["headline"],
    )
    y += stack["gaps"]["h_s"]

    y = draw_block_top_aligned(
        image, draw, stack["lines"]["subtext"], stack["heights"]["subtext"], y,
        stack["fonts"]["subtext"], config["subtext"], config["outline"],
        stroke_width=stack["strokes"]["subtext"], line_spacing=stack["line_spacings"]["subtext"],
    )

    if stack["totals"]["contact"]:
        y += stack["gaps"]["s_c"]
        y = draw_block_top_aligned(
            image, draw, stack["lines"]["contact"], stack["heights"]["contact"], y,
            stack["fonts"]["contact"], config["subtext"], config["outline"],
            stroke_width=stack["strokes"]["contact"], line_spacing=stack["line_spacings"]["contact"],
        )

    y += stack["gaps"]["c_b"]
    draw_block_top_aligned(
        image, draw, stack["lines"]["brand"], stack["heights"]["brand"], y,
        stack["fonts"]["brand"], config["brand"], config["outline"],
        stroke_width=stack["strokes"]["brand"], line_spacing=stack["line_spacings"]["brand"],
    )

    # --- Logo & CTA ---------------------------------------------------------
    if logo is not None:
        image = add_logo(image, logo, logo_rect)

    if cta_layout is not None:
        image = draw_cta(image, cta, config["accent"], cta_layout, cta_y)

    # --- QR last: avoid logo, CTA, AND every text block, trying all four
    # corners before shrinking -------------------------------------------
    if qr_data.strip():
        avoid_rects = [logo_rect, cta_rect, headline_rect, subtext_rect, contact_rect, brand_rect]
        qr_rect, used_ratio, had_to_shrink = find_best_qr_position(
            (image.width, image.height), qr_position, avoid_rects, size_ratio=0.15,
        )
        image = draw_qr_code(image, qr_data, qr_rect)

    return image.convert("RGB")


# ============================================================
# UNSPLASH
# ============================================================

def fetch_unsplash_images(query="festival", count=6):
    if not UNSPLASH_ACCESS_KEY:
        st.error(
            "UNSPLASH_ACCESS_KEY is missing. Add it to Streamlit Secrets or .env."
        )
        return []

    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "per_page": count,
                "orientation": "squarish",
                "client_id": UNSPLASH_ACCESS_KEY,
            },
            timeout=20,
        )
        response.raise_for_status()

        images = []
        for result in response.json().get("results", []):
            img_response = requests.get(
                result["urls"]["regular"],
                timeout=20,
            )
            img_response.raise_for_status()
            images.append(img_response.content)

        return images

    except Exception as exc:
        st.error(f"Unsplash error: {exc}")
        return []


# ============================================================
# OPENAI
# ============================================================

def call_openai(prompt):
    if client is None:
        return (
            "AI is disabled because OPENAI_API_KEY is not configured. "
            "Add the key to .env or Streamlit Secrets."
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert marketing assistant for Indian "
                        "small businesses. Keep copy practical, concise and "
                        "natural. Avoid unsupported claims."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        return f"AI error: {exc}"


# ============================================================
# UI
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #F8FAFC;
    }

    .main-header {
        font-size: 2.4rem;
        color: #0F172A;
        font-weight: 800;
        text-align: center;
        margin-top: 0.5rem;
    }

    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        min-height: 44px;
    }

    .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-header">🎨 A.R.I.A. Smart Poster Engine V2</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">AI copy • Smart typography • Logos • CTA • QR • Social & Print Sizes</div>',
    unsafe_allow_html=True,
)

tab_poster, tab_review, tab_inquiry = st.tabs(
    ["🎨 Smart Poster", "⭐ Review Responder", "💬 Inquiry Responder"]
)

# ============================================================
# TAB 1 — SMART POSTER
# ============================================================

with tab_poster:
    st.subheader("Create a professional poster")

    with st.sidebar:
        st.markdown("## 🎨 Poster Settings")

        bg_source = st.radio(
            "Background Source",
            [
                "📦 Pre-made Templates",
                "🌐 Unsplash",
                "📤 Upload Your Own",
            ],
        )

        design_style = st.selectbox(
            "Design Style",
            list(STYLE_CONFIGS.keys()),
        )

        size_name = st.selectbox(
            "Poster Size",
            list(POSTER_SIZES.keys()),
        )

        cta = st.selectbox("CTA Button", CTA_OPTIONS)

        cta_position = st.selectbox(
            "CTA Position",
            ["Bottom", "Top"],
        )

        logo_position = st.selectbox(
            "Logo Position",
            ["Top Right", "Top Left", "Bottom Right", "Bottom Left"],
        )

        qr_position = st.selectbox(
            "QR Position",
            ["Bottom Right", "Bottom Left", "Top Right", "Top Left"],
        )

        auto_gradient = st.checkbox(
            "Auto-detect overlay strength",
            value=True,
            help="Analyzes how bright the background photo is and picks a "
                 "readable overlay automatically. Turn off to set it manually.",
        )
        if auto_gradient:
            gradient_strength = "auto"
        else:
            gradient_strength = st.slider(
                "Gradient Strength",
                min_value=0,
                max_value=220,
                value=115,
                step=5,
            )

        uploaded_image = None
        selected_template = None

        if bg_source == "📤 Upload Your Own":
            uploaded_image = st.file_uploader(
                "Upload background",
                type=["jpg", "jpeg", "png", "webp"],
            )

        elif bg_source == "📦 Pre-made Templates":
            available_templates = [
                p.name
                for p in TEMPLATE_DIR.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]

            if available_templates:
                selected_template = st.selectbox(
                    "Choose Template",
                    available_templates,
                )
            else:
                st.info(
                    "Add festive.png, sale.png or clean.png to "
                    "assets/templates/."
                )

        else:
            unsplash_query = st.text_input(
                "Search Unsplash",
                value="indian festival lights",
            )

            if st.button("🔄 Load Backgrounds"):
                with st.spinner("Fetching backgrounds..."):
                    results = fetch_unsplash_images(unsplash_query, 6)
                    st.session_state["unsplash_images"] = results
                    st.session_state["selected_unsplash"] = 0

            if st.session_state.get("unsplash_images"):
                selected_unsplash = st.selectbox(
                    "Background",
                    range(len(st.session_state["unsplash_images"])),
                    format_func=lambda x: f"Background {x + 1}",
                )
                st.session_state["selected_unsplash"] = selected_unsplash

    left, right = st.columns([1, 1.15])

    with left:
        st.markdown("### ✍️ Content")

        business_name = st.text_input(
            "Business Name",
            value="My Bakery",
            max_chars=100,
        )

        headline = st.text_input(
            "Main Headline",
            value="50% OFF",
            max_chars=120,
        )

        subtext = st.text_input(
            "Subtext",
            value="This Weekend Only!",
            max_chars=300,
        )

        st.markdown("### 🖼️ Branding")

        logo_upload = st.file_uploader(
            "Upload Logo",
            type=["png", "jpg", "jpeg", "webp"],
            help="PNG with transparent background works best.",
        )

        st.markdown("### 🔗 QR Code")

        qr_data = st.text_input(
            "QR destination",
            placeholder="https://example.com or WhatsApp link",
            help="Leave empty to disable QR.",
        )

        st.markdown("### 📱 Contact Details")

        contact_info = st.text_input(
            "Contact / Instagram / Address",
            value="",
            placeholder="Optional",
        )

        subtext_render = subtext

        generate = st.button(
            "✨ Generate Smart Poster",
            type="primary",
            use_container_width=True,
        )

    with right:
        if generate:
            if not business_name.strip() or not headline.strip():
                st.error("Business Name and Main Headline are required.")
            else:
                base_img = None

                try:
                    if bg_source == "📤 Upload Your Own":
                        if uploaded_image is None:
                            st.error("Please upload a background image.")
                        else:
                            base_img = Image.open(uploaded_image)

                    elif bg_source == "🌐 Unsplash":
                        images = st.session_state.get("unsplash_images", [])
                        if not images:
                            st.error("Load Unsplash backgrounds first.")
                        else:
                            idx = st.session_state.get(
                                "selected_unsplash",
                                0,
                            )
                            base_img = Image.open(
                                io.BytesIO(images[idx])
                            )

                    else:
                        if not selected_template:
                            st.error(
                                "Add at least one image to "
                                "assets/templates/."
                            )
                        else:
                            base_img = Image.open(
                                TEMPLATE_DIR / selected_template
                            )

                    if base_img is not None:
                        font_name = STYLE_CONFIGS[design_style]["font"]
                        font_url = FONT_CATALOG[font_name]["url"]
                        font_path = download_font(
                            font_name,
                            font_url,
                        )

                        logo = (
                            Image.open(logo_upload)
                            if logo_upload is not None
                            else None
                        )

                        with st.spinner("🎨 Rendering V2 poster..."):
                            poster = create_smart_poster(
                                base_image=base_img,
                                headline=headline,
                                subtext=subtext_render,
                                business_name=business_name,
                                style_name=design_style,
                                size=POSTER_SIZES[size_name],
                                font_path=font_path,
                                logo=logo,
                                logo_position=logo_position,
                                cta=cta,
                                cta_position=cta_position,
                                qr_data=qr_data,
                                qr_position=qr_position,
                                gradient_strength=gradient_strength,
                                darken_background=True,
                                contact_line=contact_info,
                            )

                        st.image(
                            poster,
                            caption="A.R.I.A. Generated Poster",
                            use_container_width=True,
                        )

                        jpg_buffer = io.BytesIO()
                        poster.save(
                            jpg_buffer,
                            format="JPEG",
                            quality=96,
                            optimize=True,
                        )

                        png_buffer = io.BytesIO()
                        poster.save(
                            png_buffer,
                            format="PNG",
                            optimize=True,
                        )

                        file_base = safe_filename(business_name)

                        d1, d2 = st.columns(2)

                        with d1:
                            st.download_button(
                                "📥 Download JPG",
                                jpg_buffer.getvalue(),
                                file_name=f"{file_base}_poster.jpg",
                                mime="image/jpeg",
                                use_container_width=True,
                            )

                        with d2:
                            st.download_button(
                                "📥 Download PNG",
                                png_buffer.getvalue(),
                                file_name=f"{file_base}_poster.png",
                                mime="image/png",
                                use_container_width=True,
                            )

                        st.markdown("### ✍️ AI Caption")

                        caption = call_openai(
                            f"""
                            Write an engaging Instagram caption for:
                            Business: {business_name}
                            Headline: {headline}
                            Details: {subtext_render}
                            Contact: {contact_info or "not provided"}

                            Use Indian small-business marketing language.
                            Keep it under 120 words.
                            Include a clear CTA and 5 relevant hashtags.
                            """
                        )

                        st.text_area(
                            "Caption",
                            value=caption,
                            height=180,
                        )

                except Exception as exc:
                    st.exception(exc)

# ============================================================
# TAB 2 — REVIEW RESPONDER
# ============================================================

with tab_review:
    st.subheader("⭐ Review Responder")

    c1, c2 = st.columns(2)

    with c1:
        reviewer_name = st.text_input(
            "Reviewer Name",
            value="Customer",
            max_chars=100,
            key="review_reviewer",
        )

        rating = st.selectbox(
            "Star Rating",
            [1, 2, 3, 4, 5],
            index=4,
            key="review_rating",
        )

    with c2:
        biz_name_review = st.text_input(
            "Business Name",
            value="My Bakery",
            max_chars=100,
            key="review_biz_name",
        )

        owner_name = st.text_input(
            "Your Name",
            value="Manager",
            max_chars=50,
            key="review_owner",
        )

    review_text = st.text_area(
        "Customer Review",
        height=150,
        max_chars=1000,
        placeholder="e.g. The food was good but service was slow...",
        key="review_text",
    )

    if st.button(
        "✨ Generate Reply",
        type="primary",
        key="review_generate_btn",
    ):
        if review_text.strip():
            with st.spinner("Writing response..."):
                response = call_openai(
                    f"""
                    Act as the owner of {biz_name_review}.
                    Customer: {reviewer_name}
                    Rating: {rating}/5
                    Review: "{review_text}"

                    Write a polite professional public response.
                    For 4–5 stars, thank them warmly.
                    For 1–3 stars, acknowledge the issue and apologize
                    appropriately without making unsupported promises.
                    Keep it under 100 words.
                    Sign as {owner_name}.
                    """
                )

            st.success("Reply generated!")
            st.text_area(
                "Copy this reply",
                value=response,
                height=200,
                key="review_response",
            )

# ============================================================
# TAB 3 — INQUIRY RESPONDER
# ============================================================

with tab_inquiry:
    st.subheader("💬 Inquiry Responder")

    c1, c2 = st.columns(2)

    with c1:
        customer_name = st.text_input(
            "Customer Name",
            value="Friend",
            max_chars=100,
            key="inq_customer",
        )

        biz_name_inq = st.text_input(
            "Business Name",
            value="My Bakery",
            max_chars=100,
            key="inq_biz_name",
        )

    with c2:
        product_service = st.text_input(
            "What do you sell?",
            value="Cakes and Pastries",
            max_chars=150,
            key="inq_product",
        )

        contact_info_inq = st.text_input(
            "Contact Info",
            value="Call 9876543210",
            max_chars=200,
            key="inq_contact",
        )

    inquiry_text = st.text_area(
        "Customer's Question",
        height=150,
        max_chars=1000,
        placeholder="e.g. Do you have eggless cakes?",
        key="inq_text",
    )

    if st.button(
        "✨ Generate Reply",
        type="primary",
        key="inq_generate_btn",
    ):
        if inquiry_text.strip():
            with st.spinner("Drafting reply..."):
                response = call_openai(
                    f"""
                    Act as a sales representative for {biz_name_inq},
                    selling {product_service}.

                    Customer: {customer_name}
                    Question: "{inquiry_text}"

                    Write a friendly, helpful sales reply with a clear CTA.
                    Do not invent product availability, prices or features.
                    End with: {contact_info_inq}
                    Keep it under 150 words.
                    """
                )

            st.success("Reply drafted!")
            st.text_area(
                "Copy this reply",
                value=response,
                height=200,
                key="inq_response",
            )