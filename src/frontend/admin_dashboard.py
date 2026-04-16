import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../..')))

import tkinter as tk
from tkinter import ttk, messagebox, font
from src.backend.users import list_users, add_user, delete_user, update_password, set_role


class AdminDashboard(tk.Frame):
    GREEN = "#2E7D32"

    def __init__(self, master, on_open_scoring=None, **kwargs):
        super().__init__(master, bg=kwargs.get("bg", "#F0F0F0"))
        self.on_open_scoring = on_open_scoring

        card = tk.Frame(self, bg="white")
        card.place(relx=0.5, rely=0.5, anchor="center", width=740, height=660)

        tk.Label(card, text="Admin Dashboard", bg="white",
                 font=font.Font(size=18, weight="bold"), fg=self.GREEN).pack(pady=(18, 6))
        tk.Label(card, text="Manage users (add / delete / reset password / toggle admin)",
                 bg="white", fg="#555").pack(pady=(0, 10))

        # Users table
        wrap = tk.Frame(card, bg="white"); wrap.pack(fill="both", expand=True, padx=16, pady=8)
        cols = ("Email", "Role")
        self.user_tree = ttk.Treeview(wrap, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (460, 160)):
            self.user_tree.heading(c, text=c)
            self.user_tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.user_tree.yview)
        self.user_tree.configure(yscroll=vsb.set)
        self.user_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Buttons row
        btns = tk.Frame(card, bg="white"); btns.pack(pady=10)
        tk.Button(btns, text="Add User", command=self._add_user_dialog,
                  bg=self.GREEN, fg="black", cursor="hand2").pack(side="left", padx=6, ipadx=8, ipady=6)
        tk.Button(btns, text="Reset Password", command=self._reset_password_dialog,
                  bg=self.GREEN, fg="black", cursor="hand2").pack(side="left", padx=6, ipadx=8, ipady=6)
        tk.Button(btns, text="Delete User", command=self._delete_user,
                  bg=self.GREEN, fg="black", cursor="hand2").pack(side="left", padx=6, ipadx=8, ipady=6)
        tk.Button(btns, text="Toggle Admin", command=self._toggle_admin,
                  bg=self.GREEN, fg="black", cursor="hand2").pack(side="left", padx=6, ipadx=8, ipady=6)

        tk.Button(card, text="Open Scoring App", command=self._open_scoring,
                  bg="#eee", fg="#000", cursor="hand2").pack(pady=(4, 16), ipadx=10, ipady=6)

        self._refresh()

    # ---------- helpers ----------
    def _refresh(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        for u in list_users():
            self.user_tree.insert("", "end", values=(u["email"], u["role"]))

    def _selected_email(self) -> str:
        sel = self.user_tree.selection()
        if not sel:
            messagebox.showwarning("Select user", "Please select a user.")
            return ""
        return self.user_tree.item(sel[0], "values")[0]

    def _count_admins(self) -> int:
        return sum(1 for u in list_users() if u["role"] == "admin")

    # ---------- actions ----------
    def _add_user_dialog(self):
        import re
        top = tk.Toplevel(self)
        top.title("Add User")
        top.configure(bg="white")
        top.transient(self.winfo_toplevel())
        top.grab_set()
        top.lift()

        # Bigger dialog so buttons never get clipped
        D_W, D_H = 520, 280
        self.update_idletasks()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        pw, ph = max(self.winfo_width(), D_W), max(self.winfo_height(), D_H)
        x = px + (pw - D_W) // 2
        y = py + (ph - D_H) // 2
        top.geometry(f"{D_W}x{D_H}+{x}+{y}")
        top.minsize(D_W, D_H)
        top.resizable(False, False)

        # --- content ---
        container = tk.Frame(top, bg="white")
        container.pack(fill="both", expand=True)

        form = tk.Frame(container, bg="white")
        form.pack(fill="x", padx=16, pady=(16, 8))
        form.grid_columnconfigure(1, weight=1)

        tk.Label(form, text="Email", bg="white").grid(row=0, column=0, sticky="e", padx=(6, 10), pady=6)
        email_e = tk.Entry(form)
        email_e.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=6)

        tk.Label(form, text="Password", bg="white").grid(row=1, column=0, sticky="e", padx=(6, 10), pady=6)
        pass_e = tk.Entry(form, show="*")
        pass_e.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=6)

        # ✅ FIX: give BooleanVar a master and pass value=...
        is_admin = tk.BooleanVar(master=top, value=False)
        tk.Checkbutton(form, text="Add as admin", variable=is_admin, bg="white") \
            .grid(row=2, column=1, sticky="w", padx=(0, 6), pady=(2, 8))

        # Buttons row
        btns = tk.Frame(container, bg="white")
        btns.pack(fill="x", padx=16, pady=(6, 16))

        def do_save():
            email = email_e.get().strip()
            pwd = pass_e.get().strip()
            if not email or not pwd:
                messagebox.showwarning("Add User", "Email and password are required.")
                return
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                messagebox.showwarning("Add User", "Please enter a valid email address.")
                return
            try:
                add_user(email, pwd, role="admin" if is_admin.get() else "user")
                top.destroy()
                self._refresh()
                messagebox.showinfo("Add User", "User added successfully.")
            except Exception as e:
                messagebox.showerror("Add User", str(e))

        cancel_btn = tk.Button(btns, text="Cancel", command=top.destroy, bg="#EEEEEE", fg="black", cursor="hand2")
        save_btn = tk.Button(btns, text="Save", command=do_save, bg=self.GREEN, fg="black", cursor="hand2")
        cancel_btn.pack(side="right", padx=6, ipadx=12, ipady=6)
        save_btn.pack(side="right", padx=6, ipadx=12, ipady=6)

        # keyboard shortcuts
        top.bind("<Return>", lambda _e: do_save())
        top.bind("<Escape>", lambda _e: top.destroy())
        email_e.focus_set()

    def _reset_password_dialog(self):
        email = self._selected_email()
        if not email: return
        top = tk.Toplevel(self); top.title(f"Reset Password — {email}"); top.configure(bg="white")
        tk.Label(top, text="New Password", bg="white").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        pass_e = tk.Entry(top, width=32, show="*"); pass_e.grid(row=0, column=1, padx=8, pady=8)
        def do_reset():
            try:
                update_password(email, pass_e.get().strip())
                top.destroy()
                messagebox.showinfo("Reset Password", "Password updated.")
            except Exception as e:
                messagebox.showerror("Reset Password", str(e))
        tk.Button(top, text="Save", command=do_reset, bg=self.GREEN, fg="black").grid(row=1, column=1, sticky="e", padx=8, pady=10)

    def _delete_user(self):
        email = self._selected_email()
        if not email: return
        # prevent locking yourself out: don't delete last admin
        sel_role = None
        for item in self.user_tree.get_children():
            vals = self.user_tree.item(item, "values")
            if vals and vals[0] == email:
                sel_role = vals[1]
                break
        if sel_role == "admin" and self._count_admins() <= 1:
            return messagebox.showwarning("Delete User", "Cannot delete the last admin.")
        if not messagebox.askyesno("Delete User", f"Delete '{email}'?"):
            return
        try:
            delete_user(email)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Delete User", str(e))

    def _toggle_admin(self):
        email = self._selected_email()
        if not email: return
        # find current role
        cur_role = None
        for item in self.user_tree.get_children():
            vals = self.user_tree.item(item, "values")
            if vals and vals[0] == email:
                cur_role = vals[1]
                break
        # enforce at least one admin
        if cur_role == "admin" and self._count_admins() <= 1:
            return messagebox.showwarning("Toggle Admin", "There must be at least one admin.")
        new_role = "user" if cur_role == "admin" else "admin"
        try:
            set_role(email, new_role)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Toggle Admin", str(e))

    def _open_scoring(self):
        if callable(self.on_open_scoring):
            self.on_open_scoring()
