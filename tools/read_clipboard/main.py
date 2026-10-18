import sys
import tkinter as tk

def run():
    try:
        root = tk.Tk()
        root.withdraw()
        # Ensure we get the clipboard contents without locking up
        clipboard_text = root.clipboard_get()
        root.destroy()

        if not clipboard_text.strip():
            print("The clipboard is currently empty.")
            return

        if len(clipboard_text) > 5000:
            clipboard_text = clipboard_text[:5000] + "\n\n...[Content truncated for length]"

        print(f"Clipboard Content:\n\n{clipboard_text}")
    except tk.TclError:
        print("The clipboard is currently empty or does not contain readable text.")
    except Exception as e:
        print(f"Failed to read clipboard: {e}")

if __name__ == "__main__":
    run()
