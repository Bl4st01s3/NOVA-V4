import pythoncom
import win32com.client
import os

def test_sapi():
    pythoncom.CoInitialize()
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")

    temp_file = os.path.abspath("test_sapi_output.wav")
    print(temp_file)
    stream.Open(temp_file, 3, False)

    speaker.AudioOutputStream = stream
    speaker.Speak("This is a test of SAPI 5 directly.")

    stream.Close()
    print("Done generating.")
    print("File exists:", os.path.exists(temp_file))
    if os.path.exists(temp_file):
        print("File size:", os.path.getsize(temp_file))

test_sapi()
