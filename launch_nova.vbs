Set WshShell = CreateObject("WScript.Shell")
' Run the batch file completely hidden (0)
WshShell.Run chr(34) & "run.bat" & Chr(34), 0
Set WshShell = Nothing
