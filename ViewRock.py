import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import datetime
import math
import webbrowser
import random
import time

APP_NAME = "ViewRock OS"

# --- Theme & fonts ---
theme = {
    "dark": {
        "bg": "#1e1e2f",
        "fg": "#e0e0e0",
        "btn_bg": "#2c2c44",
        "btn_fg": "#cfcfcf",
        "active_bg": "#3a3a60",
        "btn_hover_bg": "#454a73",
        "taskbar_bg": "#161622",
        "titlebar_bg": "#2a2a44",
        "titlebar_fg": "#dddddd",
        "border_color": "#444466",
        "entry_bg": "#30304a",
        "entry_fg": "#f0f0f0"
    }
}
current_theme = "dark"
FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI Semibold", 12)
APP_TITLE_FONT = ("Segoe UI Semibold", 16)

# --- User Database (in-memory) ---
user_db = {}

# --- Contacts database (in-memory) ---
contacts_db = {}  # name -> {"username":..., "notes":...}

# --- Installed apps store (persist in-memory) ---
installed_apps = {}  # app_name -> open_func

# --- Global for logged in user ---
logged_in_user = None

# --- Main root ---
root = tk.Tk()
root.title(APP_NAME)
root.geometry("1200x720")
root.minsize(900, 600)

# --- Gradient Background ---
def draw_gradient(canvas, color1, color2):
    width = root.winfo_width()
    height = root.winfo_height()
    if height <= 0:
        return
    r1, g1, b1 = root.winfo_rgb(color1)
    r2, g2, b2 = root.winfo_rgb(color2)
    r_ratio = (r2 - r1) / max(height, 1)
    g_ratio = (g2 - g1) / max(height, 1)
    b_ratio = (b2 - b1) / max(height, 1)

    canvas.delete("gradient")
    for i in range(height):
        nr = int(r1 + (r_ratio * i))
        ng = int(g1 + (g_ratio * i))
        nb = int(b1 + (b_ratio * i))
        color = f'#{nr>>8:02x}{ng>>8:02x}{nb>>8:02x}'
        canvas.create_line(0, i, width, i, tags=("gradient",), fill=color)

bg_canvas = tk.Canvas(root, highlightthickness=0)
bg_canvas.pack(fill="both", expand=True)
root.update()
draw_gradient(bg_canvas, "#FF9800", "#BC4664")

def on_resize(event):
    draw_gradient(bg_canvas, "#FF9800", "#BC4664")
root.bind("<Configure>", on_resize)

# --- Fullscreen toggle for OS via topbar double click ---
is_fullscreen = False
def toggle_fullscreen_os(event=None):
    global is_fullscreen
    is_fullscreen = not is_fullscreen
    root.attributes("-fullscreen", is_fullscreen)

# --- Custom App Window ---
class AppWindow(tk.Toplevel):
    def __init__(self, master, title, emoji):
        super().__init__(master)
        self.master = master
        self.title_text = title
        self.emoji = emoji
        self.current_theme = current_theme
        self.is_minimized = False
        self.is_maximized = False
        self.old_geometry = None

        self.overrideredirect(True)  # Remove native window decorations
        self.geometry("600x450")
        self.configure(bg=theme[self.current_theme]["border_color"])

        self.border_width = 3

        self.frame = tk.Frame(self, bg=theme[self.current_theme]["border_color"], bd=0)
        self.frame.pack(fill="both", expand=True, padx=self.border_width, pady=self.border_width)

        # Title Bar
        self.title_bar = tk.Frame(self.frame, bg=theme[self.current_theme]["titlebar_bg"], height=32)
        self.title_bar.pack(fill="x")

        self.title_label = tk.Label(self.title_bar, text=f"{self.emoji} {self.title_text}",
                                    bg=theme[self.current_theme]["titlebar_bg"],
                                    fg=theme[self.current_theme]["titlebar_fg"],
                                    font=TITLE_FONT)
        self.title_label.pack(side="left", padx=10)

        # Custom Buttons: Minimize, Maximize, Close (colored circles)
        btn_size = 14
        btn_padx = 6

        self.btn_close = tk.Canvas(self.title_bar, width=btn_size, height=btn_size, bg=theme[self.current_theme]["titlebar_bg"], highlightthickness=0)
        self.btn_close.pack(side="right", padx=btn_padx)
        self.btn_close_circle = self.btn_close.create_oval(2, 2, btn_size-2, btn_size-2, fill="#ff5f56", outline="")
        self.btn_close.bind("<Button-1>", lambda e: self.close_window())
        self.btn_close.bind("<Enter>", lambda e: self.btn_close.itemconfig(self.btn_close_circle, fill="#ff3b30"))
        self.btn_close.bind("<Leave>", lambda e: self.btn_close.itemconfig(self.btn_close_circle, fill="#ff5f56"))

        self.btn_maximize = tk.Canvas(self.title_bar, width=btn_size, height=btn_size, bg=theme[self.current_theme]["titlebar_bg"], highlightthickness=0)
        self.btn_maximize.pack(side="right", padx=btn_padx)
        self.btn_maximize_circle = self.btn_maximize.create_oval(2, 2, btn_size-2, btn_size-2, fill="#ffbd2e", outline="")
        self.btn_maximize.bind("<Button-1>", lambda e: self.toggle_maximize())
        self.btn_maximize.bind("<Enter>", lambda e: self.btn_maximize.itemconfig(self.btn_maximize_circle, fill="#fabb00"))
        self.btn_maximize.bind("<Leave>", lambda e: self.btn_maximize.itemconfig(self.btn_maximize_circle, fill="#ffbd2e"))

        self.btn_minimize = tk.Canvas(self.title_bar, width=btn_size, height=btn_size, bg=theme[self.current_theme]["titlebar_bg"], highlightthickness=0)
        self.btn_minimize.pack(side="right", padx=btn_padx)
        self.btn_minimize_circle = self.btn_minimize.create_oval(2, 2, btn_size-2, btn_size-2, fill="#27c93f", outline="")
        self.btn_minimize.bind("<Button-1>", lambda e: self.minimize_window())
        self.btn_minimize.bind("<Enter>", lambda e: self.btn_minimize.itemconfig(self.btn_minimize_circle, fill="#12b91d"))
        self.btn_minimize.bind("<Leave>", lambda e: self.btn_minimize.itemconfig(self.btn_minimize_circle, fill="#27c93f"))

        # Content frame
        self.content_frame = tk.Frame(self.frame, bg=theme[self.current_theme]["bg"])
        self.content_frame.pack(fill="both", expand=True)

        # Dragging variables
        self._offset_x = 0
        self._offset_y = 0

        # Bind dragging events
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)

        self.lift()
        self.after(10, lambda: self.focus_force())

    def start_move(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def stop_move(self, event):
        self._offset_x = 0
        self._offset_y = 0

    def do_move(self, event):
        x = self.winfo_pointerx() - self._offset_x
        y = self.winfo_pointery() - self._offset_y
        self.geometry(f"+{x}+{y}")

    def close_window(self):
        self.destroy()
        if taskbar:
            taskbar.remove_window(self)

    def minimize_window(self):
        self.is_minimized = True
        self.withdraw()
        if taskbar:
            taskbar.update_taskbar_buttons()

    def toggle_maximize(self):
        if self.is_maximized:
            # Restore
            if self.old_geometry:
                self.geometry(self.old_geometry)
            self.is_maximized = False
        else:
            # Maximize to root window size minus taskbar and topbar height
            self.old_geometry = self.geometry()
            root_x = root.winfo_rootx()
            root_y = root.winfo_rooty()
            root_width = root.winfo_width()
            root_height = root.winfo_height()
            # Leave margin for taskbar and topbar
            taskbar_height = taskbar.winfo_height() if taskbar else 35
            topbar_height = topbar.winfo_height() if topbar else 32
            new_width = max(root_width - 20, 200)
            new_height = max(root_height - taskbar_height - topbar_height - 20, 200)
            self.geometry(f"{new_width}x{new_height}+{root_x+10}+{root_y+topbar_height+10}")
            self.is_maximized = True

# --- Taskbar ---
class Taskbar(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=theme[current_theme]["taskbar_bg"], height=35)
        self.pack(side="bottom", fill="x")
        self.windows = []

    def add_window(self, win):
        if win not in self.windows:
            self.windows.append(win)
        self.update_taskbar_buttons()

    def remove_window(self, win):
        if win in self.windows:
            self.windows.remove(win)
        self.update_taskbar_buttons()

    def update_taskbar_buttons(self):
        for widget in self.winfo_children():
            widget.destroy()
        for win in self.windows:
            if not isinstance(win, AppWindow):
                continue
            text = win.title_text
            state = " (minimized)" if win.is_minimized else ""
            btn_bg = theme[current_theme]["active_bg"] if not win.is_minimized else theme[current_theme]["btn_bg"]
            btn = tk.Button(self, text=text + state, bg=btn_bg, fg=theme[current_theme]["btn_fg"],
                            relief="flat", font=FONT, padx=10, pady=3, cursor="hand2")
            btn.pack(side="left", padx=2, pady=2)

            def handler(w=win):
                if w.is_minimized:
                    w.deiconify()
                    w.is_minimized = False
                    w.lift()
                    w.focus_force()
                else:
                    w.minimize_window()

            btn.configure(command=handler)

taskbar = Taskbar(root)

# --- Topbar (macOS-style) ---
topbar = tk.Frame(root, bg="#2e2e2e", height=32)
topbar.place(relx=0, rely=0, relwidth=1)

title_label = tk.Label(topbar, text=APP_NAME, fg="white", bg="#2e2e2e", font=("Segoe UI", 10, "bold"))
title_label.pack(side="left", padx=12)
title_label.bind("<Double-Button-1>", toggle_fullscreen_os)

clock_label = tk.Label(topbar, fg="white", bg="#2e2e2e", font=("Segoe UI", 10))
clock_label.pack(side="right", padx=12)

def update_clock():
    now = datetime.datetime.now().strftime("%a %H:%M:%S")
    clock_label.config(text=now)
    root.after(1000, update_clock)

update_clock()

# --- Dock (Bottom like macOS) ---
dock_frame = tk.Frame(root, bg="#1a1a1a", height=70)
dock_frame.place(relx=0.5, rely=1.0, anchor="s", y=-10)

# --- Utility: safe font widget config
def apply_button_styles(btn, t):
    btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], font=FONT, relief="flat", cursor="hand2")
    btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=t["active_bg"]))
    btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=t["btn_bg"]))

