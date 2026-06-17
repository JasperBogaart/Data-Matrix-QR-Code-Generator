#!/usr/bin/env python3
"""
QR Code Generator (met GUI)
============================

Genereert een PDF vol QR codes. Elke QR code bevat 1 of meer unieke
alfanumerieke codes (van een instelbare lengte, standaard 14 tekens),
gescheiden door een zelf te kiezen scheidingsteken — geen scheidingsteken
na de laatste code.

Alle gegenereerde deelcodes zijn GEGARANDEERD uniek binnen de hele batch.

------------------------------------------------------------
Benodigde packages (eenmalig installeren):

    pip install qrcode[pil] reportlab pillow

Starten:

    python qr_code_generator.py
------------------------------------------------------------
"""

import os
import random
import string
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import qrcode
    from PIL import Image  # noqa: F401  (nodig voor qrcode[pil])
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ImportError as exc:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror(
        "Ontbrekende packages",
        "Installeer eerst de benodigde packages met:\n\n"
        "pip install qrcode[pil] reportlab pillow\n\n"
        f"Foutmelding: {exc}",
    )
    raise SystemExit(1)


ALPHABET = string.ascii_uppercase + string.digits  # 36 mogelijke tekens per positie


# ----------------------------------------------------------------------
# Logica: unieke codes genereren en QR-payloads samenstellen
# ----------------------------------------------------------------------

def generate_unique_codes(amount, length):
    """Genereer `amount` unieke willekeurige codes van `length` tekens."""
    max_possible = len(ALPHABET) ** length
    if amount > max_possible:
        raise ValueError(
            f"Niet genoeg unieke combinaties mogelijk: gevraagd {amount}, "
            f"maximaal mogelijk met {length} tekens is {max_possible}.\n"
            f"Verhoog het aantal karakters per code."
        )

    codes = set()
    while len(codes) < amount:
        nog_nodig = amount - len(codes)
        for _ in range(nog_nodig):
            codes.add("".join(random.choices(ALPHABET, k=length)))
    return list(codes)


def build_qr_payloads(num_qr_codes, codes_per_qr, code_length, separator="|"):
    """Maak de payload-strings (gescheiden door `separator`) voor elke QR code."""
    total_needed = num_qr_codes * codes_per_qr
    all_codes = generate_unique_codes(total_needed, code_length)
    random.shuffle(all_codes)

    payloads = []
    idx = 0
    for _ in range(num_qr_codes):
        chunk = all_codes[idx: idx + codes_per_qr]
        idx += codes_per_qr
        payloads.append(separator.join(chunk))
    return payloads


def make_qr_image(data):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.convert("RGB")


# ----------------------------------------------------------------------
# PDF opbouwen: zoveel mogelijk QR codes van 5x5 cm per pagina (A4)
# ----------------------------------------------------------------------

