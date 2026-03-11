

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import io
import traceback
import sys
import os

# Ruta de poppler para ejecutable empaquetado
if getattr(sys, 'frozen', False):
    POPPLER_PATH = os.path.join(sys._MEIPASS, "poppler", "Library", "bin")
else:
    POPPLER_PATH = os.path.join(os.path.dirname(__file__), "poppler", "Library", "bin")

try:
    from PIL import Image, ImageTk, ImageDraw
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_OK = True
except ImportError:
    PYPDF_OK = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_OK = True
except ImportError:
    PDF2IMAGE_OK = False

# --- CONFIGURACIÓN DE POPPLER (¡IMPORTANTE!) ---
# Si no has añadido Poppler a tu PATH de sistema, descomenta y ajusta la siguiente línea.
# Asegúrate de que la ruta apunta a la carpeta 'bin' dentro de donde extrajiste Poppler.
# Si has configurado Poppler en el PATH de tu sistema, puedes dejar esta variable como None.
# El script intentará encontrarlo automáticamente.
POPPLER_PATH = r"C:\Users\Alexander\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"

# ── Paleta ────────────────────────────────────────────
C_BG      = "#FFFFFF"
C_SIDEBAR = "#20325e"
C_ACCENT  = "#7a142c"
C_HOVER   = "#5a0f21"
C_NAVY_L  = "#2d4475"
C_LIGHT   = "#f0f3f8"
C_PANEL   = "#f7f9fc"
C_BORDER  = "#dce3ee"
C_TEXT    = "#1a1a2e"
C_MUTED   = "#888888"
C_SUCCESS = "#1a6b3c"
C_SHADOW  = "#c8cdd8"

FONT_H1   = ("Helvetica", 17, "bold")
FONT_H2   = ("Helvetica", 12, "bold")
FONT_BODY = ("Helvetica", 10)
FONT_SM   = ("Helvetica", 9)
FONT_BTN  = ("Helvetica", 10, "bold")


# ══════════════════════════════════════════════════════
#  Widgets personalizados
# ══════════════════════════════════════════════════════

def _parent_bg(parent):
    """Obtiene el color de fondo del widget padre de forma segura."""
    try:
        return parent.cget("bg")
    except Exception:
        traceback.print_exc()
        return C_BG


class RoundedButton(tk.Canvas):
    """Boton con esquinas redondeadas usando polígono Canvas."""

    def __init__(self, parent, text, command=None,
                 width=160, height=38,
                 bg=C_ACCENT, fg="white", hover=C_HOVER,
                 radius=10, font=FONT_BTN, **kw):
        super().__init__(parent,
                         width=width, height=height,
                         highlightthickness=0, bd=0,
                         bg=_parent_bg(parent),
                         cursor="hand2", **kw)
        self._normal = bg
        self._hover  = hover
        self._fg     = fg
        self._text   = text
        self._font   = font
        self._r      = radius
        self._width  = width
        self._height = height
        self._cmd    = command

        self._draw(bg)
        self.bind("<Enter>",           lambda e: self._draw(hover))
        self.bind("<Leave>",           lambda e: self._draw(bg))
        self.bind("<Button-1>",        lambda e: self._draw(self._darken(bg)))
        self.bind("<ButtonRelease-1>", self._release)

    @staticmethod
    def _darken(c):
        r = max(0, int(c[1:3], 16) - 25)
        g = max(0, int(c[3:5], 16) - 25)
        b = max(0, int(c[5:7], 16) - 25)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self, color):
        self.delete("all")
        r, w, h = self._r, self._width, self._height
        # Polígono suavizado que simula bordes redondeados
        pts = [
            r, 0,
            w - r, 0,
            w, 0,
            w, r,
            w, h - r,
            w, h,
            w - r, h,
            r, h,
            0, h,
            0, h - r,
            0, r,
            0, 0,
        ]
        self.create_polygon(pts, fill=color, outline=color, smooth=True)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=self._fg, font=self._font)

    def _release(self, _e):
        self._draw(self._hover)
        if self._cmd:
            self.after(80, self._cmd)


