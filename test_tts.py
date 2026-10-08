import pyttsx3
import time

print("Init engine 1")
engine = pyttsx3.init()
engine.save_to_file("Sentence one.", "test1.wav")
engine.runAndWait()
print("Sentence 1 done")
time.sleep(0.5)

print("Starting sentence 2")
engine.save_to_file("Sentence two.", "test2.wav")
engine.runAndWait()
print("Sentence 2 done")
