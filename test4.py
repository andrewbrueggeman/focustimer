
import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys
import os
from pathlib import Path

# --- Helper to locate app directory (works for source, one-folder, one-file) ---
def get_app_dir() -> Path:
    if hasattr(sys, "frozen"):  # Running as PyInstaller exe
        return Path(os.path.dirname(sys.executable))
    return Path(os.path.dirname(os.path.abspath(__file__)))

APP_DIR = get_app_dir()
MESSAGE_FILE = APP_DIR / "message.txt"


class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Custom Timer")
        self.root.geometry("560x560")

        self.timer_running = False
        self.timer_paused = False
        self.remaining_time = 0
        self.flash_active = False

        self.last_minutes = 0
        self.last_seconds = 0

        # Store original backgrounds to restore after flashing
        self._bg_originals = {}

        # Load existing motivational message (creates file if missing)
        self.motivational_message = self._load_message()

        # ---------- CENTRAL COLUMN (everything centered) ----------
        # Vertical frame that holds: manual inputs, presets, Add Message button
        self.center_column = tk.Frame(root)
        self.center_column.pack(pady=12, fill=tk.X)
        self.center_inner = tk.Frame(self.center_column)
        self.center_inner.pack()

        # Manual duration inputs (centered)
        self.intro_label = tk.Label(self.center_inner, text="Enter timer duration:")
        self.intro_label.pack(pady=(0, 6))

        manual_row1 = tk.Frame(self.center_inner)
        manual_row1.pack()
        self.minutes_label = tk.Label(manual_row1, text="Minutes:")
        self.minutes_label.pack(side=tk.LEFT, padx=(0, 6))
        self.minutes_entry = tk.Entry(manual_row1, width=8)
        self.minutes_entry.pack(side=tk.LEFT, padx=(0, 12))

        self.seconds_label = tk.Label(manual_row1, text="Seconds:")
        self.seconds_label.pack(side=tk.LEFT, padx=(0, 6))
        self.seconds_entry = tk.Entry(manual_row1, width=8)
        self.seconds_entry.pack(side=tk.LEFT)

        self.set_button = tk.Button(self.center_inner, text="Set Timer", command=self.set_and_start_timer)
        self.set_button.pack(pady=8)

        # Preset buttons (centered, two rows)
        self.preset_frame = tk.Frame(self.center_inner)
        self.preset_frame.pack(pady=10)

        self.preset_label = tk.Label(self.preset_frame, text="Or choose a preset:")
        self.preset_label.pack(pady=(0, 6))

        # Row 1: 10, 20, 30
        self.preset_row1 = tk.Frame(self.preset_frame)
        self.preset_row1.pack()
        for mins in (10, 20, 30):
            tk.Button(
                self.preset_row1,
                text=f"{mins}:00",
                font=("Helvetica", 14),
                width=8,
                height=2,
                command=lambda m=mins: self.set_preset_timer(m)
            ).pack(side=tk.LEFT, padx=5, pady=2)

        # Row 2: 40, 50, 60
        self.preset_row2 = tk.Frame(self.preset_frame)
        self.preset_row2.pack()
        for mins in (40, 50, 60):
            tk.Button(
                self.preset_row2,
                text=f"{mins}:00",
                font=("Helvetica", 14),
                width=8,
                height=2,
                command=lambda m=mins: self.set_preset_timer(m)
            ).pack(side=tk.LEFT, padx=5, pady=2)

        # Add Message button (centered BELOW presets)
        self.add_message_button = tk.Button(self.center_inner, text="Add Message", command=self._show_message_entry)
        self.add_message_button.pack(pady=(8, 0))

        # Hidden entry (revealed by Add Message)
        self.message_entry = tk.Entry(self.center_inner, width=34, font=("Helvetica", 12))
        self.message_entry.bind("<Return>", self._commit_message)

        # ---------- MAIN AREA: timer center + message bubble right ----------
        self.main_area = tk.Frame(root)
        self.main_area.pack(pady=10, fill=tk.BOTH, expand=True)

        # Center container (timer + controls shown during countdown)
        self.center_frame = tk.Frame(self.main_area)
        self.center_frame.pack(side=tk.LEFT, expand=True)

        # Bubble container (to right of timer)
        self.bubble_frame = tk.Frame(self.main_area)
        self.bubble_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        # Bubble label (only shown if there is text)
        self.bubble_label = tk.Label(
            self.bubble_frame,
            text=self.motivational_message,
            font=("Helvetica", 12),
            bg="#e6f0ff",
            fg="#003366",
            wraplength=180,
            justify="left",
            relief="solid",
            bd=1,
            padx=8,
            pady=6
        )
        if self.motivational_message.strip():
            self.bubble_label.pack()

        # Global Return binding (handle message entry first)
        self.root.bind("<Return>", self.enter_key_pressed)

        # Timer screen elements (placed inside center_frame)
        self.label = tk.Label(self.center_frame, text="", font=("Helvetica", 48))
        self.start_button = tk.Button(self.center_frame, text="Start Timer", command=self.start_timer)
        self.pause_button = tk.Button(self.center_frame, text="Pause Timer", command=self.pause_timer)
        self.stop_button = tk.Button(self.center_frame, text="Stop Timer", command=self.stop_timer)

        # Time's up UI
        self.message_label = tk.Label(self.center_frame, text="", font=("Helvetica", 14), fg="white", bg="red")
        self.typing_prompt = tk.Label(self.center_frame, text="Type the phrase to continue: I am ready to focus again",
                                      font=("Helvetica", 12))
        self.typing_entry = tk.Entry(self.center_frame)
        self.sleep_button = tk.Button(self.center_frame, text="Sleep for 5 minutes", command=self.sleep_for_5_minutes)

    # ---------- Message persistence helpers ----------
    def _load_message(self) -> str:
        try:
            if MESSAGE_FILE.exists():
                return MESSAGE_FILE.read_text(encoding="utf-8").strip()
            else:
                MESSAGE_FILE.write_text("", encoding="utf-8")  # create empty on first run
                return ""
        except Exception:
            return ""

    def _show_message_entry(self):
        # Reveal the entry directly below the "Add Message" button; focus it
        self.message_entry.delete(0, tk.END)
        self.message_entry.pack(pady=(6, 0))
        self.message_entry.focus_set()

    def _commit_message(self, event=None):
        msg = self.message_entry.get().strip()
        try:
            MESSAGE_FILE.write_text(msg, encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save message:\n{e}")
            return

        # Update stored text and bubble
        self.motivational_message = msg
        if msg:
            if not self.bubble_label.winfo_ismapped():
                self.bubble_label.pack()
            self.bubble_label.config(text=msg)
        else:
            # If cleared, hide bubble
            if self.bubble_label.winfo_ismapped():
                self.bubble_label.pack_forget()

        # Hide the entry; keep only the Add Message button visible
        self.message_entry.pack_forget()

    # ---------- Timer logic ----------
    def enter_key_pressed(self, event):
        # If message entry is visible, commit that first
        if self.message_entry.winfo_ismapped():
            self._commit_message()
            return

        # Otherwise behave like original
        if not self.timer_running and not self.flash_active:
            self.set_and_start_timer()
        elif self.flash_active and self.typing_entry.winfo_ismapped():
            self.check_typing_challenge()

    def set_and_start_timer(self):
        try:
            minutes = int(self.minutes_entry.get()) if self.minutes_entry.get() else 0
            seconds = int(self.seconds_entry.get()) if self.seconds_entry.get() else 0
            if minutes < 0 or seconds < 0 or seconds >= 60:
                raise ValueError
            self.remaining_time = minutes * 60 + seconds
            self.last_minutes = minutes
            self.last_seconds = seconds
            self.show_timer_screen(minutes, seconds)
            self.start_timer()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid minutes and seconds (0-59).")

    def show_timer_screen(self, minutes, seconds):
        # Hide intro controls (but keep Add Message button available)
        self.intro_label.pack_forget()
        self.minutes_label.pack_forget()
        self.minutes_entry.pack_forget()
        self.seconds_label.pack_forget()
        self.seconds_entry.pack_forget()
        self.set_button.pack_forget()
        self.preset_frame.pack_forget()
        self.add_message_button.pack_forget()
        self.message_entry.pack_forget()  # ensure hidden if shown

        # Show timer + controls in center
        self.label.config(text=f"{minutes:02d}:{seconds:02d}")
        self.label.pack(pady=10)
        self.start_button.pack()
        self.pause_button.pack()
        self.stop_button.pack()

    def start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.timer_paused = False
            threading.Thread(target=self.run_timer, daemon=True).start()

    def pause_timer(self):
        self.timer_paused = not self.timer_paused
        self.pause_button.config(text="Resume Timer" if self.timer_paused else "Pause Timer")

    def stop_timer(self):
        self.timer_running = False
        self.timer_paused = False
        self._stop_flashing_and_restore_bg()
        self.reset_ui()

    def run_timer(self):
        while self.remaining_time > 0 and self.timer_running:
            if not self.timer_paused:
                mins, secs = divmod(self.remaining_time, 60)
                time_str = f"{mins:02d}:{secs:02d}"
                self.label.config(text=time_str)
                self.remaining_time -= 1
            time.sleep(1)

        if self.timer_running:
            self.timer_running = False
            self.show_time_up()

    def show_time_up(self):
        # Show time's up UI and start flashing
        self.message_label.config(text="Time's up!")
        self.message_label.pack(pady=10)
        self.typing_prompt.pack()
        self.typing_entry.pack()
        self.typing_entry.focus()
        self.sleep_button.pack(pady=5)
        self.flash_main_screen()

    # ---------- Non-blocking full-screen flashing (no overlay) ----------
    def flash_main_screen(self):
        if self.flash_active:
            return
        self.flash_active = True
        # Capture original backgrounds for all widgets once
        self._bg_originals.clear()
        self._capture_original_bg(self.root)

        def flash():
            colors = ["red", "white"]
            i = 0
            while self.flash_active:
                current_color = colors[i % 2]
                self._set_bg_recursive(self.root, current_color)
                i += 1
                time.sleep(0.5)
            # Restore when stopping
            self._restore_original_bg()

        threading.Thread(target=flash, daemon=True).start()

    def _stop_flashing_and_restore_bg(self):
        if self.flash_active:
            self.flash_active = False
        else:
            # Even if not flashing, ensure backgrounds are normal
            self._restore_original_bg()

    def _capture_original_bg(self, widget):
        # Record widget's original bg if available
        try:
            self._bg_originals[widget] = widget.cget("bg")
        except Exception:
            pass
        for child in widget.winfo_children():
            self._capture_original_bg(child)

    def _set_bg_recursive(self, widget, color):
        try:
            widget.configure(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_bg_recursive(child, color)

    def _restore_original_bg(self):
        # Restore saved backgrounds; fallback to SystemButtonFace if missing
        for widget, bg in list(self._bg_originals.items()):
            try:
                widget.configure(bg=bg if bg else "SystemButtonFace")
            except Exception:
                pass
        # Ensure root is reset even if not recorded
        try:
            self.root.configure(bg="SystemButtonFace")
        except Exception:
            pass

    def check_typing_challenge(self):
        if self.typing_entry.get().strip() == "I am ready to focus again":
            self.reset_ui()
        else:
            messagebox.showerror("Incorrect", "Please type the exact phrase to continue.")

    def sleep_for_5_minutes(self):
        # Stop flashing and start a 5-minute timer
        self._stop_flashing_and_restore_bg()
        self.message_label.pack_forget()
        self.typing_prompt.pack_forget()
        self.typing_entry.pack_forget()
        self.sleep_button.pack_forget()
        self.remaining_time = 5 * 60
        self.label.config(text="05:00")
        self.label.pack(pady=10)
        self.start_button.pack()
        self.pause_button.pack()
        self.stop_button.pack()
        self.start_timer()

    def reset_ui(self):
        self._stop_flashing_and_restore_bg()

        # Center-area widgets
        self.label.pack_forget()
        self.start_button.pack_forget()
        self.pause_button.pack_forget()
        self.stop_button.pack_forget()
        self.message_label.pack_forget()
        self.typing_prompt.pack_forget()
        self.typing_entry.delete(0, tk.END)
        self.typing_entry.pack_forget()
        self.sleep_button.pack_forget()

        # Re-show centered intro controls and presets
        self.intro_label.pack(pady=(0, 6))
        self.minutes_label.pack()
        self.minutes_entry.delete(0, tk.END)
        self.minutes_entry.insert(0, str(self.last_minutes))
        self.minutes_entry.pack()
        self.seconds_label.pack()
        self.seconds_entry.delete(0, tk.END)
        self.seconds_entry.insert(0, str(self.last_seconds))
        self.seconds_entry.pack()
        self.set_button.pack(pady=8)
        self.preset_frame.pack(pady=10)
        self.add_message_button.pack(pady=(8, 0))  # keep it at the middle-bottom under presets

        # Ensure bubble reflects latest saved message visibility
        if self.motivational_message.strip():
            if not self.bubble_label.winfo_ismapped():
                self.bubble_label.pack()
            self.bubble_label.config(text=self.motivational_message)
        else:
            if self.bubble_label.winfo_ismapped():
                self.bubble_label.pack_forget()

        # Return Pause button text to default
        self.pause_button.config(text="Pause Timer")

    def set_preset_timer(self, minutes):
        self.remaining_time = minutes * 60
        self.last_minutes = minutes
        self.last_seconds = 0
        self.show_timer_screen(minutes, 0)
        self.start_timer()


if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()
