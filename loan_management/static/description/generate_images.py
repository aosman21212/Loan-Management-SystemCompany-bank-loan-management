#!/usr/bin/env python3
"""Generate Loan Management System App Store images using PIL/Pillow."""

from PIL import Image, ImageDraw, ImageFont
import os

OUT = "/home/odoo/src/user/loan_management/static/description"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# ── colour palette ─────────────────────────────────────────────────────────────
ODOO_PURPLE   = "#714B67"
NAVY          = "#1a3c5e"
BLUE_MID      = "#2d6a9f"
BLUE_BADGE    = "#0d6efd"
GREEN_BADGE   = "#198754"
GRAY_BADGE    = "#6c757d"
RED_BADGE     = "#dc3545"
WHITE         = "#ffffff"
BG_PAGE       = "#f0f0f0"
TBL_HEADER_BG = "#f8f9fa"
TBL_HEADER_FG = "#6c757d"
TBL_BORDER    = "#dee2e6"
TBL_ALT       = "#fafafa"
TEXT_DARK     = "#212529"
TEXT_MUTED    = "#6c757d"

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size)

def badge(draw, x, y, text, color, text_color=WHITE, pad_x=10, pad_y=4, radius=4):
    tf = font(11, bold=True)
    bb = draw.textbbox((0, 0), text, font=tf)
    w, h = bb[2]-bb[0], bb[3]-bb[1]
    rx1, ry1 = x, y
    rx2, ry2 = x + w + pad_x*2, y + h + pad_y*2
    draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=radius, fill=hex2rgb(color))
    draw.text((rx1 + pad_x, ry1 + pad_y), text, font=tf, fill=hex2rgb(text_color))
    return rx2  # right edge

def odoo_topbar(draw, W, title="Loan Management"):
    """Draw the purple Odoo top navigation bar."""
    draw.rectangle([0, 0, W, 50], fill=hex2rgb(ODOO_PURPLE))
    # hamburger icon dots
    for i in range(3):
        draw.rectangle([16, 17 + i*8, 28, 19 + i*8], fill=hex2rgb(WHITE))
    # app title
    draw.text((44, 13), title, font=font(16, bold=True), fill=hex2rgb(WHITE))
    # user avatar circle on right
    draw.ellipse([W-40, 10, W-12, 38], fill=hex2rgb("#9b7ba6"))
    draw.text((W-32, 16), "Ad", font=font(12, bold=True), fill=hex2rgb(WHITE))

def odoo_breadcrumb_bar(draw, W, breadcrumbs, new_btn=True):
    """Draw white sub-header with breadcrumbs and New button."""
    draw.rectangle([0, 50, W, 100], fill=hex2rgb(WHITE))
    draw.line([(0, 100), (W, 100)], fill=hex2rgb(TBL_BORDER), width=1)
    x = 16
    for i, crumb in enumerate(breadcrumbs):
        bold = (i == len(breadcrumbs)-1)
        col = TEXT_DARK if bold else TEXT_MUTED
        draw.text((x, 65), crumb, font=font(14, bold=bold), fill=hex2rgb(col))
        bb = draw.textbbox((x, 65), crumb, font=font(14, bold=bold))
        x = bb[2] + 6
        if i < len(breadcrumbs)-1:
            draw.text((x, 65), "›", font=font(14), fill=hex2rgb(TEXT_MUTED))
            x += 16
    if new_btn:
        draw.rounded_rectangle([W-100, 60, W-16, 90], radius=4, fill=hex2rgb(ODOO_PURPLE))
        draw.text((W-82, 68), "New", font=font(13, bold=True), fill=hex2rgb(WHITE))

