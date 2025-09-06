import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import datetime, time, webbrowser, os, sys
from PIL import Image, ImageTk
import cv2
import math

# --- Globals ---
current_user = None

theme = {
    "dark": {
        "bg": "#D3D3D3",
        "fg": "#000000",
        "btn_bg": "#E0E0E0",
        "btn_fg": "#000000",
        "active_bg": "#C0C0C0",
        "taskbar_bg": "#B0B0B0",
    },
    "light": {
        "bg": "#FFFFFF",
        "fg": "#000000",
        "btn_bg": "#E0E0E0",
        "btn_fg": "#000000",
        "active_bg": "#BBBBBB",
        "taskbar_bg": "#DDDDDD",
    },
    "grey": {
        "bg": "#555555",
        "fg": "#FFFFFF",
        "btn_bg": "#777777",
        "btn_fg": "#FFFFFF",
        "active_bg": "#999999",
        "taskbar_bg": "#666666",
    }
}

current_theme = "dark"  # default
notes_data = {}

# --- Main window ---
root = tk.Tk()
root.withdraw()

# --- Helper function: apply theme to widgets recursively ---
def apply_theme_to_widget(widget):
    t = theme[current_theme]
    try:
        if isinstance(widget, (tk.Frame, tk.LabelFrame)):
            widget.configure(bg=t["bg"])
        elif isinstance(widget, tk.Button):
            widget.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"], relief='flat')
        elif isinstance(widget, tk.Label):
            widget.configure(bg=t["bg"], fg=t["fg"])
        elif isinstance(widget, tk.Listbox):
            widget.configure(bg=t["btn_bg"], fg=t["btn_fg"], selectbackground=t["active_bg"])
        elif isinstance(widget, tk.Entry):
            widget.configure(bg="white", fg="black")
        elif isinstance(widget, tk.Text):
            widget.configure(bg="white", fg="black")
    except Exception:
        pass
    for child in widget.winfo_children():
        apply_theme_to_widget(child)

def apply_theme():
    t = theme[current_theme]
    root.configure(bg=t["bg"])
    apply_theme_to_widget(root)

# --- Boot Sequence ---
def boot_sequence():
    splash = tk.Toplevel()
    splash.title("Booting ViewRock OS")
    splash.geometry("500x300")
    splash.configure(bg="#888")
    splash.attributes('-alpha', 0.0)
    label = tk.Label(splash, text="ViewRock OS is launching...", font=("Arial", 16), fg="black", bg="#888")
    label.pack(expand=True)
    splash.update()
    for alpha in range(0, 11):
        splash.attributes('-alpha', alpha / 10)
        splash.update()
        time.sleep(0.1)
    time.sleep(1.5)
    splash.destroy()

# --- Create User ---
def create_user():
    global current_user
    username = simpledialog.askstring("Create User", "Enter new username:")
    if not username:
        root.quit()
        return
    current_user = username
    show_homescreen()

# --- UI Elements ---
app_buttons = []
showing_apps = False

# Container frames (created once)
left_frame = None
center_frame = None
taskbar = None
time_label = None
start_button = None

# --- App UI placeholders ---
def clear_center_frame():
    for widget in center_frame.winfo_children():
        widget.destroy()

