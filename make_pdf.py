"""Wedding band inscriptions page, laid out on a measured vertical rhythm.

Every element's ink extent (how far its visible marks rise above and fall below its
baseline) is measured, then elements are stacked so the visible gaps are:
  GAP_IN   between elements inside a group (inscription, name, language line, description)
  gap_out  between groups (header, each ring section, divider, footer), calculated so
           the content fills the page exactly between MARGIN top and bottom."""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Paragraph
from fontTools.ttLib import TTFont as FTFont
from fontTools.pens.boundsPen import BoundsPen
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)
from PIL import Image

OUT = str(ROOT / "Wedding-Band-Inscriptions.pdf")
FONTS = {"CG-LightItalic": "CG-300-italic", "CG": "CG-400-normal", "CG-Italic": "CG-400-italic",
         "CG-Medium": "CG-500-normal", "CG-Bold": "CG-700-normal", "Engr": "Cinzel-400"}
for n, f in FONTS.items():
    pdfmetrics.registerFont(TTFont(n, str(FONT_DIR / f"{f}.ttf")))

INK = HexColor("#00563b")
MUTED = HexColor("#0a6e4a")
BODY = HexColor("#00603f")
RULE = HexColor("#409785")
BLUE = HexColor("#81D8D0")
W, H = letter

GAP_IN = 11      # pt, visible gap between every element inside a group
GAP_NAME = GAP_IN  # same gap above the names as everywhere else in the group

# ---------- glyph ink metrics ----------
_ft = {n: FTFont(str(FONT_DIR / f"{f}.ttf")) for n, f in FONTS.items()}


def ink(text, font, size):
    """(top, bottom) of the string's ink relative to its baseline, in points (bottom <= 0)."""
    f = _ft[font]
    gs, cmap, upm = f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm
    lo, hi = 0, 0
    for ch in text:
        g = cmap.get(ord(ch))
        if not g:
            continue
        p = BoundsPen(gs)
        gs[g].draw(p)
        if p.bounds:
            lo, hi = min(lo, p.bounds[1]), max(hi, p.bounds[3])
    return hi / upm * size, lo / upm * size


# ---------- flags (monochromatic) ----------
F_DARK = INK
F_LIGHT = Color(INK.red, INK.green, INK.blue, alpha=0.18)
F_MID = Color(INK.red, INK.green, INK.blue, alpha=0.55)


def flag_ie(c, x, y, h):
    w = 2 * h
    for i, col in enumerate((F_DARK, F_LIGHT, F_MID)):
        c.setFillColor(col)
        c.rect(x + i * w / 3, y, w / 3 + 0.05, h, stroke=0, fill=1)


def flag_no(c, x, y, h):
    u = h / 16
    c.setFillColor(F_DARK)
    for rx, rw in ((0, 6), (10, 12)):
        for ry in (0, 10):
            c.rect(x + rx * u, y + ry * u, rw * u, 6 * u, stroke=0, fill=1)
    c.setFillColor(F_LIGHT)
    for rx in (6, 9):
        c.rect(x + rx * u, y, u, 6 * u, stroke=0, fill=1)
        c.rect(x + rx * u, y + 10 * u, u, 6 * u, stroke=0, fill=1)
    for ry in (6, 9):
        c.rect(x, y + ry * u, 6 * u, u, stroke=0, fill=1)
        c.rect(x + 10 * u, y + ry * u, 12 * u, u, stroke=0, fill=1)
    for cx_, cy_ in ((6, 6), (9, 6), (6, 9), (9, 9)):
        c.rect(x + cx_ * u, y + cy_ * u, u, u, stroke=0, fill=1)
    c.setFillColor(F_MID)
    c.rect(x + 7 * u, y, 2 * u, h, stroke=0, fill=1)
    c.rect(x, y + 7 * u, 7 * u, 2 * u, stroke=0, fill=1)
    c.rect(x + 9 * u, y + 7 * u, 13 * u, 2 * u, stroke=0, fill=1)


