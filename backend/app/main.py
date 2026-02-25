"""
Career26: Turn almost any dataset into people and insights.
Data in (CSV, Excel, paste) → extract people. Runs on Mac, Linux, Windows.
"""
from __future__ import annotations

import os
import sys
import threading
import typing
from pathlib import Path
from tkinter import filedialog

# Project root and Career26 assets
_ROOT = Path(__file__).resolve().parent.parent
_APP_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _APP_DIR / "assets"
_LOGO_PATH = _ASSETS_DIR / "career26_logo.png"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import customtkinter as ctk

# Modern dark theme: deeper contrast, clearer hierarchy
_THEME = {
    "bg": "#0f0f0f",
    "bg_raised": "#141414",
    "sidebar": "#0a0a0a",
    "sidebar_border": "#1e293b",
    "card": "#18181b",
    "card_border": "#27272a",
    "input_bg": "#09090b",
    "accent": "#3b82f6",
    "accent_hover": "#60a5fa",
    "accent_subtle": "#1e3a5f",
    "danger": "#dc2626",
    "danger_hover": "#ef4444",
    "text": "#fafafa",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "radius": 10,
    "radius_sm": 8,
}

def _nav_btn(parent: ctk.CTkFrame, label: str, command: "typing.Callable[[], None]", selected: bool = False) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=label,
        command=command,
        anchor="w",
        height=40,
        corner_radius=_THEME["radius_sm"],
        fg_color=_THEME["accent_subtle"] if selected else "transparent",
        hover_color=_THEME["accent"] if selected else _THEME["card"],
        text_color=_THEME["text"] if selected else _THEME["text_secondary"],
        font=ctk.CTkFont(size=13),
    )


def _card(parent: ctk.CTkFrame, **kwargs: "typing.Any") -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=_THEME["card"],
        corner_radius=_THEME["radius"],
        border_width=1,
        border_color=_THEME["card_border"],
        **kwargs,
    )


def _card_label(parent: ctk.CTkFrame, text: str, row: int, col: int = 0) -> None:
    ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"]).grid(row=row, column=col, sticky="w", padx=20, pady=(0, 6))

_NAV = [
    ("data_people", "Data → People"),
    ("email", "Find email"),
    ("search", "Search people"),
    ("settings", "Settings"),
]


class VanguardApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Career26")
        self.geometry("980x640")
        self.minsize(800, 520)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=_THEME["bg"])
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar — Career26 branding and logo
        sidebar = ctk.CTkFrame(self, width=200, fg_color=_THEME["sidebar"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(5, weight=1)
        _logo_widget = self._build_logo_widget(sidebar)
        _logo_widget.grid(row=0, column=0, padx=20, pady=(24, 8), sticky="w")
        ctk.CTkLabel(
            sidebar,
            text="Turn data into people\nand insights.",
            font=ctk.CTkFont(size=11),
            text_color=_THEME["text_muted"],
        ).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        self._nav_buttons = []
        self._pages = {}
        for i, (key, label) in enumerate(_NAV):
            btn = _nav_btn(sidebar, label, lambda k=key: self._show_page(k), selected=(i == 0))
            btn.grid(row=2 + i, column=0, padx=12, pady=4, sticky="ew")
            sidebar.grid_columnconfigure(0, weight=1)
            self._nav_buttons.append(btn)
        self._current_page = "data_people"

        # Separator between sidebar and content
        sep = ctk.CTkFrame(self, width=1, fg_color=_THEME["sidebar_border"])
        sep.grid(row=0, column=1, sticky="nswe")

        # Main content
        main = ctk.CTkFrame(self, fg_color=_THEME["bg"], corner_radius=0)
        main.grid(row=0, column=2, sticky="nswe", padx=0, pady=0)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # Content area (stacked pages)
        content_stack = ctk.CTkFrame(main, fg_color="transparent")
        content_stack.grid(row=1, column=0, sticky="nswe", padx=32, pady=28)
        content_stack.grid_columnconfigure(0, weight=1)
        content_stack.grid_rowconfigure(0, weight=1)

        # ---- Tab 1: Data → People ----
        tab_data = ctk.CTkFrame(content_stack, fg_color="transparent")
        tab_data.grid(row=0, column=0, sticky="nswe")
        tab_data.grid_columnconfigure(0, weight=1)
        tab_data.grid_rowconfigure(2, weight=1)
        self._pages["data_people"] = tab_data
        ctk.CTkLabel(tab_data, text="Data → People", font=ctk.CTkFont(size=20, weight="bold"), text_color=_THEME["text"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(tab_data, text="Upload CSV, PDF, or Excel. We extract companies, then find relevant people (names, credentials) by your search parameters.", font=ctk.CTkFont(size=13), text_color=_THEME["text_secondary"]).grid(row=1, column=0, sticky="w", pady=(0, 20))
        card_dp = _card(tab_data)
        card_dp.grid(row=2, column=0, sticky="nswe", pady=(0, 12))
        card_dp.grid_columnconfigure(0, weight=1)
        card_dp.grid_rowconfigure(5, weight=1)
        row_dp1 = ctk.CTkFrame(card_dp, fg_color="transparent")
        row_dp1.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        row_dp1.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(row_dp1, text="Choose file", width=120, height=36, command=self._on_data_choose_file, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(0, 10))
        self.data_file_label = ctk.CTkLabel(row_dp1, text="No file chosen (CSV, PDF, Excel)", text_color=_THEME["text_muted"], font=ctk.CTkFont(size=12))
        self.data_file_label.grid(row=0, column=1, sticky="w")
        self.data_file_path: Path | None = None
        _card_label(card_dp, "Job titles / roles to search for (comma-separated)", 1)
        self.data_job_titles_entry = ctk.CTkEntry(card_dp, placeholder_text="e.g. Director, Partner, VP Sales", height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1)
        self.data_job_titles_entry.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        row_dp_btn = ctk.CTkFrame(card_dp, fg_color="transparent")
        row_dp_btn.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 12))
        ctk.CTkButton(row_dp_btn, text="Load & extract companies", command=self._on_data_load, width=180, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(row_dp_btn, text="Find people at companies", command=self._on_data_find_people, width=180, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(row_dp_btn, text="Export CSV", command=self._on_data_export_csv, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["card_border"], hover_color=_THEME["text_muted"], text_color=_THEME["text_secondary"], font=ctk.CTkFont(size=12)).grid(row=0, column=2)
        self.data_companies_text = ctk.CTkTextbox(card_dp, height=100, font=ctk.CTkFont(size=12), wrap="word", corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, text_color=_THEME["text"])
        self.data_companies_text.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.data_results_text = ctk.CTkTextbox(card_dp, font=ctk.CTkFont(size=12), wrap="word", corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, text_color=_THEME["text"])
        self.data_results_text.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.data_companies_list: list[str] = []
        self.data_loaded_rows: list[dict] = []
        self.data_people_results: list[dict] = []

        # ---- Tab 2: Find email ----
        tab_e = ctk.CTkFrame(content_stack, fg_color="transparent")
        tab_e.grid(row=0, column=0, sticky="nswe")
        tab_e.grid_columnconfigure(0, weight=1)
        tab_e.grid_rowconfigure(2, weight=1)
        self._pages["email"] = tab_e
        tab_e.grid_remove()
        ctk.CTkLabel(tab_e, text="Find email", font=ctk.CTkFont(size=20, weight="bold"), text_color=_THEME["text"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(tab_e, text="Name + company (or domain). Anymail API with web-search style resolution: we resolve company to domain and show steps.", font=ctk.CTkFont(size=13), text_color=_THEME["text_secondary"]).grid(row=1, column=0, sticky="w", pady=(0, 20))
        card_e = _card(tab_e)
        card_e.grid(row=2, column=0, sticky="nswe", pady=(0, 12))
        card_e.grid_columnconfigure(1, weight=1)
        card_e.grid_rowconfigure(3, weight=1)
        f1 = ctk.CTkFrame(card_e, fg_color="transparent")
        f1.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 12))
        f1.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(f1, text="Full name", font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"]).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
        self.email_name_entry = ctk.CTkEntry(f1, placeholder_text="e.g. Jane Smith", height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1)
        self.email_name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(f1, text="Company or domain", font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"]).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
        self.email_company_entry = ctk.CTkEntry(f1, placeholder_text="e.g. Acme Ltd or acme.com", height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1)
        self.email_company_entry.grid(row=1, column=1, sticky="ew", pady=(0, 12))
        self.email_resolve_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f1, text="Resolve company to domain (web search; suggests similar if ambiguous)", variable=self.email_resolve_var, text_color=_THEME["text"], font=ctk.CTkFont(size=12)).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.find_email_btn = ctk.CTkButton(card_e, text="Find email", command=self._on_find_email, width=120, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12))
        self.find_email_btn.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))
        ctk.CTkLabel(card_e, text="Log (steps and result)", font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"]).grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 4))
        self.email_result_text = ctk.CTkTextbox(card_e, height=180, font=ctk.CTkFont(size=12), wrap="word", corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, text_color=_THEME["text"])
        self.email_result_text.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=(0, 20))

        # ---- Tab 3: Search people (LLM-assisted) ----
        tab_search = ctk.CTkFrame(content_stack, fg_color="transparent")
        tab_search.grid(row=0, column=0, sticky="nswe")
        tab_search.grid_columnconfigure(0, weight=1)
        tab_search.grid_rowconfigure(2, weight=1)
        self._pages["search"] = tab_search
        tab_search.grid_remove()
        ctk.CTkLabel(tab_search, text="Search people", font=ctk.CTkFont(size=20, weight="bold"), text_color=_THEME["text"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(tab_search, text="Natural language: e.g. \"IB bankers in London who work for Goldman\". We use an LLM to improve the query, then return people and emails.", font=ctk.CTkFont(size=13), text_color=_THEME["text_secondary"]).grid(row=1, column=0, sticky="w", pady=(0, 20))
        card_search = _card(tab_search)
        card_search.grid(row=2, column=0, sticky="nswe", pady=(0, 12))
        card_search.grid_columnconfigure(0, weight=1)
        card_search.grid_rowconfigure(2, weight=1)
        self.search_query_entry = ctk.CTkEntry(card_search, placeholder_text="e.g. IB bankers in London who work for Goldman Sachs", height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, font=ctk.CTkFont(size=12))
        self.search_query_entry.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        self.search_use_llm_var = ctk.BooleanVar(value=True)
        row_sb = ctk.CTkFrame(card_search, fg_color="transparent")
        row_sb.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))
        ctk.CTkCheckBox(row_sb, text="Use LLM to improve search query", variable=self.search_use_llm_var, text_color=_THEME["text"], font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(0, 12))
        self.search_btn = ctk.CTkButton(row_sb, text="Search", command=self._on_search_people, width=100, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12))
        self.search_btn.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(row_sb, text="Export CSV", command=self._on_search_export_csv, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["card_border"], hover_color=_THEME["text_muted"], text_color=_THEME["text_secondary"], font=ctk.CTkFont(size=12)).grid(row=0, column=2)
        self.search_results_text = ctk.CTkTextbox(card_search, font=ctk.CTkFont(size=12), corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, text_color=_THEME["text"])
        self.search_results_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.search_people_data: list[dict] = []

        # ---- Page: Settings ----
        _API_KEYS = ("SERPAPI_KEY", "OPENAI_API_KEY", "ANYMAIL_API_KEY", "HUNTER_API_KEY")
        tab_cfg = ctk.CTkFrame(content_stack, fg_color="transparent")
        tab_cfg.grid(row=0, column=0, sticky="nswe")
        tab_cfg.grid_columnconfigure(0, weight=1)
        self._pages["settings"] = tab_cfg
        tab_cfg.grid_remove()
        ctk.CTkLabel(tab_cfg, text="Settings", font=ctk.CTkFont(size=20, weight="bold"), text_color=_THEME["text"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(tab_cfg, text="API keys for search, LLM, and email. Stored in .env; leave blank to keep current values.", font=ctk.CTkFont(size=13), text_color=_THEME["text_secondary"]).grid(row=1, column=0, sticky="w", pady=(0, 20))
        card_cfg = _card(tab_cfg)
        card_cfg.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        card_cfg.grid_columnconfigure(1, weight=1)
        self.settings_entries = {}
        for i, key in enumerate(_API_KEYS):
            ctk.CTkLabel(card_cfg, text=key, font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"]).grid(row=i, column=0, sticky="w", padx=(20, 12), pady=(20 if i == 0 else 12, 0))
            entry = ctk.CTkEntry(card_cfg, show="•", height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["input_bg"], border_width=1, placeholder_text="•••••••• (saved)" if os.environ.get(key) else "Not set")
            entry.grid(row=i, column=1, sticky="ew", padx=(0, 20), pady=(20 if i == 0 else 12, 0))
            self.settings_entries[key] = entry
        save_btn_row = ctk.CTkFrame(card_cfg, fg_color="transparent")
        save_btn_row.grid(row=len(_API_KEYS), column=0, columnspan=2, sticky="w", padx=20, pady=20)
        ctk.CTkButton(save_btn_row, text="Save", command=self._on_save_settings, width=100, height=36, corner_radius=_THEME["radius_sm"], fg_color=_THEME["accent"], hover_color=_THEME["accent_hover"], font=ctk.CTkFont(size=12)).grid(row=0, column=0)
        self.settings_status_label = ctk.CTkLabel(save_btn_row, text="", font=ctk.CTkFont(size=12), text_color=_THEME["text_muted"])
        self.settings_status_label.grid(row=0, column=1, padx=(12, 0), sticky="w")

        self._show_page("data_people")

    def _build_logo_widget(self, parent: ctk.CTkFrame) -> ctk.CTkLabel:
        """Career26 logo: image from assets if present, else wordmark text."""
        if _LOGO_PATH.exists():
            try:
                self._logo_image = ctk.CTkImage(
                    light_image=str(_LOGO_PATH),
                    dark_image=str(_LOGO_PATH),
                    size=(140, 36),
                )
                return ctk.CTkLabel(parent, text="", image=self._logo_image)
            except Exception:
                pass
        return ctk.CTkLabel(
            parent, text="Career26", font=ctk.CTkFont(size=17, weight="bold"), text_color=_THEME["text"]
        )

    def _show_page(self, key: str) -> None:
        for k, frame in self._pages.items():
            if k == key:
                frame.grid()
            else:
                frame.grid_remove()
        for i, (k, _) in enumerate(_NAV):
            self._nav_buttons[i].configure(
                fg_color=_THEME["accent_subtle"] if k == key else "transparent",
                text_color=_THEME["text"] if k == key else _THEME["text_secondary"],
                hover_color=_THEME["accent"] if k == key else _THEME["card"],
            )
        self._current_page = key

    def _on_data_choose_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV/PDF/Excel", "*.csv *.pdf *.xlsx *.xls"), ("CSV", "*.csv"), ("PDF", "*.pdf"), ("Excel", "*.xlsx *.xls"), ("All", "*")])
        if path:
            self.data_file_path = Path(path)
            self.data_file_label.configure(text=path)

    def _on_data_load(self) -> None:
        if not self.data_file_path:
            self.data_companies_text.delete("1.0", "end")
            self.data_companies_text.insert("end", "Choose a file first (CSV, PDF, or Excel).\n")
            return
        self.data_companies_text.delete("1.0", "end")
        self.data_companies_text.insert("end", "Loading…\n")
        self.update_idletasks()
        path = self.data_file_path

        def do() -> None:
            from app.services import load_file_any, extract_companies_from_rows
            rows, cols, err = load_file_any(path)
            def show() -> None:
                self.data_companies_text.delete("1.0", "end")
                if err:
                    self.data_companies_text.insert("end", f"Error: {err}\n")
                    return
                self.data_loaded_rows = rows
                companies = extract_companies_from_rows(rows)
                self.data_companies_list = companies
                self.data_companies_text.insert("end", f"Loaded {len(rows)} rows. Extracted {len(companies)} companies:\n\n")
                for c in companies[:100]:
                    self.data_companies_text.insert("end", c + "\n")
                if len(companies) > 100:
                    self.data_companies_text.insert("end", f"... and {len(companies) - 100} more.\n")
                self.data_companies_text.insert("end", "\nSet job titles above and click \"Find people at companies\".\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_data_find_people(self) -> None:
        if not self.data_companies_list:
            self.data_results_text.delete("1.0", "end")
            self.data_results_text.insert("end", "Load a file and extract companies first.\n")
            return
        job_titles_str = (self.data_job_titles_entry.get() or "").strip()
        job_titles = [t.strip() for t in job_titles_str.split(",") if t.strip()] if job_titles_str else ["Director", "Partner"]
        self.data_results_text.delete("1.0", "end")
        self.data_results_text.insert("end", f"Finding people at {len(self.data_companies_list)} companies (roles: {', '.join(job_titles)})…\n\n")
        self.update_idletasks()
        companies = self.data_companies_list[:30]
        titles = job_titles[:3]

        def do() -> None:
            from app.services import find_people_at_companies
            results = find_people_at_companies(companies, titles, max_per_company=5, find_emails=True)
            def show() -> None:
                self.data_people_results = results
                self.data_results_text.delete("1.0", "end")
                self.data_results_text.insert("end", f"Found {len(results)} people.\n\n")
                if results:
                    self.data_results_text.insert("end", "Name\tTitle\tCompany\tEmail\tConfidence\n")
                    for r in results:
                        self.data_results_text.insert("end", f"{r.get('name','')}\t{r.get('title','')}\t{r.get('company','')}\t{r.get('email','')}\t{r.get('confidence',0):.0%}\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_data_export_csv(self) -> None:
        if not self.data_people_results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        self.data_results_text.insert("end", "Exporting…\n")
        self.update_idletasks()
        data, cols = self.data_people_results, ["name", "title", "company", "email", "confidence", "link"]

        def do() -> None:
            from app.services import export_results_csv
            err = export_results_csv(data, path, cols)
            def show() -> None:
                if err:
                    self.data_results_text.insert("end", f"Export error: {err}\n")
                else:
                    self.data_results_text.insert("end", f"Exported to {path}\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_save_settings(self) -> None:
        _API_KEYS = ("SERPAPI_KEY", "OPENAI_API_KEY", "ANYMAIL_API_KEY", "HUNTER_API_KEY")
        values = {k: (self.settings_entries[k].get() or "").strip() for k in _API_KEYS}
        for k, val in values.items():
            if val:
                os.environ[k] = val
        self.settings_status_label.configure(text="Saving…")
        self.update_idletasks()

        def do() -> None:
            from app.services import save_env_keys
            save_env_keys(_ROOT / ".env", _API_KEYS, lambda k: values.get(k, ""))
            def show() -> None:
                for key in _API_KEYS:
                    self.settings_entries[key].delete(0, "end")
                    self.settings_entries[key].configure(placeholder_text="•••••••• (saved)" if os.environ.get(key) else "Not set")
                self.settings_status_label.configure(text="Saved.")
                self.after(2000, lambda: self.settings_status_label.configure(text="") if self.settings_status_label.winfo_exists() else None)
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_find_email(self) -> None:
        name = (self.email_name_entry.get() or "").strip()
        company = (self.email_company_entry.get() or "").strip()
        self.email_result_text.delete("1.0", "end")
        if not name or not company:
            self.email_result_text.insert("end", "Enter full name and company (or domain).\n")
            return
        self.find_email_btn.configure(state="disabled")
        self.email_result_text.insert("end", "Searching…\n")
        self.update_idletasks()
        resolve_domain = self.email_resolve_var.get()

        def do() -> None:
            from app.services import find_email_with_log
            email, conf, log_lines, suggestions = find_email_with_log(name, company, resolve_domain=resolve_domain)
            def show() -> None:
                self.find_email_btn.configure(state="normal")
                self.email_result_text.delete("1.0", "end")
                for line in log_lines:
                    self.email_result_text.insert("end", line + "\n")
                if email:
                    self.email_result_text.insert("end", f"\n→ Email: {email} (confidence {conf:.0%})\n")
                if suggestions:
                    self.email_result_text.insert("end", "\nOther options: " + ", ".join(s[0] for s in suggestions) + "\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_search_people(self) -> None:
        q = (self.search_query_entry.get() or "").strip()
        self.search_results_text.delete("1.0", "end")
        if not q:
            self.search_results_text.insert("end", "Enter a natural-language search (e.g. IB bankers in London who work for Goldman).\n")
            return
        self.search_btn.configure(state="disabled")
        self.search_results_text.insert("end", f"Query: {q}\n")
        if self.search_use_llm_var.get():
            self.search_results_text.insert("end", "Improving query with LLM…\n")
        self.search_results_text.insert("end", "Searching…\n\n")
        self.update_idletasks()
        use_llm = self.search_use_llm_var.get()

        def do() -> None:
            from app.services import llm_enhance_search_query, people_search
            query = llm_enhance_search_query(q) if use_llm else q
            results = people_search(query, max_results=15, find_emails=True)
            def show() -> None:
                self.search_btn.configure(state="normal")
                self.search_people_data = results
                self.search_results_text.delete("1.0", "end")
                if use_llm and query != q:
                    self.search_results_text.insert("end", f"Improved query: \"{query}\"\n\n")
                self.search_results_text.insert("end", f"Found {len(results)} people.\n\n")
                if results:
                    self.search_results_text.insert("end", "Name\tTitle\tCompany\tEmail\tConfidence\n")
                    for r in results:
                        self.search_results_text.insert("end", f"{r.get('name','')}\t{r.get('title','')}\t{r.get('company','')}\t{r.get('email','')}\t{r.get('confidence',0):.0%}\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()

    def _on_search_export_csv(self) -> None:
        if not self.search_people_data:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        self.search_results_text.insert("end", "Exporting…\n")
        self.update_idletasks()
        data = self.search_people_data
        cols = ["name", "title", "company", "email", "confidence", "link"]

        def do() -> None:
            from app.services import export_results_csv
            err = export_results_csv(data, path, cols)
            def show() -> None:
                if err:
                    self.search_results_text.insert("end", f"Export error: {err}\n")
                else:
                    self.search_results_text.insert("end", f"Exported to {path}\n")
            self.after(0, show)
        threading.Thread(target=do, daemon=True).start()


def main() -> None:
    app = VanguardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
