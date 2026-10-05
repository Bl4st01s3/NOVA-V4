import time
import os
import sys

def main():
    if os.name != 'nt':
        return

    try:
        import win32gui
        import win32con
    except ImportError:
        # Silently fail if pywin32 isn't installed yet
        return

    def enum_window_callback(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # Match exactly 'Bionic' or anything containing it
            if "Bionic" in title:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return False # Stop enumerating
        return True

    # Loop for 60 seconds (checks twice a second)
    # This ensures we catch it even during a slow cold boot.
    for _ in range(120):
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception:
            # Exception usually means we returned False and stopped enumeration
            break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
