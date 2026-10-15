"""
Project Controlling dashboard - opened by the existing "View" button.

Data  : db/project_dashboard.py  (real data, same weighted progress as
        the Projects page and the Roadmap)
Charts: ui/projects/charts.py
"""

import customtkinter as ctk
from tkinter import messagebox

from config import *
from licensing.gate import is_feature_enabled
from db.project_dashboard import get_project_dashboard
from utils.date_converter import gregorian_to_jalali as jal
from .charts import (
    ProgressRing, Donut, PhaseBars, Timeline, LineChart,
    T, mix, status_color, status_colors, category_colors, fmt_money, fmt_compact, CYAN, VIOLET,
)

PRIORITY = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": GREEN}
H1 = ("Segoe UI", 30, "bold")
H3 = ("Segoe UI", 15, "bold")
SMALL = ("Segoe UI", 11)
SMALL_B = ("Segoe UI", 11, "bold")
CAPS = ("Segoe UI", 10, "bold")


# ----------------------------------------------------------
# small building blocks
# ----------------------------------------------------------

def badge(parent, text, color, size=11):
    return ctk.CTkLabel(
        parent, text=f"  {text}  ", font=("Segoe UI", size, "bold"),
        text_color=color, fg_color=mix(CARD, color, 0.18),
        corner_radius=10, height=24,
    )


def card(parent, **kw):
    return ctk.CTkFrame(
        parent, fg_color=CARD, corner_radius=14,
        border_width=1, border_color=BORDER, **kw
    )


