import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import json
import time
import threading
import psutil
import keyboard
import mouse
import os
import winsound
import sys
from PIL import Image, ImageTk

# Helper to get resource path for PyInstaller
BASE_PATH = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))

SETTINGS_PATH = os.path.join(BASE_PATH, 'settings.json')
SOUNDS_PATH = os.path.join(BASE_PATH, 'resources')
ICON_PATH = os.path.join(BASE_PATH, 'resources', 'icons8-lock-100.png')

# Load or initialize settings
def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "inactivity_threshold": 300,
            "warning_messages": ["Warning: Inactivity detected!", "System will lock soon!"],
            "warning_levels": 3,
            "dark_mode": False,
            "lock_time": "22:00",
            "cpu_disk_threshold": 80,
            "user_profiles": {"default": {}},
            "active_profile": "default",
            "alert_sound_frequency": 1000,
            "alert_sound_duration": 1000,
            "num_alerts": 3,
            "selected_alert_sound": "default.wav"
        }

def save_settings():
    with open(SETTINGS_PATH, "w") as file:
        json.dump(settings, file, indent=4)

settings = load_settings()
inactivity_timer = 0
warning_counter = 0
is_locked = False
monitoring_active = False

# Available alert sounds
alert_sounds = [f for f in os.listdir(SOUNDS_PATH) if f.endswith('.wav')]
if not alert_sounds:
    alert_sounds = ["default.wav"]