# --- Notes App ---
def open_notes_window():
    win = AppWindow(root, "Notes", "📝")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="Notes", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=(12, 8))

    title_frame = tk.Frame(cf, bg=t["bg"])
    title_frame.pack(fill="x", padx=25, pady=(0, 6))
    tk.Label(title_frame, text="Title:", bg=t["bg"], fg=t["fg"], font=FONT).pack(side="left")
    title_var = tk.StringVar()
    title_entry = tk.Entry(title_frame, textvariable=title_var)
    title_entry.pack(side="left", fill="x", expand=True, padx=10)
    title_entry.configure(font=FONT)

    tk.Label(cf, text="Content:", bg=t["bg"], fg=t["fg"], font=FONT).pack(anchor="w", padx=25, pady=(6, 0))
    content_text = tk.Text(cf, height=10)
    content_text.pack(fill="both", padx=25, pady=(0, 10), expand=True)
    content_text.configure(font=FONT, wrap="word")

    list_frame = tk.Frame(cf, bg=t["bg"])
    list_frame.pack(fill="both", padx=25, pady=5, expand=True)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    notes_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
    notes_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=notes_listbox.yview)
    notes_listbox.configure(font=FONT, selectmode=tk.SINGLE, activestyle="none")

    # Data store for notes
    if not hasattr(root, 'notes_data'):
        root.notes_data = {}

    def refresh_list():
        notes_listbox.delete(0, tk.END)
        for k in sorted(root.notes_data.keys()):
            notes_listbox.insert(tk.END, k)

    def save_note():
        title = title_var.get().strip()
        content = content_text.get("1.0", tk.END).strip()
        if title and content:
            root.notes_data[title] = content
            refresh_list()
            title_var.set("")
            content_text.delete("1.0", tk.END)
        else:
            messagebox.showwarning("Warning", "Please enter both a title and content.")

    def delete_note():
        sel = notes_listbox.curselection()
        if sel:
            key = notes_listbox.get(sel[0])
            if key in root.notes_data:
                if messagebox.askyesno("Delete Note", f"Delete note '{key}'?"):
                    del root.notes_data[key]
                    refresh_list()
        else:
            messagebox.showinfo("Info", "Select a note to delete.")

    def view_note():
        sel = notes_listbox.curselection()
        if sel:
            key = notes_listbox.get(sel[0])
            if key in root.notes_data:
                title_var.set(key)
                content_text.delete("1.0", tk.END)
                content_text.insert(tk.END, root.notes_data[key])

    btn_frame = tk.Frame(cf, bg=t["bg"])
    btn_frame.pack(pady=10)

    btn_save = tk.Button(btn_frame, text="Save Note", command=save_note)
    btn_save.pack(side="left", padx=12, ipadx=10, ipady=6)

    btn_clear = tk.Button(btn_frame, text="Clear", command=lambda: (title_var.set(""), content_text.delete("1.0", tk.END)))
    btn_clear.pack(side="left", padx=12, ipadx=10, ipady=6)

    btn_delete = tk.Button(btn_frame, text="Delete Note", command=delete_note)
    btn_delete.pack(side="left", padx=12, ipadx=10, ipady=6)

    btn_view = tk.Button(cf, text="View Selected Note", command=view_note)
    btn_view.pack(pady=(0, 15), ipadx=15, ipady=7)

    refresh_list()

# --- File Explorer (unchanged) ---
virtual_fs = {
    "root": {
        "Documents": {
            "readme.txt": "Welcome to ViewRock OS File Explorer!\nThis is a sample file.",
        },
        "Notes.txt": "These are some notes in a text file.",
        "EmptyFolder": {}
    }
}
current_path = ["root"]
def get_current_dir():
    d = virtual_fs
    for p in current_path:
        d = d[p]
    return d

class FileExplorerWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("File Explorer 🗂️")
        self.geometry("700x500")
        self.configure(bg="#1e1e2f")
        self.current_dir = get_current_dir()
        self.history = []

        # Navigation bar
        nav_frame = tk.Frame(self, bg="#2c2c44")
        nav_frame.pack(fill="x")

        btn_back = tk.Button(nav_frame, text="← Back", command=self.go_back, bg="#30304a", fg="white")
        btn_back.pack(side="left", padx=5, pady=5)

        btn_up = tk.Button(nav_frame, text="↑ Up", command=self.go_up, bg="#30304a", fg="white")
        btn_up.pack(side="left", padx=5, pady=5)

        self.path_var = tk.StringVar()
        self.path_var.set("/" + "/".join(current_path[1:]) if len(current_path) > 1 else "/")
        self.path_entry = tk.Entry(nav_frame, textvariable=self.path_var, bg="#30304a", fg="white", relief="flat")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        btn_go = tk.Button(nav_frame, text="Go", command=self.go_to_path, bg="#30304a", fg="white")
        btn_go.pack(side="left", padx=5, pady=5)

        # File/folder listbox
        self.list_frame = tk.Frame(self, bg="#1e1e2f")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.list_frame, bg="#30304a", fg="white", font=("Segoe UI", 11))
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.list_frame)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

        self.file_listbox.bind("<Double-Button-1>", self.open_selected)

        # Buttons below listbox
        btn_frame = tk.Frame(self, bg="#2c2c44")
        btn_frame.pack(fill="x", padx=10, pady=10)

        btn_view = tk.Button(btn_frame, text="View / Edit", command=self.open_selected, bg="#30304a", fg="white")
        btn_view.pack(side="left", padx=5)

        btn_new_file = tk.Button(btn_frame, text="New File", command=self.new_file, bg="#30304a", fg="white")
        btn_new_file.pack(side="left", padx=5)

        btn_new_folder = tk.Button(btn_frame, text="New Folder", command=self.new_folder, bg="#30304a", fg="white")
        btn_new_folder.pack(side="left", padx=5)

        btn_rename = tk.Button(btn_frame, text="Rename", command=self.rename_item, bg="#30304a", fg="white")
        btn_rename.pack(side="left", padx=5)

        btn_delete = tk.Button(btn_frame, text="Delete", command=self.delete_item, bg="#30304a", fg="white")
        btn_delete.pack(side="left", padx=5)

        self.refresh_list()

    def refresh_list(self):
        self.current_dir = get_current_dir()
        self.file_listbox.delete(0, tk.END)
        folders = [k for k,v in self.current_dir.items() if isinstance(v, dict)]
        files = [k for k,v in self.current_dir.items() if isinstance(v, str)]
        for f in sorted(folders):
            self.file_listbox.insert(tk.END, f"[Folder] {f}")
        for f in sorted(files):
            self.file_listbox.insert(tk.END, f)
        self.path_var.set("/" + "/".join(current_path[1:]) if len(current_path) > 1 else "/")

    def go_back(self):
        if self.history:
            prev_path = self.history.pop()
            current_path.clear()
            current_path.extend(prev_path)
            self.refresh_list()
        else:
            messagebox.showinfo("Info", "No back history.")

    def go_up(self):
        if len(current_path) > 1:
            self.history.append(current_path[:])
            current_path.pop()
            self.refresh_list()
        else:
            messagebox.showinfo("Info", "Already at root folder.")

    def go_to_path(self):
        path_str = self.path_var.get().strip()
        if not path_str.startswith("/"):
            messagebox.showerror("Error", "Path must start with '/'")
            return
        parts = path_str.strip("/").split("/") if path_str.strip("/") else []
        d = virtual_fs
        try:
            new_path = ["root"]
            for part in parts:
                if part in d and isinstance(d[part], dict):
                    d = d[part]
                    new_path.append(part)
                else:
                    raise KeyError
            self.history.append(current_path[:])
            current_path.clear()
            current_path.extend(new_path)
            self.refresh_list()
        except KeyError:
            messagebox.showerror("Error", "Path does not exist.")

    def open_selected(self, event=None):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a file or folder.")
            return
        name = self.file_listbox.get(sel[0])
        is_folder = name.startswith("[Folder] ")
        item_name = name[9:] if is_folder else name

        if is_folder:
            self.history.append(current_path[:])
            current_path.append(item_name)
            self.refresh_list()
        else:
            self.open_file_editor(item_name)

    def open_file_editor(self, filename):
        file_content = self.current_dir.get(filename, "")
        editor_win = tk.Toplevel(self)
        editor_win.title(f"Editing: {filename}")
        editor_win.geometry("600x400")
        editor_win.configure(bg="#1e1e2f")

        text_area = tk.Text(editor_win, bg="#30304a", fg="white", font=("Segoe UI", 11), wrap="word")
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        text_area.insert("1.0", file_content)

        def save_file():
            new_content = text_area.get("1.0", tk.END).rstrip("\n")
            self.current_dir[filename] = new_content
            messagebox.showinfo("Saved", f"File '{filename}' saved.")
            editor_win.destroy()

        save_btn = tk.Button(editor_win, text="Save", command=save_file, bg="#30304a", fg="white")
        save_btn.pack(pady=5)

    def new_file(self):
        name = simpledialog.askstring("New File", "Enter new file name:")
        if not name:
            return
        if name in self.current_dir:
            messagebox.showerror("Error", "File or folder with this name already exists.")
            return
        self.current_dir[name] = ""
        self.refresh_list()

    def new_folder(self):
        name = simpledialog.askstring("New Folder", "Enter new folder name:")
        if not name:
            return
        if name in self.current_dir:
            messagebox.showerror("Error", "File or folder with this name already exists.")
            return
        self.current_dir[name] = {}
        self.refresh_list()

    def rename_item(self):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a file or folder to rename.")
            return
        old_name = self.file_listbox.get(sel[0])
        is_folder = old_name.startswith("[Folder] ")
        old_name_clean = old_name[9:] if is_folder else old_name

        new_name = simpledialog.askstring("Rename", f"Enter new name for '{old_name_clean}':")
        if not new_name:
            return
        if new_name in self.current_dir:
            messagebox.showerror("Error", "Name already exists.")
            return
        self.current_dir[new_name] = self.current_dir.pop(old_name_clean)
        self.refresh_list()

    def delete_item(self):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a file or folder to delete.")
            return
        name = self.file_listbox.get(sel[0])
        is_folder = name.startswith("[Folder] ")
        name_clean = name[9:] if is_folder else name
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{name_clean}'?"):
            del self.current_dir[name_clean]
            self.refresh_list()

def open_file_explorer():
    FileExplorerWindow(root)

