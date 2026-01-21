import tkinter as tk
from tkinter import font, messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
from ai_model import AIModel, resource_path
from db import fetch_ci_mock_crifv4
from datetime import datetime, timedelta, date
import threading
from splash import Splash
from users import ensure_user_store, authenticate
from admin_dashboard import AdminDashboard
import pandas as pd

class PlaceholderEntry(tk.Entry):
    def __init__(self, master=None, placeholder="", color="grey", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg = self['fg']
        self.bind("<FocusIn>", self._clear)
        self.bind("<FocusOut>", self._show)
        self._show()

    def _show(self, *_):
        if not self.get():
            self.configure(fg=self.placeholder_color)
            self.delete(0, tk.END)
            self.insert(0, self.placeholder)

    def _clear(self, *_):
        if self['fg'] == self.placeholder_color:
            self.configure(fg=self.default_fg)
            self.delete(0, tk.END)

class App(tk.Tk):
    GREEN, BG_GRAY = "#2E7D32", "#F0F0F0"
    ENTRY_BG, ENTRY_FG = "#FFFFFF", "#000000"
    BORDER = "#DDD"

    def __init__(self):
        super().__init__()
        ensure_user_store()
        self.withdraw()  # hide main window until we’re ready

        # Show splash immediately (white, JACCS primary, small “Powered by LTID”)
        self.splash = Splash(
            self,
            jaccs_logo=resource_path("jaccs_logo.png"),
            ltid_logo=resource_path("ltid_logo.png"),
            title="Credit Scoring System",
            message="Initializing model…"
        )

        # Light-weight window config can happen now
        self.title("JACCS Credit Scoring System")
        self.configure(bg=self.BG_GRAY)
        self.geometry("800x850")
        self.resizable(True, True)

        # Defer heavy work to a background thread
        self.ai = None
        self.logo = None
        threading.Thread(target=self._heavy_init, daemon=True).start()

    def _heavy_init(self):
        """Heavy work: train/load the model, load images, etc. (NO Tk calls here)."""
        try:
            # 1) Load & train AI model (heavy)
            self.ai = AIModel("20250204Variables 002 - Final01 Used Car for work for training-cleand 0501.xlsx")
            # self.ai = AIModel("20250204Variables 002 - Final01.xlsx")
            
            # 2) Load header logo image (pure PIL work is OK here)
            from PIL import Image
            img = Image.open(resource_path("logo.png")).resize((180, 70), Image.LANCZOS)

            # Hand off any Tk object creation + UI build to the main thread
            self.after(0, lambda pil_img=img: self._finish_init(pil_img))
        except Exception as e:
            # Close splash and show an error if something goes wrong
            error_msg = str(e)
            self.after(0,
                       lambda: (self.splash.destroy(), tk.messagebox.showerror("Init Error", error_msg), self.destroy()))
            
    def _finish_init(self, pil_img):
        """Back on the main thread: build Tk widgets, close splash, show main window."""
        # Convert PIL image to Tk PhotoImage on the main thread
        self.logo = ImageTk.PhotoImage(pil_img)

        # Initialize state
        self.db_row = None
        self.ai_features = None
        self.contract_date_defaulted = False
        self._edit_entry = None
        self._editing = {"item": None, "column": None}

        # Build UI (your existing routines)
        self._build_scoring()
        self.scoring_frame.place_forget()
        self._build_login()

        # Close splash & show the main window
        if self.splash and self.splash.winfo_exists():
            self.splash.destroy()
        self.deiconify()

        self.title("JACCS Credit Scoring System")
        self.configure(bg=self.BG_GRAY)
        self.geometry("800x850")
        self.resizable(True, True)

        # 1) load & train AI model (already done in _heavy_init)
        # self.ai is already set

        # 2) load logo
        logo_file = resource_path("logo.png")
        img = Image.open(logo_file).resize((180, 70), Image.LANCZOS)
        self.logo = ImageTk.PhotoImage(img)

        # state
        self.db_row = None
        self.ai_features = None
        self.contract_date_defaulted = False
        self._edit_entry = None  # inline editor widget
        self._editing = {"item": None, "column": None}

        # 3) build UI
        self._build_scoring()
        self.scoring_frame.place_forget()
        self._build_login()

    def _decorate(self, w):
        w.configure(
            bd=0, relief="flat",
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.BORDER
        )
    
    # -- Login -- #
    def _build_login(self):
        f = self.login_frame = tk.Frame(self, bg="white")
        f.place(relx=0.5, rely=0.5, anchor="center", width=420, height=440)

        tk.Label(f, image=self.logo, bg="white").pack(pady=(30, 5))
        tk.Label(f, text="Please Sign In", bg="white", fg=self.GREEN,
                 font=font.Font(size=16, weight="bold")).pack(pady=(0, 20))

        self.login_email = PlaceholderEntry(
            f, placeholder="Email", fg=self.ENTRY_FG, bg=self.ENTRY_BG,
            insertbackground=self.ENTRY_FG, font=font.Font(size=12)
        )
        self.login_email.pack(fill="x", padx=40, ipady=8, pady=5)
        self._decorate(self.login_email)

        self.login_pass = PlaceholderEntry(
            f, placeholder="Password", fg=self.ENTRY_FG, bg=self.ENTRY_BG,
            show="*", insertbackground=self.ENTRY_FG, font=font.Font(size=12)
        )
        self.login_pass.pack(fill="x", padx=40, ipady=8, pady=5)
        self._decorate(self.login_pass)

        btn = tk.Button(
            f, text="Sign In", command=self._on_signin,
            bg=self.GREEN, fg="black",
            activebackground=self.GREEN, activeforeground="black",
            font=font.Font(size=12), cursor="hand2"
        )
        btn.pack(fill="x", padx=40, ipady=8, pady=(20, 5))
        self._decorate(btn)

    def _on_signin(self):
        email = self.login_email.get().strip()
        pwd = self.login_pass.get().strip()
        role = authenticate(email, pwd)
        if not role:
            return messagebox.showerror("Login Failed", "Invalid credentials")

        self.login_frame.place_forget()
        if role.lower() == "admin":
            self._show_admin()
        else:
            self._show_scoring()

    def _show_scoring(self):
        # hide admin if it exists
        if hasattr(self, "admin_frame"):
            self.admin_frame.place_forget()
        self.scoring_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_admin(self):
        if not hasattr(self, "admin_frame"):
            self.admin_frame = AdminDashboard(self, on_open_scoring=self._show_scoring, bg=self.BG_GRAY)
        self.admin_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _forgot_pw(self):
        top = tk.Toplevel(self); top.title("Reset Password")
        top.geometry("350x180"); top.configure(bg="white")
        tk.Label(top, text="Enter your email:", bg="white",
                 font=font.Font(size=12)).pack(pady=(20, 5))
        ent = PlaceholderEntry(top, placeholder="Email",
                               fg=self.ENTRY_FG, bg=self.ENTRY_BG,
                               insertbackground=self.ENTRY_FG,
                               font=font.Font(size=12))
        ent.pack(fill="x", padx=30, ipady=6)
        self._decorate(ent)
        def send():
            messagebox.showinfo("Password Reset",
                                f"If {ent.get()} exists, a reset link was sent.")
            top.destroy()
        btn = tk.Button(top, text="Send Reset Link", command=send,
                        bg=self.GREEN, fg="black",
                        font=font.Font(size=12), cursor="hand2")
        btn.pack(pady=(20, 0), ipady=6, ipadx=10)
        self._decorate(btn)

    # —— CREDIT SCORING SCREEN —— #
    def _build_scoring(self):
        f = self.scoring_frame = tk.Frame(self, bg=self.BG_GRAY)
        f.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = tk.Frame(f, bg="white")
        card.place(relx=0.5, rely=0.5, anchor="center", width=740, height=780)

        tk.Label(card, image=self.logo, bg="white").pack(pady=(20, 5))
        tk.Label(card, text="Credit Score Calculator", bg="white", fg=self.GREEN,
                 font=font.Font(size=18, weight="bold")).pack(pady=(0, 15))

        # Search (Party No + Application No)
        frm = tk.Frame(card, bg="white"); frm.pack(pady=(0, 10))
        self.ent_party = PlaceholderEntry(
            frm, placeholder="Party No (e.g., 201614)", fg=self.ENTRY_FG, bg=self.ENTRY_BG,
            insertbackground=self.ENTRY_FG, font=font.Font(size=12), width=20
        )
        self.ent_party.pack(side="left", ipady=6, padx=(0, 8))
        self._decorate(self.ent_party)

        self.ent_app = PlaceholderEntry(
            frm, placeholder="Application No (e.g., 2)", fg=self.ENTRY_FG, bg=self.ENTRY_BG,
            insertbackground=self.ENTRY_FG, font=font.Font(size=12), width=20
        )
        self.ent_app.pack(side="left", ipady=6, padx=(0, 8))
        self._decorate(self.ent_app)

        # Checkbox for CSV mode
        self.csv_mode = tk.BooleanVar()
        tk.Checkbutton(frm, text="Load from CSV", variable=self.csv_mode, bg="white").pack(side="left", padx=(10, 0))

        btn_fetch = tk.Button(frm, text="Fetch", command=self.fetch_customer,
                              bg=self.GREEN, fg="black",
                              activebackground=self.GREEN, activeforeground="black",
                              font=font.Font(size=12), cursor="hand2")
        btn_fetch.pack(side="left", ipady=3, ipadx=10)
        self._decorate(btn_fetch)

        # Details area (AI features only)
        tk.Label(card, text="AI Feature Inputs", bg="white", fg=self.GREEN,
                 font=font.Font(size=14, weight="bold")).pack(pady=(12, 2))
        tk.Label(card, text="(Double-click a Value to edit. Leave blank = Missing.)",
                 bg="white", fg="#555", font=font.Font(size=9)).pack()

        details_wrap = tk.Frame(card, bg="white")
        details_wrap.pack(fill="both", expand=True, padx=16)

        cols = ("Field", "Value")
        self.tree = ttk.Treeview(details_wrap, columns=cols, show="headings", height=18)
        self.tree.heading("Field", text="Field")
        self.tree.heading("Value", text="Value")
        self.tree.column("Field", width=300, anchor="w")
        self.tree.column("Value", width=380, anchor="w")

        vsb = ttk.Scrollbar(details_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Inline edit bindings
        self.tree.bind("<Double-1>", self._start_cell_edit)
        self.tree.bind("<Button-1>", self._maybe_finish_edit)

        # Calculate & AI Output
        frm3 = tk.Frame(card, bg="white"); frm3.pack(pady=12)
        btn2 = tk.Button(frm3, text="Calculate Credit Score",
                         command=self.calculate_score,
                         bg=self.GREEN, fg="black",
                         activebackground=self.GREEN, activeforeground="black",
                         font=font.Font(size=12), cursor="hand2")
        btn2.pack(side="left", ipady=6, ipadx=10, padx=(0, 10))
        self._decorate(btn2)

        tk.Label(frm3, text="AI-Predicted DPD:", bg="white", fg=self.ENTRY_FG, font=font.Font(size=12)).pack(side="left")
        self.dpd_var = tk.StringVar()

        tk.Label(frm3, textvariable=self.dpd_var, bg="white", fg=self.ENTRY_FG, font=font.Font(size=12), width=8, anchor="w").pack(side="left", padx=(5, 20), ipadx=10)

        # NEW: Credit Score UI
        tk.Label(frm3, text="Credit Score:", bg="white", fg=self.ENTRY_FG, font=font.Font(size=12)).pack(side="left")
        
        self.credit_var = tk.StringVar()
        tk.Label(frm3, textvariable=self.credit_var, bg="white", fg=self.ENTRY_FG, font=font.Font(size=12), width=8, anchor="w").pack(side="left", padx=(5, 0), ipadx=10)
        
        # NEW: "Show breakdown" button (starts hidden)
        self.btn_breakdown = tk.Button(
            frm3, text="Show\nBreakdown", command=self._show_breakdown_dialog,
            bg="#EEEEEE", fg="#000000", cursor="hand2"
        )
        self.btn_breakdown_is_packed = False

    # —— Fetch & map —— #
    def fetch_customer(self):
        # Clear previous
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.dpd_var.set("")
        # clear credit score too
        if hasattr(self, "credit_var"):
            self.credit_var.set("")
        self.db_row = None
        self.ai_features = None
        self.contract_date_defaulted = False

        if self.csv_mode.get():
            # Load from CSV
            csv_path = filedialog.askopenfilename(title="Select CSV file", filetypes=[("CSV files", "*.csv")])
            if not csv_path:
                return
            try:
                df = pd.read_csv(csv_path)
                if df.empty:
                    return messagebox.showerror("CSV Error", "CSV file is empty.")
                
                # Apply same preprocessing as training data
                if 'Longest DPD' in df.columns:
                    df['Original Longest DPD'] = df['Longest DPD']
                    df['Longest DPD'] = df['Longest DPD'].apply(self.ai.quantize_longest_dpd)
                
                needed_cols = self.ai.features + ["Original Longest DPD", "Longest DPD"] if 'Longest DPD' in df.columns else self.ai.features
                df = df[needed_cols] if all(col in df.columns for col in needed_cols) else df
                
                if "Contract Start Date" in df.columns:
                    df['Contract Start Date'] = pd.to_datetime(df['Contract Start Date'], format='%m/%d/%Y', errors='coerce')
                    df['Contract Start Date'].fillna(pd.Timestamp(0), inplace=True)
                    df['Contract Start Date'] = df['Contract Start Date'].astype(int) / 10**9
                
                numerical_cols = [c for c in self.ai.features if c not in self.ai.categorical_cols]
                for col in numerical_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
                
                df.drop_duplicates(inplace=True)
                
                if len(df) > 1:
                    messagebox.showwarning("Multiple Rows", f"CSV contains {len(df)} rows. Only the first row will be processed for inference.")
                
                # Use the first row as the data
                row = df.iloc[0].to_dict()
                # Convert to match DB format (assume CSV has same column names)
                self.db_row = row
            except Exception as e:
                return messagebox.showerror("CSV Error", f"Failed to load CSV: {e}")
        else:
            # Original DB fetch
            party_txt = self.ent_party.get().strip()
            app_txt = self.ent_app.get().strip()
            if party_txt.lower().startswith("party no"):
                party_txt = ""
            if app_txt.lower().startswith("application no"):
                app_txt = ""

            if not party_txt or not app_txt:
                return messagebox.showwarning("Missing", "Please enter Party No and Application No.")

            try:
                party_no = int(party_txt)
                application_no = int(app_txt)
            except ValueError:
                return messagebox.showerror("Invalid", "Party No and Application No must be integers.")

            try:
                row = fetch_ci_mock_crifv4(party_no, application_no)
            except Exception as e:
                return messagebox.showerror("DB Error", f"Failed to fetch: {e}")

            if not row:
                return messagebox.showinfo("No Data", "No matching record found.")

            self.db_row = row

        self.ai_features = self._row_to_ai_features(self.db_row)

        # Populate table in model's feature order
        for feat_name in self.ai.features:
            val = self.ai_features.get(feat_name, "")
            if feat_name == "Contract Start Date" and self.contract_date_defaulted:
                if val:
                    val = f"{val} (defaulted from missing)"
                else:
                    val = "(defaulted from missing)"
            if val is None or val == "":
                val = "Missing"
            self.tree.insert("", "end", values=(feat_name, str(val)))

    # —— Inline editing helpers —— #
    def _strip_defaulted_note(self, v: str) -> str:
        if not isinstance(v, str):
            return v
        note_idx = v.find(" (defaulted from missing)")
        return v[:note_idx] if note_idx != -1 else v
    
    def _start_cell_edit(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#2":
            return
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self._finish_edit(commit=True)
        x, y, w, h = self.tree.bbox(row, col)
        value = self.tree.set(row, "Value")
        value = self._strip_defaulted_note(value)
        self._edit_entry = tk.Entry(self.tree)
        self._edit_entry.insert(0, value)
        self._edit_entry.select_range(0, tk.END)
        self._edit_entry.focus()
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._editing["item"] = row
        self._editing["column"] = "Value"
        self._edit_entry.bind("<Return>", lambda e: self._finish_edit(commit=True))
        self._edit_entry.bind("<Escape>", lambda e: self._finish_edit(commit=False))
        self._edit_entry.bind("<FocusOut>", lambda e: self._finish_edit(commit=True))

    def _maybe_finish_edit(self, _event):
        self._finish_edit(commit=True)

    def _finish_edit(self, commit=True):
        if self._edit_entry is None:
            return
        row = self._editing.get("item")
        col = self._editing.get("column")
        new_val = self._edit_entry.get().strip() if commit else None
        self._edit_entry.destroy()
        self._edit_entry = None
        self._editing = {"item": None, "column": None}
        if not commit or row is None or col is None:
            return
        self.tree.set(row, col, new_val if new_val != "" else "Missing")
        feat_name = self.tree.set(row, "Field")
        clean_val = self._strip_defaulted_note(new_val)
        if feat_name in self.ai.categorical_cols:
            self.ai_features[feat_name] = (clean_val if clean_val else "Missing")
        else:
            if isinstance(clean_val, str):
                clean_val = clean_val.replace(",", "")
            self.ai_features[feat_name] = clean_val

    def _sync_tree_to_features(self):
        if not self.ai_features:
            return
        for item in self.tree.get_children():
            feat, val = self.tree.item(item, "values")
            val = self._strip_defaulted_note(val)
            if feat in self.ai.categorical_cols:
                self.ai_features[feat] = val if val and val.lower() != "missing" else "Missing"
            else:
                if isinstance(val, str):
                    val = val.replace(",", "")
                self.ai_features[feat] = "" if val == "Missing" else val

    # —— Mapping row -> features —— #
    def _row_to_ai_features(self, r: dict) -> dict:
        def num(*keys, default=0.0):
            for k in keys:
                if k in r and r[k] not in (None, ""):
                    try:
                        return float(str(r[k]).replace(",", ""))
                    except Exception:
                        pass
            return float(default)

        def txt(*keys, default="Missing"):
            for k in keys:
                if k in r and r[k] not in (None, ""):
                    s = str(r[k]).strip()
                    if s != "":
                        return s
            return default

        def fmt_mdY(v):
            if isinstance(v, (datetime, date)):
                return v.strftime("%m/%d/%Y")
            return str(v)
        
        dp_amt = num('Downpayment - Amount', 'DP')
        vlp = num('Vehicle List Price', 'ListCashPrice')
        amt_fin = num('Amount Financed - Amount', 'AmountFinance',
                      default=(vlp - dp_amt if (vlp or dp_amt) else 0.0))
        pay_terms = int(round(num('Payment Terms - Number', 'Terms', default=0)))

        brand_sc = num('Unit Brand   - Scoring Code', 'BrandScore', 'UnitBrandScore')
        typeunit_sc = num('Type of unit  - Scoring Code', 'TypeUnitScore', 'TypeUnitScoreCode')
        pricegap_sc = num('Price Gap - Scoring Code', 'PriceGapScore', 'PriceGap')
        loanhist_sc = num('Loan History - Scoring Code', 'CreditExpScore')
        bap_sc = num('BAP / CIC Findings - Scoring Code', 'BAPScore')

        income_amt = num('INCOME - Amount', 'TotalNetCombined', 'NetMonthly')
        dscr_pct = num('DSCR - %', 'DSCR')

        emp_type = txt('Employment Type  - type', 'EmpType', 'EmploymentCategory')
        tenure_sc = num('Employment / Business Tenure  - Scoring Code', 'TenureCategoryScore')

        home_type = txt('Home Ownership - TYPE', 'HomeOwner')
        res_ten_sc = num('Residence Tenure  - Scoring Code', 'ResidenceScore')
        citizen = txt('Citizenship  - type', 'Nationality', 'CBNationality')

        dealer_sc = num('Type of dealer  - Scoring Code', 'DealerScore')
        id_type = txt('Submitted ID   - type', 'IDSubmit')
        marital_sc = num('Marital Status - Scoring Code', 'CivilScore')

        product = txt('Product Type', 'Type', 'LoanPurpose')

        self.contract_date_defaulted = False
        raw_cstart = r.get('Contract Start Date') or r.get('ContractStartDate') or None
        if raw_cstart in (None, ""):
            yday = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
            cstart = yday
            self.contract_date_defaulted = True
        else:
            cstart = fmt_mdY(raw_cstart)

        loan_amort = num('LOAN AMORT', 'EMIFunction')
        mop = txt('Mode of Payment')
        cob = txt('Co-Borrowers', default=None)
        if cob is None:
            cob = 'Yes' if int(round(num('CBCount', default=0))) > 0 else 'Missing'

        age_val = int(round(num('Age', 'AGE', default=0)))
        lrd_val = txt('LRD')

        features = {
            'Amount Financed - Amount': amt_fin,
            'Downpayment - Amount': dp_amt,
            'Payment Terms - Number': pay_terms,
            'Unit Brand   - Scoring Code': brand_sc,
            'Type of unit  - Scoring Code': typeunit_sc,
            'Price Gap - Scoring Code': pricegap_sc,
            'Loan History - Scoring Code': loanhist_sc,
            'BAP / CIC Findings - Scoring Code': bap_sc,
            'INCOME - Amount': income_amt,
            'Employment Type  - type': emp_type,
            'Employment / Business Tenure  - Scoring Code': tenure_sc,
            'DSCR - %': dscr_pct,
            'Home Ownership - TYPE': home_type,
            'Residence Tenure  - Scoring Code': res_ten_sc,
            'Citizenship  - type': citizen,
            'Type of dealer  - Scoring Code': dealer_sc,
            'Submitted ID   - type': id_type,
            'Marital Status - Scoring Code': marital_sc,
            'Product Type': product,
            'Contract Start Date': cstart,
            'Vehicle List Price': vlp,
            'LOAN AMORT': loan_amort,
            'Mode of Payment': mop,
            'Co-Borrowers': cob,
            'Age': age_val,
            'LRD': lrd_val,
        }

        for k in ('Mode of Payment', 'Co-Borrowers', 'Product Type',
                  'Employment Type  - type', 'Home Ownership - TYPE',
                  'Citizenship  - type', 'Submitted ID   - type', 'LRD'):
            if features[k] in (None, ''):
                features[k] = 'Missing'

        return features
    
    # —— Predict —— #
    def _predict_with_current(self):
        self._sync_tree_to_features()
        feats = self.ai_features or self._row_to_ai_features(self.db_row)
        ai_pred = self.ai.predict_from_features(feats)
        self.dpd_var.set(f"{ai_pred:.2f}")

        # NEW: compute & show Credit Score = DPD * (-8/3) + 100
        credit_score = int((ai_pred * (-8.0/3.0)) + 100.0)
        if hasattr(self, "credit_var"):
            self.credit_var.set(f"{credit_score:.2f}")

        # Reveal "Show breakdown" button on first successful prediction
        if hasattr(self, "btn_breakdown") and not self.btn_breakdown_is_packed:
            self.btn_breakdown.pack(side="left", padx=(14, 0), ipadx=10, ipady=6)
            self.btn_breakdown_is_packed = True

        messagebox.showinfo("AI Prediction", "Prediction complete.")

    def _show_breakdown_dialog(self):
        if not self.ai_features:
            return messagebox.showwarning("Breakdown", "Please calculate a prediction first.")
        try:
            # Get SHAP breakdown from the model
            result = self.ai.breakdown_for_features(self.ai_features)
        except Exception as e:
            return messagebox.showerror("Breakdown Error", str(e))

        top = tk.Toplevel(self)
        top.title("Prediction Breakdown")
        top.configure(bg="white")
        top.geometry("700x560")
        top.minsize(640, 420)

        # Summary header
        header = tk.Frame(top, bg="white")
        header.pack(fill="x", padx=12, pady=(12, 6))

        def lab(txt, val):
            frm = tk.Frame(header, bg="white"); frm.pack(side="left", padx=14)
            tk.Label(frm, text=txt, bg="white", fg="#333", font=font.Font(size=10)).pack(anchor="w")
            tk.Label(frm, text=val, bg="white", fg="#000", font=font.Font(size=12, weight="bold")).pack(anchor="w")

        lab("Base value", f"{result['base_value']:.4f}")
        lab("Predicted DPD", f"{result['prediction']:.4f}")
        lab("Base + ΣSHAP", f"{result['reconstructed']:.4f}")

        # Table with contributions
        wrap = tk.Frame(top, bg="white"); wrap.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        cols = ("Feature", "Value", "Impact (SHAP)", "|Impact|")
        tree = ttk.Treeview(wrap, columns=cols, show="headings", height=18)
        for c, w, anchor in (
            ("Feature", 300, "w"),
            ("Value", 200, "w"),
            ("Impact (SHAP)", 120, "e"),
            ("|Impact|", 100, "e"),
        ):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor=anchor)

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscroll=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Insert rows (already sorted by abs impact)
        for row in result["rows"]:
            tree.insert("", "end", values=(
                row["feature"],
                str(row["value"]),
                f"{row['shap']:.6f}",
                f"{row['abs_shap']:.6f}",
            ))

        # Close shortcut
        top.bind("<Escape>", lambda _e: top.destroy())

    def calculate_score(self):
        if not self.db_row:
            return messagebox.showwarning("No Data", "Please fetch a customer first.")
        try:
            self._predict_with_current()
        except Exception as e:
            return messagebox.showerror("Prediction Error", f"Failed to predict: {e}")

if __name__ == "__main__":
    App().mainloop()