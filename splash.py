import sys, os, tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageColor

def resource_path(rel_path: str) -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel_path)  # type: ignore[attr-defined]
    return os.path.join(os.path.dirname(__file__), rel_path)

class Splash(tk.Toplevel):
    BG = "white"
    FG = "#1C1C1C"
    SUB = "#6A6F76"
    BORDER = "#E5E8EE"
    ACCENT = "#2E7D32"  # JACCS green

    def __init__(self, master, jaccs_logo="jaccs_logo.png", ltid_logo="ltid_logo.png",
                 title="Credit Scoring System", message="Initializing…"):
        
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=self.BG)

        # --- size & center ---
        w, h = 640, 360
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 3
        self.geometry(f"{w}x{h}+{x}+{y}")

        # --- outer card ---
        card = tk.Frame(self, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=w-24, height=h-20)

        # --- JACCS logo (hero) ---
        jac_img = self._load_logo(jaccs_logo, (260, 92))
        tk.Label(card, image=jac_img, bg=self.BG).pack(pady=(28, 8))

        # --- title ---
        tk.Label(card, text=title, bg=self.BG, fg=self.FG,
                 font=("SF Pro Display", 18, "bold")).pack()

        # --- "Powered by" (line above LTID) ---
        tk.Label(card, text="Powered by", bg=self.BG, fg=self.SUB,
                 font=("SF Pro Text", 10)).pack(pady=(8, 4))

        # LTID badge with lighter shadow
        badge_img = self._make_ltid_badge(ltid_logo, size=(220, 48), shadow_alpha=45, shadow_blur=3)
        tk.Label(card, image=badge_img, bg=self.BG, bd=0).pack()  # centered

        # accent line
        tk.Frame(card, bg=self.ACCENT, height=2).pack(fill="x", padx=40, pady=(10, 14))

        # --- progressbar + message ---
        style = ttk.Style(card)
        style.theme_use("clam")
        style.configure("Splash.Horizontal.TProgressbar",
                        troughcolor="#F2F4F8", bordercolor="#F2F4F8",
                        background=self.ACCENT, lightcolor=self.ACCENT, darkcolor=self.ACCENT)
        pb = ttk.Progressbar(card, mode="indeterminate",
                             style="Splash.Horizontal.TProgressbar", length=440)
        pb.pack(pady=(0, 8))
        pb.start(12)

        tk.Label(card, text=message, bg=self.BG, fg=self.SUB,
                 font=("SF Pro Text", 10)).pack()

        # keep refs
        self._keep_refs = [jac_img, badge_img]

        self.bind("<Escape>", lambda e: self.destroy())

    # ---------- helpers ----------
    def _load_logo(self, path, size_wh):
        try:
            p = path if os.path.isabs(path) else resource_path(path)
            img = Image.open(p).convert("RGBA").resize(size_wh, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return ImageTk.PhotoImage(Image.new("RGBA", size_wh, (0, 0, 0, 0)))

    def _make_ltid_badge(self, logo_path, size=(220, 48), shadow_alpha=45, shadow_blur=3):
        """Compose a rounded gradient badge with a softer shadow, then place the LTID logo on top."""
        w, h = size

        # gradient background (left → right)
        grad = self._h_gradient(size, "#1A2438", "#31435B", alpha=220)

        # rounded mask
        mask = Image.new("L", size, 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle((0, 0, w-1, h-1), radius=12, fill=255)
        grad.putalpha(mask)

        # softer shadow
        shadow = Image.new("RGBA", (w+6, h+6), (0, 0, 0, 0))
        ds = ImageDraw.Draw(shadow)
        ds.rounded_rectangle((3, 3, w+3-1, h+3-1), radius=12, fill=(0, 0, 0, shadow_alpha))
        shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow.alpha_composite(grad, dest=(0, 0))
        badge = shadow

        # place LTID logo
        try:
            p = logo_path if os.path.isabs(logo_path) else resource_path(logo_path)
            logo = Image.open(p).convert("RGBA")
            maxw, maxh = w-16, h-12
            ratio = min(maxw / logo.width, maxh / logo.height, 1.0)
            logo = logo.resize((int(logo.width*ratio), int(logo.height*ratio)), Image.LANCZOS)
            x = 8 + (maxw - logo.width) // 2
            y = 6 + (maxh - logo.height) // 2
            badge.alpha_composite(logo, dest=(x, y))
        except Exception:
            pass

        return ImageTk.PhotoImage(badge)

    def _h_gradient(self, size, c1, c2, alpha=220):
        w, h = size
        r1, g1, b1 = ImageColor.getrgb(c1)
        r2, g2, b2 = ImageColor.getrgb(c2)
        img = Image.new("RGBA", (w, h))
        for x in range(w):
            t = x / max(1, w-1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            img.paste((r, g, b, alpha), (x, 0, x+1, h))
        return img