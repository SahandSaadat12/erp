"""
Main dashboard  =  KPI cards + charts + tables.

Data  : db/dashboard.py  (get_dashboard_stats, get_dashboard_overview)
Charts: ui/projects/charts.py  (same toolkit as the Project Controlling window)
"""

import customtkinter as ctk

from config import *
from db.dashboard import get_dashboard_stats, get_dashboard_overview
from utils.date_converter import gregorian_to_jalali as jal
from ui.projects.charts import (
    Donut, LineChart, HBars,
    T, mix, status_color, fmt_compact, CYAN, category_colors, status_colors,
)
from ui.projects.project_dashboard import card, section, kpi, badge

PRIORITY = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": GREEN}
SMALL = ("Segoe UI", 11)
SMALL_B = ("Segoe UI", 11, "bold")
CAPS = ("Segoe UI", 10, "bold")


def short_price(value):
    return fmt_compact(float(value or 0))


def money(value):
    return f"{short_price(value)} {CURRENCY}"


# ==========================================================
# Table  (plain CTk widgets, no ttk styling needed)
# ==========================================================

def table(parent, columns, rows, empty="Nothing to show yet."):
    """
    columns: [(header, weight, anchor)]
    rows   : [[cell, ...]]   cell = "text" | ("text", color) | ("@badge", "text", color)
    """

    wrap = ctk.CTkFrame(parent, fg_color="transparent")
    wrap.grid_columnconfigure(0, weight=1)

    def configure(frame):
        for i, (_h, weight, _a) in enumerate(columns):
            frame.grid_columnconfigure(i, weight=weight, uniform="c")

    head = ctk.CTkFrame(wrap, fg_color=mix(CARD, TEXT, 0.05), corner_radius=8, height=30)
    head.grid(row=0, column=0, sticky="ew")
    configure(head)
    for i, (title, _w, anchor) in enumerate(columns):
        ctk.CTkLabel(head, text=title.upper(), font=CAPS, text_color=TEXT2,
                     anchor=anchor).grid(row=0, column=i, sticky="ew", padx=10, pady=5)

    if not rows:
        ctk.CTkLabel(wrap, text=empty, font=SMALL, text_color=TEXT2).grid(row=1, column=0, pady=26)
        return wrap

    for r, cells in enumerate(rows, start=1):
        line = ctk.CTkFrame(wrap, fg_color="transparent", corner_radius=8, height=34)
        line.grid(row=r, column=0, sticky="ew", pady=1)
        configure(line)

        def on(_e, f=line):
            f.configure(fg_color=T.hover_bg)

        def off(_e, f=line):
            f.configure(fg_color="transparent")

        line.bind("<Enter>", on)
        line.bind("<Leave>", off)

        for i, cell in enumerate(cells):
            anchor = columns[i][2]
            if isinstance(cell, tuple) and cell and cell[0] == "@badge":
                w = badge(line, cell[1], cell[2], size=10)
                w.grid(row=0, column=i, padx=10, pady=5, sticky=anchor)
            else:
                text, color = cell if isinstance(cell, tuple) else (cell, TEXT)
                w = ctk.CTkLabel(line, text=str(text), font=SMALL, text_color=color, anchor=anchor)
                w.grid(row=0, column=i, sticky="ew", padx=10, pady=5)
            w.bind("<Enter>", on)
            w.bind("<Leave>", off)

    return wrap


def due_text(days):
    if days is None:
        return "—", TEXT2
    if days < 0:
        return f"{-days} d overdue", RED
    if days == 0:
        return "Due today", ORANGE
    if days <= 14:
        return f"{days} d left", ORANGE
    return f"{days} d left", GREEN


# ==========================================================
# Build
# ==========================================================

def create_dashboard(dashboard_frame):

    for widget in dashboard_frame.winfo_children():
        widget.destroy()

    page = ctk.CTkScrollableFrame(dashboard_frame, fg_color="transparent")
    page.pack(fill="both", expand=True, padx=6, pady=(4, 8))
    page.grid_columnconfigure(0, weight=1)

    stats = get_dashboard_stats()
    data = get_dashboard_overview()

    kpis(page, stats, data).grid(row=0, column=0, sticky="ew", pady=(0, 10))
    row1(page, data).grid(row=1, column=0, sticky="ew", pady=(0, 10))
    row2(page, data).grid(row=2, column=0, sticky="ew", pady=(0, 10))
    row3(page, data).grid(row=3, column=0, sticky="ew", pady=(0, 10))


def _row(parent, weights):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    for i, w in enumerate(weights):
        row.grid_columnconfigure(i, weight=w, uniform="r")
    row.grid_rowconfigure(0, weight=1)
    return row


def _put(row, col, title, subtitle, of, colspan=1):
    """Section card in column `col`; returns its body frame."""
    left = col == 0
    c, body = section(row, title, subtitle)
    c.grid(row=0, column=col, columnspan=colspan, sticky="nsew",
           padx=(0 if left else 6, 6 if of else 0))
    return body


# ----------------------------------------------------------
# KPI cards
# ----------------------------------------------------------

