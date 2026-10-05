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

    # Wait 15 seconds to allow the Bionic backend to fully spin up
    time.sleep(15)

    def enum_window_callback(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # Strict exact match to avoid false positives (like closing a browser tab)
            if title == "Bionic" or title == "LM Studio":
                # Send WM_CLOSE to gracefully close the UI window
                # This leaves the server running silently in the system tray
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return False # Stop enumerating
        return True

    # Check for the window up to 10 times (5 seconds total after the initial 15s wait)
    for _ in range(10):
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception:
            # Exception means we returned False and successfully sent the close command
            break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