class ModernSlider(tk.Frame):
    """Slider estilizado con badge de valor."""

    def __init__(self, parent, label, from_=0, to=100,
                 initial=50, unit="%", command=None, **kw):
        super().__init__(parent, bg=C_BG, **kw)
        self._cmd  = command
        self._unit = unit

        tk.Label(self, text=label, bg=C_BG,
                 fg=C_TEXT, font=FONT_BODY).pack(anchor="w")

        row = tk.Frame(self, bg=C_BG)
        row.pack(fill="x", pady=(4, 0))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("AM.Horizontal.TScale",
                         troughcolor=C_LIGHT,
                         background=C_ACCENT,
                         sliderthickness=18,
                         sliderrelief="flat",
                         borderwidth=0)

        self._var = tk.DoubleVar(value=initial)
        ttk.Scale(row, from_=from_, to=to, orient="horizontal",
                  variable=self._var,
                  style="AM.Horizontal.TScale",
                  command=self._changed).pack(
                      side="left", fill="x", expand=True, padx=(0, 10))

        self._badge = tk.Label(row, text=f"{initial}{unit}",
                               bg=C_ACCENT, fg="white",
                               font=FONT_SM, width=7,
                               relief="flat", padx=4, pady=3)
        self._badge.pack(side="right")

    def _changed(self, val):
        v = round(float(val))
        self._badge.configure(text=f"{v}{self._unit}")
        if self._cmd:
            self._cmd(v)

    def get(self):
        return round(self._var.get())


class SectionCard(tk.Frame):
    """Tarjeta con franja burdeos en la parte superior."""

    def __init__(self, parent, title, **kw):
        super().__init__(parent, bg=C_BG,
                         highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        tk.Frame(self, bg=C_ACCENT, height=3).pack(fill="x")

        hdr = tk.Frame(self, bg=C_PANEL, padx=12, pady=9)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=C_PANEL,
                 fg=C_SIDEBAR, font=FONT_H2).pack(side="left")

        self.body = tk.Frame(self, bg=C_BG, padx=12, pady=12)
        self.body.pack(fill="both", expand=True)


# ══════════════════════════════════════════════════════
#  Logica de marca de agua
# ══════════════════════════════════════════════════════

def _calc_size(page_w, page_h, img_w, img_h, scale_pct):
    ratio = img_w / img_h
    dw = page_w * (scale_pct / 100.0)
    dh = dw / ratio
    if dh > page_h:
        dh = page_h * (scale_pct / 100.0)
        dw = dh * ratio
    return dw, dh


def _apply_opacity(img, opacity):
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * opacity))
    img.putalpha(a)
    return img


def create_watermark_pdf_bytes(image_path, page_w, page_h,
                               opacity, scale_pct):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))

    img = Image.open(image_path).convert("RGBA")
    img = _apply_opacity(img, opacity)
    dw, dh = _calc_size(page_w, page_h, img.width, img.height, scale_pct)

    tmp = io.BytesIO()
    img.save(tmp, format="PNG")
    tmp.seek(0)

    x = (page_w - dw) / 2
    y = (page_h - dh) / 2
    c.saveState()
    c.drawImage(ImageReader(tmp), x, y, width=dw, height=dh, mask="auto")
    c.restoreState()
    c.save()
    buf.seek(0)
    return buf.read()


