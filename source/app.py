"""
Visual PDF Signature Field Placement Tool
Lets the user draw rectangles on a PDF page preview and save them as
signature fields using pyHanko.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image, ImageTk
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec, append_signature_field

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

CANVAS_MAX_W = 600
CANVAS_MAX_H = 800


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PendingField:
    field_name: str                              # e.g. "Sig_1"
    page_index: int                              # 0-based (pyHanko)
    page_label: int                              # 1-based (display)
    pdf_box: tuple[float, float, float, float]   # ll_x, ll_y, ur_x, ur_y (PDF pts)


@dataclass
class AppState:
    pdf_path: Optional[str] = None
    total_pages: int = 0
    current_page_index: int = 0        # 0-based
    page_width_pts: float = 0.0        # native PDF page width in points
    page_height_pts: float = 0.0       # native PDF page height in points
    display_width_px: int = 0          # actual rendered image width
    display_height_px: int = 0         # actual rendered image height
    pending_fields: list = field(default_factory=list)  # list[PendingField]
    field_counter: int = 1             # monotonically increments for unique names
    drag_start: Optional[tuple] = None  # canvas (x, y) where drag began
    drag_end: Optional[tuple] = None    # canvas (x, y) current drag end


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

class CoordConverter:
    """Pure math: convert between canvas pixels and PDF points."""

    @staticmethod
    def scale(state: AppState) -> tuple[float, float]:
        """Return (scale_x, scale_y): pixels per PDF point."""
        if state.page_width_pts == 0 or state.page_height_pts == 0:
            return 1.0, 1.0
        sx = state.display_width_px / state.page_width_pts
        sy = state.display_height_px / state.page_height_pts
        return sx, sy

    @staticmethod
    def canvas_to_pdf(
        state: AppState,
        cx1: float, cy1: float,
        cx2: float, cy2: float,
    ) -> tuple[float, float, float, float]:
        """
        Convert canvas pixel rectangle to PDF-space box (ll_x, ll_y, ur_x, ur_y).
        Y-axis is inverted: canvas top=0 → PDF bottom.
        """
        sx, sy = CoordConverter.scale(state)
        pdf_h = state.page_height_pts

        # normalise so left < right, top < bottom in canvas space
        left   = max(0, min(cx1, cx2))
        right  = min(state.display_width_px, max(cx1, cx2))
        top    = max(0, min(cy1, cy2))
        bottom = min(state.display_height_px, max(cy1, cy2))

        ll_x = left   / sx
        ur_x = right  / sx
        ll_y = pdf_h - (bottom / sy)   # invert Y
        ur_y = pdf_h - (top    / sy)   # invert Y

        return (ll_x, ll_y, ur_x, ur_y)

    @staticmethod
    def pdf_to_canvas(
        state: AppState,
        ll_x: float, ll_y: float,
        ur_x: float, ur_y: float,
    ) -> tuple[float, float, float, float]:
        """Convert PDF-space box back to canvas pixel rectangle (x1,y1,x2,y2)."""
        sx, sy = CoordConverter.scale(state)
        pdf_h = state.page_height_pts

        cx1 = ll_x * sx
        cx2 = ur_x * sx
        cy1 = (pdf_h - ur_y) * sy
        cy2 = (pdf_h - ll_y) * sy
        return (cx1, cy1, cx2, cy2)


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

class PageRenderer:
    """Renders a PDF page to a PIL image using PyMuPDF."""

    def render(
        self,
        pdf_path: str,
        page_index: int,
        max_width: int = CANVAS_MAX_W,
        max_height: int = CANVAS_MAX_H,
    ) -> tuple[Image.Image, int, int, float, float]:
        """
        Returns (pil_image, actual_px_w, actual_px_h, pdf_page_w_pts, pdf_page_h_pts).
        """
        doc = fitz.open(pdf_path)
        page = doc[page_index]
        rect = page.rect  # width/height in PDF points

        zoom = min(max_width / rect.width, max_height / rect.height)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()

        return img, pix.width, pix.height, rect.width, rect.height


# ---------------------------------------------------------------------------
# Batch save helper
# ---------------------------------------------------------------------------

def save_all_fields(
    input_pdf: str,
    output_pdf: str,
    fields: list[PendingField],
) -> None:
    """Open the PDF once, append all signature fields, write once."""
    with open(input_pdf, "rb") as inf:
        writer = IncrementalPdfFileWriter(inf)
        for f in fields:
            append_signature_field(
                writer,
                SigFieldSpec(
                    sig_field_name=f.field_name,
                    on_page=f.page_index,
                    box=f.pdf_box,
                ),
            )
        with open(output_pdf, "wb") as outf:
            writer.write(outf)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class App:
    CANVAS_TAG_PREVIEW = "preview_img"
    CANVAS_TAG_DRAG    = "drag_rect"
    CANVAS_TAG_SAVED   = "saved_rect"

    def __init__(
        self,
        root: tk.Tk,
        dnd_available: bool = False,
    ) -> None:
        self.root = root
        self.root.title("PDF Signature Field Placer")
        self.root.resizable(False, False)
        self.dnd_available = dnd_available

        self.state    = AppState()
        self.renderer = PageRenderer()
        self.converter = CoordConverter()

        # Keep a reference so the image is not garbage-collected
        self._photo: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        if self.dnd_available:
            self._setup_dnd()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 6, "pady": 4}

        # ---- top bar ----
        top = tk.Frame(self.root, bd=1, relief=tk.GROOVE)
        top.pack(fill=tk.X, **pad)

        file_label = "Drop a PDF here or click Browse"
        if not self.dnd_available:
            file_label = "Click Browse to open a PDF"
        self.lbl_file = tk.Label(top, text=file_label, anchor="w")
        self.lbl_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        tk.Button(top, text="Browse", command=self._browse).pack(side=tk.RIGHT, padx=4)

        # ---- nav bar ----
        nav = tk.Frame(self.root)
        nav.pack(fill=tk.X, **pad)

        tk.Label(nav, text="Page:").pack(side=tk.LEFT)
        self.entry_page = tk.Entry(nav, width=5)
        self.entry_page.pack(side=tk.LEFT, padx=2)
        self.entry_page.bind("<Return>", lambda _e: self._load_page())

        self.lbl_total = tk.Label(nav, text="/ —")
        self.lbl_total.pack(side=tk.LEFT, padx=2)

        tk.Button(nav, text="Load Page", command=self._load_page).pack(side=tk.LEFT, padx=6)
        tk.Button(nav, text="◀", width=3, command=self._prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(nav, text="▶", width=3, command=self._next_page).pack(side=tk.LEFT, padx=2)

        self.lbl_nav_err = tk.Label(nav, text="", fg="red")
        self.lbl_nav_err.pack(side=tk.LEFT)

        # ---- main area ----
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, **pad)

        # Canvas (left)
        canvas_frame = tk.Frame(main, bd=1, relief=tk.SUNKEN,
                                width=CANVAS_MAX_W, height=CANVAS_MAX_H)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        canvas_frame.pack_propagate(False)

        self.canvas = tk.Canvas(canvas_frame, cursor="crosshair",
                                bg="#cccccc", width=CANVAS_MAX_W, height=CANVAS_MAX_H)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>",   self._on_drag_start)
        self.canvas.bind("<B1-Motion>",        self._on_drag_move)
        self.canvas.bind("<ButtonRelease-1>",  self._on_drag_end)

        # Right panel
        right = tk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        tk.Label(right, text="Pending Fields:", anchor="w").pack(fill=tk.X)

        tree_frame = tk.Frame(right)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("name", "page", "box")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        self.tree.heading("name", text="Field Name")
        self.tree.heading("page", text="Page")
        self.tree.heading("box",  text="Box (PDF pts)")
        self.tree.column("name", width=90,  anchor="w")
        self.tree.column("page", width=45,  anchor="center")
        self.tree.column("box",  width=190, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        btn_row = tk.Frame(right)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        tk.Button(btn_row, text="Remove Selected",
                  command=self._remove_field).pack(side=tk.LEFT, padx=2)

        action_row = tk.Frame(right)
        action_row.pack(fill=tk.X, pady=(8, 0))

        tk.Button(action_row, text="Add", width=10,
                  command=self._add_field).pack(side=tk.LEFT, padx=2)
        tk.Button(action_row, text="Save PDF", width=10,
                  command=self._save).pack(side=tk.LEFT, padx=2)

        # ---- edit form (shown when a field is selected) ----
        self.edit_frame = tk.LabelFrame(right, text="Edit Selected Field", padx=4, pady=4)
        # not packed until a row is selected

        edit_grid = tk.Frame(self.edit_frame)
        edit_grid.pack(fill=tk.X)

        for col, label in enumerate(("x1", "y1", "Width", "Height")):
            tk.Label(edit_grid, text=label).grid(row=0, column=col, padx=4)

        self._edit_x1 = tk.Entry(edit_grid, width=7)
        self._edit_y1 = tk.Entry(edit_grid, width=7)
        self._edit_w  = tk.Entry(edit_grid, width=7)
        self._edit_h  = tk.Entry(edit_grid, width=7)
        for col, entry in enumerate((self._edit_x1, self._edit_y1,
                                     self._edit_w, self._edit_h)):
            entry.grid(row=1, column=col, padx=4, pady=2)

        tk.Button(self.edit_frame, text="Update", command=self._apply_edit).pack(
            pady=(4, 0))

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # ---- status bar ----
        status = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_coords = tk.Label(
            status,
            text="Coords: x1=—  y1=—  x2=—  y2=— (PDF pts)",
            anchor="w", font=("Courier", 9),
        )
        self.lbl_coords.pack(fill=tk.X, padx=4)

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def _setup_dnd(self) -> None:
        if not self.dnd_available or DND_FILES is None:
            return
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        # tkinterdnd2 wraps paths in {} when they contain spaces
        path = event.data.strip().strip("{}")
        self._open_pdf(path)

    # ------------------------------------------------------------------
    # PDF loading
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self._open_pdf(path)

    def _open_pdf(self, path: str) -> None:
        if not path.lower().endswith(".pdf"):
            messagebox.showerror("Invalid file", "Please select a PDF file.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("File not found", f"Cannot read:\n{path}")
            return
        try:
            doc = fitz.open(path)
            total = doc.page_count
            doc.close()
        except Exception as exc:
            messagebox.showerror("Error", f"Cannot open PDF:\n{exc}")
            return

        self.state.pdf_path = path
        self.state.total_pages = total
        self.state.current_page_index = 0

        self.lbl_file.config(text=f"{os.path.basename(path)}  ({total} pages)")
        self.lbl_total.config(text=f"/ {total}")
        self.entry_page.delete(0, tk.END)
        self.entry_page.insert(0, "1")
        self.lbl_nav_err.config(text="")

        self._load_page()

    # ------------------------------------------------------------------
    # Page loading / preview
    # ------------------------------------------------------------------

    def _load_page(self) -> None:
        if not self.state.pdf_path:
            self.lbl_nav_err.config(text="No PDF loaded.")
            return

        raw = self.entry_page.get().strip()
        if not raw.isdigit():
            self.lbl_nav_err.config(text="Enter a valid page number.")
            return

        page_label = int(raw)
        if not (1 <= page_label <= self.state.total_pages):
            self.lbl_nav_err.config(
                text=f"Page must be 1–{self.state.total_pages}."
            )
            return

        self.lbl_nav_err.config(text="")
        self.state.current_page_index = page_label - 1
        self.state.drag_start = None
        self.state.drag_end   = None

        img, px_w, px_h, pdf_w, pdf_h = self.renderer.render(
            self.state.pdf_path,
            self.state.current_page_index,
        )

        self.state.display_width_px  = px_w
        self.state.display_height_px = px_h
        self.state.page_width_pts    = pdf_w
        self.state.page_height_pts   = pdf_h

        photo = ImageTk.PhotoImage(img, master=self.canvas)
        self._photo = photo  # keep reference bound to this canvas/root
        self.canvas.config(width=px_w, height=px_h)
        self.canvas.delete("all")
        self.canvas.create_image(
            0, 0,
            anchor=tk.NW,
            image=self._photo,
            tags=self.CANVAS_TAG_PREVIEW,
        )

        self._redraw_saved_fields()
        self._update_coord_label()

    def _prev_page(self) -> None:
        if not self.state.pdf_path:
            return
        page_label = self.state.current_page_index  # current is 0-based, so label = index+1; prev = index
        if page_label < 1:
            return
        self.entry_page.delete(0, tk.END)
        self.entry_page.insert(0, str(page_label))
        self._load_page()

    def _next_page(self) -> None:
        if not self.state.pdf_path:
            return
        page_label = self.state.current_page_index + 2  # next page label
        if page_label > self.state.total_pages:
            return
        self.entry_page.delete(0, tk.END)
        self.entry_page.insert(0, str(page_label))
        self._load_page()

    # ------------------------------------------------------------------
    # Rectangle drawing
    # ------------------------------------------------------------------

    def _on_drag_start(self, event) -> None:
        self.state.drag_start = (event.x, event.y)
        self.state.drag_end   = (event.x, event.y)
        self.canvas.delete(self.CANVAS_TAG_DRAG)

    def _on_drag_move(self, event) -> None:
        self.state.drag_end = (event.x, event.y)
        self._redraw_drag_rect()
        self._update_coord_label()

    def _on_drag_end(self, event) -> None:
        self.state.drag_end = (event.x, event.y)
        self._redraw_drag_rect()
        self._update_coord_label()

    def _redraw_drag_rect(self) -> None:
        self.canvas.delete(self.CANVAS_TAG_DRAG)
        if self.state.drag_start and self.state.drag_end:
            x1, y1 = self.state.drag_start
            x2, y2 = self.state.drag_end
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="red", width=2, dash=(4, 2),
                tags=self.CANVAS_TAG_DRAG,
            )

    def _redraw_saved_fields(self) -> None:
        self.canvas.delete(self.CANVAS_TAG_SAVED)
        for f in self.state.pending_fields:
            if f.page_index != self.state.current_page_index:
                continue
            cx1, cy1, cx2, cy2 = CoordConverter.pdf_to_canvas(
                self.state, *f.pdf_box
            )
            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline="blue", width=2, dash=(6, 3),
                tags=self.CANVAS_TAG_SAVED,
            )
            # Field name label above the rectangle
            self.canvas.create_text(
                cx1 + 2, cy1 - 2, anchor=tk.SW,
                text=f.field_name, fill="blue", font=("Arial", 8),
                tags=self.CANVAS_TAG_SAVED,
            )

    def _update_coord_label(self) -> None:
        if not (self.state.drag_start and self.state.drag_end):
            self.lbl_coords.config(
                text="Coords: x1=—  y1=—  x2=—  y2=— (PDF pts)"
            )
            return
        x1, y1 = self.state.drag_start
        x2, y2 = self.state.drag_end
        ll_x, ll_y, ur_x, ur_y = CoordConverter.canvas_to_pdf(
            self.state, x1, y1, x2, y2
        )
        self.lbl_coords.config(
            text=f"Coords: x1={ll_x:.1f}  y1={ll_y:.1f}  x2={ur_x:.1f}  y2={ur_y:.1f} (PDF pts)"
        )

    # ------------------------------------------------------------------
    # Field list
    # ------------------------------------------------------------------

    def _add_field(self) -> None:
        if not self.state.pdf_path:
            messagebox.showwarning("No PDF", "Load a PDF first.")
            return
        if not (self.state.drag_start and self.state.drag_end):
            messagebox.showwarning("No rectangle", "Draw a rectangle on the preview first.")
            return

        x1, y1 = self.state.drag_start
        x2, y2 = self.state.drag_end
        box = CoordConverter.canvas_to_pdf(self.state, x1, y1, x2, y2)
        ll_x, ll_y, ur_x, ur_y = box

        if abs(ur_x - ll_x) < 1 or abs(ur_y - ll_y) < 1:
            messagebox.showwarning("Too small", "Rectangle is too small. Draw a larger area.")
            return

        name = f"Sig_{self.state.field_counter}"
        self.state.field_counter += 1

        pf = PendingField(
            field_name=name,
            page_index=self.state.current_page_index,
            page_label=self.state.current_page_index + 1,
            pdf_box=box,
        )
        self.state.pending_fields.append(pf)

        box_str = f"({ll_x:.1f}, {ll_y:.1f}, {ur_x:.1f}, {ur_y:.1f})"
        self.tree.insert("", tk.END, values=(name, pf.page_label, box_str))

        # Clear temp drag state and redraw
        self.state.drag_start = None
        self.state.drag_end   = None
        self.canvas.delete(self.CANVAS_TAG_DRAG)
        self._redraw_saved_fields()
        self._update_coord_label()

    def _remove_field(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select a field to remove.")
            return
        iid = selected[0]
        idx = self.tree.index(iid)
        self.tree.delete(iid)
        del self.state.pending_fields[idx]
        self._redraw_saved_fields()

    # ------------------------------------------------------------------
    # Field edit form
    # ------------------------------------------------------------------

    def _on_tree_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            self.edit_frame.pack_forget()
            return
        idx = self.tree.index(selected[0])
        pf = self.state.pending_fields[idx]
        ll_x, ll_y, ur_x, ur_y = pf.pdf_box
        for entry, val in zip(
            (self._edit_x1, self._edit_y1, self._edit_w, self._edit_h),
            (ll_x, ll_y, ur_x - ll_x, ur_y - ll_y),
        ):
            entry.delete(0, tk.END)
            entry.insert(0, f"{val:.2f}")
        self.edit_frame.pack(fill=tk.X, pady=(6, 0))

    def _apply_edit(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        try:
            x1 = float(self._edit_x1.get())
            y1 = float(self._edit_y1.get())
            w  = float(self._edit_w.get())
            h  = float(self._edit_h.get())
        except ValueError:
            messagebox.showerror("Invalid input", "All fields must be numbers.")
            return
        if w <= 0 or h <= 0:
            messagebox.showerror("Invalid input", "Width and Height must be positive.")
            return

        iid = selected[0]
        idx = self.tree.index(iid)
        pf = self.state.pending_fields[idx]
        new_box = (x1, y1, x1 + w, y1 + h)
        pf.pdf_box = new_box

        box_str = f"({x1:.1f}, {y1:.1f}, {x1+w:.1f}, {y1+h:.1f})"
        self.tree.item(iid, values=(pf.field_name, pf.page_label, box_str))
        self._redraw_saved_fields()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self.state.pdf_path:
            messagebox.showwarning("No PDF", "Load a PDF first.")
            return
        if not self.state.pending_fields:
            messagebox.showwarning("No fields", "Add at least one signature field.")
            return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="output_with_fields.pdf",
        )
        if not out_path:
            return  # user cancelled

        if os.path.abspath(out_path) == os.path.abspath(self.state.pdf_path):
            messagebox.showerror(
                "Same file",
                "Output path cannot be the same as the source PDF.\n"
                "Choose a different file name.",
            )
            return

        try:
            save_all_fields(self.state.pdf_path, out_path, self.state.pending_fields)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        messagebox.showinfo(
            "Saved",
            f"Saved {len(self.state.pending_fields)} field(s) to:\n{out_path}",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    dnd_available = False

    if TkinterDnD is not None:
        try:
            if sys.platform == "darwin":
                # TkinterDnD.Tk() creates a spurious blank window on macOS;
                # load the extension into a plain Tk root instead.
                root = tk.Tk()
                TkinterDnD._require(root)
            else:
                root = TkinterDnD.Tk()
            dnd_available = True
        except Exception as exc:
            print(f"Drag-and-drop disabled: {exc}")
            root = tk.Tk()
    else:
        root = tk.Tk()

    app = App(root, dnd_available=dnd_available)
    root.mainloop()


if __name__ == "__main__":
    main()