def draw_table_header(draw, cols, y, row_h=36):
    """cols = list of (x, w, label). Returns y after header."""
    tf = font(12, bold=True)
    for (x, w, label) in cols:
        draw.rectangle([x, y, x+w, y+row_h], fill=hex2rgb(TBL_HEADER_BG))
        draw.text((x+8, y + (row_h-14)//2), label, font=tf, fill=hex2rgb(TBL_HEADER_FG))
    return y + row_h

def draw_table_row(draw, cols_data, y, row_h=40, alt=False):
    """cols_data = list of (x, w, text_or_callable). Returns y after row."""
    bg = hex2rgb(TBL_ALT) if alt else hex2rgb(WHITE)
    tf = font(13)
    x0 = cols_data[0][0]
    x1 = cols_data[-1][0] + cols_data[-1][1]
    draw.rectangle([x0, y, x1, y+row_h], fill=bg)
    for (x, w, val) in cols_data:
        if callable(val):
            val(draw, x+8, y + (row_h-20)//2)
        else:
            draw.text((x+8, y + (row_h-14)//2), str(val), font=tf, fill=hex2rgb(TEXT_DARK))
    return y + row_h

def draw_row_borders(draw, cols, y_start, y_end, step=40, header_h=36):
    """Draw horizontal and vertical borders for a table."""
    x0 = cols[0][0]; x1 = cols[-1][0] + cols[-1][1]
    # horizontal lines
    for y in range(y_start, y_end+1, step):
        draw.line([(x0, y), (x1, y)], fill=hex2rgb(TBL_BORDER), width=1)
    draw.line([(x0, y_end), (x1, y_end)], fill=hex2rgb(TBL_BORDER), width=1)
    # vertical lines
    for (x, w, _) in cols:
        draw.line([(x, y_start), (x, y_end)], fill=hex2rgb(TBL_BORDER), width=1)
    draw.line([(x1, y_start), (x1, y_end)], fill=hex2rgb(TBL_BORDER), width=1)

# ══════════════════════════════════════════════════════════════════════════════
# 1. icon.png  128×128
# ══════════════════════════════════════════════════════════════════════════════
def make_icon():
    # Draw at 4× scale then down-sample for anti-aliasing, save uncompressed
    S = 4
    W = H = 128 * S
    img = Image.new("RGB", (W, H), hex2rgb(NAVY))
    d = ImageDraw.Draw(img)

    def s(v): return v * S  # scale helper

    # Subtle gradient overlay
    n1 = hex2rgb(NAVY); n2 = hex2rgb(BLUE_MID)
    for y in range(H):
        t = y / H * 0.5
        r = int(n1[0] + (n2[0]-n1[0]) * t)
        g = int(n1[1] + (n2[1]-n1[1]) * t)
        b = int(n1[2] + (n2[2]-n1[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Bank building — columns (4 pillars)
    col_w, col_h, col_gap = s(8), s(36), s(7)
    cols_start_x = s(22)
    base_y = s(88)
    for i in range(4):
        cx = cols_start_x + i * (col_w + col_gap)
        d.rectangle([cx, base_y - col_h, cx + col_w, base_y], fill=hex2rgb(WHITE))

    # Roof / triangle
    d.polygon([(s(14), s(56)), (s(64), s(32)), (s(114), s(56))], fill=hex2rgb(WHITE))

    # Entablature (bar between roof and columns)
    d.rectangle([s(14), s(56), s(114), s(64)], fill=hex2rgb(WHITE))

    # Base step
    d.rectangle([s(12), s(88), s(116), s(94)], fill=hex2rgb(WHITE))
    d.rectangle([s(8),  s(94), s(120), s(98)], fill=hex2rgb(WHITE))

    # Small dollar sign inside triangle
    d.text((s(56), s(34)), "$", font=font(s(10), bold=True), fill=hex2rgb(NAVY))

    # Bottom strip with purple
    d.rectangle([0, s(100), W, H], fill=hex2rgb(ODOO_PURPLE))

    tf = font(s(17), bold=True)
    bb = d.textbbox((0, 0), "LOAN", font=tf)
    tw = bb[2] - bb[0]
    d.text(((W-tw)//2, s(104)), "LOAN", font=tf, fill=hex2rgb(WHITE))

    # Downsample to 128×128
    img = img.resize((128, 128), Image.LANCZOS)
    # Save with compress_level=0 for maximum file size / minimum compression
    img.save(os.path.join(OUT, "icon.png"), compress_level=0)
    print("  icon.png created")

# ══════════════════════════════════════════════════════════════════════════════
# 2. banner.png  1200×300
# ══════════════════════════════════════════════════════════════════════════════
def make_banner():
    W, H = 1200, 300
    img = Image.new("RGB", (W, H), hex2rgb(NAVY))
    d = ImageDraw.Draw(img)

    # Gradient: left NAVY → right BLUE_MID
    n1 = hex2rgb(NAVY); n2 = hex2rgb(BLUE_MID)
    for x in range(W):
        t = x / W
        r = int(n1[0] + (n2[0]-n1[0]) * t)
        g = int(n1[1] + (n2[1]-n1[1]) * t)
        b = int(n1[2] + (n2[2]-n1[2]) * t)
        d.line([(x, 0), (x, H)], fill=(r, g, b))

    # Left side text
    d.text((60, 70), "Loan Management System", font=font(46, bold=True), fill=hex2rgb(WHITE))
    d.text((62, 136), "Bank Loan Lifecycle  ·  Amortisation Schedules  ·  Liability Accounting",
           font=font(20), fill=(180, 210, 240))

    # Decorative: stacked schedule bars on right
    bar_x = 780
    bar_labels = ["Principal", "Interest", "Balance", "EMI", "Schedule"]
    bar_lengths = [220, 140, 190, 110, 170]
    bar_colors  = [(255,255,255), (180,210,240), (255,255,255), (180,210,240), (255,255,255)]
    for i, (lbl, blen, bcol) in enumerate(zip(bar_labels, bar_lengths, bar_colors)):
        by = 60 + i * 44
        d.rounded_rectangle([bar_x, by, bar_x + blen, by+28], radius=4, fill=bcol)
        d.text((bar_x + blen + 14, by+6), lbl, font=font(14), fill=(180,210,240))

    # Small tag line bottom left
    d.text((60, 240), "Odoo 19 Module  ·  Full Loan Lifecycle Management",
           font=font(15), fill=(150, 190, 230))

    img.save(os.path.join(OUT, "banner.png"))
    print("  banner.png created")

# ══════════════════════════════════════════════════════════════════════════════
# 3. screenshot_01_loans_list.png  1280×720
# ══════════════════════════════════════════════════════════════════════════════
def make_loans_list():
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), hex2rgb(BG_PAGE))
    d = ImageDraw.Draw(img)

    odoo_topbar(d, W)
    odoo_breadcrumb_bar(d, W, ["Loans", "Loan Management"])

    # Content card
    card_x, card_y, card_w = 16, 110, W-32
    d.rectangle([card_x, card_y, card_x+card_w, H-16], fill=hex2rgb(WHITE),
                outline=hex2rgb(TBL_BORDER), width=1)

    # Search bar area
    d.rounded_rectangle([card_x+16, card_y+12, card_x+400, card_y+44],
                         radius=4, outline=hex2rgb(TBL_BORDER), width=1, fill=hex2rgb(WHITE))
    d.text((card_x+28, card_y+20), "🔍  Search loans...", font=font(13), fill=hex2rgb(TEXT_MUTED))

    # Group-by / Filter buttons
    for i, lbl in enumerate(["Filters ▾", "Group By ▾", "Favorites ▾"]):
        bx = card_x + 420 + i * 110
        d.text((bx, card_y+20), lbl, font=font(13), fill=hex2rgb(TEXT_MUTED))

    # View toggle icons (list/kanban)
    d.text((W-80, card_y+20), "☰  ⊞", font=font(13), fill=hex2rgb(TEXT_MUTED))

    # Table
    PAD = card_x + 16
    tbl_y = card_y + 62

    cols = [
        (PAD,       20,   "☐"),
        (PAD+28,   160,   "Loan Reference"),
        (PAD+196,  170,   "Lender / Bank"),
        (PAD+374,  170,   "Type"),
        (PAD+552,  110,   "Amount"),
        (PAD+670,   70,   "Rate %"),
        (PAD+748,  110,   "EMI"),
        (PAD+866,  120,   "Total Payable"),
        (PAD+994,  100,   "Status"),
    ]
    header_end = draw_table_header(d, cols, tbl_y, row_h=36)

    loans = [
        ("LN/2025/0001", "Al Rajhi Bank",  "Term Loan",            "500,000.00", "6.5%", "9,769.55",  "586,173.00", "Running"),
        ("LN/2025/0002", "SABB",           "Working Capital Loan",  "200,000.00", "8.0%", "9,666.67",  "232,000.00", "Running"),
        ("LN/2025/0003", "Alinma Bank",    "Vehicle Finance",       "120,000.00", "4.5%", "2,479.05",  "118,994.40", "Running"),
    ]

    y = header_end
    for idx, (ref, lender, ltype, amt, rate, emi, total, status) in enumerate(loans):
        def make_badge_fn(s):
            def fn(draw, bx, by):
                badge(draw, bx, by, s, BLUE_BADGE)
            return fn

        row_data = [
            (cols[0][0], cols[0][1], "☐"),
            (cols[1][0], cols[1][1], ref),
            (cols[2][0], cols[2][1], lender),
            (cols[3][0], cols[3][1], ltype),
            (cols[4][0], cols[4][1], amt),
            (cols[5][0], cols[5][1], rate),
            (cols[6][0], cols[6][1], emi),
            (cols[7][0], cols[7][1], total),
            (cols[8][0], cols[8][1], make_badge_fn(status)),
        ]
        y = draw_table_row(d, row_data, y, row_h=40, alt=(idx % 2 == 1))

    draw_row_borders(d, cols, tbl_y, y, step=40, header_h=36)

    # Footer count
    d.text((PAD, y+10), "3 loans", font=font(12), fill=hex2rgb(TEXT_MUTED))

    img.save(os.path.join(OUT, "screenshot_01_loans_list.png"))
    print("  screenshot_01_loans_list.png created")

# ══════════════════════════════════════════════════════════════════════════════
# 4. screenshot_02_loan_form.png  1280×720
# ══════════════════════════════════════════════════════════════════════════════
def make_loan_form():
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), hex2rgb(BG_PAGE))
    d = ImageDraw.Draw(img)

    odoo_topbar(d, W)

    # Sub-header breadcrumb
    d.rectangle([0, 50, W, 100], fill=hex2rgb(WHITE))
    d.line([(0, 100), (W, 100)], fill=hex2rgb(TBL_BORDER), width=1)
    d.text((16, 65), "Loans", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((70, 65), "›", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((86, 65), "LN/2025/0001", font=font(14, bold=True), fill=hex2rgb(TEXT_DARK))

    # Action buttons
    btn_defs = [("Save manually", ODOO_PURPLE, True), ("Discard", WHITE, False)]
    bx = W - 220
    for lbl, bg, is_filled in btn_defs:
        bw = 100 if lbl == "Save manually" else 80
        if is_filled:
            d.rounded_rectangle([bx, 62, bx+bw, 90], radius=4, fill=hex2rgb(bg))
            d.text((bx+8, 70), lbl, font=font(12, bold=True), fill=hex2rgb(WHITE))
        else:
            d.rounded_rectangle([bx, 62, bx+bw, 90], radius=4,
                                  outline=hex2rgb(TBL_BORDER), width=1, fill=hex2rgb(WHITE))
            d.text((bx+8, 70), lbl, font=font(12), fill=hex2rgb(TEXT_DARK))
        bx += bw + 8

    # Status bar
    statuses = ["Draft", "Confirmed", "Approved", "Running", "Done"]
    active = "Running"
    sb_y = 108
    seg_w = (W - 32) // len(statuses)
    for i, s in enumerate(statuses):
        sx = 16 + i * seg_w
        is_active = s == active
        is_past = statuses.index(s) < statuses.index(active)
        bg = hex2rgb(ODOO_PURPLE) if is_active else (hex2rgb("#d0bfca") if is_past else hex2rgb("#e9ecef"))
        fg = hex2rgb(WHITE) if (is_active or is_past) else hex2rgb(TEXT_MUTED)
        d.rectangle([sx, sb_y, sx+seg_w-2, sb_y+32], fill=bg)
        bb = d.textbbox((0,0), s, font=font(13, bold=is_active))
        tw = bb[2]-bb[0]
        d.text((sx + (seg_w-tw)//2, sb_y+9), s, font=font(13, bold=is_active), fill=fg)

    # Action buttons row below status bar
    ab_y = sb_y + 40
    for lbl, col in [("Receive Loan", "#e9ecef"), ("Cancel", "#e9ecef")]:
        d.rounded_rectangle([16, ab_y, 16+120, ab_y+34], radius=4, fill=hex2rgb(col))
        d.text((28, ab_y+9), lbl, font=font(13), fill=hex2rgb(TEXT_MUTED))
        ab_x = 16 + 130

    # Smart buttons row
    sb2_y = ab_y + 48
    for i, (icon, lbl) in enumerate([("📋", "8 Installments"), ("📒", "9 Journal Entries")]):
        bx2 = 16 + i*160
        d.rounded_rectangle([bx2, sb2_y, bx2+148, sb2_y+48], radius=6,
                              fill=hex2rgb(WHITE), outline=hex2rgb(TBL_BORDER), width=1)
        d.text((bx2+14, sb2_y+6), icon, font=font(18), fill=hex2rgb(ODOO_PURPLE))
        d.text((bx2+42, sb2_y+13), lbl, font=font(13, bold=True), fill=hex2rgb(ODOO_PURPLE))

    # Form title
    title_y = sb2_y + 62
    d.text((16, title_y), "LN/2025/0001", font=font(22, bold=True), fill=hex2rgb(TEXT_DARK))

    # Two column groups
    grp_y = title_y + 40
    col_mid = W // 2

    def field_row(draw, lx, fy, label, value, label_w=160):
        draw.text((lx, fy), label, font=font(13), fill=hex2rgb(TEXT_MUTED))
        draw.text((lx + label_w, fy), value, font=font(13, bold=True), fill=hex2rgb(TEXT_DARK))

    # Left group header
    d.text((24, grp_y), "Loan Details", font=font(14, bold=True), fill=hex2rgb(TEXT_DARK))
    d.line([(24, grp_y+22), (col_mid-24, grp_y+22)], fill=hex2rgb(TBL_BORDER), width=1)

    left_fields = [
        ("Loan Type:", "Term Loan"),
        ("Lender Type:", "● Bank"),
        ("Lender / Bank:", "Al Rajhi Bank"),
        ("Responsible:", "Administrator"),
    ]
    for i, (lbl, val) in enumerate(left_fields):
        field_row(d, 24, grp_y + 34 + i*34, lbl, val)

    # Right group header
    d.text((col_mid + 24, grp_y), "Loan Terms", font=font(14, bold=True), fill=hex2rgb(TEXT_DARK))
    d.line([(col_mid+24, grp_y+22), (W-24, grp_y+22)], fill=hex2rgb(TBL_BORDER), width=1)

    right_fields = [
        ("Loan Amount:", "500,000.00"),
        ("Interest Rate:", "6.5%"),
        ("Interest Method:", "Reducing Balance"),
        ("Duration:", "60 months"),
        ("Application Date:", "09/18/2024"),
        ("First Payment Date:", "10/18/2024"),
    ]
    for i, (lbl, val) in enumerate(right_fields):
        field_row(d, col_mid + 24, grp_y + 34 + i*34, lbl, val)

    # Summary banner (4 boxes)
    sum_y = grp_y + 34 + 6*34 + 10
    sum_boxes = [
        ("Loan Amount",   "500,000"),
        ("Total Payable", "586,173"),
        ("Amount Paid",   "78,156"),
        ("Outstanding",   "508,017"),
    ]
    box_w = (W - 48) // 4
    for i, (title_s, val_s) in enumerate(sum_boxes):
        bx3 = 16 + i*(box_w + 4)
        d.rounded_rectangle([bx3, sum_y, bx3+box_w, sum_y+68], radius=6,
                              fill=hex2rgb(WHITE), outline=hex2rgb(TBL_BORDER), width=1)
        bb = d.textbbox((0,0), title_s, font=font(12))
        tw = bb[2]-bb[0]
        d.text((bx3 + (box_w-tw)//2, sum_y+10), title_s, font=font(12), fill=hex2rgb(TEXT_MUTED))
        bb2 = d.textbbox((0,0), val_s, font=font(18, bold=True))
        tw2 = bb2[2]-bb2[0]
        d.text((bx3 + (box_w-tw2)//2, sum_y+30), val_s,
               font=font(18, bold=True), fill=hex2rgb(ODOO_PURPLE))

    img.save(os.path.join(OUT, "screenshot_02_loan_form.png"))
    print("  screenshot_02_loan_form.png created")

# ══════════════════════════════════════════════════════════════════════════════
# 5. screenshot_03_repayment_schedule.png  1280×720
# ══════════════════════════════════════════════════════════════════════════════
def make_repayment_schedule():
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), hex2rgb(BG_PAGE))
    d = ImageDraw.Draw(img)

    odoo_topbar(d, W)

    # Breadcrumb
    d.rectangle([0, 50, W, 100], fill=hex2rgb(WHITE))
    d.line([(0, 100), (W, 100)], fill=hex2rgb(TBL_BORDER), width=1)
    d.text((16, 65), "Loans", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((70, 65), "›", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((86, 65), "LN/2025/0001", font=font(14, bold=True), fill=hex2rgb(TEXT_DARK))

    # Status bar (compact)
    statuses = ["Draft", "Confirmed", "Approved", "Running", "Done"]
    active = "Running"
    sb_y = 108
    seg_w = (W - 32) // len(statuses)
    for i, s in enumerate(statuses):
        sx = 16 + i * seg_w
        is_active = s == active
        is_past = statuses.index(s) < statuses.index(active)
        bg = hex2rgb(ODOO_PURPLE) if is_active else (hex2rgb("#d0bfca") if is_past else hex2rgb("#e9ecef"))
        fg = hex2rgb(WHITE) if (is_active or is_past) else hex2rgb(TEXT_MUTED)
        d.rectangle([sx, sb_y, sx+seg_w-2, sb_y+28], fill=bg)
        bb = d.textbbox((0,0), s, font=font(12, bold=is_active))
        tw = bb[2]-bb[0]
        d.text((sx + (seg_w-tw)//2, sb_y+8), s, font=font(12, bold=is_active), fill=fg)

    # Tabs
    tabs_y = sb_y + 36
    tabs = ["Loan Information", "Repayment Schedule", "Notes"]
    tx = 16
    for tab in tabs:
        is_active_tab = tab == "Repayment Schedule"
        col = ODOO_PURPLE if is_active_tab else TEXT_MUTED
        d.text((tx, tabs_y+6), tab, font=font(13, bold=is_active_tab), fill=hex2rgb(col))
        bb = d.textbbox((tx, tabs_y+6), tab, font=font(13, bold=is_active_tab))
        if is_active_tab:
            d.line([(tx, tabs_y+26), (bb[2], tabs_y+26)], fill=hex2rgb(ODOO_PURPLE), width=2)
        tx = bb[2] + 30
    d.line([(0, tabs_y+28), (W, tabs_y+28)], fill=hex2rgb(TBL_BORDER), width=1)

    # Table
    PAD = 16
    tbl_y = tabs_y + 36

    cols = [
        (PAD,       30,   "#"),
        (PAD+38,   110,   "Due Date"),
        (PAD+156,  110,   "Principal"),
        (PAD+274,  100,   "Interest"),
        (PAD+382,  100,   "EMI"),
        (PAD+490,  120,   "Balance"),
        (PAD+618,   90,   "Status"),
        (PAD+716,  110,   "Payment Date"),
        (PAD+834,   80,   "Action"),
    ]
    header_end = draw_table_header(d, cols, tbl_y, row_h=32)

    schedule = [
        (1,  "11/17/2024", "8,478.88",  "2,708.33", "9,769.55", "491,521.12", "Paid",    "11/17/2024"),
        (2,  "12/17/2024", "8,524.78",  "2,661.57", "9,769.55", "482,996.34", "Paid",    "12/17/2024"),
        (3,  "01/16/2025", "8,571.94",  "2,614.37", "9,769.55", "474,424.40", "Paid",    "01/16/2025"),
        (4,  "02/15/2025", "8,619.37",  "2,566.91", "9,769.55", "465,805.03", "Paid",    "02/15/2025"),
        (5,  "03/17/2025", "8,667.07",  "2,519.19", "9,769.55", "457,137.96", "Paid",    "03/17/2025"),
        (6,  "04/16/2025", "8,715.05",  "2,471.22", "9,769.55", "448,422.91", "Paid",    "04/16/2025"),
        (7,  "05/16/2025", "8,763.31",  "2,423.00", "9,769.55", "439,659.60", "Paid",    "05/16/2025"),
        (8,  "06/15/2025", "8,811.85",  "2,374.41", "9,769.55", "430,847.75", "Paid",    "06/15/2025"),
        (9,  "07/15/2025", "8,860.67",  "2,325.59", "9,769.55", "421,987.08", "Pending", "—"),
        (10, "08/14/2025", "8,909.79",  "2,276.48", "9,769.55", "413,077.29", "Pending", "—"),
    ]

    y = header_end
    for idx, (num, due, principal, interest, emi, balance, status, pay_date) in enumerate(schedule):
        status_color = GREEN_BADGE if status == "Paid" else GRAY_BADGE
        is_paid = status == "Paid"

        def make_status_fn(s, c):
            def fn(draw, bx, by):
                badge(draw, bx, by, s, c)
            return fn

        def make_pay_btn(is_p):
            def fn(draw, bx, by):
                if not is_p:
                    draw.rounded_rectangle([bx, by-2, bx+52, by+20], radius=3,
                                            fill=hex2rgb(ODOO_PURPLE))
                    draw.text((bx+8, by+2), "Pay", font=font(12, bold=True), fill=hex2rgb(WHITE))
            return fn

        # Green highlight for paid rows
        row_bg = "#f0fff4" if is_paid else (TBL_ALT if idx % 2 == 1 else WHITE)

        row_data = [
            (cols[0][0], cols[0][1], str(num)),
            (cols[1][0], cols[1][1], due),
            (cols[2][0], cols[2][1], principal),
            (cols[3][0], cols[3][1], interest),
            (cols[4][0], cols[4][1], emi),
            (cols[5][0], cols[5][1], balance),
            (cols[6][0], cols[6][1], make_status_fn(status, status_color)),
            (cols[7][0], cols[7][1], pay_date),
            (cols[8][0], cols[8][1], make_pay_btn(is_paid)),
        ]

        # Manual row with custom bg
        bg = hex2rgb(row_bg)
        x0 = cols[0][0]; x1 = cols[-1][0] + cols[-1][1]
        d.rectangle([x0, y, x1, y+36], fill=bg)
        for (cx, cw, val) in row_data:
            if callable(val):
                val(d, cx+8, y + (36-20)//2)
            else:
                d.text((cx+8, y + (36-14)//2), str(val), font=font(12), fill=hex2rgb(TEXT_DARK))
        y += 36

    draw_row_borders(d, cols, tbl_y, y, step=36, header_h=32)

    img.save(os.path.join(OUT, "screenshot_03_repayment_schedule.png"))
    print("  screenshot_03_repayment_schedule.png created")

# ══════════════════════════════════════════════════════════════════════════════
# 6. screenshot_04_journal_entries.png  1280×720
# ══════════════════════════════════════════════════════════════════════════════
def make_journal_entries():
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), hex2rgb(BG_PAGE))
    d = ImageDraw.Draw(img)

    odoo_topbar(d, W, title="Accounting")

    # Breadcrumb
    d.rectangle([0, 50, W, 100], fill=hex2rgb(WHITE))
    d.line([(0, 100), (W, 100)], fill=hex2rgb(TBL_BORDER), width=1)
    d.text((16, 60), "Journal Entries", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((130, 60), "›", font=font(14), fill=hex2rgb(TEXT_MUTED))
    d.text((146, 60), "LN/2025/0001", font=font(14, bold=True), fill=hex2rgb(TEXT_DARK))

    # Filter tag
    d.rounded_rectangle([16, 78, 270, 96], radius=4, fill=hex2rgb("#e7f0fb"))
    d.text((24, 81), "Loan: LN/2025/0001  ✕", font=font(12), fill=hex2rgb(BLUE_BADGE))

    # New button
    d.rounded_rectangle([W-100, 60, W-16, 90], radius=4, fill=hex2rgb(ODOO_PURPLE))
    d.text((W-84, 69), "New", font=font(13, bold=True), fill=hex2rgb(WHITE))

    # Table
    PAD = 16
    tbl_y = 108

    cols = [
        (PAD,       20,   "☐"),
        (PAD+28,    90,   "Date"),
        (PAD+126,  480,   "Reference"),
        (PAD+614,  100,   "Journal"),
        (PAD+722,  120,   "Debit"),
        (PAD+850,  120,   "Credit"),
        (PAD+978,   90,   "Status"),
    ]
    header_end = draw_table_header(d, cols, tbl_y, row_h=36)

    entries = [
        ("09/18/2024", "Loan Received from Al Rajhi Bank — LN/2025/0001",       "Bank", "500,000.00", "500,000.00"),
        ("11/17/2024", "Loan Payment - LN/2025/0001 - Installment #1",           "Bank",  "11,187.21",  "11,187.21"),
        ("12/17/2024", "Loan Payment - LN/2025/0001 - Installment #2",           "Bank",  "11,186.35",  "11,186.35"),
        ("01/16/2025", "Loan Payment - LN/2025/0001 - Installment #3",           "Bank",  "11,186.31",  "11,186.31"),
        ("02/15/2025", "Loan Payment - LN/2025/0001 - Installment #4",           "Bank",  "11,186.28",  "11,186.28"),
        ("03/17/2025", "Loan Payment - LN/2025/0001 - Installment #5",           "Bank",  "11,186.26",  "11,186.26"),
        ("04/16/2025", "Loan Payment - LN/2025/0001 - Installment #6",           "Bank",  "11,186.27",  "11,186.27"),
        ("05/16/2025", "Loan Payment - LN/2025/0001 - Installment #7",           "Bank",  "11,186.31",  "11,186.31"),
        ("06/15/2025", "Loan Payment - LN/2025/0001 - Installment #8",           "Bank",  "11,186.26",  "11,186.26"),
    ]

    y = header_end
    for idx, (date, ref, journal, debit, credit) in enumerate(entries):
        def make_green_badge(_):
            def fn(draw, bx, by):
                badge(draw, bx, by, "Posted", GREEN_BADGE)
            return fn

        row_data = [
            (cols[0][0], cols[0][1], "☐"),
            (cols[1][0], cols[1][1], date),
            (cols[2][0], cols[2][1], ref),
            (cols[3][0], cols[3][1], journal),
            (cols[4][0], cols[4][1], debit),
            (cols[5][0], cols[5][1], credit),
            (cols[6][0], cols[6][1], make_green_badge(None)),
        ]
        y = draw_table_row(d, row_data, y, row_h=40, alt=(idx % 2 == 1))

    draw_row_borders(d, cols, tbl_y, y, step=40, header_h=36)

    # Footer
    d.text((PAD, y+10), "9 records", font=font(12), fill=hex2rgb(TEXT_MUTED))

    # Total row
    d.rectangle([PAD, y+32, PAD+cols[-1][0]+cols[-1][1]-PAD, y+60],
                 fill=hex2rgb(TBL_HEADER_BG), outline=hex2rgb(TBL_BORDER), width=1)
    d.text((cols[4][0]+8, y+40), "578,670.98", font=font(13, bold=True), fill=hex2rgb(TEXT_DARK))
    d.text((cols[5][0]+8, y+40), "578,670.98", font=font(13, bold=True), fill=hex2rgb(TEXT_DARK))
    d.text((cols[2][0]+8, y+40), "Total", font=font(13, bold=True), fill=hex2rgb(TEXT_MUTED))

    img.save(os.path.join(OUT, "screenshot_04_journal_entries.png"))
    print("  screenshot_04_journal_entries.png created")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating Loan Management System images...")
    make_icon()
    make_banner()
    make_loans_list()
    make_loan_form()
    make_repayment_schedule()
    make_journal_entries()

    print("\nFile sizes:")
    files = [
        "icon.png",
        "banner.png",
        "screenshot_01_loans_list.png",
        "screenshot_02_loan_form.png",
        "screenshot_03_repayment_schedule.png",
        "screenshot_04_journal_entries.png",
    ]
    all_ok = True
    for f in files:
        path = os.path.join(OUT, f)
        if os.path.exists(path):
            size = os.path.getsize(path)
            ok = size > 10_000
            status = "OK" if ok else "TOO SMALL"
            print(f"  {f}: {size:,} bytes  [{status}]")
            if not ok:
                all_ok = False
        else:
            print(f"  {f}: MISSING")
            all_ok = False

    print("\nAll files generated successfully!" if all_ok else "\nSome files have issues!")