# --- Settings app (small cleanup) ---
def open_settings_app():
    settings = tk.Toplevel(root)
    settings.title("Settings - ViewRock OS")
    settings.geometry("500x720")
    settings.configure(bg="#ececec")

    title = tk.Label(settings, text="⚙️ ViewRock OS Settings", font=("Segoe UI", 18, "bold"), bg="#ececec")
    title.pack(pady=10)

    username = logged_in_user or "Guest"
    tk.Label(settings, text=f"User: {username}", bg="#ececec", font=("Segoe UI", 11, "italic")).pack(pady=2)

    section_pad = 10

    # === 1. Theme Switcher ===
    tk.Label(settings, text="Theme", bg="#ececec", font=("Segoe UI", 12, "bold")).pack(pady=section_pad)
    theme_var = tk.StringVar(value="Gradient")
    def apply_theme(opt):
        if opt == "Light":
            root.configure(bg="white")
        elif opt == "Dark":
            root.configure(bg="#121212")
        elif opt == "Gradient":
            # simulated
            pass
        print("[Theme]", opt)
    tk.OptionMenu(settings, theme_var, "Gradient", "Light", "Dark", command=apply_theme).pack()

    # === other settings stubbed ===
    tk.Label(settings, text="(Other settings simulated)", bg="#ececec").pack(pady=section_pad)

# --- Calculator App ---
def open_calculator_window():
    win = AppWindow(root, "Calculator", "🧮")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="Calculator", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=(12, 10))

    expression = ""

    display_var = tk.StringVar()
    display_entry = tk.Entry(cf, textvariable=display_var, font=("Segoe UI", 24), bd=0, relief="flat", justify="right",
                             bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_fg"])
    display_entry.pack(fill="x", ipady=15, padx=20, pady=10)
    display_entry.focus()

    history_box = tk.Listbox(cf, height=4, font=FONT)
    history_box.pack(fill="x", padx=20, pady=(0, 10))
    history_box.configure(bg=t["btn_bg"], fg=t["btn_fg"], selectbackground=t["active_bg"])

    def update_display(val):
        nonlocal expression
        expression += str(val)
        display_var.set(expression)

    def calculate(event=None):
        nonlocal expression
        try:
            exp = expression.replace('^', '**').replace('π', str(math.pi))
            result = str(eval(exp, {"__builtins__": None}, math.__dict__))
            history_box.insert(tk.END, f"{expression} = {result}")
            display_var.set(result)
            expression = result
        except Exception:
            display_var.set("Error")
            expression = ""

    def clear(event=None):
        nonlocal expression
        expression = ""
        display_var.set("")

    button_frame = tk.Frame(cf, bg=t["bg"])
    button_frame.pack(pady=10, padx=20)

    standard_buttons = [
        ('7', '8', '9', '/'),
        ('4', '5', '6', '*'),
        ('1', '2', '3', '-'),
        ('0', '.', '=', '+')
    ]

    for row in standard_buttons:
        row_frame = tk.Frame(button_frame, bg=t["bg"])
        row_frame.pack(expand=True, fill="both")
        for btn in row:
            if btn == '=':
                action = calculate
            else:
                action = lambda val=btn: update_display(val)
            b = tk.Button(row_frame, text=btn, font=("Segoe UI", 16), width=6, height=2,
                          command=action, bg=t["btn_bg"], fg=t["btn_fg"], relief="flat")
            b.pack(side="left", expand=True, fill="both", padx=3, pady=3)
            b.bind("<Enter>", lambda e, b=b: b.configure(bg=t["active_bg"]))
            b.bind("<Leave>", lambda e, b=b: b.configure(bg=t["btn_bg"]))

    sci_frame = tk.LabelFrame(cf, text="Scientific Functions", bg=t["bg"], fg=t["fg"], font=FONT, padx=10, pady=5)
    sci_frame.pack(fill="x", padx=20, pady=(5, 15))

    def handle_sci(func):
        nonlocal expression
        if func == 'clear':
            clear()
            return
        if func == 'π':
            update_display('π')
            return
        try:
            result = str(eval(func, {"__builtins__": None}, math.__dict__))
            display_var.set(result)
            expression = result
        except Exception:
            display_var.set("Error")
            expression = ""

    sci_buttons = [
        ("sin(π/2)", "math.sin(math.pi/2)"),
        ("cos(0)", "math.cos(0)"),
        ("tan(π/4)", "math.tan(math.pi/4)"),
        ("log(10)", "math.log10(10)"),
        ("ln(1)", "math.log(1)"),
        ("√(16)", "math.sqrt(16)"),
        ("π", "π"),
        ("Clear", "clear")
    ]

    for text, cmd in sci_buttons:
        b = tk.Button(sci_frame, text=text, font=FONT, bg=t["btn_bg"], fg=t["btn_fg"], relief="flat",
                      command=lambda c=cmd: handle_sci(c))
        b.pack(side="left", expand=True, fill="both", padx=5, pady=3)
        b.bind("<Enter>", lambda e, b=b: b.configure(bg=t["active_bg"]))
        b.bind("<Leave>", lambda e, b=b: b.configure(bg=t["btn_bg"]))

# --- Simple Terminal ---
def open_terminal_window():
    win = AppWindow(root, "Terminal", "💻")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    output_text = tk.Text(cf, bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_fg"],
                         font=FONT, state="disabled")
    output_text.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    input_var = tk.StringVar()
    input_entry = tk.Entry(cf, textvariable=input_var, bg=t["entry_bg"], fg=t["entry_fg"],
                           font=FONT, insertbackground=t["entry_fg"])
    input_entry.pack(fill="x", padx=10, pady=10)

    def print_output(text):
        output_text.configure(state="normal")
        output_text.insert(tk.END, text + "\n")
        output_text.see(tk.END)
        output_text.configure(state="disabled")

    def execute_command(event=None):
        cmd = input_var.get().strip()
        print_output(f"> {cmd}")
        input_var.set("")
        handle_command(cmd)

    def handle_command(cmd):
        cmd_lower = cmd.lower()
        if cmd_lower == "mith.help":
            print_output("Commands:")
            print_output("mith.help - Show help")
            print_output("onconsole() - Show system info")
            print_output("admin*var(shutdown) - Shutdown OS")
            print_output("admin*var(clear) - Clear terminal")
            print_output("user.catch() - Show user")
            print_output("restart - Restart OS")
            print_output("sleep - Sleep mode")
            print_output("shutdown - Shutdown OS")
        elif cmd_lower == "onconsole()":
            print_output("ViewRock OS Terminal v1.0")
            print_output(f"User: {logged_in_user}")
            print_output(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        elif cmd_lower == "admin*var(shutdown)":
            print_output("Shutting down...")
            root.destroy()
        elif cmd_lower == "admin*var(clear)":
            output_text.configure(state="normal")
            output_text.delete("1.0", tk.END)
            output_text.configure(state="disabled")
        elif cmd_lower == "user.catch()":
            print_output(f"User: {logged_in_user}")
        elif cmd_lower == "restart":
            print_output("Restarting...")
            root.destroy()
            main()
        elif cmd_lower == "sleep":
            print_output("Sleep mode (simulated)...")
        elif cmd_lower == "shutdown":
            print_output("Shutting down...")
            root.destroy()
        else:
            print_output(f"Unknown command: {cmd}")

    input_entry.bind("<Return>", execute_command)
    print_output("Welcome to ViewRock OS Terminal!")
    print_output("Type 'mith.help' for commands.")
    input_entry.focus()

# --- Tic Tac Toe App ---
def open_tictactoe_window():
    win = AppWindow(root, "Tic-Tac-Toe", "❌⭕")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="Tic Tac Toe", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=10)

    board = ["" for _ in range(9)]
    current_player = ["X"]
    buttons = []

    status_label = tk.Label(cf, text="Player X's turn", bg=t["bg"], fg=t["fg"], font=FONT)
    status_label.pack(pady=(0,10))

    def check_winner():
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if board[a] == board[b] == board[c] != "":
                return board[a]
        if all(cell != "" for cell in board):
            return "Tie"
        return None

    def button_click(i):
        if board[i] == "":
            board[i] = current_player[0]
            buttons[i].config(text=current_player[0], state="disabled")
            winner = check_winner()
            if winner:
                if winner == "Tie":
                    status_label.config(text="It's a Tie!")
                else:
                    status_label.config(text=f"Player {winner} wins!")
                for b in buttons:
                    b.config(state="disabled")
            else:
                current_player[0] = "O" if current_player[0] == "X" else "X"
                status_label.config(text=f"Player {current_player[0]}'s turn")

    board_frame = tk.Frame(cf, bg=t["bg"])
    board_frame.pack()

    for i in range(9):
        b = tk.Button(board_frame, text="", font=("Segoe UI", 24), width=5, height=2,
                      command=lambda i=i: button_click(i), bg=t["btn_bg"], fg=t["btn_fg"])
        b.grid(row=i//3, column=i%3, padx=5, pady=5)
        buttons.append(b)

    def reset_game():
        for i in range(9):
            board[i] = ""
            buttons[i].config(text="", state="normal")
        current_player[0] = "X"
        status_label.config(text="Player X's turn")

    reset_btn = tk.Button(cf, text="Reset Game", command=reset_game, bg=t["btn_bg"], fg=t["btn_fg"])
    reset_btn.pack(pady=12)

# --- Whiteboard Pro+Mega App (unchanged) ---
def open_whiteboard_pro_mega_window():
    win = AppWindow(root, "Whiteboard Pro+Mega", "🖌️")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="Whiteboard Pro+Mega", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=10)

    tools_frame = tk.Frame(cf, bg=t["bg"])
    tools_frame.pack(pady=5)

    color_var = tk.StringVar(value="black")
    size_var = tk.IntVar(value=3)
    strokes = []
    undone_strokes = []

    def choose_color(c):
        color_var.set(c)

    colors = ["black", "red", "blue", "green"]
    for c in colors:
        tk.Button(tools_frame, bg=c, width=2, command=lambda col=c: choose_color(col)).pack(side="left", padx=2)

    tk.Label(tools_frame, text="Size:", bg=t["bg"], fg=t["fg"]).pack(side="left", padx=5)
    tk.Spinbox(tools_frame, from_=1, to=10, textvariable=size_var, width=3).pack(side="left")

    canvas = tk.Canvas(cf, bg="white", cursor="cross")
    canvas.pack(fill="both", expand=True, padx=10, pady=10)
    last_x, last_y = [None], [None]

    def start_draw(event):
        last_x[0], last_y[0] = event.x, event.y

    def draw(event):
        if last_x[0] and last_y[0]:
            line = canvas.create_line(last_x[0], last_y[0], event.x, event.y,
                                      width=size_var.get(), fill=color_var.get(), capstyle="round", smooth=True)
            strokes.append(line)
            last_x[0], last_y[0] = event.x, event.y
            undone_strokes.clear()

    def end_draw(event):
        last_x[0], last_y[0] = None, None

    def undo():
        if strokes:
            line = strokes.pop()
            canvas.delete(line)
            undone_strokes.append(line)

    def clear_canvas():
        canvas.delete("all")
        strokes.clear()
        undone_strokes.clear()

    def save_canvas():
        messagebox.showinfo("Save", "Drawing saved (simulated).")

    def load_canvas():
        messagebox.showinfo("Load", "Loaded previous drawing (simulated).")

    canvas.bind("<ButtonPress-1>", start_draw)
    canvas.bind("<B1-Motion>", draw)
    canvas.bind("<ButtonRelease-1>", end_draw)

    btn_frame = tk.Frame(cf, bg=t["bg"])
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Undo", command=undo).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Clear", command=clear_canvas).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Save", command=save_canvas).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Load", command=load_canvas).pack(side="left", padx=5)

