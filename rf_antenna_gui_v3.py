import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from math import log10, sqrt, pi, cos, sin
import json, os, time
from dataclasses import dataclass, asdict

# -----------------------------
# Optional matplotlib support
# -----------------------------
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

# -----------------------------
# Files
# -----------------------------
SETTINGS_FILE = "calculator_settings.json"
HISTORY_FILE = "calc_history.json"

# -----------------------------
# Databases
# -----------------------------
COAX_DB = {
    "RG-58":   {50: 1.9, 150: 3.8, 450: 7.0, 900: 10.3, 1500: 13.5},
    "RG-213":  {50: 0.7, 150: 1.4, 450: 2.6, 900: 3.9, 1500: 5.1},
    "LMR-240": {50: 0.6, 150: 1.3, 450: 2.7, 900: 4.1, 1500: 5.4},
    "LMR-400": {50: 0.3, 150: 0.7, 450: 1.5, 900: 2.3, 1500: 3.0},
    "LMR-600": {50: 0.2, 150: 0.5, 450: 1.1, 900: 1.7, 1500: 2.2},
}

CONNECTOR_LOSS_DB = {
    "None": 0.0,
    "PL-259/SO-239": 0.15,
    "N-Type": 0.05,
    "BNC": 0.10,
    "SMA": 0.08,
}

COAX_VF_DB = {
    "RG-58": 0.66,
    "RG-213": 0.66,
    "LMR-240": 0.84,
    "LMR-400": 0.85,
    "LMR-600": 0.87,
}

MATERIAL_VF = {"Copper": 0.95, "Aluminum": 0.94, "Steel": 0.90, "Iron": 0.88}

# -----------------------------
# History record
# -----------------------------
@dataclass
class CalcRecord:
    timestamp: float
    category: str
    title: str
    inputs: dict
    outputs: dict