def apply_watermark_to_all_pages(input_path, wm_img_path, opacity, scale_pct, output_path):
    """Aplica la marca de agua a cada página recalculando el tamaño según las dimensiones de la página."""
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)
        
        # Crear marca de agua específica para este tamaño de página
        wm_bytes = create_watermark_pdf_bytes(wm_img_path, pw, ph, opacity, scale_pct)
        wm_page = PdfReader(io.BytesIO(wm_bytes)).pages[0]
        
        page.merge_page(wm_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


def render_preview_image(pdf_path, img_path, opacity, scale_pct,
                          max_w=480, max_h=580):
    pages = convert_from_path(pdf_path, dpi=110,
                           first_page=1, last_page=1,
                           poppler_path=POPPLER_PATH)
    base  = pages[0].convert("RGBA")
    bw, bh = base.size

    wm = Image.open(img_path).convert("RGBA")
    dw, dh = _calc_size(bw, bh, wm.width, wm.height, scale_pct)
    wm = wm.resize((int(dw), int(dh)), Image.LANCZOS)
    wm = _apply_opacity(wm, opacity)

    composite = base.copy()
    composite.paste(wm,
                    ((bw - int(dw)) // 2, (bh - int(dh)) // 2),
                    wm)

    ratio = min(max_w / bw, max_h / bh)
    composite = composite.resize(
        (int(bw * ratio), int(bh * ratio)), Image.LANCZOS)
    return composite.convert("RGB")


# ══════════════════════════════════════════════════════
#  Ventana principal
# ══════════════════════════════════════════════════════

class AquaMarkApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Marl-ICEP — Marca de Agua para PDF")
        self.configure(bg=C_BG)
        self.resizable(True, True)
        self.minsize(900, 580)

        self.pdf_path = tk.StringVar()
        self.img_path = tk.StringVar()
        
        # Inicialización preventiva de atributos
        self._preview_img    = None
        self._preview_thread = None
        self._debounce_id    = None
        self._thumb          = None
        self._progress       = None
        self._status         = None
        self._canvas         = None
        self._pdf_lbl        = None
        self._img_lbl        = None
        self._sl_opacity     = None
        self._sl_size        = None

        self._check_deps()
        self._build_ui()
        self._center(960, 660)

    # ── Dependencias ─────────────────────────────────

    def _check_deps(self):
        missing = []
        if not PILLOW_OK:     missing.append("Pillow")
        if not REPORTLAB_OK: missing.append("reportlab")
        if not PYPDF_OK:     missing.append("pypdf")
        if not PDF2IMAGE_OK: missing.append("pdf2image")
        if missing:
            messagebox.showwarning(
                "Dependencias faltantes",
                "Instala los paquetes faltantes y reinicia:\n\n"
                + "  pip install " + " ".join(missing))

    # ── Layout ───────────────────────────────────────

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        # Barra superior
        topbar = tk.Frame(self, bg=C_SIDEBAR, height=56)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Marl-ICEP",
                 bg=C_SIDEBAR, fg="white",
                 font=FONT_H1).pack(side="left", padx=(20, 8), pady=14)
        tk.Label(topbar, text="Marca de Agua Profesional para PDF",
                 bg=C_SIDEBAR, fg="#8da8d4",
                 font=("Helvetica", 9)).pack(side="left", pady=21)
        tk.Label(topbar, text="v1.0",
                 bg=C_ACCENT, fg="white",
                 font=FONT_SM, padx=8, pady=4).pack(
                     side="right", padx=18, pady=16)

        # Contenido
        main = tk.Frame(self, bg=C_BG)
        main.pack(fill="both", expand=True)

        # Izquierda
        left = tk.Frame(main, bg=C_BG, width=385)
        left.pack(side="left", fill="y", padx=(18, 8), pady=16)
        left.pack_propagate(False)
        self._build_left(left)

        # Divisor
        tk.Frame(main, bg=C_BORDER, width=1).pack(
            side="left", fill="y", pady=8)

        # Derecha (preview)
        right = tk.Frame(main, bg=C_BG)
        right.pack(side="left", fill="both", expand=True,
                   padx=(8, 18), pady=16)
        self._build_right(right)

        # Barra inferior
        botbar = tk.Frame(self, bg=C_LIGHT, height=62,
                          highlightbackground=C_BORDER,
                          highlightthickness=1)
        botbar.pack(fill="x", side="bottom")
        botbar.pack_propagate(False)

        inner = tk.Frame(botbar, bg=C_LIGHT)
        inner.pack(expand=True, fill="y")

        RoundedButton(inner, "Aplicar y Guardar PDF",
                      command=self._apply_watermark,
                      width=215, height=38,
                      bg=C_ACCENT, hover=C_HOVER).pack(
                          side="left", padx=(12, 8), pady=12)

        RoundedButton(inner, "Actualizar Vista Previa",
                      command=lambda: self._trigger_preview(force=True),
                      width=210, height=38,
                      bg=C_SIDEBAR, hover=C_NAVY_L).pack(
                          side="left", padx=8, pady=12)

        self._progress = ttk.Progressbar(inner, mode="indeterminate",
                                          length=130)
        self._progress.pack(side="left", padx=16, pady=20)

    def _build_left(self, parent):
        # Seccion PDF
        c1 = SectionCard(parent, "Documento PDF")
        c1.pack(fill="x", pady=(0, 10))

        self._pdf_lbl = tk.Label(c1.body,
                                  text="Ningun archivo seleccionado",
                                  bg=C_BG, fg=C_MUTED, font=FONT_SM,
                                  anchor="w", wraplength=320)
        self._pdf_lbl.pack(fill="x", pady=(0, 8))

        RoundedButton(c1.body, "Seleccionar PDF",
                      command=self._pick_pdf,
                      width=190, height=36,
                      bg=C_SIDEBAR, hover=C_NAVY_L).pack(anchor="w")

        # Seccion imagen
        c2 = SectionCard(parent, "Imagen de Marca de Agua")
        c2.pack(fill="x", pady=(0, 10))

        self._thumb = tk.Label(c2.body, bg=C_PANEL,
                                text="Sin imagen", fg=C_MUTED,
                                font=FONT_SM, width=10, height=3)
        self._thumb.pack(pady=(0, 6))

        self._img_lbl = tk.Label(c2.body,
                                  text="Ninguna imagen seleccionada",
                                  bg=C_BG, fg=C_MUTED, font=FONT_SM,
                                  anchor="w", wraplength=320)
        self._img_lbl.pack(fill="x", pady=(0, 8))

        RoundedButton(c2.body, "Seleccionar Imagen",
                      command=self._pick_image,
                      width=190, height=36,
                      bg=C_SIDEBAR, hover=C_NAVY_L).pack(anchor="w")

        # Seccion configuracion
        c3 = SectionCard(parent, "Configuracion")
        c3.pack(fill="x", pady=(0, 10))

        self._sl_opacity = ModernSlider(
            c3.body, "Opacidad de la marca de agua",
            from_=5, to=100, initial=40, unit="%",
            command=self._schedule_preview)
        self._sl_opacity.pack(fill="x", pady=(0, 14))

        self._sl_size = ModernSlider(
            c3.body, "Tamano de la marca de agua",
            from_=10, to=100, initial=50, unit="%",
            command=self._schedule_preview)
        self._sl_size.pack(fill="x")

    def _build_right(self, parent):
        hdr = tk.Frame(parent, bg=C_BG)
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text="Vista Previa",
                 bg=C_BG, fg=C_SIDEBAR,
                 font=("Helvetica", 13, "bold")).pack(side="left")

        self._status = tk.Label(hdr, text="", bg=C_BG,
                                 fg=C_MUTED, font=FONT_SM)
        self._status.pack(side="right")

        frame = tk.Frame(parent, bg=C_LIGHT,
                          highlightbackground=C_BORDER,
                          highlightthickness=1)
        frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(frame, bg=C_LIGHT,
                                  highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", self._on_resize)
        self._show_placeholder()

    # ── Archivos ──────────────────────────────────────

    def _pick_pdf(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if path:
            self.pdf_path.set(path)
            self._pdf_lbl.configure(
                text=os.path.basename(path), fg=C_SIDEBAR)
            self._trigger_preview()

    def _pick_image(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[("Imagenes",
                        "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"),
                       ("Todos", "*.*")])
        if path:
            self.img_path.set(path)
            self._img_lbl.configure(
                text=os.path.basename(path), fg=C_SIDEBAR)
            self._update_thumb(path)
            self._trigger_preview()

    def _update_thumb(self, path):
        if not PILLOW_OK or not self._thumb:
            return
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((90, 60), Image.LANCZOS)
            checker = Image.new("RGBA", img.size)
            draw = ImageDraw.Draw(checker)
            cs = 8
            for y in range(0, img.height, cs):
                for x in range(0, img.width, cs):
                    col = (210, 210, 210, 255) \
                          if (x // cs + y // cs) % 2 == 0 \
                          else (175, 175, 175, 255)
                    draw.rectangle([x, y, x + cs, y + cs], fill=col)
            checker.paste(img, (0, 0), img)
            photo = ImageTk.PhotoImage(checker)
            self._thumb.configure(image=photo, text="",
                                   width=img.width, height=img.height)
            self._thumb._photo = photo
        except Exception:
            traceback.print_exc()

    # ── Vista previa ──────────────────────────────────

    def _schedule_preview(self, *_):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(450, self._trigger_preview)

    def _trigger_preview(self, force=False):
        if not self.pdf_path.get() or not self.img_path.get():
            return
        if not PILLOW_OK:
            self._status.configure(
                text="Pillow no disponible", fg="red")
            return
        if not PDF2IMAGE_OK:
            self._status.configure(
                text="pdf2image no disponible", fg="red")
            return
        if self._preview_thread and self._preview_thread.is_alive():
            return
        self._status.configure(text="Generando...", fg=C_MUTED)
        if self._progress:
            self._progress.start(10)
        self._preview_thread = threading.Thread(
            target=self._preview_worker, daemon=True)
        self._preview_thread.start()

    def _preview_worker(self):
        try:
            img = render_preview_image(
                self.pdf_path.get(), self.img_path.get(),
                self._sl_opacity.get() / 100.0,
                self._sl_size.get(),
                max_w=490, max_h=600)
            self._preview_img = img
            self.after(0, self._show_preview)
        except Exception as e:
            traceback.print_exc()
            # Captura el valor de 'e' en el momento de la definición del lambda
            self.after(0, lambda e=e: self._status.configure(
                text=f"Error: {e}", fg="red"))
        finally:
            if self._progress:
                self.after(0, self._progress.stop)

    def _show_preview(self):
        if not self._preview_img:
            return
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        img = self._preview_img.copy()
        iw, ih = img.size
        # Evitar división por cero o ratios inválidos en redimensionamiento extremo
        avail_w = max(1, cw - 24)
        avail_h = max(1, ch - 24)
        ratio = min(avail_w / iw, avail_h / ih)
        nw = max(1, int(iw * ratio))
        nh = max(1, int(ih * ratio))
        img = img.resize((nw, nh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        x0 = (cw - nw) // 2
        y0 = (ch - nh) // 2
        self._canvas.delete("all")

        # Sombra
        self._canvas.create_rectangle(
            x0 + 5, y0 + 5, x0 + nw + 5, y0 + nh + 5,
            fill=C_SHADOW, outline="")

        self._canvas.create_image(x0, y0, anchor="nw", image=photo)
        self._canvas._photo = photo
        self._status.configure(text="Vista previa lista", fg=C_SUCCESS)

    def _show_placeholder(self):
        self._canvas.delete("all")
        self._canvas.create_text(
            240, 200,
            text="Selecciona un PDF y una imagen\npara ver la vista previa aqui",
            fill="#b0b8c8", font=("Helvetica", 12), justify="center")

    def _on_resize(self, _):
        if self._preview_img:
            self._show_preview()
        else:
            self._show_placeholder()

    # ── Guardar ───────────────────────────────────────

    def _apply_watermark(self):
        if not (REPORTLAB_OK and PYPDF_OK and PILLOW_OK):
            messagebox.showerror("Error",
                                  "Faltan dependencias: reportlab, pypdf o Pillow")
            return
        if not self.pdf_path.get():
            messagebox.showwarning("Falta PDF",
                                    "Selecciona un archivo PDF primero.")
            return
        if not self.img_path.get():
            messagebox.showwarning("Falta imagen",
                                    "Selecciona una imagen de marca de agua.")
            return

        out = filedialog.asksaveasfilename(
            title="Guardar PDF resultante",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="documento_con_marca_de_agua.pdf")
        if not out:
            return

        if self._progress:
            self._progress.start(10)
        self._status.configure(text="Procesando...", fg=C_MUTED)

        def worker():
            try:
                apply_watermark_to_all_pages(
                    self.pdf_path.get(), 
                    self.img_path.get(),
                    self._sl_opacity.get() / 100.0,
                    self._sl_size.get(),
                    out
                )
                self.after(0, lambda: self._done(out))
            except Exception as e:
                traceback.print_exc()
                # Captura el valor de 'e' en el momento de la definición del lambda
                self.after(0, lambda e=e: messagebox.showerror(
                    "Error", f"No se pudo guardar:\n\n{e}"))
            finally:
                if self._progress:
                    self.after(0, self._progress.stop)

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, path):
        self._status.configure(text="PDF guardado", fg=C_SUCCESS)
        messagebox.showinfo("Listo",
                             f"PDF guardado correctamente en:\n\n{path}")


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = AquaMarkApp()
    app.mainloop()