# -----------------------------
# --- CONTACTS APP (NEW) ---
# -----------------------------
def open_contacts_app():
    win = AppWindow(root, "Contacts", "👥")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="Contacts Manager", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=8)

    frame = tk.Frame(cf, bg=t["bg"])
    frame.pack(fill="both", expand=True, padx=10, pady=8)

    list_frame = tk.Frame(frame, bg=t["bg"])
    list_frame.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    contacts_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=FONT)
    contacts_listbox.pack(fill="both", expand=True)
    scrollbar.config(command=contacts_listbox.yview)

    detail_frame = tk.Frame(frame, bg=t["bg"])
    detail_frame.pack(side="right", fill="both", expand=True, padx=10)

    tk.Label(detail_frame, text="Username:", bg=t["bg"], fg=t["fg"]).pack(anchor="w")
    username_var = tk.StringVar()
    username_entry = tk.Entry(detail_frame, textvariable=username_var)
    username_entry.pack(fill="x", pady=3)

    tk.Label(detail_frame, text="Notes:", bg=t["bg"], fg=t["fg"]).pack(anchor="w")
    notes_text = tk.Text(detail_frame, height=8)
    notes_text.pack(fill="both", pady=3, expand=True)

    def refresh_list():
        contacts_listbox.delete(0, tk.END)
        for name in sorted(contacts_db.keys()):
            contacts_listbox.insert(tk.END, name)

    def on_select(evt=None):
        sel = contacts_listbox.curselection()
        if sel:
            name = contacts_listbox.get(sel[0])
            data = contacts_db.get(name, {})
            username_var.set(data.get("username", ""))
            notes_text.delete("1.0", tk.END)
            notes_text.insert("1.0", data.get("notes", ""))

    contacts_listbox.bind("<<ListboxSelect>>", on_select)

    def add_contact():
        name = simpledialog.askstring("Add Contact", "Contact Name:")
        if not name:
            return
        if name in contacts_db:
            messagebox.showerror("Exists", "Contact already exists.")
            return
        username = simpledialog.askstring("Add Contact", "Contact username / handle (for display):")
        contacts_db[name] = {"username": username or "", "notes": ""}
        refresh_list()

    def save_contact():
        sel = contacts_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a contact to save changes.")
            return
        name = contacts_listbox.get(sel[0])
        contacts_db[name]["username"] = username_var.get().strip()
        contacts_db[name]["notes"] = notes_text.get("1.0", tk.END).strip()
        messagebox.showinfo("Saved", f"Contact '{name}' saved.")
        refresh_list()

    def delete_contact():
        sel = contacts_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a contact to delete.")
            return
        name = contacts_listbox.get(sel[0])
        if messagebox.askyesno("Delete", f"Delete contact '{name}'?"):
            del contacts_db[name]
            username_var.set("")
            notes_text.delete("1.0", tk.END)
            refresh_list()

    btns = tk.Frame(detail_frame, bg=t["bg"])
    btns.pack(fill="x", pady=6)
    tk.Button(btns, text="Add", command=add_contact).pack(side="left", padx=4)
    tk.Button(btns, text="Save", command=save_contact).pack(side="left", padx=4)
    tk.Button(btns, text="Delete", command=delete_contact).pack(side="left", padx=4)

    refresh_list()

