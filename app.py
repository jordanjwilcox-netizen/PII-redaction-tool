import os
import customtkinter as ctk
from tkinter import filedialog

from file_ops import process_file, process_folder


# -----------------------------
# UI CONFIG
# -----------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Privacy Shield Pro")
        self.geometry("1200x700")

        # layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------
        # SIDEBAR
        # -----------------------------
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.title_label = ctk.CTkLabel(
            self.sidebar,
            text="Privacy Shield",
            font=("Arial", 18, "bold")
        )
        self.title_label.pack(pady=15)

        self.status = ctk.CTkLabel(self.sidebar, text="Ready")
        self.status.pack(pady=10)

        self.btn_file = ctk.CTkButton(
            self.sidebar,
            text="Open File",
            command=self.open_file
        )
        self.btn_file.pack(pady=8)

        self.btn_folder = ctk.CTkButton(
            self.sidebar,
            text="Open Folder",
            command=self.open_folder
        )
        self.btn_folder.pack(pady=8)

        # progress bar
        self.progress = ctk.CTkProgressBar(self.sidebar)
        self.progress.set(0)
        self.progress.pack(pady=15)

        # -----------------------------
        # MAIN TEXT AREA
        # -----------------------------
        self.textbox = ctk.CTkTextbox(self)
        self.textbox.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # -----------------------------
        # ENTITY PANEL
        # -----------------------------
        self.entity_panel = ctk.CTkTextbox(self, width=300)
        self.entity_panel.grid(row=0, column=2, sticky="ns", padx=10, pady=10)

        self.entity_panel.insert("end", "Detected Entities\n-----------------\n\n")

    # -----------------------------
    # FILE HANDLER
    # -----------------------------
    def open_file(self):

        path = filedialog.askopenfilename()
        if not path:
            return

        self.status.configure(text="Processing file...")

        result = process_file(path)

        self.render_result(result)

        self.status.configure(text="Done ✓")

    # -----------------------------
    # FOLDER HANDLER
    # -----------------------------
    def open_folder(self):

        folder = filedialog.askdirectory()
        if not folder:
            return

        self.status.configure(text="Processing folder...")

        files = []

        for root_dir, _, filenames in os.walk(folder):
            for f in filenames:
                if f.lower().endswith((".txt", ".docx")):
                    files.append(os.path.join(root_dir, f))

        total = len(files)

        self.progress.set(0)

        last_result = None

        for i, file in enumerate(files):

            last_result = process_file(file)

            self.progress.set((i + 1) / total)
            self.update_idletasks()

        # show last file result + summary
        self.render_result(last_result)

        self.textbox.insert("end", f"\n\nProcessed {total} files total")

        self.status.configure(text="Done ✓")
        self.progress.set(1)

    # -----------------------------
    # SAFE RENDER (FIXED CRASHES)
    # -----------------------------
    def render_result(self, result):

        # -----------------------------
        # SAFETY: handle string fallback
        # -----------------------------
        if isinstance(result, str):
            result = {
                "text": result,
                "entities": []
            }

        # -----------------------------
        # MAIN TEXT
        # -----------------------------
        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", result.get("text", ""))

        # -----------------------------
        # ENTITY PANEL
        # -----------------------------
        self.entity_panel.delete("1.0", "end")
        self.entity_panel.insert("end", "Detected Entities\n-----------------\n\n")

        entities = result.get("entities", [])

        if not entities:
            self.entity_panel.insert("end", "No entities detected\n")
            return

        for e in entities:

            self.entity_panel.insert(
                "end",
                f"{e.get('type','?')} → {e.get('value','?')} ({e.get('confidence',0)})\n"
            )


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()