# GUI Setup
class ActivityDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart User Inactivity Monitor")
        self.geometry("700x800")
        self.resizable(True, True)  # Allow maximize
        self.protocol("WM_DELETE_WINDOW", self.exit_application)
        self.dark_mode = settings.get("dark_mode", False)
        self.configure_theme()
        self.create_widgets()
        self.show_welcome()
        self.update_metrics()

    def configure_theme(self):
        if self.dark_mode:
            self.bg_color = "#23272e"
            self.fg_color = "#f8f8f2"
            self.button_bg = "#44475a"
            self.button_fg = "#f8f8f2"
            self.entry_bg = "#282a36"
        else:
            self.bg_color = "white"
            self.fg_color = "black"
            self.button_bg = "#357edd"
            self.button_fg = "white"
            self.entry_bg = "#f0f0f0"
        self.configure(bg=self.bg_color)

    def create_widgets(self):
        # Remove previous widgets if any
        for widget in self.winfo_children():
            widget.destroy()

        # Set window size
        self.geometry("700x800")

        # Configure grid for root window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Exit button (top right, not in scroll area)
        self.exit_button = tk.Button(self, text="Exit", command=self.exit_application, bg="red", fg="white", width=10, height=2, font=("Comic Sans MS", 12))
        self.exit_button.grid(row=0, column=1, sticky='ne', padx=10, pady=30)

        # Create a canvas and a vertical scrollbar for scrolling
        canvas = tk.Canvas(self, bg=self.bg_color, highlightthickness=0)
        v_scroll = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.grid(row=1, column=0, columnspan=2, sticky='nsew')
        v_scroll.grid(row=1, column=2, sticky='ns')

        # Mouse wheel scrolling support (only scroll, no zoom)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _on_linux_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_linux_mousewheel)
        canvas.bind_all("<Button-5>", _on_linux_mousewheel)

        # Main frame inside the canvas, centered
        self.main_frame = tk.Frame(canvas, bg=self.bg_color)
        self.main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.main_frame, anchor="center")

        # Centered content frame for all widgets
        center_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        center_frame.pack(expand=True)

        # Icon at the top
        try:
            img = Image.open(ICON_PATH)
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            self.icon_img = ImageTk.PhotoImage(img)
            self.icon_label = tk.Label(center_frame, image=self.icon_img, bg=self.bg_color)
            self.icon_label.pack(pady=(30, 10))
        except Exception:
            self.icon_label = None
        # Status label with icon
        self.status_label = tk.Label(center_frame, text="✔ Active", font=("Comic Sans MS", 20, "bold"), fg="green", bg=self.bg_color)
        self.status_label.pack(pady=(30, 10))

        # System metrics
        self.cpu_label = tk.Label(center_frame, text="CPU Usage: 0.0%", font=("Comic Sans MS", 12), bg=self.bg_color, fg=self.fg_color)
        self.cpu_label.pack(pady=5)
        self.disk_label = tk.Label(center_frame, text="Disk Usage: 0.0%", font=("Comic Sans MS", 12), bg=self.bg_color, fg=self.fg_color)
        self.disk_label.pack(pady=5)
        self.warning_label = tk.Label(center_frame, text="Warnings: 0", font=("Comic Sans MS", 12), fg="darkred", bg=self.bg_color)
        self.warning_label.pack(pady=(5, 20))

        # Profile selection (centered)
        profile_frame = tk.Frame(center_frame, bg=self.bg_color)
        profile_frame.pack(pady=8)
        profile_frame.grid_columnconfigure(0, weight=1)
        profile_frame.grid_columnconfigure(1, weight=1)
        profile_frame.grid_columnconfigure(2, weight=1)
        profile_frame.grid_columnconfigure(3, weight=1)
        tk.Label(profile_frame, text="Profile:", bg=self.bg_color, fg=self.fg_color, font=("Comic Sans MS", 12)).grid(row=0, column=0, padx=5, sticky='e')
        self.profile_var = tk.StringVar(value=settings.get("active_profile", "default"))
        self.profile_dropdown = ttk.Combobox(profile_frame, values=list(settings["user_profiles"].keys()), textvariable=self.profile_var, width=15, font=("Comic Sans MS", 12))
        self.profile_dropdown.grid(row=0, column=1, padx=5, sticky='e')
        self.profile_dropdown.bind("<<ComboboxSelected>>", self.on_profile_change)
        tk.Button(profile_frame, text="New", command=self.add_profile, bg=self.button_bg, fg=self.button_fg, font=("Comic Sans MS", 12)).grid(row=0, column=2, padx=2, sticky='e')
        tk.Button(profile_frame, text="Delete", command=self.delete_profile, bg=self.button_bg, fg=self.button_fg, font=("Comic Sans MS", 12)).grid(row=0, column=3, padx=2, sticky='e')

        # Lock Now and Start Monitoring (centered)
        btn_frame_top = tk.Frame(center_frame, bg=self.bg_color)
        btn_frame_top.pack(pady=10)
        btn_frame_top.grid_columnconfigure(0, weight=1)
        btn_frame_top.grid_columnconfigure(1, weight=1)
        self.lock_button = tk.Button(btn_frame_top, text="Lock Now", bg=self.button_bg, fg=self.button_fg, width=15, height=2, command=self.lock_system, font=("Comic Sans MS", 14))
        self.lock_button.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.start_button = tk.Button(btn_frame_top, text="Start Monitoring", bg=self.button_bg, fg=self.button_fg, width=15, height=2, command=self.start_monitoring, font=("Comic Sans MS", 14))
        self.start_button.grid(row=0, column=1, padx=10, pady=10, sticky='e')

        # Vertical buttons for timers and sound settings
        self.set_inactivity_button = tk.Button(center_frame, text="Set Inactivity Timer", width=30, height=2, command=self.set_timer, bg=self.button_bg, fg=self.button_fg, font=("Comic Sans MS", 12))
        self.set_inactivity_button.pack(pady=10)
        self.set_alert_button = tk.Button(center_frame, text="Set Alert Sounds", width=30, height=2, command=self.set_alert_settings, bg=self.button_bg, fg=self.button_fg, font=("Comic Sans MS", 12))
        self.set_alert_button.pack(pady=8)

        # Dropdown for selecting sound (friendly names, supports .wav and .mp3)
        sound_label = tk.Label(center_frame, text="Select Alert Sound:", bg=self.bg_color, fg=self.fg_color, font=("Comic Sans MS", 12))
        sound_label.pack(pady=8)
        global alert_sounds, alert_sound_map
        alert_sounds = []
        alert_sound_map = {}
        for f in os.listdir(SOUNDS_PATH):
            if f.lower().endswith('.wav') or f.lower().endswith('.mp3'):
                if f.lower() == 'alert_1.wav' or f.lower() == 'alert_1.mp3':
                    friendly = 'Alert 1'
                elif f.lower() == 'alert_2.wav' or f.lower() == 'alert_2.mp3':
                    friendly = 'Alert 2'
                else:
                    friendly = os.path.splitext(f)[0].replace('_', ' ').title()
                alert_sounds.append(friendly)
                alert_sound_map[friendly] = f
        if not alert_sounds:
            alert_sounds = ['Default']
            alert_sound_map['Default'] = 'default.wav'
        selected_sound_file = settings.get('selected_alert_sound', alert_sound_map[alert_sounds[0]])
        # Find the friendly name for the selected file
        selected_friendly = next((k for k, v in alert_sound_map.items() if v == selected_sound_file), alert_sounds[0])
        self.sound_dropdown = ttk.Combobox(center_frame, values=alert_sounds, width=27, font=("Comic Sans MS", 12))
        self.sound_dropdown.set(selected_friendly)
        self.sound_dropdown.pack(pady=8)
        self.sound_dropdown.bind("<<ComboboxSelected>>", self.on_sound_selection)

        # Dark mode toggle
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        self.dark_mode_check = tk.Checkbutton(center_frame, text="Dark Mode", variable=self.dark_mode_var, command=self.toggle_dark_mode, bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color, font=("Comic Sans MS", 12))
        self.dark_mode_check.pack(pady=10)

    def show_welcome(self):
        if not getattr(self, '_welcome_shown', False):
            welcome = tk.Toplevel(self)
            welcome.title('Welcome')
            welcome.geometry('350x200')
            welcome.configure(bg=self.bg_color)
            tk.Label(welcome, text='Welcome to Smart Inactivity Monitor!', font=('Comic Sans MS', 14, 'bold'), bg=self.bg_color, fg=self.fg_color).pack(pady=10)
            tk.Label(welcome, text='Set your preferences and start monitoring.\nFor help, see README.txt.', font=('Comic Sans MS', 10), bg=self.bg_color, fg=self.fg_color).pack(pady=10)
            tk.Button(welcome, text='OK', command=welcome.destroy, bg=self.button_bg, fg=self.button_fg).pack(pady=20)
            self._welcome_shown = True

    def update_metrics(self):
        global inactivity_timer, warning_counter, is_locked
        cpu_usage = psutil.cpu_percent()
        disk_usage = psutil.disk_usage('/').percent
        self.cpu_label.config(text=f"CPU Usage: {cpu_usage:.1f}%")
        self.disk_label.config(text=f"Disk Usage: {disk_usage:.1f}%")
        self.warning_label.config(text=f"Warnings: {warning_counter}")
        if monitoring_active and inactivity_timer >= settings["inactivity_threshold"] and not is_locked:
            self.issue_warning()
        self.after(1000, self.update_metrics)

    def issue_warning(self):
        global warning_counter, is_locked
        if warning_counter < settings["warning_levels"]:
            self.show_notification(settings["warning_messages"][warning_counter % len(settings["warning_messages"])])
            for _ in range(settings["num_alerts"]):
                winsound.Beep(settings["alert_sound_frequency"], settings["alert_sound_duration"])
                time.sleep(0.5)
            warning_counter += 1
        else:
            self.lock_system()

    def show_notification(self, message):
        notification_window = tk.Toplevel(self)
        notification_window.title("Warning")
        notification_window.geometry("300x100")
        notification_window.configure(bg=self.bg_color)
        tk.Label(notification_window, text=message, fg="red", font=("Comic Sans MS", 12), bg=self.bg_color).pack(pady=10)

    def lock_system(self):
        global is_locked
        is_locked = True
        self.status_label.config(text="✖ Locked", fg="red")
        os.system("rundll32.exe user32.dll, LockWorkStation")

    def set_timer(self):
        global settings
        new_time = simpledialog.askinteger("Set Timer", "Enter inactivity time (seconds):", minvalue=10, maxvalue=3600)
        if new_time:
            settings["inactivity_threshold"] = new_time
            save_settings()
            self.start_monitoring()

    def set_alert_settings(self):
        global settings
        frequency = simpledialog.askinteger("Set Frequency", "Enter alert sound frequency (Hz):", minvalue=200, maxvalue=3000)
        duration = simpledialog.askinteger("Set Duration", "Enter alert duration (ms):", minvalue=100, maxvalue=20000)
        num_alerts = simpledialog.askinteger("Set Number of Alerts", "Enter number of alert sounds:", minvalue=1, maxvalue=10)
        if frequency and duration and num_alerts:
            settings["alert_sound_frequency"] = frequency
            settings["alert_sound_duration"] = duration
            settings["num_alerts"] = num_alerts
            save_settings()

    def on_sound_selection(self, event):
        # Use the friendly name to get the file
        selected_friendly = self.sound_dropdown.get()
        selected_file = alert_sound_map.get(selected_friendly, 'default.wav')
        settings["selected_alert_sound"] = selected_file
        save_settings()

    def start_monitoring(self):
        global monitoring_active, inactivity_timer, warning_counter, is_locked
        monitoring_active = True
        inactivity_timer = 0
        warning_counter = 0
        is_locked = False
        self.status_label.config(text="✔ Active", fg="green")

    def exit_application(self):
        global monitoring_active
        monitoring_active = False
        save_settings()
        keyboard.unhook_all()
        mouse.unhook_all()
        self.destroy()

    def toggle_dark_mode(self):
        self.dark_mode = self.dark_mode_var.get()
        settings["dark_mode"] = self.dark_mode
        save_settings()
        self.configure_theme()
        for widget in self.winfo_children():
            for opt in ("bg", "background"):
                if opt in widget.keys():
                    widget.configure(**{opt: self.bg_color})
            for opt in ("fg", "foreground"):
                if opt in widget.keys():
                    widget.configure(**{opt: self.fg_color})
        self.create_widgets()

    def on_profile_change(self, event):
        selected = self.profile_var.get()
        if selected in settings["user_profiles"]:
            settings["active_profile"] = selected
            save_settings()

    def add_profile(self):
        new_profile = simpledialog.askstring("New Profile", "Enter profile name:")
        if new_profile and new_profile not in settings["user_profiles"]:
            settings["user_profiles"][new_profile] = {}
            settings["active_profile"] = new_profile
            self.profile_dropdown["values"] = list(settings["user_profiles"].keys())
            self.profile_var.set(new_profile)
            save_settings()

    def delete_profile(self):
        current = self.profile_var.get()
        if current != "default" and current in settings["user_profiles"]:
            del settings["user_profiles"][current]
            settings["active_profile"] = "default"
            self.profile_dropdown["values"] = list(settings["user_profiles"].keys())
            self.profile_var.set("default")
            save_settings()

# Activity Tracking
def on_activity(event):
    global inactivity_timer, warning_counter, is_locked
    inactivity_timer = 0
    warning_counter = 0
    if is_locked:
        dashboard.status_label.config(text="✔ Active", fg="green")
        is_locked = False

def monitor_activity():
    global inactivity_timer
    while True:
        time.sleep(1)
        if monitoring_active:
            inactivity_timer += 1

# Register activity listeners
keyboard.on_press(on_activity)
mouse.hook(lambda event: on_activity(event))

def main():
    global dashboard
    dashboard = ActivityDashboard()
    activity_thread = threading.Thread(target=monitor_activity, daemon=True)
    activity_thread.start()
    dashboard.mainloop()
    save_settings()

if __name__ == "__main__":
    main() 