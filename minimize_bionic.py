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

    target_hwnd = None

    def enum_window_callback(hwnd, lparam):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # Strict exact match to avoid false positives (like closing a browser tab)
            if title == "Bionic" or title == "LM Studio":
                target_hwnd = hwnd
                # Immediately minimize it to hide it from the screen
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return False # Stop enumerating
        return True

    # 1. Fast polling loop: check 4 times a second for up to 30 seconds
    for _ in range(120):
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception:
            # Exception means we returned False and successfully found & minimized the window
            break
        time.sleep(0.25)

    # 2. Wait 15 seconds to allow the Bionic backend server to fully finish its cold boot sequence
    if target_hwnd:
        time.sleep(15)
        # 3. Send WM_CLOSE to gracefully close the minimized UI window, leaving the server running
        try:
            win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass

if __name__ == "__main__":
    main()
