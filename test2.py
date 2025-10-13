import tkinter as tk
from tkinter import messagebox
import threading
import time

class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Custom Timer")
        self.root.geometry("350x350")

        self.timer_running = False
        self.timer_paused = False
        self.remaining_time = 0
        self.flash_active = False

        self.last_minutes = 0
        self.last_seconds = 0

        self.intro_label = tk.Label(root, text="Enter timer duration:")
        self.intro_label.pack(pady=10)

        self.minutes_label = tk.Label(root, text="Minutes:")
        self.minutes_label.pack()
        self.minutes_entry = tk.Entry(root)
        self.minutes_entry.pack()

        self.seconds_label = tk.Label(root, text="Seconds:")
        self.seconds_label.pack()
        self.seconds_entry = tk.Entry(root)
        self.seconds_entry.pack()

        self.set_button = tk.Button(root, text="Set Timer", command=self.set_and_start_timer)
        self.set_button.pack(pady=10)

        self.root.bind('<Return>', self.enter_key_pressed)

        self.label = tk.Label(root, text="", font=("Helvetica", 32))
        self.start_button = tk.Button(root, text="Start Timer", command=self.start_timer)
        self.pause_button = tk.Button(root, text="Pause Timer", command=self.pause_timer)
        self.stop_button = tk.Button(root, text="Stop Timer", command=self.stop_timer)

        self.message_label = tk.Label(root, text="", font=("Helvetica", 14), fg="white", bg="red")
        self.typing_prompt = tk.Label(root, text="Type the phrase to continue: I am ready to focus again", font=("Helvetica", 12))
        self.typing_entry = tk.Entry(root)
        self.sleep_button = tk.Button(root, text="Sleep for 5 minutes", command=self.sleep_for_5_minutes)

    def enter_key_pressed(self, event):
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
        self.intro_label.pack_forget()
        self.minutes_label.pack_forget()
        self.minutes_entry.pack_forget()
        self.seconds_label.pack_forget()
        self.seconds_entry.pack_forget()
        self.set_button.pack_forget()

        self.label.config(text=f"{minutes:02d}:{seconds:02d}")
        self.label.pack(pady=10)
        self.start_button.pack()
        self.pause_button.pack()
        self.stop_button.pack()

    def start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.timer_paused = False
            threading.Thread(target=self.run_timer).start()

    def pause_timer(self):
        self.timer_paused = not self.timer_paused
        self.pause_button.config(text="Resume Timer" if self.timer_paused else "Pause Timer")

    def stop_timer(self):
        self.timer_running = False
        self.timer_paused = False
        self.flash_active = False
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
        self.message_label.config(text="Time's up!")
        self.message_label.pack(pady=10)
        self.typing_prompt.pack()
        self.typing_entry.pack()
        self.typing_entry.focus()
        self.sleep_button.pack(pady=5)
        self.flash_main_screen()

    def flash_main_screen(self):
        self.flash_active = True
        def flash():
            colors = ["red", "white"]
            i = 0
            while self.flash_active:
                self.root.configure(bg=colors[i % 2])
                i += 1
                time.sleep(0.5)
        threading.Thread(target=flash).start()

    def check_typing_challenge(self):
        if self.typing_entry.get().strip() == "I am ready to focus again":
            self.reset_ui()
        else:
            messagebox.showerror("Incorrect", "Please type the exact phrase to continue.")

    def sleep_for_5_minutes(self):
        self.flash_active = False
        self.root.configure(bg="SystemButtonFace")
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
        self.flash_active = False
        self.root.configure(bg="SystemButtonFace")
        self.label.pack_forget()
        self.start_button.pack_forget()
        self.pause_button.pack_forget()
        self.stop_button.pack_forget()
        self.message_label.pack_forget()
        self.typing_prompt.pack_forget()
        self.typing_entry.delete(0, tk.END)
        self.typing_entry.pack_forget()
        self.sleep_button.pack_forget()
        self.intro_label.pack(pady=10)
        self.minutes_label.pack()
        self.minutes_entry.delete(0, tk.END)
        self.minutes_entry.insert(0, str(self.last_minutes))
        self.minutes_entry.pack()
        self.seconds_label.pack()
        self.seconds_entry.delete(0, tk.END)
        self.seconds_entry.insert(0, str(self.last_seconds))
        self.seconds_entry.pack()
        self.set_button.pack(pady=10)
        self.pause_button.config(text="Pause Timer")

if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()