def section(parent, title, subtitle=None):
    """Card with a title row; returns (card, body_frame)."""
    c = card(parent)
    c.grid_columnconfigure(0, weight=1)
    c.grid_rowconfigure(1, weight=1)
    head = ctk.CTkFrame(c, fg_color="transparent")
    head.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
    ctk.CTkLabel(head, text=title, font=H3, text_color=TEXT).pack(side="left")
    if subtitle:
        ctk.CTkLabel(head, text=subtitle, font=SMALL, text_color=TEXT2).pack(side="left", padx=10)
    body = ctk.CTkFrame(c, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    body.grid_columnconfigure(0, weight=1)
    return c, body


def kpi(parent, col, label, value, sub, pct=None, color=CYAN, sub_color=None):
    c = card(parent)
    c.grid(row=0, column=col, sticky="nsew", padx=6)
    ctk.CTkLabel(c, text=label.upper(), font=CAPS, text_color=TEXT2).pack(anchor="w", padx=16, pady=(14, 0))
    ctk.CTkLabel(c, text=value, font=("Segoe UI", 26, "bold"), text_color=TEXT).pack(anchor="w", padx=16, pady=(2, 0))
    ctk.CTkLabel(c, text=sub, font=SMALL, text_color=sub_color or TEXT2).pack(anchor="w", padx=16)
    bar = ctk.CTkProgressBar(c, height=7, corner_radius=4, fg_color=T.track, progress_color=color)
    bar.pack(fill="x", padx=16, pady=(8, 14))
    if pct is None:
        bar.set(0)
    else:
        bar.set(max(0, min(1, pct / 100)))
    c.bind("<Enter>", lambda e: c.configure(border_color=color))
    c.bind("<Leave>", lambda e: c.configure(border_color=BORDER))
    return c


# ----------------------------------------------------------
# The window
# ----------------------------------------------------------

class ProjectDashboard(ctk.CTkToplevel):

    def __init__(self, parent, project_id, current_user=None, database=None, tree=None):

        super().__init__(parent)

        self.project_id = project_id
        self.current_user = current_user
        self.database = database
        self.tree = tree

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1440, sw - 60), min(860, sh - 90)

        self.title("Project Controlling")
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(min(1200, sw), min(700, sh))
        self.configure(fg_color=BACKGROUND)
        self.transient(parent)

        self.page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.page.pack(fill="both", expand=True, padx=14, pady=(10, 14))
        self.page.grid_columnconfigure(0, weight=1)

        self.build()

    # ------------------------------------------------------
    def refresh(self):
        self.build()

    def build(self):

        for child in self.page.winfo_children():
            child.destroy()

        data = get_project_dashboard(self.project_id)

        if data is None:
            ctk.CTkLabel(self.page, text="This project no longer exists.",
                         font=FONT_NORMAL, text_color=TEXT2).grid(pady=60)
            return

        self.data = data
        self.title(f"Project Controlling - {data['name']}")

        self._header(data).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._kpis(data).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._progress_row(data).grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self._timeline(data).grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._expenses_row(data).grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self._bottom_row(data).grid(row=5, column=0, sticky="ew")

    # ------------------------------------------------------ header
    def _header(self, d):

        c = card(self.page)
        c.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(c, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=22, pady=16)

        ctk.CTkLabel(left, text="PROJECT CONTROLLING", font=CAPS, text_color=CYAN).pack(anchor="w")
        ctk.CTkLabel(left, text=d["name"], font=H1, text_color=TEXT).pack(anchor="w", pady=(0, 2))

        meta = ctk.CTkFrame(left, fg_color="transparent")
        meta.pack(anchor="w", pady=(2, 0))
        for i, (k, v) in enumerate([
            ("Code", d["code"]), ("Client", d["client"] or "-"), ("Manager", d["manager"] or "-")
        ]):
            ctk.CTkLabel(meta, text=k.upper(), font=("Segoe UI", 9, "bold"), text_color=TEXT2).grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else 26, 0))
            ctk.CTkLabel(meta, text=v, font=("Segoe UI", 13), text_color=TEXT).grid(row=1, column=i, sticky="w", padx=(0 if i == 0 else 26, 0))

        right = ctk.CTkFrame(c, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=22)

        badges = ctk.CTkFrame(right, fg_color="transparent")
        badges.pack(anchor="e", pady=(0, 10))
        badge(badges, d["status"] or "-", status_color(d["status"]), 12).pack(side="left", padx=4)
        if d["priority"]:
            badge(badges, f"{d['priority']} priority", PRIORITY.get(d["priority"].lower(), T.other), 12).pack(side="left", padx=4)

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.pack(anchor="e")

        def btn(text, cmd, fg=NEUTRAL, hover=NEUTRAL_HOVER, state="normal"):
            ctk.CTkButton(buttons, text=text, width=110, height=34, font=SMALL_B, fg_color=fg,
                          hover_color=hover, state=state, command=cmd).pack(side="left", padx=4)

        btn("← Back", self.destroy)

        can_edit = self.database is not None and self.tree is not None and \
            self.database.has_permission(self.current_user, "projects.edit")
        if self.database is not None and self.tree is not None:
            btn("✏ Edit Project", self._edit, BLUE, BLUE_HOVER, "normal" if can_edit else "disabled")

        can_export = self.database is None or self.database.has_permission(self.current_user, "roadmap.view")
        if is_feature_enabled("excel_export"):      # licensed feature
            btn("📊 Export Excel", self._export, GREEN, GREEN_HOVER, "normal" if can_export else "disabled")
        btn("🔄 Refresh", self.refresh, VIEW, VIEW_HOVER)

        return c

    def _edit(self):
        from .edit_projects import edit_project
        self.destroy()
        edit_project(self.database, self.tree)

    def _export(self):
        from utils.roadmap_export import export_roadmap_dialog
        export_roadmap_dialog(self, self.project_id)

    # ------------------------------------------------------ KPIs
    def _kpis(self, d):

        row = ctk.CTkFrame(self.page, fg_color="transparent")

        cards = []
        prog = d["progress"]
        cards.append(("Overall Progress", f"{prog:.0f}%",
                      f"{d['phases_total']} phases · weighted" if d["phases_total"] else "No phases yet",
                      prog if d["phases_total"] else None, GREEN if prog >= 99.99 else CYAN, None))

        if d["duration"]:
            dl = d["days_left"]
            sub = (f"{dl} days left" if dl > 0 else "Ends today" if dl == 0 else f"Overdue by {-dl} days")
            cards.append(("Project Duration", f"{d['duration']} days", sub, d["elapsed_pct"], BLUE,
                          RED if dl < 0 and prog < 99.99 else None))
        else:
            cards.append(("Project Duration", "—", "Start / end date not set", None, BLUE, None))

        usage = d["budget_usage"]
        if usage is not None:
            col = RED if usage > 100 else ORANGE if usage > 85 else YELLOW if usage > 70 else GREEN
            cards.append(("Total Expenses", fmt_money(d["total_expenses"]), f"Budget usage {usage:.0f}%",
                          usage, col, RED if usage > 100 else None))
        else:
            cards.append(("Total Expenses", fmt_money(d["total_expenses"]),
                          f"{d['expense_count']} expense records · no budget set", None, YELLOW, None))

        cards.append(("Phases", f"{d['phases_completed']} / {d['phases_total']}",
                      f"{d['overdue_count']} overdue" if d["overdue_count"] else "Completed",
                      d["phases_completed"] / d["phases_total"] * 100 if d["phases_total"] else None,
                      GREEN, ORANGE if d["overdue_count"] else None))

        if d["remaining_budget"] is not None:
            rem = d["remaining_budget"]
            cards.append(("Remaining Budget", fmt_money(rem), f"of {fmt_money(d['budget'])}",
                          max(0, rem) / d["budget"] * 100, GREEN if rem >= 0 else RED, RED if rem < 0 else None))
        if d["contract_count"]:
            paid = d["contract_paid"] / d["contract_value"] * 100 if d["contract_value"] else None
            cards.append(("Contracts", fmt_money(d["contract_value"]),
                          f"{fmt_money(d['contract_paid'])} paid" if paid is not None else f"{d['contract_count']} contracts",
                          paid, VIOLET, None))

        for i, args in enumerate(cards):
            row.grid_columnconfigure(i, weight=1, uniform="kpi")
            kpi(row, i, *args)
        return row

    # ------------------------------------------------------ progress + status
    def _progress_row(self, d):

        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.grid_columnconfigure(0, weight=3, uniform="pr")
        row.grid_columnconfigure(1, weight=2, uniform="pr")

        # ---- left: ring + phase bars
        left, body = section(row, "Project Progress", "weighted by phase")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        body.grid_columnconfigure(0, weight=0, minsize=230)
        body.grid_columnconfigure(1, weight=1)

        ring = ProgressRing(body, 230)
        ring.grid(row=0, column=0, sticky="n", padx=(0, 10))
        ring.set_data(d["progress"], [
            f"{d['phases_completed']} of {d['phases_total']} phases completed",
            f"{d['overdue_count']} overdue" if d["overdue_count"] else "No overdue phases",
        ], has_data=d["phases_total"] > 0)

        bars = PhaseBars(body)
        bars.grid(row=0, column=1, sticky="nsew")
        bars.set_data([{
            "name": p["name"], "progress": p["progress"], "weight": p["weight"],
            "status": self._phase_label(p), "color": status_color(self._phase_label(p)),
        } for p in d["phases"]])

        # ---- right: status donut
        right, body2 = section(row, "Phase Status", "live from phases")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        counts = {}
        for p in d["phases"]:
            counts[self._phase_label(p)] = counts.get(self._phase_label(p), 0) + 1
        order = ["Completed", "In Progress", "Pending", "Delayed", "Skipped", "Cancelled"]
        keys = sorted(counts, key=lambda k: order.index(k) if k in order else 99)

        donut = Donut(body2, 250)
        donut.grid(row=0, column=0, sticky="nsew")
        phase_colors = status_colors(keys)
        donut.set_data(
            [(k, counts[k], phase_colors[k],
              ["Past its end date and not finished"] if k == "Delayed" else None) for k in keys],
            str(d["phases_total"]), "phases",
        )
        return row

    @staticmethod
    def _phase_label(p):
        return "Delayed" if p["overdue"] else p["status"]

    # ------------------------------------------------------ timeline
    def _timeline(self, d):

        c, body = section(self.page, "Project Timeline", "phases over time · dashed line = today")

        rows = []
        for p in d["phases"]:
            label = self._phase_label(p)
            rows.append({
                "name": p["name"], "start": _date(p["start"]), "end": _date(p["end"]),
                "progress": p["progress"], "status": p["status"], "label": label,
                "color": status_color(label), "overdue": p["overdue"],
            })

        tl = Timeline(body)
        tl.grid(row=0, column=0, sticky="nsew")
        tl.set_data(rows, d["start_date"], d["end_date"])
        return c

    # ------------------------------------------------------ expenses
    def _expenses_row(self, d):

        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.grid_columnconfigure(0, weight=2, uniform="ex")
        row.grid_columnconfigure(1, weight=3, uniform="ex")

        left, b1 = section(row, "Cost Structure", "by category")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        cats = list(d["categories"])
        if len(cats) > 6:
            cats = cats[:5] + [("Other", sum(v for _k, v in cats[5:]))]
        donut = Donut(b1, 250, money=True)
        donut.grid(row=0, column=0, sticky="nsew")
        donut.empty_title, donut.empty_hint = "No expense data available", "Expenses added to this project will appear here."
        cat_colors = category_colors([k for k, _v in cats])
        donut.set_data(
            [(k, v, cat_colors[k], None) for k, v in cats],
            _short(d["total_expenses"]), "total expenses",
        )

        right, b2 = section(row, "Expense Trend", "monthly")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        line = LineChart(b2, 250)
        line.grid(row=0, column=0, sticky="nsew")
        line.set_data(d["months"])
        return row

    # ------------------------------------------------------ deadlines + details
    def _bottom_row(self, d):

        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.grid_columnconfigure(0, weight=3, uniform="bt")
        row.grid_columnconfigure(1, weight=2, uniform="bt")

        left, body = section(row, "Upcoming Deadlines", "nearest end date first")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        if not d["upcoming"]:
            ctk.CTkLabel(body, text="No pending phase deadlines", font=SMALL_B,
                         text_color=TEXT2).grid(pady=40)
        else:
            body.grid_columnconfigure(0, weight=3)
            for i, h in enumerate(("PHASE", "END DATE", "PROGRESS", "STATUS")):
                ctk.CTkLabel(body, text=h, font=("Segoe UI", 9, "bold"), text_color=TEXT2).grid(
                    row=0, column=i, sticky="w", padx=8, pady=(0, 4))
            for r, p in enumerate(d["upcoming"][:8], start=1):
                dl = p["days_left"]
                if p["overdue"]:
                    txt, col = f"Overdue {-dl}d", RED
                elif dl is not None and dl <= 7:
                    txt, col = ("Due today" if dl == 0 else f"Due in {dl}d"), ORANGE
                else:
                    txt, col = "On track", BLUE
                ctk.CTkLabel(body, text=p["name"], font=SMALL_B, text_color=TEXT, anchor="w").grid(row=r, column=0, sticky="w", padx=8, pady=5)
                ctk.CTkLabel(body, text=jal(p["end"]), font=SMALL, text_color=TEXT2).grid(row=r, column=1, sticky="w", padx=8)
                pb = ctk.CTkProgressBar(body, width=110, height=7, fg_color=T.track, progress_color=col)
                pb.set(p["progress"] / 100)
                pb.grid(row=r, column=2, sticky="w", padx=8)
                badge(body, txt, col, 10).grid(row=r, column=3, sticky="w", padx=8)
            if len(d["upcoming"]) > 8:
                ctk.CTkLabel(body, text=f"+ {len(d['upcoming']) - 8} more phases", font=SMALL,
                             text_color=TEXT2).grid(row=9, column=0, sticky="w", padx=8, pady=(6, 0))

        right, body2 = section(row, "Project Details")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        body2.grid_columnconfigure(1, weight=1)
        items = [
            ("Type", d["type"]), ("Department", d["department"]),
            ("Start", jal(d["start"])), ("End", jal(d["end"])),
            ("Budget", fmt_money(d["budget"]) if d["budget"] else None),
            ("Contracts", f"{d['contract_count']} · {fmt_money(d['contract_value'])}" if d["contract_count"] else None),
            ("Documents", str(d["documents"])),
            ("Description", d["description"]),
        ]
        r = 0
        for k, v in items:
            if not v:
                continue
            ctk.CTkLabel(body2, text=k, font=SMALL, text_color=TEXT2).grid(row=r, column=0, sticky="nw", padx=(8, 14), pady=4)
            ctk.CTkLabel(body2, text=str(v), font=SMALL_B, text_color=TEXT, anchor="w", justify="left",
                         wraplength=330).grid(row=r, column=1, sticky="w", pady=4)
            r += 1
        return row


# ----------------------------------------------------------

def _date(text):
    from datetime import datetime
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _short(v):
    return fmt_compact(v)


def open_project_dashboard(parent, project_id, current_user=None, database=None, tree=None):
    try:
        ProjectDashboard(parent, project_id, current_user, database, tree)
    except Exception as error:                     # never crash the ERP
        import traceback
        traceback.print_exc()
        messagebox.showerror("View Project", f"Could not open the project dashboard:\n{error}")