FLAGS = {"IE": (flag_ie, 2.0), "NO": (flag_no, 22 / 16)}

# ---------- text ----------
HIS = ("<font name='CG-Bold'>GO DEO</font> is Irish for forever. Long days and quiet nights, "
       "David carries a little of Shauneen with him, close\u00a0against\u00a0his\u00a0skin.")
HERS = ("<font name='CG-Bold'>FOR ALLTID</font> is Norwegian for forever. On ordinary days and hard "
        "ones, Shauneen will have a little of David with her, right\u00a0against\u00a0her\u00a0skin.")
BODY_STYLE = ParagraphStyle("body", fontName="CG-Italic", fontSize=15, leading=20.5,
                            textColor=BODY, alignment=TA_CENTER)
PARA_W = 400
INTRO = ("One love, two languages.<br/>"
         "Hers from Ireland. His from Norway.<br/>"
         "Both mean forever.")
INTRO_STYLE = ParagraphStyle("intro", fontName="CG-Italic", fontSize=30, leading=31,
                             textColor=INK, alignment=TA_CENTER)
INTRO_W = 504

# ---------- element builders ----------
# Each element: (ink_height, draw(c, ink_top_y)).  Elements draw themselves given the y of
# their visible top, so stacking is: next_top = this_top - ink_height - gap.


def el_tracked(text, font, size, color, spacing):
    t, b = ink(text, font, size)
    w = sum(pdfmetrics.stringWidth(ch, font, size) for ch in text) + spacing * (len(text) - 1)

    def draw(c, top):
        c.setFont(font, size)
        c.setFillColor(color)
        x, y = (W - w) / 2, top - t
        for ch in text:
            c.drawString(x, y, ch)
            x += pdfmetrics.stringWidth(ch, font, size) + spacing
    return t - b, draw


def el_center(text, font, size, color, flag=None, flag_h=8.5, flag_gap=8):
    t, b = ink(text, font, size)
    tw = pdfmetrics.stringWidth(text, font, size)
    if flag:
        fn, ratio = FLAGS[flag]
        fw = ratio * flag_h
        xh = ink("o", font, size)[0]                 # x-height: center the flag on lowercase
        flag_mid = xh / 2 + 0.6
        t = max(t, flag_mid + flag_h / 2)
        b = min(b, flag_mid - flag_h / 2)
    else:
        fw = flag_gap = 0

    def draw(c, top):
        base = top - t
        x0 = (W - (fw + flag_gap + tw)) / 2
        if flag:
            fn(c, x0, base + flag_mid - flag_h / 2, flag_h)
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawString(x0 + fw + flag_gap, base, text)
    return t - b, draw


_para_cache = {}


def para_ink(text, style=None, width=None):
    """Measure a paragraph's ink offset from its box top and its ink height by rendering it."""
    style, width = style or BODY_STYLE, width or PARA_W
    key = (text, style.name, width)
    if key in _para_cache:
        return _para_cache[key]
    PARA_W_ = width
    p = Paragraph(text, style)
    _, h = p.wrap(PARA_W_, 1000)
    tmp = str(BUILD / "_para.pdf")
    c = canvas.Canvas(tmp, pagesize=(PARA_W_ + 40, h + 40))
    p.drawOn(c, 20, 20)
    c.save()
    dpi = 600
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", tmp,
                    str(BUILD / "_para")], check=True)
    im = Image.open(str(BUILD / "_para.png")).convert("L")
    bbox = im.point(lambda v: 255 if v < 200 else 0).getbbox()
    px = 72 / dpi
    box_top_px = 20 / px                           # box top is 20pt below the image top
    ink_top_off = bbox[1] * px - 20                # pt below the box top
    ink_h = (bbox[3] - bbox[1]) * px
    _para_cache[key] = (h, ink_top_off, ink_h)
    return _para_cache[key]


