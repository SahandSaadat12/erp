"""
Roadmap -> Excel export (needs: pip install xlsxwriter).

One workbook per project with real, editable Excel charts:
  Summary  : KPI block, progress doughnut, phase-status pie
  Phases   : phase table + progress bar chart + expected-vs-actual cost chart
  Expenses : category table + pie chart + monthly trend line chart
All numbers come from db/project_dashboard.py (same source as the
Roadmap / Projects pages).
"""

import os
from tkinter import filedialog, messagebox

from db.project_dashboard import get_project_dashboard
from utils.date_converter import gregorian_to_jalali as jal

BG, CARD, HEAD = "#1B1F27", "#242A38", "#2F3850"
BLUE, GREEN, ORANGE, RED, CYAN, GRAY = "#3B82F6", "#22C55E", "#F59E0B", "#EF4444", "#38BDF8", "#8B95A7"
STATUS_COLORS = {"Completed": GREEN, "In Progress": BLUE, "Pending": GRAY,
                 "Delayed": ORANGE, "Skipped": "#5B6474", "Cancelled": RED}
CAT_COLORS = [BLUE, CYAN, "#A78BFA", ORANGE, GREEN, "#F472B6", GRAY]


def build_roadmap_workbook(project_id, path):
    import xlsxwriter

    d = get_project_dashboard(project_id)
    if d is None:
        raise ValueError("Project not found.")

    wb = xlsxwriter.Workbook(path)
    wb.set_properties({"title": f"Roadmap - {d['name']}", "subject": d["code"]})

    f = lambda **k: wb.add_format({"font_name": "Segoe UI", "font_size": 10, **k})
    title = f(bold=True, font_size=20, font_color="#FFFFFF", bg_color=BG)
    sub = f(font_color="#BFC7D5", bg_color=BG)
    bg = f(bg_color=BG)
    head = f(bold=True, font_color="#FFFFFF", bg_color=HEAD, border=1, border_color="#32394A", align="center", valign="vcenter")
    txt = f(font_color="#FFFFFF", bg_color=CARD, border=1, border_color="#32394A")
    num = f(font_color="#FFFFFF", bg_color=CARD, border=1, border_color="#32394A", num_format="#,##0")
    pct = f(font_color="#FFFFFF", bg_color=CARD, border=1, border_color="#32394A", num_format='0"%"', align="center")
    ctr = f(font_color="#FFFFFF", bg_color=CARD, border=1, border_color="#32394A", align="center")
    k_lab = f(font_color="#BFC7D5", bg_color=CARD, font_size=9, bold=True, top=1, left=1, right=1, border_color="#32394A")
    k_val = f(font_color="#FFFFFF", bg_color=CARD, font_size=18, bold=True, bottom=1, left=1, right=1, border_color="#32394A", num_format="#,##0.##", align="center")

    def paint(ws, cols=22, rows=60):
        ws.hide_gridlines(2)
        ws.set_column(0, cols, 14, bg)
        ws.set_default_row(18)

    def chart_style(ch, name):
        ch.set_title({"name": name, "name_font": {"color": "#FFFFFF", "size": 12, "name": "Segoe UI"}})
        ch.set_chartarea({"fill": {"color": CARD}, "border": {"color": "#32394A"}})
        ch.set_plotarea({"fill": {"color": CARD}})
        ch.set_legend({"font": {"color": "#BFC7D5"}, "position": "right"})

    def axes(ch, y_fmt=None):
        ax = {"num_font": {"color": "#BFC7D5"}, "line": {"color": "#32394A"},
              "major_gridlines": {"visible": True, "line": {"color": "#30394B"}}}
        ch.set_x_axis({"num_font": {"color": "#BFC7D5"}, "line": {"color": "#32394A"}})
        if y_fmt:
            ax["num_format"] = y_fmt
        ch.set_y_axis(ax)

    # ================================================= Summary
    ws = wb.add_worksheet("Summary")
    paint(ws)
    ws.set_row(1, 32)
    ws.merge_range("B2:J2", d["name"], title)
    ws.write("B3", f"{d['code']}  ·  Client: {d['client'] or '-'}  ·  Manager: {d['manager'] or '-'}  ·  Status: {d['status'] or '-'}", sub)
    ws.write("B4", f"{jal(d['start']) or '-'}  →  {jal(d['end']) or '-'}", sub)

    kpis = [
        ("OVERALL PROGRESS %", round(d["progress"], 1)),
        ("PHASES COMPLETED", f"{d['phases_completed']} / {d['phases_total']}"),
        ("BUDGET", d["budget"] or 0),
        ("TOTAL EXPENSES", d["total_expenses"]),
        ("REMAINING", d["remaining_budget"] if d["remaining_budget"] is not None else "-"),
    ]
    for i, (lab, val) in enumerate(kpis):
        col = 1 + i * 2
        ws.merge_range(5, col, 5, col + 1, lab, k_lab)
        ws.merge_range(6, col, 6, col + 1, val, k_val)
    ws.set_row(6, 30)

    # helper data for the charts (kept visible, to the right)
    ws.write("T2", "Progress", head); ws.write("U2", "Value", head)
    ws.write("T3", "Done", txt); ws.write_number("U3", round(d["progress"], 2), num)
    ws.write("T4", "Remaining", txt); ws.write_number("U4", round(100 - d["progress"], 2), num)
    ring = wb.add_chart({"type": "doughnut"})
    ring.add_series({
        "name": "Overall progress", "categories": "=Summary!$T$3:$T$4", "values": "=Summary!$U$3:$U$4",
        "points": [{"fill": {"color": GREEN if d["progress"] >= 99.99 else CYAN}}, {"fill": {"color": "#30394B"}}],
        "data_labels": {"value": True, "font": {"color": "#FFFFFF"}, "num_format": '0"%"'},
    })
    ring.set_hole_size(68)
    chart_style(ring, f"Overall Progress  {d['progress']:.0f}%")
    ws.insert_chart("B9", ring, {"x_scale": 1.0, "y_scale": 1.15})

    ws.write("T7", "Status", head); ws.write("U7", "Phases", head)
    r = 7
    order = list(STATUS_COLORS)
    counts = {}
    for p in d["phases"]:
        k = "Delayed" if p["overdue"] else p["status"]
        counts[k] = counts.get(k, 0) + 1
    keys = sorted(counts, key=lambda k: order.index(k) if k in order else 99)
    for k in keys:
        ws.write(r, 19, k, txt); ws.write_number(r, 20, counts[k], num); r += 1
    if keys:
        pie = wb.add_chart({"type": "pie"})
        pie.add_series({
            "name": "Phase status", "categories": f"=Summary!$T$8:$T${7 + len(keys)}",
            "values": f"=Summary!$U$8:$U${7 + len(keys)}",
            "points": [{"fill": {"color": STATUS_COLORS.get(k, GRAY)}, "border": {"color": CARD}} for k in keys],
            "data_labels": {"value": True, "percentage": True, "separator": "\n", "font": {"color": "#FFFFFF"}},
        })
        chart_style(pie, "Phase Status")
        ws.insert_chart("H9", pie, {"x_scale": 1.0, "y_scale": 1.15})
    else:
        ws.write("H10", "No phase data available", sub)

    # ================================================= Phases
    wp = wb.add_worksheet("Phases")
    paint(wp)
    wp.set_row(1, 28)
    wp.merge_range("B2:I2", "Phase Roadmap", title)
    cols = ["Phase", "Weight %", "Progress %", "Status", "Start", "End", "Expected cost", "Actual cost"]
    wp.set_row(3, 24)
    for i, c in enumerate(cols):
        wp.write(3, 1 + i, c, head)
    wp.set_column("B:B", 30); wp.set_column("C:D", 12); wp.set_column("E:E", 14); wp.set_column("F:G", 14); wp.set_column("H:I", 16)
    for r, p in enumerate(d["phases"], start=4):
        label = "Delayed" if p["overdue"] else p["status"]
        wp.write(r, 1, p["name"], txt)
        wp.write_number(r, 2, p["weight"], pct)
        wp.write_number(r, 3, round(p["progress"], 1), pct)
        wp.write(r, 4, label, f(font_color=STATUS_COLORS.get(label, "#FFFFFF"), bg_color=CARD, border=1, border_color="#32394A", bold=True, align="center"))
        wp.write(r, 5, jal(p["start"]) or "-", ctr)
        wp.write(r, 6, jal(p["end"]) or "-", ctr)
        wp.write_number(r, 7, p["price"], num)
        wp.write_number(r, 8, p["actual"], num)
    n = len(d["phases"])
    last = 4 + n
    if n:
        wp.conditional_format(4, 3, last - 1, 3, {"type": "data_bar", "bar_color": CYAN, "bar_solid": True,
                                                     "min_type": "num", "min_value": 0, "max_type": "num", "max_value": 100})
        bar = wb.add_chart({"type": "bar"})
        bar.add_series({"name": "Progress %", "categories": f"=Phases!$B$5:$B${last}", "values": f"=Phases!$D$5:$D${last}",
                        "fill": {"color": CYAN}, "gap": 60, "data_labels": {"value": True, "font": {"color": "#FFFFFF"}, "num_format": '0"%"'}})
        chart_style(bar, "Phase Progress")
        bar.set_legend({"none": True})
        bar.set_x_axis({"min": 0, "max": 100, "num_font": {"color": "#BFC7D5"}, "major_gridlines": {"visible": True, "line": {"color": "#30394B"}}})
        bar.set_y_axis({"reverse": True, "num_font": {"color": "#FFFFFF"}, "line": {"color": "#32394A"}})
        wp.insert_chart(last + 1, 1, bar, {"x_scale": 1.35, "y_scale": max(1.0, 0.25 * n + 0.6)})

        cost = wb.add_chart({"type": "column"})
        cost.add_series({"name": "Expected", "categories": f"=Phases!$B$5:$B${last}", "values": f"=Phases!$H$5:$H${last}", "fill": {"color": BLUE}, "gap": 80})
        cost.add_series({"name": "Actual", "categories": f"=Phases!$B$5:$B${last}", "values": f"=Phases!$I$5:$I${last}", "fill": {"color": ORANGE}})
        chart_style(cost, "Expected vs Actual Cost per Phase")
        cost.set_legend({"font": {"color": "#BFC7D5"}, "position": "bottom"})
        axes(cost, "#,##0")
        wp.insert_chart(last + 1, 8, cost, {"x_scale": 1.5, "y_scale": max(1.0, 0.25 * n + 0.6)})
    else:
        wp.write("B6", "No phase data available", sub)

    # ================================================= Expenses
    we = wb.add_worksheet("Expenses")
    paint(we)
    we.set_row(1, 28)
    we.merge_range("B2:H2", "Cost Analysis", title)
    we.set_column("B:B", 24); we.set_column("C:E", 16)
    we.write_row(3, 1, ["Category", "Amount", "Share %"], head)
    total = d["total_expenses"] or 0
    for r, (k, v) in enumerate(d["categories"], start=4):
        we.write(r, 1, k, txt); we.write_number(r, 2, v, num)
        we.write_number(r, 3, v / total * 100 if total else 0, f(font_color="#FFFFFF", bg_color=CARD, border=1, border_color="#32394A", num_format='0.0"%"', align="center"))
    nc = len(d["categories"])
    if nc:
        we.write(4 + nc, 1, "TOTAL", head); we.write_number(4 + nc, 2, total, num)
        pie2 = wb.add_chart({"type": "doughnut"})
        pie2.add_series({"name": "Expenses", "categories": f"=Expenses!$B$5:$B${4 + nc}", "values": f"=Expenses!$C$5:$C${4 + nc}",
                         "points": [{"fill": {"color": CAT_COLORS[i % len(CAT_COLORS)]}, "border": {"color": CARD}} for i in range(nc)],
                         "data_labels": {"percentage": True, "font": {"color": "#FFFFFF"}}})
        pie2.set_hole_size(55)
        chart_style(pie2, "Cost Structure")
        we.insert_chart(6 + nc, 1, pie2, {"x_scale": 1.0, "y_scale": 1.1})
        mc = len(d["months"])
        if mc >= 2:
            we.write_row(3, 6, ["Month (Jalali)", "Amount"], head)
            we.set_column("G:H", 16)
            for r, (m, v) in enumerate(d["months"], start=4):
                we.write(r, 6, m, ctr); we.write_number(r, 7, v, num)
            line = wb.add_chart({"type": "line"})
            line.add_series({"name": "Monthly expenses", "categories": f"=Expenses!$G$5:$G${4 + mc}", "values": f"=Expenses!$H$5:$H${4 + mc}",
                             "line": {"color": CYAN, "width": 2.75}, "smooth": True,
                             "marker": {"type": "circle", "size": 6, "fill": {"color": CARD}, "border": {"color": CYAN}}})
            chart_style(line, "Expense Trend")
            line.set_legend({"none": True})
            axes(line, "#,##0")
            we.insert_chart(6 + nc, 6, line, {"x_scale": 1.6, "y_scale": 1.1})
    else:
        we.write("B6", "No expense data available", sub)

    wb.close()


def export_roadmap_dialog(parent, project_id):
    """Ask where to save, build the workbook, offer to open it."""

    try:
        import xlsxwriter  # noqa: F401
    except ImportError:
        messagebox.showerror("Export", "The 'xlsxwriter' package is missing.\nRun:  pip install xlsxwriter")
        return

    d = get_project_dashboard(project_id)
    if d is None:
        messagebox.showwarning("Export", "Project not found.")
        return

    path = filedialog.asksaveasfilename(
        parent=parent, title="Export Roadmap", defaultextension=".xlsx",
        initialfile=f"Roadmap_{d['code']}.xlsx", filetypes=[("Excel workbook", "*.xlsx")],
    )
    if not path:
        return

    try:
        build_roadmap_workbook(project_id, path)
    except PermissionError:
        messagebox.showerror("Export", "Cannot write the file - is it open in Excel? Close it and try again.")
        return
    except Exception as error:
        messagebox.showerror("Export", f"Export failed:\n{error}")
        return

    if messagebox.askyesno("Export", f"Roadmap exported:\n{path}\n\nOpen it now?"):
        try:
            os.startfile(path)                      # Windows
        except AttributeError:
            import subprocess, sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
        except OSError:
            pass