# -----------------------------
# --- VIDEO CALL APP (SIMULATED) ---
# -----------------------------
class SimulatedVideoCall(AppWindow):
    def __init__(self, master):
        super().__init__(master, "Video Call", "📹")
        self.call_active = False
        self.camera_active = False
        self.audio_muted = False
        self.video_muted = False
        self.current_call_target = None
        self.call_start_time = None
        taskbar.add_window(self)
        self.init_ui()
        self.local_anim_id = None
        self.remote_anim_id = None

    def init_ui(self):
        t = theme[current_theme]
        cf = self.content_frame
        for w in cf.winfo_children():
            w.destroy()

        header = tk.Frame(cf, bg=t["bg"])
        header.pack(fill="x", padx=10, pady=6)
        tk.Label(header, text="Video Call (simulated)", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(side="left")

        body = tk.Frame(cf, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=10, pady=6)

        left = tk.Frame(body, bg=t["bg"])
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg=t["bg"], width=220)
        right.pack(side="right", fill="y")

        # Local & remote "video" canvases
        self.local_canvas = tk.Canvas(left, bg="black", height=220)
        self.local_canvas.pack(fill="both", expand=True, padx=6, pady=6)

        self.remote_canvas = tk.Canvas(left, bg="black", height=220)
        self.remote_canvas.pack(fill="both", expand=True, padx=6, pady=6)

        # Call state label
        self.call_status_var = tk.StringVar(value="No active call")
        tk.Label(left, textvariable=self.call_status_var, bg=t["bg"], fg=t["fg"]).pack(pady=(4, 8))

        # Controls
        controls = tk.Frame(left, bg=t["bg"])
        controls.pack(fill="x", pady=6)

        self.btn_start_camera = tk.Button(controls, text="Start Camera", command=self.toggle_camera)
        self.btn_start_camera.pack(side="left", padx=6)
        self.btn_mute_audio = tk.Button(controls, text="Mute Audio", command=self.toggle_mute_audio)
        self.btn_mute_audio.pack(side="left", padx=6)
        self.btn_mute_video = tk.Button(controls, text="Mute Video", command=self.toggle_mute_video)
        self.btn_mute_video.pack(side="left", padx=6)

        # Right: Contacts + call controls
        tk.Label(right, text="Contacts", bg=t["bg"], fg=t["fg"], font=TITLE_FONT).pack(anchor="w", pady=(4,6))
        contacts_listbox = tk.Listbox(right, height=10)
        contacts_listbox.pack(fill="both", padx=4, pady=4, expand=False)

        def refresh_contacts_list():
            contacts_listbox.delete(0, tk.END)
            for name in sorted(contacts_db.keys()):
                contacts_listbox.insert(tk.END, name)

        refresh_contacts_list()

        def on_contact_double(evt=None):
            sel = contacts_listbox.curselection()
            if not sel:
                return
            name = contacts_listbox.get(sel[0])
            self.start_call(name)

        contacts_listbox.bind("<Double-Button-1>", on_contact_double)

        btn_frame = tk.Frame(right, bg=t["bg"])
        btn_frame.pack(fill="x", pady=6)
        tk.Button(btn_frame, text="Add Contact", command=lambda: (open_contacts_app(), self.lift())).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Refresh", command=refresh_contacts_list).pack(side="left", padx=2)

        # Call control buttons
        call_controls = tk.Frame(right, bg=t["bg"])
        call_controls.pack(fill="x", pady=(8,4))
        self.call_btn = tk.Button(call_controls, text="Start Call", command=lambda: self.call_from_selection(contacts_listbox))
        self.call_btn.pack(fill="x", pady=3)
        self.end_call_btn = tk.Button(call_controls, text="End Call", command=self.end_call, state="disabled")
        self.end_call_btn.pack(fill="x", pady=3)

        # Timer
        self.timer_var = tk.StringVar(value="00:00")
        tk.Label(right, textvariable=self.timer_var, bg=t["bg"], fg=t["fg"], font=("Segoe UI", 12)).pack(pady=6)

        # info
        tk.Label(right, text="Note: This is a simulated call UI.\nNo real camera or network used.", bg=t["bg"], fg=t["fg"], wraplength=200).pack(pady=6)

        # initial state
        self.render_local_frame(clear=True)
        self.render_remote_frame(clear=True)

    def call_from_selection(self, listbox):
        sel = listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a contact to call (or double-click).")
            return
        name = listbox.get(sel[0])
        self.start_call(name)

    def toggle_camera(self):
        if self.camera_active:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        self.camera_active = True
        self.btn_start_camera.config(text="Stop Camera")
        self._animate_local()
        self.update_status_text()

    def stop_camera(self):
        self.camera_active = False
        self.btn_start_camera.config(text="Start Camera")
        if self.local_anim_id:
            try:
                self.after_cancel(self.local_anim_id)
            except Exception:
                pass
            self.local_anim_id = None
        self.render_local_frame(clear=True)
        self.update_status_text()

    def toggle_mute_audio(self):
        self.audio_muted = not self.audio_muted
        self.btn_mute_audio.config(text="Unmute Audio" if self.audio_muted else "Mute Audio")
        self.update_status_text()

    def toggle_mute_video(self):
        self.video_muted = not self.video_muted
        self.btn_mute_video.config(text="Unmute Video" if self.video_muted else "Mute Video")
        # hide/show remote canvas to simulate video mute for remote (local still controlled by camera)
        if self.video_muted:
            self.remote_canvas.delete("all")
            self.remote_canvas.create_text(10, 10, anchor="nw", text="Remote video muted", fill="white")
        else:
            # resume remote animation if call active
            if self.call_active:
                self._animate_remote()
        self.update_status_text()

    def update_status_text(self):
        status = []
        if self.call_active:
            status.append(f"On call with {self.current_call_target}")
        if self.camera_active:
            status.append("Camera: On")
        else:
            status.append("Camera: Off")
        status.append("Audio: Muted" if self.audio_muted else "Audio: On")
        status.append("Video: Muted" if self.video_muted else "Video: On")
        self.call_status_var.set(" | ".join(status))

    def start_call(self, contact_name):
        if contact_name not in contacts_db:
            messagebox.showerror("Error", "Contact does not exist.")
            return
        if self.call_active:
            messagebox.showinfo("Call", "Already on a call.")
            return
        # Simulate dialing
        self.current_call_target = contact_name
        self.call_active = True
        self.call_start_time = time.time()
        self.call_btn.config(state="disabled")
        self.end_call_btn.config(state="normal")
        self.update_status_text()
        self._animate_remote()
        self._update_timer()
        messagebox.showinfo("Calling", f"Calling {contact_name} (simulated)...")
        # ensure camera on (simulated)
        if not self.camera_active:
            self.start_camera()

    def end_call(self):
        if not self.call_active:
            return
        self.call_active = False
        self.current_call_target = None
        self.call_start_time = None
        self.call_btn.config(state="normal")
        self.end_call_btn.config(state="disabled")
        # stop animations
        if self.remote_anim_id:
            try:
                self.after_cancel(self.remote_anim_id)
            except Exception:
                pass
            self.remote_anim_id = None
        self.render_remote_frame(clear=True)
        self.update_status_text()
        self.timer_var.set("00:00")
        messagebox.showinfo("Call ended", "Call has ended (simulated).")

    def _update_timer(self):
        if not self.call_active or not self.call_start_time:
            return
        elapsed = int(time.time() - self.call_start_time)
        mm = elapsed // 60
        ss = elapsed % 60
        self.timer_var.set(f"{mm:02d}:{ss:02d}")
        self.after(1000, self._update_timer)

    def render_local_frame(self, clear=False):
        self.local_canvas.delete("all")
        if clear or not self.camera_active:
            self.local_canvas.configure(bg="black")
            self.local_canvas.create_text(10, 10, anchor="nw", text="Local camera off", fill="white")
            return
        # draw a simulated "camera feed" frame composed of colored rectangles
        w = self.local_canvas.winfo_width() or 300
        h = self.local_canvas.winfo_height() or 180
        for i in range(6):
            x1 = random.randint(0, max(1, w-20))
            y1 = random.randint(0, max(1, h-20))
            x2 = min(w, x1 + random.randint(30, 120))
            y2 = min(h, y1 + random.randint(20, 80))
            color = f'#{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}'
            self.local_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        self.local_canvas.create_text(8, 8, anchor="nw", text="You (simulated)", fill="white")

    def render_remote_frame(self, clear=False):
        self.remote_canvas.delete("all")
        if clear or not self.call_active or self.video_muted:
            self.remote_canvas.configure(bg="black")
            if self.call_active and self.video_muted:
                self.remote_canvas.create_text(10, 10, anchor="nw", text="Remote video muted", fill="white")
            else:
                self.remote_canvas.create_text(10, 10, anchor="nw", text="No remote feed", fill="white")
            return
        w = self.remote_canvas.winfo_width() or 300
        h = self.remote_canvas.winfo_height() or 180
        # simulated person box and "moving" shapes
        self.remote_canvas.create_oval(10, 10, 80, 80, fill="#5aa", outline="")
        for i in range(8):
            x1 = random.randint(0, max(1, w-30))
            y1 = random.randint(0, max(1, h-30))
            x2 = x1 + random.randint(10, 60)
            y2 = y1 + random.randint(10, 60)
            color = f'#{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}'
            self.remote_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        self.remote_canvas.create_text(8, 8, anchor="nw", text="Remote (simulated)", fill="white")
        # show contact name if available
        if self.current_call_target:
            self.remote_canvas.create_text(w-10, 10, anchor="ne", text=self.current_call_target, fill="white")

    def _animate_local(self):
        if not self.camera_active:
            return
        self.render_local_frame()
        # schedule next frame
        self.local_anim_id = self.after(450, self._animate_local)

    def _animate_remote(self):
        if not self.call_active or self.video_muted:
            return
        self.render_remote_frame()
        self.remote_anim_id = self.after(650, self._animate_remote)

