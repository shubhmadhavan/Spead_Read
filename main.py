import pyperclip
import time
import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
import threading
import keyboard
import json
import os


# Default settings
default_settings = {
    "highlight_color": "#AD0321",
    "speed": 4.70
}

# Path to config file
config_path = "config.json"

# Initialize global variables
label = None 

stop_event = threading.Event()  # Global stop event
current_index = 0  # Tracks the current word index
stop_button_press_count = 0  # Tracks stop button presses
current_thread = None  # Track the current thread
last_speed = default_settings["speed"]  # Track the last used speed

# Load settings from config.json or use defaults
def load_settings():
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError):
            pass  # Fall back to default settings if there's an error
    return default_settings

# Save settings to config.json
def save_settings(settings):
    with open(config_path, "w") as file:
        json.dump(settings, file)

# Load the initial settings
settings = load_settings()
highlight_color = settings.get("highlight_color", default_settings["highlight_color"])
default_speed = settings.get("speed", default_settings["speed"])

# Function to replace new lines with a forward slash
def process_text(text):
    text = '\n'.join([' '.join(line.strip().split()) for line in text.split('\n') if line.strip()])
    text = text.replace("\n", "\n")
    return text

# Function to reveal text word by word
def reveal_text(words, speed, label, text_widget):
    global current_index
    num_words = len(words)

    while current_index < num_words:
        if stop_event.is_set():  # Check if the thread should stop
            return

        word = words[current_index]
        label.config(text=word)
        highlight_word_by_index(current_index, words, text_widget)

        current_index += 1
        time.sleep(1 / speed)

    current_index = 0

# Function to highlight the word in the text widget by index
def highlight_word_by_index(index, words, text_widget):
    pos = 0

    for i in range(index):
        pos += len(words[i])
        if words[i] != "\n":
            pos += 1

    start_idx = f"1.0 + {pos}c"
    end_idx = f"{start_idx} + {len(words[index])}c"

    text_widget.tag_remove("highlight", "1.0", "end")
    text_widget.tag_add("highlight", start_idx, end_idx)
    text_widget.tag_configure("highlight", foreground=highlight_color)
    text_widget.see(start_idx)

# Function to update the current speed label
def update_speed_label(speed_var, speed_label):
    speed = speed_var.get()
    seconds_per_word = 1 / speed
    speed_label.config(text=f"{speed:.2f} words per second / {seconds_per_word:.2f} seconds per word")
    settings["speed"] = speed
    save_settings(settings)

# Function to start the reveal process
def start_reveal_process(label, speed_var, root, text_widget, speed_label):
    global stop_event, stop_button_press_count, current_index, current_thread, last_speed
    
    stop_button_press_count = 0
    text = pyperclip.paste().strip()
    if not text:
        label.config(text="No text found in clipboard!")
        return

    text = process_text(text)
    text_widget.delete(1.0, "end")
    text_widget.insert("1.0", text)

    label.config(text="")
    speed = speed_var.get()

    # Ensure the previous thread has completed or text_widget is empty before starting new thread
    if current_thread is not None and current_thread.is_alive():
        return  # Do nothing if a thread is already running
    
    last_speed = speed  # Update the last used speed
    if stop_event is not None and stop_event.is_set():
        stop_event.clear()

    stop_event = threading.Event()
    words = text.split()
    current_thread = threading.Thread(target=reveal_text, args=(words, last_speed, label, text_widget), daemon=True)
    current_thread.start()

    bring_window_to_front(root)
    update_speed_label(speed_var, speed_label)

# Function to stop the reveal process
def stop_reveal(label, text_widget, speed_var, speed_label):
    global stop_event, stop_button_press_count, current_index
    if stop_event is not None:
        stop_event.set()

    stop_button_press_count += 1

    if stop_button_press_count == 2:
        stop_button_press_count = 0
        current_index = 0
        label.config(text="")
        text_widget.delete(1.0, "end")
    
    # Update speed label with the last used speed (no reset to default)
    update_speed_label(speed_var, speed_label)

# Function to bring the window to the front
def bring_window_to_front(root):
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

# Function to open the color chooser dialog
def open_color_chooser():
    global highlight_color, label
    color = colorchooser.askcolor(initialcolor=highlight_color)[1]
    if color:
        highlight_color = color
        settings["highlight_color"] = highlight_color
        save_settings(settings)
        # Update the label and text widget foreground color
        label.config(foreground=highlight_color)
        update_highlight_color_for_text_widget()

# Function to update highlight color for text widget
def update_highlight_color_for_text_widget():
    global highlight_color
    text_widget.tag_configure("highlight", foreground=highlight_color)

# Main function to create the GUI
def main():
    global label, text_widget

    root = tk.Tk()
    root.title("Speed Read")
    root.geometry("515x575")
    root.iconbitmap('icon.ico')

    # Initialize label globally
    label = tk.Label(root, text="", font=("Helvetica", 22), wraplength=580, justify="center", foreground=highlight_color)
    label.pack(pady=28)

    # Button frame
    button_frame = tk.Frame(root)
    button_frame.pack(pady=1)

    # Speed control
    speed_var = tk.DoubleVar(value=default_speed)
    speed_label = tk.Label(root, text="")
    speed_label.pack()

    speed_slider = ttk.Scale(root, from_=1, to=15, variable=speed_var, orient="horizontal", length=500)
    speed_slider.pack(fill="x", padx=20)

    speed_value_label = tk.Label(root, text=f"{default_speed:.2f} words per second / {1 / default_speed:.2f} seconds per word", font=("Helvetica", 8), fg="gray")
    speed_value_label.pack()

    speed_slider.config(command=lambda val: update_speed_label(speed_var, speed_value_label))

    # Start/Stop buttons
    start_button = ttk.Button(
        button_frame,
        text="Start",
        command=lambda: start_reveal_process(label, speed_var, root, text_widget, speed_value_label)
    )
    start_button.pack(side="left", padx=2, ipadx=2, ipady=2)

    stop_button = ttk.Button(
        button_frame,
        text="Stop",
        command=lambda: stop_reveal(label, text_widget, speed_var, speed_value_label)
    )
    stop_button.pack(side="left", padx=2, ipadx=2, ipady=2)

    # Text widget
    text_widget = tk.Text(root, wrap="word", height=10, width=70, font=("Helvetica", 12))
    text_widget.pack(pady=20, fill="both", expand=True)

    # Settings button to open color chooser
    settings_button = ttk.Button(
        root,
        text="",
        command=open_color_chooser,
        style="TButton",
        width=4
    )
    settings_button.pack(side="right", padx=10, pady=2)

    # Hotkey
    keyboard.add_hotkey(
        "ctrl+alt+shift+q",
        lambda: start_reveal_process(label, speed_var, root, text_widget, speed_value_label),
        suppress=True
    )

    # Instructions label
    instructions = tk.Label(
        root,
        text="Ctrl+Alt+Shift+Q",
        font=("Helvetica", 8),
        fg="#808080",
        anchor="e",
        justify="right"
    )
    instructions.pack(pady=2, fill="x", padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()