def el_para(text, style=None, width=None):
    style, width = style or BODY_STYLE, width or PARA_W
    h, off, ink_h = para_ink(text, style, width)

    def draw(c, top):
        p = Paragraph(text, style)
        p.wrap(width, 1000)
        box_top = top + off
        p.drawOn(c, (W - width) / 2, box_top - h)
    return ink_h, draw


def el_rule(half=36, width=0.75):
    def draw(c, top):
        c.setStrokeColor(RULE)
        c.setLineWidth(width)
        c.line(W / 2 - half, top - width / 2, W / 2 + half, top - width / 2)
    return width, draw


def el_logo(width=118 * 0.62 * 1.2):
    h = width * 434 / 3607

    def draw(c, top):
        c.drawImage(str(ROOT / "logo_green.png"), (W - width) / 2, top - h,
                    width=width, height=h, mask="auto")
    return h, draw


def el_header():
    """Staggered SHAUNEEN & DAVID around a page-centered &."""
    NAME, TRACK, CAP, LINE_GAP, NUDGE, GAP = 30, 0.28, 0.625, 16, 10, 14
    AMP = (64, -12, 709.56, 646)
    cap = CAP * NAME
    span = 2 * cap + LINE_GAP                      # & ink height
    amp_size = span / ((AMP[3] - AMP[1]) / 1000)
    aw = (AMP[2] - AMP[0]) / 1000 * amp_size

    def wwidth(word):
        return sum(pdfmetrics.stringWidth(ch, "CG-Medium", NAME) for ch in word) + TRACK * NAME * (len(word) - 1)

    def tracked(c, word, x, y):
        c.setFont("CG-Medium", NAME)
        c.setFillColor(INK)
        for ch in word:
            c.drawString(x, y, ch)
            x += pdfmetrics.stringWidth(ch, "CG-Medium", NAME) + TRACK * NAME

    def draw(c, top):
        b1, b2 = top - cap, top - span
        c.setFont("CG-Medium", amp_size)
        c.setFillColor(INK)
        c.drawString(W / 2 - (AMP[0] + AMP[2]) / 2000 * amp_size, b2 - AMP[1] / 1000 * amp_size, "&")
        tracked(c, "SHAUNEEN", W / 2 - aw / 2 - GAP - wwidth("SHAUNEEN"), b1 - NUDGE)
        tracked(c, "DAVID", W / 2 + aw / 2 + GAP, b2 + NUDGE)
    return span, draw


# ---------- page ----------
MINT = BLUE
WHITE = HexColor("#ffffff")


def el_band(phrase, style):
    """Full-bleed band with the inscription reversed out of it.
    style A: solid dark-green band, mint letters.
    style B: solid band with thin mint rules inset at top and bottom, like a ring's edges.
    style C: band shaded top-to-bottom like the curved inside of a ring, white letters."""
    size = 50
    t, b = ink(phrase, "Engr", size)
    cap = t - b
    pad = 22 if style != "B" else 26
    h = cap + 2 * pad
    tw = pdfmetrics.stringWidth(phrase, "Engr", size)

    def draw(c, top):
        y0 = top - h
        if style == "D":
            # Solid band that fades into the page at both sides; full strength under the letters
            c.saveState()
            p = c.beginPath()
            p.rect(0, y0, W, h)
            c.clipPath(p, stroke=0, fill=0)
            lead = 0.18                              # same fade on both bands: full strength 18%-82%
            c.linearGradient(0, 0, W, 0, (MINT, INK, INK, MINT), (0, lead, 1 - lead, 1), extend=True)
            c.restoreState()
        elif style == "C":
            c.saveState()
            p = c.beginPath()
            p.rect(0, y0, W, h)
            c.clipPath(p, stroke=0, fill=0)
            dark = INK
            lift = Color(*[i + (m - i) * 0.28 for i, m in zip((INK.red, INK.green, INK.blue),
                                                              (MINT.red, MINT.green, MINT.blue))])
            c.linearGradient(0, y0 + h, 0, y0, (dark, lift, dark), (0, 0.5, 1), extend=True)
            c.restoreState()
        else:
            c.setFillColor(INK)
            c.rect(0, y0, W, h, stroke=0, fill=1)
        if style == "B":
            c.setStrokeColor(MINT)
            c.setLineWidth(0.6)
            for yy in (y0 + 8, top - 8):
                c.line(0, yy, W, yy)
        c.setFont("Engr", size)
        c.setFillColor(WHITE if style == "C" else MINT)   # A, B and D use mint letters
        c.drawString((W - tw) / 2, y0 + pad - b, phrase)
    return h, draw