# Helper function to open Video Call app
def open_video_call_app():
    SimulatedVideoCall(root)

# --- Store App ---
def open_store_window():
    win = AppWindow(root, "Store", "🛒")
    taskbar.add_window(win)
    t = theme[current_theme]
    cf = win.content_frame
    for w in cf.winfo_children():
        w.destroy()

    tk.Label(cf, text="ViewRock OS Store", font=APP_TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(pady=12)

    apps_for_install = {
        "Whiteboard Pro+Mega": {
            "desc": "Advanced whiteboard for drawing and notes.",
            "icon": "🖌️",
            "open_func": open_whiteboard_pro_mega_window
        },
        "Tic-Tac-Toe": {
            "desc": "Classic tic-tac-toe game.",
            "icon": "❌⭕",
            "open_func": open_tictactoe_window
        },
        "Terminal++": {
            "desc": "Enhanced terminal with extra commands.",
            "icon": "💻",
            "open_func": lambda: TerminalPlus(root)
        },
        "Contacts": {
            "desc": "Manage your contacts (create/edit/delete).",
            "icon": "👥",
            "open_func": open_contacts_app
        },
        "Video Call (Simulated)": {
            "desc": "Simulated video call UI with mute/camera buttons.",
            "icon": "📹",
            "open_func": open_video_call_app
        }
    }

    def install_app(app_name):
        if app_name in installed_apps:
            messagebox.showinfo("Store", f"'{app_name}' is already installed.")
            return
        installed_apps[app_name] = apps_for_install[app_name]["open_func"]
        add_to_dock(app_name, apps_for_install[app_name]["icon"], apps_for_install[app_name]["open_func"])
        messagebox.showinfo("Store", f"'{app_name}' has been installed!")

    for app_name, app_info in apps_for_install.items():
        frame = tk.Frame(cf, bg=t["bg"], relief="ridge", bd=1)
        frame.pack(fill="x", padx=20, pady=10)

        icon_lbl = tk.Label(frame, text=app_info["icon"], font=("Segoe UI", 24), bg=t["bg"], fg=t["fg"])
        icon_lbl.pack(side="left", padx=10, pady=10)

        info_frame = tk.Frame(frame, bg=t["bg"])
        info_frame.pack(side="left", fill="x", expand=True)

        tk.Label(info_frame, text=app_name, font=TITLE_FONT, bg=t["bg"], fg=t["fg"]).pack(anchor="w")
        tk.Label(info_frame, text=app_info["desc"], font=FONT, bg=t["bg"], fg=t["fg"]).pack(anchor="w")

        install_btn = tk.Button(frame, text="Install", bg=t["btn_bg"], fg=t["btn_fg"],
                                command=lambda n=app_name: install_app(n))
        install_btn.pack(side="right", padx=20, pady=20)

# --- Dock Integration ---
dock_buttons = {}
def add_to_dock(app_name, emoji, open_func):
    # avoid duplicates
    if app_name in dock_buttons:
        return
    btn = tk.Button(dock_frame, text=f"{emoji}\n{app_name}", font=FONT, bg="#1a1a1a", fg="white",
                    relief="flat", padx=10, pady=5, cursor="hand2", justify="center", wraplength=80,
                    command=open_func)
    btn.pack(side="left", padx=8, pady=8)
    dock_buttons[app_name] = btn

def remove_from_dock(app_name):
    btn = dock_buttons.get(app_name)
    if btn:
        btn.destroy()
        del dock_buttons[app_name]

# --- Preinstall core apps in dock ---
def preinstall_core_apps():
    add_to_dock("Notes", "📝", open_notes_window)
    add_to_dock("Calculator", "🧮", open_calculator_window)
    add_to_dock("Terminal", "💻", open_terminal_window)
    add_to_dock("Store", "🛒", open_store_window)
    add_to_dock("File Explorer", "🗂️", open_file_explorer)
    # Do not auto-add Contacts/Video Call — they are in store; but install by default for convenience:
    installed_apps["Contacts"] = open_contacts_app
    installed_apps["Video Call (Simulated)"] = open_video_call_app
    # also add quick icons to dock for convenience
    add_to_dock("Contacts", "👥", open_contacts_app)
    add_to_dock("Video Call", "📹", open_video_call_app)

    settings_icon = tk.Button(dock_frame, text="⚙️", font=("Helvetica", 14), command=open_settings_app, bd=0,
                              bg="white", activebackground="lightgray")
    settings_icon.pack(side="left", padx=5)

preinstall_core_apps()

# --- Terminal++ class (used by store) ---
class TerminalPlus(AppWindow):
    def __init__(self, master):
        super().__init__(master, "Terminal++", "💻")
        self.cwd = "home"
        self.virtual_fs = {
            "home": {"welcome.txt": "Welcome to ViewRock OS!", "info.md": "This is a virtual OS terminal."},
            "docs": {"readme.txt": "This is your documents folder."},
        }
        self.init_ui()
        taskbar.add_window(self)

    def init_ui(self):
        t = theme[current_theme]
        cf = self.content_frame
        for w in cf.winfo_children():
            w.destroy()

        self.output_text = tk.Text(cf, bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_fg"],
                                   font=FONT, state="disabled")
        self.output_text.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(cf, textvariable=self.input_var, bg=t["entry_bg"], fg=t["entry_fg"],
                                    font=FONT, insertbackground=t["entry_fg"])
        self.input_entry.pack(fill="x", padx=10, pady=10)
        self.input_entry.bind("<Return>", self.execute_command)
        self.print_welcome()

    def print(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.output_text.configure(state="disabled")

    def print_welcome(self):
        self.print("Terminal++ for ViewRock OS (Simulated Filesystem)")
        self.print("Type 'mith.help' for commands.")

    def execute_command(self, event=None):
        cmd = self.input_var.get().strip()
        self.print(f"{self.cwd}> {cmd}")
        self.input_var.set("")
        self.handle_command(cmd)

    def handle_command(self, cmd):
        parts = cmd.split()
        if not parts:
            return
        base = parts[0].lower()

        if base == "mith.help":
            self.print("Commands: mith.help, dir, cd <folder>, open <file>, user.catch(), shutdown, restart")
        elif base == "dir":
            items = self.virtual_fs.get(self.cwd, {})
            for item in items:
                self.print(f"- {item}")
        elif base == "cd":
            if len(parts) < 2:
                self.print("Usage: cd <folder>")
            elif parts[1] in self.virtual_fs:
                self.cwd = parts[1]
                self.print(f"Changed directory to {self.cwd}")
            else:
                self.print("Folder not found.")
        elif base == "open":
            if len(parts) < 2:
                self.print("Usage: open <file>")
            else:
                file = parts[1]
                contents = self.virtual_fs.get(self.cwd, {}).get(file)
                if contents:
                    self.print(f"--- {file} ---\n{contents}\n")
                else:
                    self.print(f"File '{file}' not found.")
        elif base == "user.catch()":
            self.print(f"Logged in user: {logged_in_user or 'Guest'}")
        elif base == "shutdown":
            self.print("Shutting down ViewRock OS...")
            root.destroy()
        elif base == "restart":
            self.print("Restarting OS...")
            root.destroy()
            main()
        else:
            self.print(f"Unknown command: {cmd}")

# --- Signup/Login system ---
def signup_window():
    global logged_in_user
    win = tk.Toplevel(root)
    win.title(f"{APP_NAME} - Create Account")
    win.geometry("400x280")
    win.configure(bg=theme[current_theme]["bg"])
    win.resizable(False, False)

    tk.Label(win, text="Create New Account", font=APP_TITLE_FONT, bg=theme[current_theme]["bg"],
             fg=theme[current_theme]["fg"]).pack(pady=20)

    username_var = tk.StringVar()
    password_var = tk.StringVar()

    frm = tk.Frame(win, bg=theme[current_theme]["bg"])
    frm.pack(pady=10, padx=30, fill="x")

    tk.Label(frm, text="Username:", bg=theme[current_theme]["bg"], fg=theme[current_theme]["fg"]).pack(anchor="w")
    username_entry = tk.Entry(frm, textvariable=username_var, font=FONT)
    username_entry.pack(fill="x", pady=5)

    tk.Label(frm, text="Password:", bg=theme[current_theme]["bg"], fg=theme[current_theme]["fg"]).pack(anchor="w")
    password_entry = tk.Entry(frm, textvariable=password_var, show="*", font=FONT)
    password_entry.pack(fill="x", pady=5)

    def create_account():
        username = username_var.get().strip()
        password = password_var.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return
        if username in user_db:
            messagebox.showerror("Error", "Username already exists.")
            return
        user_db[username] = password
        messagebox.showinfo("Success", f"Account '{username}' created! You can now login.")
        win.destroy()

    create_btn = tk.Button(win, text="Create Account", command=create_account)
    create_btn.pack(pady=20, ipadx=10, ipady=5)

    username_entry.focus()

def login_window():
    global logged_in_user
    win = tk.Toplevel(root)
    win.title(f"{APP_NAME} - Login")
    win.geometry("400x280")
    win.configure(bg=theme[current_theme]["bg"])
    win.resizable(False, False)

    tk.Label(win, text="Login to ViewRock OS", font=APP_TITLE_FONT,
             bg=theme[current_theme]["bg"], fg=theme[current_theme]["fg"]).pack(pady=20)

    username_var = tk.StringVar()
    password_var = tk.StringVar()

    frm = tk.Frame(win, bg=theme[current_theme]["bg"])
    frm.pack(pady=10, padx=30, fill="x")

    tk.Label(frm, text="Username:", bg=theme[current_theme]["bg"], fg=theme[current_theme]["fg"]).pack(anchor="w")
    username_entry = tk.Entry(frm, textvariable=username_var, font=FONT)
    username_entry.pack(fill="x", pady=5)

    tk.Label(frm, text="Password:", bg=theme[current_theme]["bg"], fg=theme[current_theme]["fg"]).pack(anchor="w")
    password_entry = tk.Entry(frm, textvariable=password_var, show="*", font=FONT)
    password_entry.pack(fill="x", pady=5)

    def try_login():
        username = username_var.get().strip()
        password = password_var.get().strip()
        if username in user_db and user_db[username] == password:
            nonlocal_message = f"Welcome, {username}!"
            logged_in_user = username
            messagebox.showinfo("Login Successful", nonlocal_message)
            win.destroy()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    login_btn = tk.Button(win, text="Login", command=try_login)
    login_btn.pack(pady=20, ipadx=10, ipady=5)

    username_entry.focus()

# --- Start the OS ---
def main():
    root.deiconify()
    # For convenience: skip signup/login in dev if user_db contains default
    if not user_db:
        # create a default account for quick testing
        user_db["demo"] = "demo"
    signup_window()
    login_window()
    root.mainloop()

if __name__ == "__main__":
    root.withdraw()
    main()
