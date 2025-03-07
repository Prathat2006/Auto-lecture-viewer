import time
import pyautogui

def getlocations():
    time.sleep(5)
    p=pyautogui.position()
    print(p)

getlocations()