def section(phrase, name, meta, flag, text, band=None):
    insc = el_band(phrase, band) if band else el_center(phrase, "Engr", 50, INK)
    return [(insc[0], insc[1], GAP_NAME),          # third value: gap after this element
            el_tracked(name, "CG-Medium", 12, MUTED, 3.7),
            el_center(meta, "CG", 12.5, INK, flag=flag),
            el_para(text)]


def gap_after(el):
    return el[2] if len(el) > 2 else GAP_IN


faded = Color(BODY.red, BODY.green, BODY.blue, alpha=0.76)
FOOTER_LINE_GAP = 4      # tight gap between the two small footer lines, and under the label
MARGIN = 54              # pt (19 mm) top and bottom, matching the side margins


def render(c, band=None, label=None):
    groups = [
        [el_header()],
        [el_para(INTRO, INTRO_STYLE, INTRO_W)],
        [el_rule()],
        section("FOR ALLTID", "SHAUNEEN", "Norwegian  \u00b7  Norsk", "NO", HERS, band),
        [el_rule()],
        section("GO DEO", "DAVID", "Irish  \u00b7  Gaeilge", "IE", HIS, band),
        [el_logo(),
         el_tracked("ENGRAVED BY HAND", "CG-Medium", 7.5, MUTED, 2.4)],
    ]
    footer_lines = [el_center("Each letter cut by hand by Tiffany & Co. engravers in New York City,",
                              "CG", 9.24, faded),
                    el_center("a craft passed from one generation to the next.", "CG", 9.24, faded)]
    total = 0
    for gi, g in enumerate(groups):
        total += sum(el[0] for el in g) + sum(gap_after(el) for el in g[:-1])
    total += sum(FOOTER_LINE_GAP + h for h, _ in footer_lines)
    # Fill the page: spread the leftover height evenly across the between-group gaps
    gap_out = (H - 2 * MARGIN - total) / (len(groups) - 1)
    y = H - MARGIN
    c.setFillColor(BLUE)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    for gi, g in enumerate(groups):
        for i, el in enumerate(g):
            h, draw = el[0], el[1]
            draw(c, y)
            y -= h + (gap_after(el) if i < len(g) - 1 else 0)
        if gi < len(groups) - 1:
            y -= gap_out
    for h, draw in footer_lines:
        y -= FOOTER_LINE_GAP
        draw(c, y)
        y -= h
    if label:
        c.setFont("CG", 8)
        c.setFillColor(Color(INK.red, INK.green, INK.blue, alpha=0.45))
        c.drawString(18, 14, label)
    c.showPage()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bands":
        c = canvas.Canvas(str(ROOT / "Band-Options.pdf"), pagesize=letter)
        c.setTitle("Shauneen & David: Band Options")
        render(c, "A", "Band A: solid band, mint letters")
        render(c, "B", "Band B: band with thin ring-edge lines")
        render(c, "C", "Band C: shaded like the inside of a ring, white letters")
        c.save()
        print(str(ROOT / "Band-Options.pdf"))
    else:
        c = canvas.Canvas(OUT, pagesize=letter)
        c.setTitle("Shauneen & David: Wedding Band Inscriptions")
        c.setAuthor("David Ehlers")
        render(c)               # no band: inscriptions set directly on the page
        c.save()
        print(OUT)
