"""
FinTrack Pro - Personal Budget & Expense Tracker
Author: Your Name
Tech Stack: Python, CustomTkinter, Matplotlib, SQLite3
"""

import customtkinter as ctk
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import datetime
import os

# ─── Theme Configuration ───────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg":        "#0f0f1a",
    "card":      "#1a1a2e",
    "card2":     "#16213e",
    "accent":    "#00d4aa",
    "accent2":   "#7c3aed",
    "danger":    "#ef4444",
    "warning":   "#f59e0b",
    "success":   "#10b981",
    "text":      "#e2e8f0",
    "subtext":   "#94a3b8",
    "border":    "#2d3748",
    "income":    "#10b981",
    "expense":   "#ef4444",
}

CATEGORIES = {
    "expense": ["🍔 Food", "🚗 Transport", "🏠 Housing", "💊 Health",
                "🎮 Entertainment", "👗 Shopping", "📚 Education", "⚡ Utilities", "🔧 Other"],
    "income":  ["💼 Salary", "💻 Freelance", "📈 Investment", "🎁 Gift", "💰 Other"],
}


# ─── Database Layer ────────────────────────────────────────────────────────────
class Database:
    def __init__(self, db_path="fintrack.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT NOT NULL,
                category    TEXT NOT NULL,
                amount      REAL NOT NULL,
                description TEXT,
                date        TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                limit_amount REAL NOT NULL
            )
        """)
        self.conn.commit()

    def add_transaction(self, type_, category, amount, description, date):
        self.conn.execute(
            "INSERT INTO transactions (type, category, amount, description, date) VALUES (?,?,?,?,?)",
            (type_, category, amount, description, date)
        )
        self.conn.commit()

    def delete_transaction(self, tid):
        self.conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
        self.conn.commit()

    def get_transactions(self, month=None):
        if month:
            return self.conn.execute(
                "SELECT * FROM transactions WHERE date LIKE ? ORDER BY date DESC",
                (f"{month}%",)
            ).fetchall()
        return self.conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()

    def get_summary(self, month=None):
        rows = self.get_transactions(month)
        income  = sum(r[3] for r in rows if r[1] == "income")
        expense = sum(r[3] for r in rows if r[1] == "expense")
        return income, expense, income - expense

    def get_category_totals(self, type_, month=None):
        if month:
            rows = self.conn.execute(
                "SELECT category, SUM(amount) FROM transactions WHERE type=? AND date LIKE ? GROUP BY category",
                (type_, f"{month}%")
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT category, SUM(amount) FROM transactions WHERE type=? GROUP BY category",
                (type_,)
            ).fetchall()
        return dict(rows)

    def set_budget(self, category, limit):
        self.conn.execute(
            "INSERT OR REPLACE INTO budgets (category, limit_amount) VALUES (?,?)",
            (category, limit)
        )
        self.conn.commit()

    def get_budgets(self):
        return dict(self.conn.execute("SELECT category, limit_amount FROM budgets").fetchall())


# ─── Reusable Widget: Stat Card ───────────────────────────────────────────────
class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value, icon, color, **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=16,
                         border_width=1, border_color=COLORS["border"], **kwargs)
        self.grid_columnconfigure(0, weight=1)

        icon_lbl = ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=28))
        icon_lbl.grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")

        self.val_lbl = ctk.CTkLabel(self, text=value,
                                     font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"),
                                     text_color=color)
        self.val_lbl.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=12),
                     text_color=COLORS["subtext"]).grid(row=2, column=0, padx=20, pady=(2, 16), sticky="w")

    def update_value(self, value):
        self.val_lbl.configure(text=value)


# ─── Screen: Dashboard ────────────────────────────────────────────────────────
class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, db: Database, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self.db = db
        self.grid_columnconfigure((0,1,2), weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, padx=24, pady=(24,8), sticky="ew")
        ctk.CTkLabel(header, text="💎 FinTrack Pro",
                     font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
                     text_color=COLORS["accent"]).pack(side="left")
        month = datetime.date.today().strftime("%B %Y")
        ctk.CTkLabel(header, text=month, font=ctk.CTkFont(size=14),
                     text_color=COLORS["subtext"]).pack(side="right", padx=8)

        # Stat Cards
        income, expense, balance = self.db.get_summary(datetime.date.today().strftime("%Y-%m"))
        color = COLORS["success"] if balance >= 0 else COLORS["danger"]

        self.card_income  = StatCard(self, "Total Income",  f"₹{income:,.2f}",  "📥", COLORS["income"])
        self.card_expense = StatCard(self, "Total Expenses", f"₹{expense:,.2f}", "📤", COLORS["expense"])
        self.card_balance = StatCard(self, "Net Balance",   f"₹{balance:,.2f}", "💰", color)

        self.card_income .grid(row=1, column=0, padx=(24,8), pady=8, sticky="ew")
        self.card_expense.grid(row=1, column=1, padx=8,      pady=8, sticky="ew")
        self.card_balance.grid(row=1, column=2, padx=(8,24), pady=8, sticky="ew")

        # Chart Area
        chart_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16,
                                   border_width=1, border_color=COLORS["border"])
        chart_frame.grid(row=2, column=0, columnspan=2, padx=(24,8), pady=(8,24), sticky="nsew")
        chart_frame.grid_rowconfigure(1, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chart_frame, text="📊 Expense Breakdown",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=20, pady=(16,4), sticky="w")
        self._build_pie(chart_frame)

        # Recent Transactions
        recent_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16,
                                    border_width=1, border_color=COLORS["border"])
        recent_frame.grid(row=2, column=2, padx=(8,24), pady=(8,24), sticky="nsew")
        recent_frame.grid_rowconfigure(1, weight=1)
        recent_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(recent_frame, text="🕐 Recent Activity",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=20, pady=(16,4), sticky="w")
        self._build_recent(recent_frame)

    def _build_pie(self, parent):
        cat_totals = self.db.get_category_totals("expense", datetime.date.today().strftime("%Y-%m"))
        fig = Figure(figsize=(5, 3.5), facecolor=COLORS["card"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(COLORS["card"])

        if cat_totals:
            labels = [k.split(" ", 1)[-1] for k in cat_totals]
            sizes  = list(cat_totals.values())
            palette = ["#00d4aa","#7c3aed","#f59e0b","#ef4444","#3b82f6",
                       "#ec4899","#10b981","#6366f1","#f97316"]
            wedge_props = {"linewidth": 2, "edgecolor": COLORS["card"]}
            ax.pie(sizes, labels=labels, colors=palette[:len(sizes)],
                   autopct="%1.0f%%", startangle=90,
                   wedgeprops=wedge_props,
                   textprops={"color": COLORS["text"], "fontsize": 9})
        else:
            ax.text(0.5, 0.5, "No expense data yet", ha="center", va="center",
                    color=COLORS["subtext"], fontsize=12, transform=ax.transAxes)
            ax.axis("off")

        fig.tight_layout(pad=1)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=10, pady=(0,16), sticky="nsew")

    def _build_recent(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        txns = self.db.get_transactions()[:10]
        if not txns:
            ctk.CTkLabel(scroll, text="No transactions yet\nAdd one to get started!",
                         text_color=COLORS["subtext"], justify="center").pack(pady=30)
            return

        for t in txns:
            _, type_, cat, amt, desc, date = t
            color = COLORS["income"] if type_ == "income" else COLORS["expense"]
            sign  = "+" if type_ == "income" else "-"
            row   = ctk.CTkFrame(scroll, fg_color=COLORS["card2"], corner_radius=10)
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text=cat.split(" ")[0], font=ctk.CTkFont(size=20)).grid(
                row=0, column=0, rowspan=2, padx=(12,8), pady=8)
            ctk.CTkLabel(row, text=cat.split(" ", 1)[-1] if " " in cat else cat,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="w", padx=4)
            ctk.CTkLabel(row, text=date, font=ctk.CTkFont(size=10),
                         text_color=COLORS["subtext"]).grid(row=1, column=1, sticky="w", padx=4)
            ctk.CTkLabel(row, text=f"{sign}₹{amt:,.0f}",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).grid(row=0, column=2, rowspan=2, padx=12)

    def refresh(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._build()


# ─── Screen: Add Transaction ──────────────────────────────────────────────────
class AddTransactionScreen(ctk.CTkFrame):
    def __init__(self, master, db: Database, on_success=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self.db = db
        self.on_success = on_success
        self.type_var = ctk.StringVar(value="expense")
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        # Title
        ctk.CTkLabel(self, text="➕ Add Transaction",
                     font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"),
                     text_color=COLORS["accent"]).grid(row=0, column=0, padx=32, pady=(32,8), sticky="w")

        # Card
        card = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=20,
                            border_width=1, border_color=COLORS["border"])
        card.grid(row=1, column=0, padx=32, pady=8, sticky="ew")
        card.grid_columnconfigure((0,1), weight=1)

        # Type Selector
        ctk.CTkLabel(card, text="Transaction Type", font=ctk.CTkFont(size=13),
                     text_color=COLORS["subtext"]).grid(row=0, column=0, columnspan=2, padx=24, pady=(24,4), sticky="w")

        seg = ctk.CTkSegmentedButton(card, values=["expense", "income"],
                                     variable=self.type_var,
                                     command=self._on_type_change,
                                     font=ctk.CTkFont(size=13, weight="bold"),
                                     selected_color=COLORS["accent2"],
                                     selected_hover_color=COLORS["accent"])
        seg.grid(row=1, column=0, columnspan=2, padx=24, pady=(0,16), sticky="ew")

        # Amount
        ctk.CTkLabel(card, text="Amount (₹)", font=ctk.CTkFont(size=13),
                     text_color=COLORS["subtext"]).grid(row=2, column=0, columnspan=2, padx=24, sticky="w")
        self.amount_entry = ctk.CTkEntry(card, placeholder_text="e.g. 1500",
                                          font=ctk.CTkFont(size=20, weight="bold"),
                                          height=50, corner_radius=12)
        self.amount_entry.grid(row=3, column=0, columnspan=2, padx=24, pady=(4,16), sticky="ew")

        # Category
        ctk.CTkLabel(card, text="Category", font=ctk.CTkFont(size=13),
                     text_color=COLORS["subtext"]).grid(row=4, column=0, columnspan=2, padx=24, sticky="w")
        self.cat_var = ctk.StringVar(value=CATEGORIES["expense"][0])
        self.cat_menu = ctk.CTkOptionMenu(card, variable=self.cat_var,
                                           values=CATEGORIES["expense"],
                                           height=42, corner_radius=12,
                                           fg_color=COLORS["card2"],
                                           button_color=COLORS["accent2"])
        self.cat_menu.grid(row=5, column=0, columnspan=2, padx=24, pady=(4,16), sticky="ew")

        # Description
        ctk.CTkLabel(card, text="Description (optional)", font=ctk.CTkFont(size=13),
                     text_color=COLORS["subtext"]).grid(row=6, column=0, columnspan=2, padx=24, sticky="w")
        self.desc_entry = ctk.CTkEntry(card, placeholder_text="e.g. Lunch at café",
                                        height=42, corner_radius=12)
        self.desc_entry.grid(row=7, column=0, columnspan=2, padx=24, pady=(4,16), sticky="ew")

        # Date
        ctk.CTkLabel(card, text="Date", font=ctk.CTkFont(size=13),
                     text_color=COLORS["subtext"]).grid(row=8, column=0, columnspan=2, padx=24, sticky="w")
        self.date_entry = ctk.CTkEntry(card, height=42, corner_radius=12)
        self.date_entry.insert(0, datetime.date.today().isoformat())
        self.date_entry.grid(row=9, column=0, columnspan=2, padx=24, pady=(4,24), sticky="ew")

        # Submit Button
        self.msg_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.msg_lbl.grid(row=2, column=0, pady=4)

        btn = ctk.CTkButton(self, text="💾  Save Transaction", height=52,
                            corner_radius=14, font=ctk.CTkFont(size=15, weight="bold"),
                            fg_color=COLORS["accent"], hover_color=COLORS["accent2"],
                            text_color="#000000", command=self._save)
        btn.grid(row=3, column=0, padx=32, pady=(4,32), sticky="ew")

    def _on_type_change(self, val):
        self.cat_var.set(CATEGORIES[val][0])
        self.cat_menu.configure(values=CATEGORIES[val])

    def _save(self):
        amt_str = self.amount_entry.get().strip()
        cat     = self.cat_var.get()
        desc    = self.desc_entry.get().strip()
        date    = self.date_entry.get().strip()
        type_   = self.type_var.get()

        if not amt_str:
            self._show_msg("⚠️ Please enter an amount.", COLORS["warning"])
            return
        try:
            amt = float(amt_str)
            if amt <= 0:
                raise ValueError
        except ValueError:
            self._show_msg("⚠️ Enter a valid positive number.", COLORS["warning"])
            return

        self.db.add_transaction(type_, cat, amt, desc, date)
        self._show_msg("✅ Transaction saved successfully!", COLORS["success"])
        self.amount_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        if self.on_success:
            self.on_success()

    def _show_msg(self, text, color):
        self.msg_lbl.configure(text=text, text_color=color)
        self.after(3000, lambda: self.msg_lbl.configure(text=""))


# ─── Screen: Transaction History ──────────────────────────────────────────────
class HistoryScreen(ctk.CTkFrame):
    def __init__(self, master, db: Database, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self.db = db
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24,8), sticky="ew")
        ctk.CTkLabel(header, text="📋 Transaction History",
                     font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"),
                     text_color=COLORS["accent"]).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["card"], corner_radius=16)
        scroll.grid(row=1, column=0, padx=24, pady=(0,24), sticky="nsew")
        scroll.grid_columnconfigure((0,1,2,3,4), weight=1)

        # Column Headers
        headers = ["Type", "Category", "Amount", "Description", "Date", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(scroll, text=h, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLORS["subtext"]).grid(row=0, column=i, padx=10, pady=(16,8), sticky="w")

        txns = self.db.get_transactions()
        if not txns:
            ctk.CTkLabel(scroll, text="No transactions yet.",
                         text_color=COLORS["subtext"]).grid(row=1, column=0, columnspan=6, pady=30)
            return

        for i, t in enumerate(txns, start=1):
            tid, type_, cat, amt, desc, date = t
            color = COLORS["income"] if type_ == "income" else COLORS["expense"]
            sign  = "+" if type_ == "income" else "-"
            bg    = COLORS["card2"] if i % 2 == 0 else COLORS["card"]

            row_frame = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=8, height=40)
            row_frame.grid(row=i, column=0, columnspan=6, padx=4, pady=2, sticky="ew")
            row_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

            badge_color = COLORS["income"] if type_ == "income" else COLORS["expense"]
            ctk.CTkLabel(row_frame, text=type_.upper(),
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=badge_color).grid(row=0, column=0, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(row_frame, text=cat, font=ctk.CTkFont(size=12)).grid(
                row=0, column=1, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(row_frame, text=f"{sign}₹{amt:,.2f}",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).grid(row=0, column=2, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(row_frame, text=desc or "—", font=ctk.CTkFont(size=11),
                         text_color=COLORS["subtext"]).grid(row=0, column=3, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(row_frame, text=date, font=ctk.CTkFont(size=11),
                         text_color=COLORS["subtext"]).grid(row=0, column=4, padx=8, pady=10, sticky="w")
            ctk.CTkButton(row_frame, text="🗑", width=32, height=28, corner_radius=8,
                          fg_color=COLORS["danger"], hover_color="#b91c1c",
                          command=lambda t=tid: self._delete(t)).grid(
                row=0, column=5, padx=8, pady=6)

    def _delete(self, tid):
        self.db.delete_transaction(tid)
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()


# ─── Screen: Analytics ────────────────────────────────────────────────────────
class AnalyticsScreen(ctk.CTkFrame):
    def __init__(self, master, db: Database, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self.db = db
        self.grid_columnconfigure((0,1), weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="📈 Analytics",
                     font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"),
                     text_color=COLORS["accent"]).grid(
            row=0, column=0, columnspan=2, padx=32, pady=(28,12), sticky="w")

        self._build_bar_chart()
        self._build_income_chart()

    def _build_bar_chart(self):
        frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16,
                             border_width=1, border_color=COLORS["border"])
        frame.grid(row=1, column=0, padx=(24,8), pady=(0,24), sticky="nsew")
        ctk.CTkLabel(frame, text="Monthly Spending by Category",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(16,4), anchor="w")

        cat_totals = self.db.get_category_totals("expense")
        fig = Figure(figsize=(5.5, 4), facecolor=COLORS["card"])
        ax  = fig.add_subplot(111, facecolor=COLORS["card"])

        if cat_totals:
            labels = [k.split(" ", 1)[-1] for k in cat_totals]
            values = list(cat_totals.values())
            bars = ax.barh(labels, values,
                           color=["#00d4aa","#7c3aed","#f59e0b","#ef4444",
                                  "#3b82f6","#ec4899","#10b981","#6366f1","#f97316"],
                           height=0.55, edgecolor="none")
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + max(values)*0.01, bar.get_y() + bar.get_height()/2,
                        f"₹{val:,.0f}", va="center", color=COLORS["text"], fontsize=9)
            ax.set_xlim(0, max(values) * 1.25)
        else:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    color=COLORS["subtext"], fontsize=12, transform=ax.transAxes)

        ax.tick_params(colors=COLORS["text"], labelsize=9)
        ax.spines[:].set_visible(False)
        ax.set_xlabel("Amount (₹)", color=COLORS["subtext"], fontsize=9)
        ax.xaxis.set_tick_params(colors=COLORS["subtext"])
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=(0,16), fill="both", expand=True)

    def _build_income_chart(self):
        frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16,
                             border_width=1, border_color=COLORS["border"])
        frame.grid(row=1, column=1, padx=(8,24), pady=(0,24), sticky="nsew")
        ctk.CTkLabel(frame, text="Income vs Expense Summary",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(16,4), anchor="w")

        income, expense, _ = self.db.get_summary()
        fig = Figure(figsize=(5, 4), facecolor=COLORS["card"])
        ax  = fig.add_subplot(111, facecolor=COLORS["card"])

        labels = ["Income", "Expense"]
        values = [income, expense]
        colors = [COLORS["income"], COLORS["expense"]]

        if income > 0 or expense > 0:
            bars = ax.bar(labels, values, color=colors, width=0.4,
                          edgecolor="none", zorder=3)
            ax.bar_label(bars, fmt="₹%.0f", padding=6,
                         color=COLORS["text"], fontsize=11, fontweight="bold")
            ax.set_ylim(0, max(values) * 1.3 if max(values) > 0 else 1)
        else:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    color=COLORS["subtext"], fontsize=12, transform=ax.transAxes)

        ax.tick_params(colors=COLORS["text"], labelsize=10)
        ax.spines[:].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=COLORS["border"], linewidth=0.5, zorder=0)
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=(0,16), fill="both", expand=True)

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()


# ─── Main Application ──────────────────────────────────────────────────────────
class FinTrackApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("💎 FinTrack Pro")
        self.geometry("1100x720")
        self.minsize(900, 620)
        self.configure(fg_color=COLORS["bg"])

        self.db = Database()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()
        self.show_screen("dashboard")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=COLORS["card"], width=220,
                               corner_radius=0, border_width=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(32,24), sticky="ew")
        ctk.CTkLabel(logo_frame, text="💎", font=ctk.CTkFont(size=32)).pack(side="left")
        ctk.CTkLabel(logo_frame, text="FinTrack\nPro",
                     font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
                     text_color=COLORS["accent"], justify="left").pack(side="left", padx=8)

        # Nav Buttons
        nav_items = [
            ("dashboard",    "🏠", "Dashboard"),
            ("add",          "➕", "Add Transaction"),
            ("history",      "📋", "History"),
            ("analytics",    "📈", "Analytics"),
        ]
        self.nav_buttons = {}
        for i, (key, icon, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                sidebar, text=f"  {icon}  {label}", anchor="w",
                font=ctk.CTkFont(size=14), height=46, corner_radius=12,
                fg_color="transparent", hover_color=COLORS["card2"],
                text_color=COLORS["text"],
                command=lambda k=key: self.show_screen(k)
            )
            btn.grid(row=i, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        # Footer
        ctk.CTkLabel(sidebar, text="Made with ❤️ in Python",
                     font=ctk.CTkFont(size=10), text_color=COLORS["subtext"]).grid(
            row=9, column=0, padx=16, pady=20, sticky="s")

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.screens = {
            "dashboard": DashboardScreen(self.content, self.db),
            "add":       AddTransactionScreen(self.content, self.db, on_success=self._on_add),
            "history":   HistoryScreen(self.content, self.db),
            "analytics": AnalyticsScreen(self.content, self.db),
        }
        for s in self.screens.values():
            s.grid(row=0, column=0, sticky="nsew")

    def show_screen(self, name):
        self.screens[name].tkraise()
        for key, btn in self.nav_buttons.items():
            btn.configure(
                fg_color=COLORS["accent2"] if key == name else "transparent",
                text_color=COLORS["text"]
            )

    def _on_add(self):
        self.screens["dashboard"].refresh()
        self.screens["history"].refresh()
        self.screens["analytics"].refresh()


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = FinTrackApp()
    app.mainloop()
