import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
from collections import defaultdict

# --- Helper to locate app directory (works for source, one-folder, one-file) ---
def get_app_dir() -> Path:
    if hasattr(sys, "frozen"):  # Running as PyInstaller exe
        return Path(os.path.dirname(sys.executable))
    return Path(os.path.dirname(os.path.abspath(__file__)))

APP_DIR = get_app_dir()
MESSAGE_FILE = APP_DIR / "message.txt"
USAGE_FILE = APP_DIR / "usage_stats.json"


class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Custom Timer")
        self.root.geometry("600x560")  # Back to original height since we're using less space

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
        
        # Load usage statistics
        self.usage_stats = self._load_usage_stats()

        # ---------- USAGE STATS DISPLAY (at the top) ----------
        self.stats_frame = tk.Frame(root, bg="#f0f0f0", relief="solid", bd=1)
        self.stats_frame.pack(pady=(10, 5), padx=10, fill=tk.X)
        
        # Line 1: Header with totals
        self.stats_summary = tk.Label(self.stats_frame, text="", 
                                     font=("Helvetica", 10, "bold"), bg="#f0f0f0", justify="center")
        self.stats_summary.pack(pady=(5, 2))
        
        # Line 2: Daily breakdown
        self.stats_daily = tk.Label(self.stats_frame, text="", 
                                   font=("Helvetica", 9), bg="#f0f0f0", justify="center")
        self.stats_daily.pack(pady=(0, 5))
        
        # Update stats display
        self._update_stats_display()

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

    # ---------- Usage Statistics Methods ----------
    def _load_usage_stats(self) -> dict:
        """Load usage statistics from JSON file"""
        try:
            if USAGE_FILE.exists():
                with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception:
            return {}
    
    def _save_usage_stats(self):
        """Save usage statistics to JSON file"""
        try:
            with open(USAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.usage_stats, f, indent=2)
        except Exception as e:
            print(f"Could not save usage stats: {e}")
    
    def _record_timer_completion(self, duration_minutes):
        """Record a completed timer session"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self.usage_stats:
            self.usage_stats[today] = {'sessions': 0, 'total_minutes': 0}
        
        self.usage_stats[today]['sessions'] += 1
        self.usage_stats[today]['total_minutes'] += duration_minutes
        
        # Clean up old data (keep only last 30 days to prevent file from growing too large)
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.usage_stats = {
            date: data for date, data in self.usage_stats.items() 
            if date >= cutoff_date
        }
        
        self._save_usage_stats()
        self._update_stats_display()
    
    def _get_7_day_stats(self):
        """Get statistics for the past 7 days (including today)"""
        stats = []
        
        # Get data for last 7 days (6 days ago + today)
        for i in range(6, -1, -1):  # 6 days ago to today
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            if date_str in self.usage_stats:
                day_data = self.usage_stats[date_str]
            else:
                day_data = {'sessions': 0, 'total_minutes': 0}
            
            # Add formatted date info
            day_data['date'] = date
            day_data['date_str'] = date_str
            stats.append(day_data)
        
        return stats
    
    def _update_stats_display(self):
        """Update the statistics display with compact 2-line format"""
        seven_day_stats = self._get_7_day_stats()
        
        # Calculate totals
        total_sessions = sum(day['sessions'] for day in seven_day_stats)
        total_minutes = sum(day['total_minutes'] for day in seven_day_stats)
        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60
        
        # Format total time display
        if total_hours > 0:
            total_time_str = f"{total_hours}h {remaining_minutes}m"
        else:
            total_time_str = f"{total_minutes}m"
        
        # Line 1: Header with totals
        summary_text = f"Prior Usage of past 7 days: {total_sessions} Sessions / {total_time_str}"
        self.stats_summary.config(text=summary_text)
        
        # Line 2: Daily breakdown from yesterday backwards
        daily_parts = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Skip today (index 6), go from yesterday (index 5) backwards to 7 days ago (index 0)
        for i in range(5, -1, -1):  # 5, 4, 3, 2, 1, 0 (yesterday to 6 days ago)
            day = seven_day_stats[i]
            sessions = day['sessions']
            minutes = day['total_minutes']
            
            # Format time compactly
            if minutes == 0:
                time_str = "0m"
            elif minutes >= 60:
                hours = minutes // 60
                mins = minutes % 60
                if mins > 0:
                    time_str = f"{hours}h{mins}m"
                else:
                    time_str = f"{hours}h"
            else:
                time_str = f"{minutes}m"
            
            # Create compact format: sessions/time
            daily_parts.append(f"{sessions}/{time_str}")
        
        # Join with dashes
        daily_text = " - ".join(daily_parts)
        self.stats_daily.config(text=daily_text)

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
            # Store the original duration for stats tracking
            self.original_duration = self.remaining_time
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
            # Record the completed session
            duration_minutes = self.original_duration // 60
            if self.original_duration % 60 > 0:  # Round up if there were seconds
                duration_minutes += 1
            self._record_timer_completion(duration_minutes)
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
        self.original_duration = self.remaining_time  # Track this sleep session too
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
        self.add_message_button.pack(pady=(8, 0))

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
