import pyttsx3
import traceback

def test():
    engine = pyttsx3.init()
    print("Init")
    try:
        engine.save_to_file("Hello", "test.wav")
        engine.runAndWait()
        print("Done 1")
    except Exception as e:
        print(e)

    try:
        engine.save_to_file("Hello 2", "test2.wav")
        engine.runAndWait()
        print("Done 2")
    except Exception as e:
        print(traceback.format_exc())

test()