# Notes app inside center frame
def show_notes():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="Notes", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    title_var = tk.StringVar()
    tk.Label(center_frame, text="Title:", bg=t["bg"], fg=t["fg"]).pack(anchor="w", padx=20)
    title_entry = tk.Entry(center_frame, textvariable=title_var, width=40)
    title_entry.pack(padx=20, pady=5)

    tk.Label(center_frame, text="Content:", bg=t["bg"], fg=t["fg"]).pack(anchor="w", padx=20)
    content_text = tk.Text(center_frame, height=10, width=50)
    content_text.pack(padx=20, pady=5)

    notes_listbox = tk.Listbox(center_frame, width=50, height=7)
    notes_listbox.pack(pady=10, padx=20)

    def refresh_list():
        notes_listbox.delete(0, tk.END)
        for k in notes_data:
            notes_listbox.insert(tk.END, k)

    def save_note():
        title = title_var.get().strip()
        content = content_text.get("1.0", tk.END).strip()
        if title and content:
            notes_data[title] = content
            refresh_list()
            title_var.set("")
            content_text.delete("1.0", tk.END)

    def delete_note():
        sel = notes_listbox.curselection()
        if sel:
            key = notes_listbox.get(sel[0])
            if key in notes_data:
                del notes_data[key]
                refresh_list()

    def view_note():
        sel = notes_listbox.curselection()
        if sel:
            key = notes_listbox.get(sel[0])
            if key in notes_data:
                title_var.set(key)
                content_text.delete("1.0", tk.END)
                content_text.insert(tk.END, notes_data[key])

    btn_frame = tk.Frame(center_frame, bg=t["bg"])
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="Save", command=save_note, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Clear", command=lambda: (title_var.set(""), content_text.delete("1.0", tk.END)), bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete", command=delete_note, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(side="left", padx=5)

    tk.Button(center_frame, text="View Note", command=view_note, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(pady=5)

    refresh_list()

# Calculator app inside center frame
def show_calculator():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="Calculator", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    expression = ""
    history = []

    display_var = tk.StringVar()
    display_entry = tk.Entry(center_frame, textvariable=display_var, font=("Arial", 20), bd=5, relief="sunken", justify="right", bg="white")
    display_entry.pack(fill="x", ipady=10, pady=10, padx=20)
    display_entry.focus()

    history_box = tk.Listbox(center_frame, height=4, font=("Arial", 10))
    history_box.pack(fill="x", padx=20, pady=5)

    def update_display(val):
        nonlocal expression
        expression += str(val)
        display_var.set(expression)

    def calculate(event=None):
        nonlocal expression
        try:
            exp = expression.replace('^', '**').replace('π', str(math.pi))
            result = str(eval(exp, {"__builtins__": {}}, math.__dict__))
            history.append(f"{expression} = {result}")
            history_box.insert(tk.END, f"{expression} = {result}")
            display_var.set(result)
            expression = result
        except:
            display_var.set("Error")
            expression = ""

    def clear(event=None):
        nonlocal expression
        expression = ""
        display_var.set("")

    button_frame = tk.Frame(center_frame, bg=t["bg"])
    button_frame.pack()

    standard_buttons = [
        ('7', '8', '9', '/'),
        ('4', '5', '6', '*'),
        ('1', '2', '3', '-'),
        ('0', '.', '=', '+')
    ]

    sci_buttons = [
        ('π', 'sqrt', '^', 'log'),
        ('sin', 'cos', 'tan', 'clear')
    ]

    for row in standard_buttons:
        row_frame = tk.Frame(button_frame, bg=t["bg"])
        row_frame.pack(expand=True, fill="both")
        for btn in row:
            if btn == '=':
                action = calculate
            else:
                action = lambda val=btn: update_display(val)
            b = tk.Button(row_frame, text=btn, font=("Arial", 14), width=5, height=2,
                          command=action, bg=t["btn_bg"], fg=t["btn_fg"],
                          activebackground=t["active_bg"])
            b.pack(side="left", expand=True, fill="both", padx=2, pady=2)

    sci_frame = tk.LabelFrame(center_frame, text="Scientific", bg=t["bg"], fg=t["fg"])
    sci_frame.pack(fill="x", padx=20, pady=10)

    def handle_sci(func):
        nonlocal expression
        if func == 'clear':
            clear()
        elif func in ['sin', 'cos', 'tan', 'log', 'sqrt']:
            expression = f"{func}({expression})"
            display_var.set(expression)
        else:
            update_display(func)

    for row in sci_buttons:
        row_frame = tk.Frame(sci_frame, bg=t["bg"])
        row_frame.pack(fill="x")
        for btn in row:
            b = tk.Button(row_frame, text=btn, font=("Arial", 12), width=5,
                          command=lambda val=btn: handle_sci(val),
                          bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"])
            b.pack(side="left", expand=True, fill="both", padx=2, pady=2)

    def key_input(event):
        key = event.char
        if key in '0123456789.+-*/^':
            update_display(key)
        elif key == '\r':
            calculate()
        elif key == '\x08':
            nonlocal expression
            expression = expression[:-1]
            display_var.set(expression)

    center_frame.bind_all("<Key>", key_input)
    center_frame.bind_all("<Return>", calculate)
    center_frame.bind_all("<BackSpace>", key_input)

# Whiteboard app inside center frame
def show_whiteboard():
    clear_center_frame()

    t = theme[current_theme]

    tk.Label(center_frame, text="Whiteboard", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)
    canvas = tk.Canvas(center_frame, bg="white")
    canvas.pack(fill="both", expand=True, padx=20, pady=10)

    def draw(event):
        x, y = event.x, event.y
        canvas.create_oval(x-2, y-2, x+2, y+2, fill="black", outline="")

    canvas.bind("<B1-Motion>", draw)

# Browser app opens external browser (small popup)
def show_browser():
    url = simpledialog.askstring("Browser", "Enter site name or URL (without https://):")
    if url:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)

# File Storage placeholder (just a small window)
def show_file_storage():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="File Storage", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)
    def upload():
        filepath = filedialog.askopenfilename()
        if filepath:
            filename = os.path.basename(filepath)
            tk.Label(center_frame, text=f"Uploaded: {filename}", bg=t["bg"], fg=t["fg"]).pack()

    tk.Button(center_frame, text="Upload File", command=upload, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(pady=10)

# Camera app inside center frame with OpenCV feed
def show_camera():
    clear_center_frame()

    t = theme[current_theme]

    tk.Label(center_frame, text="Camera", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    cam_label = tk.Label(center_frame)
    cam_label.pack()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Camera not supported or found.")
        return

    def update_frame():
        ret, frame = cap.read()
        if ret:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            cam_label.imgtk = imgtk
            cam_label.configure(image=imgtk)
        cam_label.after(20, update_frame)

    update_frame()

    def on_close():
        cap.release()
        clear_center_frame()

    center_frame.bind("<Destroy>", lambda e: cap.release())

# Task Manager placeholder inside center frame
def show_task_manager():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="Task Manager", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    frame_list = tk.Frame(center_frame, bg=t["bg"])
    frame_list.pack(fill="both", expand=True)

    def refresh():
        for widget in frame_list.winfo_children():
            widget.destroy()
        # List all Toplevel windows except root
        for win in root.winfo_children():
            if isinstance(win, tk.Toplevel):
                title = win.title()
                row = tk.Frame(frame_list, bg=t["bg"])
                row.pack(fill="x", padx=10, pady=3)
                tk.Label(row, text=title, bg=t["bg"], fg=t["fg"]).pack(side="left")
                tk.Button(row, text="End Task", command=win.destroy, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(side="right")
    refresh()

# Settings placeholder inside center frame
def show_settings():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="Settings", font=("Arial", 16), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    def toggle_theme_button():
        toggle_theme()

    tk.Button(center_frame, text="Toggle Theme", command=toggle_theme_button, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(pady=10)
    tk.Button(center_frame, text="Toggle Glass Mode", command=toggle_glass_mode, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(pady=10)

# Control Panel placeholder
def show_control_panel():
    clear_center_frame()
    t = theme[current_theme]

    tk.Label(center_frame, text="Control Panel", font=("Arial", 16, "bold"), bg=t["bg"], fg=t["fg"]).pack(pady=10)

    tk.Label(center_frame, text=f"Current User: {current_user}", bg=t["bg"], fg=t["fg"], font=("Arial", 12)).pack(pady=5)

    tk.Label(center_frame, text="Select Theme:", bg=t["bg"], fg=t["fg"], font=("Arial", 12)).pack(pady=10)

    theme_var = tk.StringVar(value=current_theme)

    def set_theme():
        global current_theme
        current_theme = theme_var.get()
        apply_theme()

    for th in theme.keys():
        rb = tk.Radiobutton(center_frame, text=th.capitalize(), variable=theme_var, value=th,
                            bg=t["bg"], fg=t["fg"], selectcolor=t["btn_bg"], activebackground=t["active_bg"],
                            command=set_theme)
        rb.pack(anchor="w", padx=20)

    tk.Button(center_frame, text="Toggle Glass Mode", command=toggle_glass_mode, bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["active_bg"]).pack(pady=20)

# --- Other functions ---
def toggle_theme():
    global current_theme
    themes = list(theme.keys())
    idx = themes.index(current_theme)
    current_theme = themes[(idx + 1) % len(themes)]
    apply_theme()

def toggle_glass_mode():
    if root.attributes('-alpha') == 1.0:
        root.attributes('-alpha', 0.85)
    else:
        root.attributes('-alpha', 1.0)

def restart_os():
    root.destroy()
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- Taskbar ---
def create_taskbar():
    global taskbar, time_label, start_button
    t = theme[current_theme]
    taskbar = tk.Frame(root, bg=t["taskbar_bg"], height=40)
    taskbar.pack(side="bottom", fill="x")

    start_button = tk.Button(taskbar, text="Start", command=toggle_left_menu, bg=t["btn_bg"], fg=t["btn_fg"], relief='flat')
    start_button.place(x=5, y=5)

    tk.Label(taskbar, text="ViewRock OS", fg=t["btn_fg"], bg=t["taskbar_bg"], font=("Arial", 10, "bold")).pack(side="left", padx=50)

    time_label = tk.Label(taskbar, fg=t["btn_fg"], bg=t["taskbar_bg"], font=("Arial", 10))
    time_label.pack(side="right", padx=10)

    def update_clock():
        now = datetime.datetime.now()
        time_label.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        time_label.after(1000, update_clock)

    update_clock()

# --- Left app menu ---
def create_left_menu():
    global left_frame
    left_frame = tk.Frame(root, width=200)
    # Initially hidden, pack on demand

    buttons = [
        ("Notes", show_notes),
        ("Calculator", show_calculator),
        ("Whiteboard", show_whiteboard),
        ("Browser", show_browser),
        ("File Storage", show_file_storage),
        ("Camera", show_camera),
        ("Task Manager", show_task_manager),
        ("Settings", show_settings),
        ("Control Panel", show_control_panel),
        ("Toggle Theme", toggle_theme),
        ("Toggle Glass Mode", toggle_glass_mode),
        ("Restart OS", restart_os),
        ("Shutdown OS", root.quit)
    ]

    for (text, cmd) in buttons:
        b = tk.Button(left_frame, text=text, command=cmd, width=20, pady=5, relief='flat')
        b.pack(pady=4, padx=5)

def toggle_left_menu():
    global showing_apps
    if left_frame.winfo_ismapped():
        left_frame.pack_forget()
    else:
        left_frame.pack(side="left", fill="y")

# --- Center frame ---
def create_center_frame():
    global center_frame
    center_frame = tk.Frame(root, bd=2, relief="sunken")
    center_frame.pack(side="left", fill="both", expand=True)

# --- Show Home Screen ---
def show_homescreen():
    root.deiconify()
    root.title(f"ViewRock OS Desktop - {current_user}")
    root.geometry("900x700")
    root.minsize(900, 700)
    create_taskbar()
    create_left_menu()
    create_center_frame()
    apply_theme()

    # Show welcome message
    clear_center_frame()
    t = theme[current_theme]
    tk.Label(center_frame, text="Welcome to ViewRock OS!\nSelect an app from the left menu.",
             justify="center", font=("Arial", 18), bg=t["bg"], fg=t["fg"]).pack(expand=True)

# --- Start OS ---
boot_sequence()
create_user()
root.mainloop()