def kpis(parent, s, d):

    row = ctk.CTkFrame(parent, fg_color="transparent")
    for i in range(6):
        row.grid_columnconfigure(i, weight=1, uniform="k")

    value = float(s["contracts_value"] or 0)
    paid = float(s["contracts_paid"] or 0)
    expenses = float(s["expenses_total"] or 0)
    paid_pct = paid / value * 100 if value else 0
    progress = max(0, min(float(s["overall_progress"] or 0), 100))
    overdue = d["overdue"]

    kpi(row, 0, "Projects", str(s["total_projects"]),
        f"{s['active_projects']} active · {s['completed_projects']} completed",
        s["completed_projects"] / s["total_projects"] * 100 if s["total_projects"] else 0, BLUE)
    kpi(row, 1, "Overall progress", f"{progress:.0f}%", "weighted by phase", progress, CYAN)
    kpi(row, 2, "Contracts value", money(value), f"{money(value - paid)} remaining", 100 if value else 0, T.categories[2])
    kpi(row, 3, "Paid", money(paid), f"{paid_pct:.0f}% of contracts", paid_pct, GREEN)
    kpi(row, 4, "Expenses", money(expenses), f"net {money(paid - expenses)}",
        min(100, expenses / paid * 100) if paid else 0, ORANGE)
    kpi(row, 5, "Overdue", str(overdue), "open projects past end date" if overdue else "all on schedule",
        min(100, overdue / max(1, len(d["open_projects"])) * 100),
        RED if overdue else GREEN, RED if overdue else GREEN)
    return row


# ----------------------------------------------------------
# Row 1 :  expense trend  |  projects by status
# ----------------------------------------------------------

def row1(parent, d):

    row = _row(parent, (3, 2))

    body = _put(row, 0, "Expense Trend", "monthly", True)
    line = LineChart(body, 260)
    line.grid(row=0, column=0, sticky="nsew")
    line.set_data(d["trend"])

    body = _put(row, 1, "Projects by Status", None, False)
    donut = Donut(body, 260)
    donut.grid(row=0, column=0, sticky="nsew")
    order = ["Open", "In Progress", "On Hold", "Completed", "Cancelled", "Closed"]
    segs = sorted(d["status"], key=lambda s: order.index(s[0]) if s[0] in order else 99)
    seg_colors = status_colors([k for k, _v in segs])
    donut.set_data([(k, v, seg_colors[k], None) for k, v in segs],
                   str(sum(v for _k, v in segs)), "projects")
    return row


# ----------------------------------------------------------
# Row 2 :  progress  |  contracts paid  |  expenses by category
# ----------------------------------------------------------

def row2(parent, d):

    row = _row(parent, (1, 1, 1))

    # --- progress of open projects
    body = _put(row, 0, "Project Progress", "open projects", True)
    bars = HBars(body)
    bars.grid(row=0, column=0, sticky="nsew")
    bars.empty_title, bars.empty_hint = "No open projects", "Projects you add will appear here."
    projs = sorted(d["open_projects"], key=lambda p: -p["progress"])[:6]
    bars.set_data([{
        "label": p["name"], "value": p["progress"], "total": 100,
        "color": status_color(p["status"]), "display": f"{p['progress']:.0f}%",
        "tip": [f"Status: {p['status']}", f"Phases: {p['phases']}",
                f"Progress: {p['progress']:.1f}%"],
    } for p in projs])

    # --- contracts: paid out of value
    body = _put(row, 1, "Contracts", "paid vs value", True)
    cb = HBars(body)
    cb.grid(row=0, column=0, sticky="nsew")
    cb.empty_title, cb.empty_hint = "No contracts yet", "Contracts you add will appear here."
    cb.set_data([{
        "label": c["project"] or c["name"], "value": c["paid"], "total": c["value"],
        "color": GREEN if c["value"] and c["paid"] >= c["value"] else BLUE,
        "display": f"{c['paid'] / c['value'] * 100:.0f}%" if c["value"] else "—",
        "tip": [f"Value: {money(c['value'])}", f"Paid: {money(c['paid'])}",
                f"Remaining: {money(max(0, c['value'] - c['paid']))}"],
    } for c in d["contracts"][:6]])

    # --- expenses by category
    body = _put(row, 2, "Expenses by Category", None, False)
    donut = Donut(body, 250, money=True)
    donut.grid(row=0, column=0, sticky="nsew")
    donut.empty_title, donut.empty_hint = "No expense data available", "Expenses you add will appear here."
    cats = list(d["categories"])
    if len(cats) > 6:
        cats = cats[:5] + [("Other", sum(v for _k, v in cats[5:]))]
    cat_colors = category_colors([k for k, _v in cats])
    donut.set_data(
        [(k, v, cat_colors[k], None) for k, v in cats],
        short_price(sum(v for _k, v in cats)), "total expenses",
    )
    return row


# ----------------------------------------------------------
# Row 3 :  tables
# ----------------------------------------------------------

def row3(parent, d):

    row = _row(parent, (1, 1))

    # --- deadlines
    body = _put(row, 0, "Upcoming Deadlines", "open projects, soonest first", True)
    rows = []
    for p in d["deadlines"]:
        txt, col = due_text(p["days_left"])
        pr = str(p["priority"] or "")
        rows.append([
            p["name"],
            ("@badge", p["status"], status_color(p["status"])),
            ("@badge", pr, PRIORITY.get(pr.lower(), TEXT2)) if pr else "—",
            jal(p["end_date"]) or "—",
            (txt, col),
        ])
    table(body, [("Project", 3, "w"), ("Status", 2, "w"), ("Priority", 2, "w"),
                 ("End", 2, "w"), ("Due", 2, "w")],
          rows, "No open projects with an end date.").grid(row=0, column=0, sticky="nsew")

    # --- recent expenses
    body = _put(row, 1, "Recent Expenses", "latest first", False)
    rows = []
    for e in d["recent_expenses"]:
        paid = str(e["status"]).lower() == "paid"
        rows.append([
            e["title"] or "—",
            e["project"] or "—",
            money(e["amount"]),
            jal(e["date"]) or "—",
            ("@badge", e["status"], GREEN if paid else YELLOW),
        ])
    table(body, [("Title", 3, "w"), ("Project", 3, "w"), ("Amount", 2, "w"),
                 ("Date", 2, "w"), ("Status", 2, "w")],
          rows, "No expenses recorded yet.").grid(row=0, column=0, sticky="nsew")
    return row