# -----------------------------
# Main App
# -----------------------------
class RFAntennaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Professional RF + Antenna Toolkit")
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)

        self.settings = self.load_settings()
        self.dark_mode = self.settings.get("dark_mode", True)
        self.unit_system = self.settings.get("unit_system", "metric")
        self.history = self.load_history()

        self.setup_styles()
        self.create_widgets()
        self.apply_theme()

    # -----------------------------
    # Settings / history
    # -----------------------------
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    return [CalcRecord(**d) for d in data]
            except:
                return []
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump([asdict(r) for r in self.history], f, indent=2)

    def add_history(self, category, title, inputs, outputs):
        self.history.append(CalcRecord(time.time(), category, title, inputs, outputs))
        self.save_history()
        self.refresh_history_tab()

    # -----------------------------
    # Theme
    # -----------------------------
    def setup_styles(self):
        self.light_bg = "#f0f0f0"
        self.light_fg = "#000000"
        self.light_entry_bg = "#ffffff"
        self.dark_bg = "#1f1f1f"
        self.dark_fg = "#e6e6e6"
        self.dark_entry_bg = "#2a2a2a"
        self.accent = "#0078d4"

    def apply_theme(self):
        bg = self.dark_bg if self.dark_mode else self.light_bg
        fg = self.dark_fg if self.dark_mode else self.light_fg
        entry_bg = self.dark_entry_bg if self.dark_mode else self.light_entry_bg

        self.root.config(bg=bg)
        self.update_widget_colors(self.root, bg, fg, entry_bg)

    def update_widget_colors(self, widget, bg, fg, entry_bg):
        try:
            if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                widget.config(bg=bg)
            elif isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton)):
                widget.config(bg=bg, fg=fg)
            elif isinstance(widget, (tk.Entry, tk.Text, tk.Canvas)):
                try:
                    widget.config(bg=entry_bg, fg=fg, insertbackground=fg)
                except:
                    widget.config(bg=entry_bg)

            for child in widget.winfo_children():
                self.update_widget_colors(child, bg, fg, entry_bg)
        except:
            pass

    # -----------------------------
    # UI setup
    # -----------------------------
    def create_widgets(self):
        header = tk.Frame(self.root, bg=self.accent)
        header.pack(side=tk.TOP, fill=tk.X)

        tk.Label(
            header,
            text="Professional RF + Antenna Toolkit",
            font=("Arial", 16, "bold"),
            bg=self.accent,
            fg="white",
        ).pack(side=tk.LEFT, padx=20, pady=10)

        self.dark_mode_btn = tk.Button(
            header,
            text="☀ Light Mode" if self.dark_mode else "🌙 Dark Mode",
            command=self.toggle_dark_mode,
            bg=self.accent,
            fg="white",
        )
        self.dark_mode_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        unit_frame = tk.Frame(header, bg=self.accent)
        unit_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        tk.Label(unit_frame, text="Units:", bg=self.accent, fg="white").pack(side=tk.LEFT, padx=5)
        self.unit_var = tk.StringVar(value=self.unit_system)
        unit_combo = ttk.Combobox(unit_frame, textvariable=self.unit_var,
                                  values=["metric", "imperial"], state="readonly", width=10)
        unit_combo.pack(side=tk.LEFT)
        unit_combo.bind("<<ComboboxSelected>>", lambda e: self.change_units())

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.rf_tab = tk.Frame(self.notebook)
        self.friis_tab = tk.Frame(self.notebook)
        self.fresnel_tab = tk.Frame(self.notebook)
        self.coax_tab = tk.Frame(self.notebook)
        self.smith_tab = tk.Frame(self.notebook)
        self.ant_tab = tk.Frame(self.notebook)
        self.pattern_tab = tk.Frame(self.notebook)
        self.history_tab = tk.Frame(self.notebook)

        self.notebook.add(self.rf_tab, text="RF Link Budget")
        self.notebook.add(self.friis_tab, text="Friis Noise Figure")
        self.notebook.add(self.fresnel_tab, text="Fresnel Zone / LOS")
        self.notebook.add(self.coax_tab, text="Coax / Connector Loss")
        self.notebook.add(self.smith_tab, text="Smith / SWR / Match")
        self.notebook.add(self.ant_tab, text="Antenna Calculator")
        self.notebook.add(self.pattern_tab, text="Radiation Patterns")
        self.notebook.add(self.history_tab, text="History / Export")

        self.create_rf_tab()
        self.create_friis_tab()
        self.create_fresnel_tab()
        self.create_coax_tab()
        self.create_smith_tab()     # Option B fallback built-in
        self.create_antenna_tab()
        self.create_pattern_tab()
        self.create_history_tab()

    # -----------------------------
    # Conversions
    # -----------------------------
    def freqToMhz(self, value, unit):
        u = unit.lower()
        if u == "hz": return value / 1e6
        if u in ["khz", "k"]: return value / 1e3
        if u in ["mhz", "m"]: return value
        if u in ["ghz", "g"]: return value * 1e3
        return value

    def freqToHz(self, value, unit):
        u = unit.lower()
        if u == "hz": return value
        if u in ["khz", "k"]: return value * 1e3
        if u in ["mhz", "m"]: return value * 1e6
        if u in ["ghz", "g"]: return value * 1e9
        return value

    def distToKm(self, value, unit):
        u = unit.lower()
        if u == "km": return value
        if u == "m": return value / 1000.0
        if u == "mi": return value * 1.609344
        if u == "ft": return value / 3280.84
        return value

    def powerToDbm(self, value, unit):
        u = unit.lower()
        if u == "dbm": return value
        if u == "w": return 10 * log10(value * 1000.0) if value > 0 else -300
        if u == "mw": return 10 * log10(value) if value > 0 else -300
        return value

    def dbmToWatts(self, dbm):
        return 10 ** ((dbm - 30) / 10)

    def formatLength(self, meters):
        if self.unit_system == "metric":
            if meters >= 1: return f"{meters:.4f} m"
            if meters >= 0.01: return f"{meters * 100:.4f} cm"
            return f"{meters * 1000:.4f} mm"
        else:
            feet = meters * 3.28084
            inches = meters * 39.3701
            if feet >= 1: return f"{feet:.4f} ft"
            return f"{inches:.4f} in"

    def formatWatts(self, watts):
        if watts >= 1: return f"{watts:.3f} W"
        if watts >= 1e-3: return f"{watts*1e3:.3f} mW"
        if watts >= 1e-6: return f"{watts*1e6:.3f} µW"
        if watts >= 1e-9: return f"{watts*1e9:.3f} nW"
        return f"{watts:.3e} W"

    # -----------------------------
    # RF math
    # -----------------------------
    def fspl(self, distanceKm, freqMhz):
        if distanceKm <= 0 or freqMhz <= 0:
            raise ValueError("Distance and frequency must be positive.")
        return 20 * log10(distanceKm) + 20 * log10(freqMhz) + 32.44

    def wavelengthMeters(self, freqHz):
        c = 299792458.0
        if freqHz <= 0:
            raise ValueError("Frequency must be positive.")
        return c / freqHz

    # -----------------------------
    # Antenna helpers
    # -----------------------------
    def velocityFactor(self, material):
        return MATERIAL_VF.get(material, 0.95)

    def yagiLengths(self, lam, elements, vf):
        reflector = lam * 0.53 * vf
        driven = lam * 0.50 * vf
        directors = []
        if elements >= 3:
            ndir = elements - 2
            for i in range(ndir):
                frac = 0.48 - (0.01 * i)
                if frac < 0.44:
                    frac = 0.44
                directors.append(lam * frac * vf)
        return reflector, driven, directors

    def yagiSpacing(self, lam, elements):
        if elements < 3:
            raise ValueError("Yagi requires at least 3 elements.")
        spacings = [0.20 * lam, 0.15 * lam]
        for _ in range(elements - 3):
            spacings.append(0.15 * lam)
        return spacings, sum(spacings)

    # -----------------------------
    # Coax loss interpolation
    # -----------------------------
    def coax_loss_db_per_100ft(self, coax_type, freq_mhz):
        points = COAX_DB.get(coax_type)
        if not points:
            return 0.0
        freqs = sorted(points.keys())
        if freq_mhz <= freqs[0]:
            return points[freqs[0]]
        if freq_mhz >= freqs[-1]:
            return points[freqs[-1]]
        for i in range(len(freqs) - 1):
            f1, f2 = freqs[i], freqs[i + 1]
            if f1 <= freq_mhz <= f2:
                l1, l2 = points[f1], points[f2]
                t = (freq_mhz - f1) / (f2 - f1)
                return l1 + t * (l2 - l1)
        return points[freqs[-1]]

    # -----------------------------
    # Scroll helper
    # -----------------------------
    def make_scrollable(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return scrollable_frame

    # ============================================================
    # RF LINK TAB
    # ============================================================
    def create_rf_tab(self):
        scroll = self.make_scrollable(self.rf_tab)

        tx = tk.LabelFrame(scroll, text="Transmitter", font=("Arial", 10, "bold"))
        tx.pack(fill=tk.X, padx=10, pady=5)

        self.rf_ptx_val = tk.DoubleVar(value=5)
        self.rf_ptx_unit = tk.StringVar(value="W")
        tk.Label(tx, text="Power:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(tx, textvariable=self.rf_ptx_val, width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Combobox(tx, textvariable=self.rf_ptx_unit,
                     values=["W", "mW", "dBm"], state="readonly", width=8)\
            .grid(row=0, column=2, padx=5, pady=5)

        self.rf_gtx = tk.DoubleVar(value=0)
        tk.Label(tx, text="Antenna Gain (dBi):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(tx, textvariable=self.rf_gtx, width=15).grid(row=1, column=1, padx=5, pady=5)

        self.rf_ltx = tk.DoubleVar(value=0)
        tk.Label(tx, text="TX Cable Loss (dB):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(tx, textvariable=self.rf_ltx, width=15).grid(row=2, column=1, padx=5, pady=5)

        rx = tk.LabelFrame(scroll, text="Receiver", font=("Arial", 10, "bold"))
        rx.pack(fill=tk.X, padx=10, pady=5)

        self.rf_grx = tk.DoubleVar(value=0)
        tk.Label(rx, text="Antenna Gain (dBi):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(rx, textvariable=self.rf_grx, width=15).grid(row=0, column=1, padx=5, pady=5)

        self.rf_lrx = tk.DoubleVar(value=0)
        tk.Label(rx, text="RX Cable Loss (dB):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(rx, textvariable=self.rf_lrx, width=15).grid(row=1, column=1, padx=5, pady=5)

        path = tk.LabelFrame(scroll, text="Path Parameters", font=("Arial", 10, "bold"))
        path.pack(fill=tk.X, padx=10, pady=5)

        self.rf_freq_val = tk.DoubleVar(value=433)
        self.rf_freq_unit = tk.StringVar(value="MHz")
        tk.Label(path, text="Frequency:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(path, textvariable=self.rf_freq_val, width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Combobox(path, textvariable=self.rf_freq_unit,
                     values=["Hz", "kHz", "MHz", "GHz"], state="readonly", width=8)\
            .grid(row=0, column=2, padx=5, pady=5)

        self.rf_dist_val = tk.DoubleVar(value=10)
        self.rf_dist_unit = tk.StringVar(value="km")
        tk.Label(path, text="Distance:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(path, textvariable=self.rf_dist_val, width=15).grid(row=1, column=1, padx=5, pady=5)
        ttk.Combobox(path, textvariable=self.rf_dist_unit,
                     values=["km", "m", "mi", "ft"], state="readonly", width=8)\
            .grid(row=1, column=2, padx=5, pady=5)

        self.rf_misc_loss = tk.DoubleVar(value=0)
        tk.Label(path, text="Misc Losses (dB):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(path, textvariable=self.rf_misc_loss, width=15).grid(row=2, column=1, padx=5, pady=5)

        margins = tk.LabelFrame(scroll, text="Link Margin / Availability", font=("Arial", 10, "bold"))
        margins.pack(fill=tk.X, padx=10, pady=5)

        self.rf_sensitivity_dbm = tk.DoubleVar(value=-120)
        tk.Label(margins, text="Receiver Sensitivity (dBm):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(margins, textvariable=self.rf_sensitivity_dbm, width=15).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(scroll, text="Calculate RF Link Budget", command=self.calculate_rf,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=10)

        self.rf_results = tk.Text(scroll, height=16, state=tk.DISABLED)
        self.rf_results.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def calculate_rf(self):
        try:
            ptx_dbm = self.powerToDbm(self.rf_ptx_val.get(), self.rf_ptx_unit.get())
            gtx = self.rf_gtx.get()
            grx = self.rf_grx.get()
            ltx = self.rf_ltx.get()
            lrx = self.rf_lrx.get()
            freqMhz = self.freqToMhz(self.rf_freq_val.get(), self.rf_freq_unit.get())
            distanceKm = self.distToKm(self.rf_dist_val.get(), self.rf_dist_unit.get())
            miscLoss = self.rf_misc_loss.get()

            lfs = self.fspl(distanceKm, freqMhz)
            prx_dbm = ptx_dbm + gtx - ltx - lfs + grx - lrx - miscLoss
            prx_watts = self.dbmToWatts(prx_dbm)

            sens = self.rf_sensitivity_dbm.get()
            margin = prx_dbm - sens

            if margin < 0:
                avail = 0.0
            else:
                avail = 1 - (10 ** (-margin / 10.0))
                avail = max(0.0, min(avail, 0.99999))

            results = []
            results.append("RF LINK BUDGET RESULTS")
            results.append("=" * 60)
            results.append(f"Frequency: {freqMhz:.3f} MHz")
            results.append(f"Distance:  {distanceKm:.3f} km")
            results.append(f"TX Power:  {ptx_dbm:.3f} dBm")
            results.append(f"TX Gain:   {gtx:.3f} dBi")
            results.append(f"TX Loss:   {ltx:.3f} dB")
            results.append(f"RX Gain:   {grx:.3f} dBi")
            results.append(f"RX Loss:   {lrx:.3f} dB")
            results.append("")
            results.append(f"Path Loss (FSPL): {lfs:.3f} dB")
            results.append(f"Misc Losses:      {miscLoss:.3f} dB")
            results.append("")
            results.append(f"Received Power: {prx_dbm:.3f} dBm")
            results.append(f"Received Power: {self.formatWatts(prx_watts)}")
            results.append("")
            results.append(f"Receiver Sensitivity: {sens:.2f} dBm")
            results.append(f"Link Margin: {margin:.2f} dB")
            results.append(f"Estimated Availability: {avail*100:.3f} %")

            text = "\n".join(results)
            self.rf_results.config(state=tk.NORMAL)
            self.rf_results.delete(1.0, tk.END)
            self.rf_results.insert(1.0, text)
            self.rf_results.config(state=tk.DISABLED)

            self.add_history("RF", "RF Link Budget", {
                "ptx_dbm": ptx_dbm, "gtx": gtx, "grx": grx, "ltx": ltx, "lrx": lrx,
                "freqMhz": freqMhz, "distanceKm": distanceKm, "miscLoss": miscLoss, "sensitivity": sens
            }, {
                "prx_dbm": prx_dbm, "margin_db": margin, "availability": avail
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # FRIIS TAB
    # ============================================================
    def create_friis_tab(self):
        scroll = self.make_scrollable(self.friis_tab)
        tk.Label(scroll, text="Add each stage in order (front-end to backend).").pack(anchor="w", padx=10, pady=5)

        cols = ("Stage", "Gain (dB)", "NF (dB)", "Noise Temp (K)", "Use Temp?")
        self.friis_tree = ttk.Treeview(scroll, columns=cols, show="headings", height=7)
        for c in cols:
            self.friis_tree.heading(c, text=c)
            self.friis_tree.column(c, width=140 if c != "Stage" else 80)
        self.friis_tree.pack(fill=tk.X, padx=10, pady=5)

        entry_frame = tk.Frame(scroll)
        entry_frame.pack(fill=tk.X, padx=10, pady=5)

        self.stage_gain = tk.DoubleVar(value=10)
        self.stage_nf = tk.DoubleVar(value=2)
        self.stage_temp = tk.DoubleVar(value=290)
        self.stage_use_temp = tk.BooleanVar(value=False)

        tk.Label(entry_frame, text="Gain (dB)").grid(row=0, column=0, padx=5, pady=2)
        tk.Entry(entry_frame, textvariable=self.stage_gain, width=8).grid(row=1, column=0, padx=5)

        tk.Label(entry_frame, text="NF (dB)").grid(row=0, column=1, padx=5, pady=2)
        tk.Entry(entry_frame, textvariable=self.stage_nf, width=8).grid(row=1, column=1, padx=5)

        tk.Label(entry_frame, text="Noise Temp (K)").grid(row=0, column=2, padx=5, pady=2)
        tk.Entry(entry_frame, textvariable=self.stage_temp, width=8).grid(row=1, column=2, padx=5)

        tk.Checkbutton(entry_frame, text="Use Temp instead of NF",
                       variable=self.stage_use_temp).grid(row=1, column=3, sticky="w", padx=10)

        btns = tk.Frame(scroll)
        btns.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btns, text="Add Stage", command=self.add_friis_stage).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Remove Selected", command=self.remove_friis_stage).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Clear All", command=self.clear_friis_stages).pack(side=tk.LEFT, padx=5)

        tk.Button(scroll, text="Calculate Cascade NF", command=self.calculate_friis,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=8)

        self.friis_results = tk.Text(scroll, height=12, state=tk.DISABLED)
        self.friis_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.add_friis_stage()

    def add_friis_stage(self):
        idx = len(self.friis_tree.get_children()) + 1
        self.friis_tree.insert("", "end", values=(
            idx, self.stage_gain.get(), self.stage_nf.get(),
            self.stage_temp.get(), self.stage_use_temp.get()
        ))

    def remove_friis_stage(self):
        sel = self.friis_tree.selection()
        for s in sel:
            self.friis_tree.delete(s)
        for i, item in enumerate(self.friis_tree.get_children(), 1):
            vals = list(self.friis_tree.item(item, "values"))
            vals[0] = i
            self.friis_tree.item(item, values=vals)

    def clear_friis_stages(self):
        for item in self.friis_tree.get_children():
            self.friis_tree.delete(item)

    def calculate_friis(self):
        try:
            stages = []
            for item in self.friis_tree.get_children():
                st, g_db, nf_db, t_k, use_t = self.friis_tree.item(item, "values")
                g_db = float(g_db)
                nf_db = float(nf_db)
                t_k = float(t_k)
                use_t = (str(use_t).lower() == "true")
                stages.append((g_db, nf_db, t_k, use_t))

            if not stages:
                raise ValueError("Add at least one stage.")

            G = [10**(g/10.0) for g,_,_,_ in stages]

            F = []
            for (g_db, nf_db, t_k, use_t) in stages:
                if use_t:
                    F.append(1.0 + t_k/290.0)
                else:
                    F.append(10**(nf_db/10.0))

            F_total = F[0]
            gain_prod = 1.0
            for i in range(1, len(F)):
                gain_prod *= G[i-1]
                F_total += (F[i] - 1.0) / gain_prod

            NF_total_db = 10 * log10(F_total)
            T_total = (F_total - 1.0) * 290.0
            G_total_db = 10 * log10(self._prod(G))

            text = []
            text.append("FRIIS CASCADE NOISE FIGURE RESULTS")
            text.append("=" * 60)
            text.append(f"Total Gain: {G_total_db:.3f} dB")
            text.append(f"Total Noise Factor: {F_total:.6f}")
            text.append(f"Total Noise Figure: {NF_total_db:.3f} dB")
            text.append(f"Equivalent Noise Temperature: {T_total:.2f} K")

            self.friis_results.config(state=tk.NORMAL)
            self.friis_results.delete(1.0, tk.END)
            self.friis_results.insert(1.0, "\n".join(text))
            self.friis_results.config(state=tk.DISABLED)

            self.add_history("Receiver", "Friis Noise Figure", {
                "stages": stages
            }, {
                "G_total_db": G_total_db, "NF_total_db": NF_total_db, "T_total_K": T_total
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _prod(self, arr):
        p=1.0
        for a in arr:
            p*=a
        return p

    # ============================================================
    # FRESNEL TAB
    # ============================================================
    def create_fresnel_tab(self):
        scroll = self.make_scrollable(self.fresnel_tab)

        frame = tk.LabelFrame(scroll, text="Fresnel Zone Calculator", font=("Arial", 10, "bold"))
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.fr_freq_val = tk.DoubleVar(value=2400)
        self.fr_freq_unit = tk.StringVar(value="MHz")
        self.fr_dist_val = tk.DoubleVar(value=10)
        self.fr_dist_unit = tk.StringVar(value="km")
        self.fr_point_pct = tk.DoubleVar(value=50)
        self.fr_obstacle_h = tk.DoubleVar(value=0)

        tk.Label(frame, text="Frequency:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.fr_freq_val, width=12).grid(row=0, column=1)
        ttk.Combobox(frame, textvariable=self.fr_freq_unit,
                     values=["MHz", "GHz"], state="readonly", width=6).grid(row=0, column=2, padx=5)

        tk.Label(frame, text="Path Distance:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.fr_dist_val, width=12).grid(row=1, column=1)
        ttk.Combobox(frame, textvariable=self.fr_dist_unit,
                     values=["km", "mi"], state="readonly", width=6).grid(row=1, column=2, padx=5)

        tk.Label(frame, text="Point along path (%):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.fr_point_pct, width=12).grid(row=2, column=1, padx=5)

        tk.Label(frame, text="Obstacle height INTO zone (m):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.fr_obstacle_h, width=12).grid(row=3, column=1, padx=5)

        tk.Button(scroll, text="Calculate Fresnel Zone", command=self.calculate_fresnel,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=8)

        self.fresnel_results = tk.Text(scroll, height=12, state=tk.DISABLED)
        self.fresnel_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def calculate_fresnel(self):
        try:
            f_mhz = self.fr_freq_val.get()
            if self.fr_freq_unit.get() == "GHz":
                f_mhz *= 1000.0

            d_km = self.fr_dist_val.get()
            if self.fr_dist_unit.get() == "mi":
                d_km *= 1.609344

            pct = self.fr_point_pct.get() / 100.0
            if not (0.0 < pct < 1.0):
                raise ValueError("Point % must be between 0 and 100 (exclusive).")

            d1 = d_km * pct
            d2 = d_km * (1 - pct)

            lam = self.wavelengthMeters(f_mhz * 1e6)

            d1_m = d1 * 1000.0
            d2_m = d2 * 1000.0
            r1 = sqrt((lam * d1_m * d2_m) / (d1_m + d2_m))

            obs = self.fr_obstacle_h.get()
            clearance_pct = max(0.0, min(100.0, (1 - obs/r1) * 100.0)) if r1>0 else 0.0

            text = []
            text.append("FRESNEL ZONE RESULTS (n=1)")
            text.append("=" * 60)
            text.append(f"Frequency: {f_mhz:.3f} MHz")
            text.append(f"Total distance: {d_km:.3f} km")
            text.append(f"Point at: {pct*100:.1f}% (d1={d1:.3f} km, d2={d2:.3f} km)")
            text.append(f"Wavelength: {self.formatLength(lam)}")
            text.append("")
            text.append(f"Fresnel radius at point (r1): {self.formatLength(r1)}")
            text.append(f"Obstacle intrusion: {obs:.3f} m")
            text.append(f"Remaining clearance: {clearance_pct:.2f}%")

            self.fresnel_results.config(state=tk.NORMAL)
            self.fresnel_results.delete(1.0, tk.END)
            self.fresnel_results.insert(1.0, "\n".join(text))
            self.fresnel_results.config(state=tk.DISABLED)

            self.add_history("Path", "Fresnel Zone", {
                "f_mhz": f_mhz, "d_km": d_km, "pct": pct, "obs_m": obs
            }, {
                "r1_m": r1, "clearance_pct": clearance_pct
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # COAX TAB
    # ============================================================
    def create_coax_tab(self):
        scroll = self.make_scrollable(self.coax_tab)

        frame = tk.LabelFrame(scroll, text="Coax Loss Calculator", font=("Arial", 10, "bold"))
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.cx_type = tk.StringVar(value="LMR-400")
        self.cx_len_val = tk.DoubleVar(value=50)
        self.cx_len_unit = tk.StringVar(value="ft")
        self.cx_freq_val = tk.DoubleVar(value=146.52)
        self.cx_freq_unit = tk.StringVar(value="MHz")
        self.cx_conn_type = tk.StringVar(value="PL-259/SO-239")
        self.cx_conn_count = tk.IntVar(value=2)

        tk.Label(frame, text="Coax Type:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.cx_type,
                     values=list(COAX_DB.keys()), state="readonly", width=15)\
            .grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Length:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.cx_len_val, width=10).grid(row=1, column=1, sticky="w")
        ttk.Combobox(frame, textvariable=self.cx_len_unit,
                     values=["ft", "m"], state="readonly", width=5)\
            .grid(row=1, column=2, padx=5)

        tk.Label(frame, text="Frequency:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.cx_freq_val, width=10).grid(row=2, column=1, sticky="w")
        ttk.Combobox(frame, textvariable=self.cx_freq_unit,
                     values=["MHz", "GHz"], state="readonly", width=5)\
            .grid(row=2, column=2, padx=5)

        tk.Label(frame, text="Connector Type:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.cx_conn_type,
                     values=list(CONNECTOR_LOSS_DB.keys()), state="readonly", width=15)\
            .grid(row=3, column=1, padx=5)

        tk.Label(frame, text="Count:").grid(row=3, column=2, sticky="e", padx=5)
        tk.Entry(frame, textvariable=self.cx_conn_count, width=5).grid(row=3, column=3, sticky="w")

        tk.Button(scroll, text="Calculate Coax + Connector Loss", command=self.calculate_coax,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=8)

        self.coax_results = tk.Text(scroll, height=10, state=tk.DISABLED)
        self.coax_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def calculate_coax(self):
        try:
            freq_mhz = self.cx_freq_val.get()
            if self.cx_freq_unit.get() == "GHz":
                freq_mhz *= 1000.0

            length_ft = self.cx_len_val.get()
            if self.cx_len_unit.get() == "m":
                length_ft *= 3.28084

            coax = self.cx_type.get()
            loss_100ft = self.coax_loss_db_per_100ft(coax, freq_mhz)
            loss = loss_100ft * (length_ft/100.0)

            conn_type = self.cx_conn_type.get()
            conn_loss_each = CONNECTOR_LOSS_DB.get(conn_type, 0.0)
            conn_loss = conn_loss_each * self.cx_conn_count.get()

            total = loss + conn_loss
            vf = COAX_VF_DB.get(coax, 0.66)

            text = []
            text.append("COAX / CONNECTOR LOSS RESULTS")
            text.append("=" * 60)
            text.append(f"Type: {coax}")
            text.append(f"Frequency: {freq_mhz:.3f} MHz")
            text.append(f"Length: {length_ft:.2f} ft")
            text.append(f"Attenuation: {loss_100ft:.3f} dB / 100 ft")
            text.append(f"Coax Loss: {loss:.3f} dB")
            text.append("")
            text.append(f"Connector: {conn_type} x {self.cx_conn_count.get()}")
            text.append(f"Connector Loss: {conn_loss:.3f} dB")
            text.append("")
            text.append(f"TOTAL INSERTION LOSS: {total:.3f} dB")
            text.append(f"Velocity Factor (approx): {vf:.2f}")

            self.coax_results.config(state=tk.NORMAL)
            self.coax_results.delete(1.0, tk.END)
            self.coax_results.insert(1.0, "\n".join(text))
            self.coax_results.config(state=tk.DISABLED)

            self.add_history("Feedline", "Coax Loss", {
                "coax": coax, "freq_mhz": freq_mhz, "length_ft": length_ft,
                "conn_type": conn_type, "conn_count": self.cx_conn_count.get()
            }, {
                "coax_loss_db": loss, "connector_loss_db": conn_loss, "total_loss_db": total, "vf": vf
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # SMITH / SWR TAB (Option B built-in)
    # ============================================================
    def create_smith_tab(self):
        scroll = self.make_scrollable(self.smith_tab)

        frame = tk.LabelFrame(scroll, text="Impedance / Smith Chart", font=("Arial", 10, "bold"))
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.sm_r = tk.DoubleVar(value=25)
        self.sm_x = tk.DoubleVar(value=10)
        self.sm_z0 = tk.DoubleVar(value=50)
        self.sm_freq_mhz = tk.DoubleVar(value=146.52)

        tk.Label(frame, text="Load R (Ω):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(frame, textvariable=self.sm_r, width=8).grid(row=0, column=1)

        tk.Label(frame, text="Load X (Ω):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        tk.Entry(frame, textvariable=self.sm_x, width=8).grid(row=0, column=3)

        tk.Label(frame, text="Line Z0 (Ω):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(frame, textvariable=self.sm_z0, width=8).grid(row=1, column=1)

        tk.Label(frame, text="Freq (MHz):").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        tk.Entry(frame, textvariable=self.sm_freq_mhz, width=8).grid(row=1, column=3)

        tk.Button(scroll, text="Compute SWR + Plot Smith", command=self.calculate_smith,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=8)

        self.smith_results = tk.Text(scroll, height=10, state=tk.DISABLED)
        self.smith_results.pack(fill=tk.X, padx=10, pady=5)

        # Always build a Tkinter smith chart canvas fallback
        self.smith_canvas_tk = tk.Canvas(scroll, width=450, height=450, highlightthickness=0)
        self.smith_canvas_tk.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.draw_smith_background()

        # If matplotlib exists, overlay a nicer chart below the Tk fallback
        if MATPLOTLIB_OK:
            fig = Figure(figsize=(5, 5), dpi=100)
            self.smith_ax = fig.add_subplot(111)
            self.smith_canvas = FigureCanvasTkAgg(fig, master=scroll)
            self.smith_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def calculate_smith(self):
        try:
            R = self.sm_r.get()
            X = self.sm_x.get()
            Z0 = self.sm_z0.get()
            f_mhz = self.sm_freq_mhz.get()

            ZL = complex(R, X)
            gamma = (ZL - Z0) / (ZL + Z0)
            mag = abs(gamma)
            swr = (1 + mag) / (1 - mag) if mag < 1 else float("inf")

            match_text = self.suggest_l_match(R, X, Z0, f_mhz)

            text = []
            text.append("SMITH / SWR RESULTS")
            text.append("=" * 60)
            text.append(f"ZL = {R:.2f} + j{X:.2f} Ω")
            text.append(f"Z0 = {Z0:.2f} Ω")
            text.append(f"|Γ| = {mag:.4f}")
            text.append(f"SWR = {swr:.3f}")
            text.append("")
            text.append("Basic L-match suggestion:")
            text.append(match_text)

            self.smith_results.config(state=tk.NORMAL)
            self.smith_results.delete(1.0, tk.END)
            self.smith_results.insert(1.0, "\n".join(text))
            self.smith_results.config(state=tk.DISABLED)

            # Always plot on Tk chart
            self.plot_smith_point_tk(gamma)

            # If matplotlib is available, plot also on mpl chart
            if MATPLOTLIB_OK:
                self.plot_smith_mpl(gamma)

            self.add_history("Match", "Smith/SWR", {
                "R": R, "X": X, "Z0": Z0, "freq_mhz": f_mhz
            }, {
                "gamma_mag": mag, "swr": swr
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---- Tkinter Smith chart ----
    def draw_smith_background(self):
        c = self.smith_canvas_tk
        c.delete("all")

        w = int(c["width"]); h = int(c["height"])
        cx, cy = w//2, h//2
        r = min(w, h)//2 - 10

        # Outer circle
        c.create_oval(cx-r, cy-r, cx+r, cy+r)

        # Resistance circles (normalized)
        for rr in [0.2, 0.5, 1, 2, 5]:
            x0 = cx + r*(rr/(1+rr))
            rad = r/(1+rr)
            c.create_oval(x0-rad, cy-rad, x0+rad, cy+rad, dash=(2,2))

        # Reactance arcs (normalized)
        for xx in [0.2, 0.5, 1, 2, 5]:
            x0 = cx + r
            # upper
            y0 = cy - r/xx
            rad = r/xx
            c.create_oval(x0-rad, y0-rad, x0+rad, y0+rad, dash=(2,2))
            # lower
            y0 = cy + r/xx
            c.create_oval(x0-rad, y0-rad, x0+rad, y0+rad, dash=(2,2))

        # Center line
        c.create_line(cx-r, cy, cx+r, cy, dash=(2,2))

    def plot_smith_point_tk(self, gamma):
        c = self.smith_canvas_tk
        self.draw_smith_background()

        w = int(c["width"]); h = int(c["height"])
        cx, cy = w//2, h//2
        r = min(w, h)//2 - 10

        x = cx + gamma.real * r
        y = cy - gamma.imag * r

        c.create_oval(x-4, y-4, x+4, y+4, fill="black")
        c.create_text(10, 10, anchor="nw",
                      text=f"Γ = {gamma.real:+.3f} {gamma.imag:+.3f}j")

    # ---- matplotlib Smith chart ----
    def plot_smith_mpl(self, gamma):
        ax = self.smith_ax
        ax.clear()
        ax.set_title("Smith Chart (normalized)")
        ax.set_aspect("equal", "box")
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.grid(True, alpha=0.3)

        th = [i*2*pi/400 for i in range(401)]
        ax.plot([cos(t) for t in th], [sin(t) for t in th])
        ax.plot([gamma.real], [gamma.imag], marker="o")

        self.smith_canvas.draw()

    def suggest_l_match(self, R, X, Z0, freq_mhz):
        f = freq_mhz * 1e6
        if R <= 0:
            return "Invalid R."

        if abs(X) > 1e-6:
            cancel = "Add series capacitor to cancel +jX." if X > 0 else "Add series inductor to cancel -jX."
        else:
            cancel = "No reactive cancel needed."

        if R < Z0:
            Q = sqrt(Z0/R - 1)
            Xs = Q * R
            Xp = Z0 / Q
            Ls = Xs / (2*pi*f)
            Cp = 1 / (2*pi*f*Xp)
            return (f"{cancel}\nLow-pass L: series L={Ls:.2e} H, shunt C={Cp:.2e} F\n(Q≈{Q:.2f})")
        elif R > Z0:
            Q = sqrt(R/Z0 - 1)
            Xs = Q * Z0
            Xp = R / Q
            Cs = 1 / (2*pi*f*Xs)
            Lp = Xp / (2*pi*f)
            return (f"{cancel}\nHigh-pass L: series C={Cs:.2e} F, shunt L={Lp:.2e} H\n(Q≈{Q:.2f})")
        else:
            return f"{cancel}\nR already matched to Z0."

    # ============================================================
    # ANTENNA TAB
    # ============================================================
    def create_antenna_tab(self):
        scroll = self.make_scrollable(self.ant_tab)

        frame = tk.LabelFrame(scroll, text="Antenna Parameters", font=("Arial", 10, "bold"))
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.ant_freq_val = tk.DoubleVar(value=146.52)
        self.ant_freq_unit = tk.StringVar(value="MHz")
        tk.Label(frame, text="Frequency:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.ant_freq_val, width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.ant_freq_unit,
                     values=["Hz", "kHz", "MHz", "GHz"], state="readonly", width=8)\
            .grid(row=0, column=2, padx=5, pady=5)

        self.ant_type = tk.StringVar(value="Half-wave dipole")
        tk.Label(frame, text="Antenna Type:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.ant_type,
                     values=[
                         "Quarter-wave ground plane",
                         "Half-wave dipole",
                         "Five-eighths-wave vertical",
                         "Full-wave loop",
                         "J-pole (basic)",
                         "End-fed half-wave (basic)",
                         "Yagi-Uda beam"],
                     state="readonly", width=30)\
            .grid(row=1, column=1, columnspan=2, padx=5, pady=5)

        self.ant_material = tk.StringVar(value="Copper")
        tk.Label(frame, text="Material:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.ant_material,
                     values=list(MATERIAL_VF.keys()), state="readonly", width=10)\
            .grid(row=2, column=1, padx=5, pady=5)

        self.ant_elements = tk.IntVar(value=3)
        tk.Label(frame, text="Yagi Elements:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(frame, textvariable=self.ant_elements, width=10).grid(row=3, column=1, padx=5, pady=5)

        tk.Button(scroll, text="Calculate Antenna", command=self.calculate_antenna,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=10)

        self.ant_results = tk.Text(scroll, height=18, state=tk.DISABLED)
        self.ant_results.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def calculate_antenna(self):
        try:
            freqHz = self.freqToHz(self.ant_freq_val.get(), self.ant_freq_unit.get())
            lam = self.wavelengthMeters(freqHz)
            vf = self.velocityFactor(self.ant_material.get())

            results = []
            results.append("ANTENNA CALCULATOR RESULTS")
            results.append("=" * 60)
            results.append(f"Frequency: {self.ant_freq_val.get()} {self.ant_freq_unit.get()}")
            results.append(f"Wavelength: {self.formatLength(lam)}")
            results.append(f"Material: {self.ant_material.get()} (VF: {vf})")
            results.append(f"Antenna Type: {self.ant_type.get()}")
            results.append("")

            if self.ant_type.get() == "Yagi-Uda beam":
                elements = self.ant_elements.get()
                refl, driv, dirs = self.yagiLengths(lam, elements, vf)
                spacings, boomLen = self.yagiSpacing(lam, elements)

                results.append("YAGI-UDA ELEMENT LENGTHS:")
                results.append(f"Reflector: {self.formatLength(refl)}")
                results.append(f"Driven:    {self.formatLength(driv)}")
                for i, d in enumerate(dirs, 1):
                    results.append(f"Director {i}: {self.formatLength(d)}")

                results.append("")
                results.append("YAGI-UDA BOOM SPACING:")
                results.append(f"Reflector to Driven:   {self.formatLength(spacings[0])}")
                results.append(f"Driven to Director 1:  {self.formatLength(spacings[1])}")
                for i in range(2, len(spacings)):
                    results.append(f"Director {i-1} to Director {i}: {self.formatLength(spacings[i])}")
                results.append(f"Boom Length: {self.formatLength(boomLen)}")

            else:
                mults = {
                    "Quarter-wave ground plane": 0.25,
                    "Half-wave dipole": 0.50,
                    "Five-eighths-wave vertical": 0.625,
                    "Full-wave loop": 1.00,
                    "J-pole (basic)": 0.75,
                    "End-fed half-wave (basic)": 0.50,
                }
                mult = mults.get(self.ant_type.get(), 0.50)
                ideal = lam * mult
                adj = ideal * vf

                results.append(f"Ideal Length: {self.formatLength(ideal)}")
                results.append(f"Adjusted Length (VF): {self.formatLength(adj)}")

                if self.ant_type.get() == "Quarter-wave ground plane":
                    rad = lam * 0.25 * vf
                    results.append("")
                    results.append(f"Radial Length (4 recommended): {self.formatLength(rad)}")

                if self.ant_type.get() == "J-pole (basic)":
                    half = lam * 0.5 * vf
                    quarter = lam * 0.25 * vf
                    results.append("")
                    results.append(f"Long element ~ 1/2λ: {self.formatLength(half)}")
                    results.append(f"Short stub ~ 1/4λ:  {self.formatLength(quarter)}")

                if self.ant_type.get() == "End-fed half-wave (basic)":
                    half = lam * 0.5 * vf
                    results.append("")
                    results.append(f"Radiator ~ 1/2λ: {self.formatLength(half)}")
                    results.append("Match typically required (49:1 or 64:1 transformer).")

            text = "\n".join(results)
            self.ant_results.config(state=tk.NORMAL)
            self.ant_results.delete(1.0, tk.END)
            self.ant_results.insert(1.0, text)
            self.ant_results.config(state=tk.DISABLED)

            self.add_history("Antenna", "Antenna Calc", {
                "freqHz": freqHz, "vf": vf, "type": self.ant_type.get()
            }, {
                "lambda_m": lam
            })

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # PATTERN TAB
    # ============================================================
    def create_pattern_tab(self):
        scroll = self.make_scrollable(self.pattern_tab)
        tk.Label(scroll, text="Theoretical patterns (placeholders for real NEC patterns).").pack(anchor="w", padx=10)

        self.pat_type = tk.StringVar(value="Half-wave dipole")
        ttk.Combobox(scroll, textvariable=self.pat_type,
                     values=["Half-wave dipole", "Quarter-wave vertical", "Yagi-Uda beam"],
                     state="readonly", width=25).pack(padx=10, pady=5, anchor="w")

        tk.Button(scroll, text="Plot Pattern", command=self.plot_pattern,
                  bg=self.accent, fg="white", font=("Arial", 10, "bold")).pack(pady=8)

        if MATPLOTLIB_OK:
            fig = Figure(figsize=(5.5, 5.5), dpi=100)
            self.pat_ax = fig.add_subplot(111, polar=True)
            self.pat_canvas = FigureCanvasTkAgg(fig, master=scroll)
            self.pat_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        else:
            tk.Label(scroll, text="(Install matplotlib for polar plots.)").pack(anchor="w", padx=10)

    def plot_pattern(self):
        if not MATPLOTLIB_OK:
            messagebox.showwarning("Plot unavailable", "Install matplotlib to use pattern plots.")
            return
        ax = self.pat_ax
        ax.clear()
        t = [i*2*pi/720 for i in range(721)]

        typ = self.pat_type.get()
        if typ == "Half-wave dipole":
            r = [abs(sin(th)) for th in t]
        elif typ == "Quarter-wave vertical":
            r = [abs(sin(th))**0.7 for th in t]
        else:
            r = []
            for th in t:
                forward = max(0.0, cos(th))**3
                back = max(0.0, cos(th+pi))**1.5 * 0.3
                r.append(forward + back)

        ax.plot(t, r)
        ax.set_title(f"{typ} Pattern (normalized)")
        self.pat_canvas.draw()

    # ============================================================
    # HISTORY TAB
    # ============================================================
    def create_history_tab(self):
        frame = tk.Frame(self.history_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("Time", "Category", "Title")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            self.hist_tree.heading(c, text=c)
        self.hist_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.LEFT, fill=tk.Y)

        btns = tk.Frame(self.history_tab)
        btns.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btns, text="View Details", command=self.view_history_details).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Export Selected to CSV", command=self.export_history_csv).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Save Profile", command=self.save_profile).pack(side=tk.RIGHT, padx=5)
        tk.Button(btns, text="Load Profile", command=self.load_profile).pack(side=tk.RIGHT, padx=5)

        self.refresh_history_tab()

    def refresh_history_tab(self):
        if not hasattr(self, "hist_tree"):
            return
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        for rec in self.history:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec.timestamp))
            self.hist_tree.insert("", "end", values=(ts, rec.category, rec.title))

    def view_history_details(self):
        sel = self.hist_tree.selection()
        if not sel:
            return
        idx = self.hist_tree.index(sel[0])
        rec = self.history[idx]
        msg = f"{rec.title}\n\nInputs:\n{json.dumps(rec.inputs, indent=2)}\n\nOutputs:\n{json.dumps(rec.outputs, indent=2)}"
        messagebox.showinfo("Calculation Details", msg)

    def export_history_csv(self):
        sel = self.hist_tree.selection()
        if not sel:
            messagebox.showwarning("Pick one", "Select a record first.")
            return
        idx = self.hist_tree.index(sel[0])
        rec = self.history[idx]

        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return

        with open(path, "w") as f:
            f.write("key,value\n")
            for k, v in rec.inputs.items():
                f.write(f"input.{k},{v}\n")
            for k, v in rec.outputs.items():
                f.write(f"output.{k},{v}\n")
        messagebox.showinfo("Exported", f"Saved CSV:\n{path}")

    def save_profile(self):
        profile = {
            "rf": {
                "ptx_val": self.rf_ptx_val.get(), "ptx_unit": self.rf_ptx_unit.get(),
                "gtx": self.rf_gtx.get(), "grx": self.rf_grx.get(),
                "ltx": self.rf_ltx.get(), "lrx": self.rf_lrx.get(),
                "freq_val": self.rf_freq_val.get(), "freq_unit": self.rf_freq_unit.get(),
                "dist_val": self.rf_dist_val.get(), "dist_unit": self.rf_dist_unit.get(),
                "misc_loss": self.rf_misc_loss.get(), "sensitivity": self.rf_sensitivity_dbm.get()
            },
            "ant": {
                "freq_val": self.ant_freq_val.get(), "freq_unit": self.ant_freq_unit.get(),
                "type": self.ant_type.get(), "material": self.ant_material.get(),
                "elements": self.ant_elements.get()
            }
        }
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
        messagebox.showinfo("Saved", f"Profile saved:\n{path}")

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "r") as f:
            profile = json.load(f)

        rf = profile.get("rf", {})
        self.rf_ptx_val.set(rf.get("ptx_val", self.rf_ptx_val.get()))
        self.rf_ptx_unit.set(rf.get("ptx_unit", self.rf_ptx_unit.get()))
        self.rf_gtx.set(rf.get("gtx", self.rf_gtx.get()))
        self.rf_grx.set(rf.get("grx", self.rf_grx.get()))
        self.rf_ltx.set(rf.get("ltx", self.rf_ltx.get()))
        self.rf_lrx.set(rf.get("lrx", self.rf_lrx.get()))
        self.rf_freq_val.set(rf.get("freq_val", self.rf_freq_val.get()))
        self.rf_freq_unit.set(rf.get("freq_unit", self.rf_freq_unit.get()))
        self.rf_dist_val.set(rf.get("dist_val", self.rf_dist_val.get()))
        self.rf_dist_unit.set(rf.get("dist_unit", self.rf_dist_unit.get()))
        self.rf_misc_loss.set(rf.get("misc_loss", self.rf_misc_loss.get()))
        self.rf_sensitivity_dbm.set(rf.get("sensitivity", self.rf_sensitivity_dbm.get()))

        ant = profile.get("ant", {})
        self.ant_freq_val.set(ant.get("freq_val", self.ant_freq_val.get()))
        self.ant_freq_unit.set(ant.get("freq_unit", self.ant_freq_unit.get()))
        self.ant_type.set(ant.get("type", self.ant_type.get()))
        self.ant_material.set(ant.get("material", self.ant_material.get()))
        self.ant_elements.set(ant.get("elements", self.ant_elements.get()))

        messagebox.showinfo("Loaded", f"Profile loaded:\n{path}")

    # -----------------------------
    # UI actions
    # -----------------------------
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.settings["dark_mode"] = self.dark_mode
        self.save_settings()
        self.apply_theme()
        self.dark_mode_btn.config(text="☀ Light Mode" if self.dark_mode else "🌙 Dark Mode")

    def change_units(self):
        self.unit_system = self.unit_var.get()
        self.settings["unit_system"] = self.unit_system
        self.save_settings()


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = RFAntennaGUI(root)
    root.mainloop()
