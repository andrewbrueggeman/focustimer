import tkinter as tk

def launch_app():
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("300x150")
    tk.Label(root, text="Hello, this is a test!").pack(pady=20)
    root.mainloop()

launch_app()