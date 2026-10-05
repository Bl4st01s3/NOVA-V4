# LM Studio (`lms`) CLI Reference

This document stores the known commands and flags for the `lms` CLI tool used by the Bionic engine.

## `lms server start`

```
Usage: lms server start [options]

Starts the local server

Options:
   -p, --port <port>   Port to run the server on. If not provided, the server will run on
                       the same port as the last time it was started.
   --bind <address>    Network address to bind the server to. Use "0.0.0.0" to accept
                       connections from the local network, or "127.0.0.1" (default) for
                       localhost only. Can also be set via the LMS_SERVER_HOST environment
                       variable.
   --cors              Enable CORS on the server. Allows any website you visit to access
                       the server. This is required if you are developing a web
                       application.
```

**Note:** As of the current build, there is no `--headless` or `--no-window` flag. Launching `lms server start` will forcibly open the Electron GUI for LM Studio. To achieve a silent boot, external OS-level window manipulation (e.g., Python `ctypes`) must be used to minimize the window after launch.