def build_pdf(payloads, output_path, progress_callback=None):
    qr_size = 5 * cm
    margin = 1 * cm
    gap = 0.4 * cm

    page_width, page_height = A4
    cell_w = qr_size + gap
    cell_h = qr_size + gap

    cols = max(1, int((page_width - 2 * margin + gap) // cell_w))
    rows = max(1, int((page_height - 2 * margin + gap) // cell_h))
    per_page = cols * rows

    c = canvas.Canvas(output_path, pagesize=A4)

    for i, payload in enumerate(payloads):
        pos = i % per_page
        if pos == 0 and i != 0:
            c.showPage()

        col = pos % cols
        row = pos // cols

        cell_top = page_height - margin - row * cell_h
        x = margin + col * cell_w
        qr_y = cell_top - qr_size

        img = make_qr_image(payload)
        c.drawImage(ImageReader(img), x, qr_y, width=qr_size, height=qr_size)

        if progress_callback:
            progress_callback(i + 1, len(payloads))

    c.save()


# ----------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------

class QRGeneratorApp:
    def __init__(self, master):
        self.master = master
        master.title("Data Matrix QR Code Generator")
        master.geometry("460x440")
        master.resizable(False, False)

        tk.Label(
            master, text="Data Matrix QR Code Generator", font=("Segoe UI", 14, "bold")
        ).pack(pady=(18, 4))

        tk.Label(
            master,
            text="Generate a PDF with unique QR codes(5 x 5 cm)\n each QR is a string with ... random characters & chosen seperator.",
            font=("Segoe UI", 9),
            fg="#555555",
        ).pack(pady=(0, 14))

        form = tk.Frame(master)
        form.pack(padx=20)

        tk.Label(form, text="Amount of QR codes:", anchor="w", width=30).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.var_num_qr = tk.StringVar(value="50")
        tk.Entry(form, textvariable=self.var_num_qr, width=12).grid(row=0, column=1, pady=5)

        tk.Label(form, text="Amount per pallet:", anchor="w", width=30).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.var_codes_per_qr = tk.StringVar(value="12")
        tk.Entry(form, textvariable=self.var_codes_per_qr, width=12).grid(row=1, column=1, pady=5)

        tk.Label(form, text="Amount of characters per code:", anchor="w", width=30).grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.var_code_length = tk.StringVar(value="14")
        tk.Entry(form, textvariable=self.var_code_length, width=12).grid(row=2, column=1, pady=5)

        tk.Label(form, text="separator:", anchor="w", width=30).grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.var_separator = tk.StringVar(value="|")
        tk.Entry(form, textvariable=self.var_separator, width=12).grid(row=3, column=1, pady=5)

        self.btn_generate = tk.Button(
            master,
            text="Genereer PDF...",
            command=self.on_generate,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=7,
            relief="flat",
        )
        self.btn_generate.pack(pady=(20, 10))

        self.progress = ttk.Progressbar(master, length=400, mode="determinate")
        self.progress.pack(pady=(0, 8))

        self.status_var = tk.StringVar(value="Klaar om te starten.")
        tk.Label(master, textvariable=self.status_var, fg="#555555").pack()

    def on_generate(self):
        try:
            num_qr = int(self.var_num_qr.get())
            codes_per_qr = int(self.var_codes_per_qr.get())
            code_length = int(self.var_code_length.get())
            if num_qr <= 0 or codes_per_qr <= 0 or code_length <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ongeldige invoer", "Vul geldige positieve getallen in.")
            return

        separator = self.var_separator.get()
        if separator == "":
            messagebox.showerror("Ongeldige invoer", "Vul een scheidingsteken in.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Sla PDF op als...",
            defaultextension=".pdf",
            filetypes=[("PDF bestand", "*.pdf")],
            initialfile=f"qrcodes_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        )
        if not output_path:
            return

        self.btn_generate.config(state="disabled")
        self.progress["value"] = 0
        self.status_var.set("Unieke codes genereren...")

        thread = threading.Thread(
            target=self.run_generation,
            args=(num_qr, codes_per_qr, code_length, separator, output_path),
            daemon=True,
        )
        thread.start()

    def run_generation(self, num_qr, codes_per_qr, code_length, separator, output_path):
        try:
            payloads = build_qr_payloads(num_qr, codes_per_qr, code_length, separator)

            self.master.after(0, lambda: self.status_var.set("PDF opbouwen..."))

            def progress_cb(done, total):
                pct = int(done / total * 100)
                self.master.after(0, lambda: self.progress.config(value=pct))

            build_pdf(payloads, output_path, progress_callback=progress_cb)

            # Bewaar ook een tekstbestand met alle volledige QR-inhoud (traceerbaarheid)
            txt_path = os.path.splitext(output_path)[0] + "_codes.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(payloads))

            self.master.after(0, lambda: self.on_success(output_path, txt_path, len(payloads)))
        except Exception as e:
            self.master.after(0, lambda: self.on_error(str(e)))

    def on_success(self, pdf_path, txt_path, count):
        self.status_var.set(f"Klaar! {count} QR codes gegenereerd.")
        self.btn_generate.config(state="normal")
        messagebox.showinfo(
            "Gereed",
            f"De PDF is opgeslagen:\n{pdf_path}\n\n"
            f"Een overzicht van alle codes is opgeslagen in:\n{txt_path}",
        )

    def on_error(self, message):
        self.status_var.set("Er ging iets mis.")
        self.btn_generate.config(state="normal")
        messagebox.showerror("Fout", message)


if __name__ == "__main__":
    root = tk.Tk()
    app = QRGeneratorApp(root)
    root.mainloop()
