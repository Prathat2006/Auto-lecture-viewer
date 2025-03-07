import pyautogui
import time

def openalgo():
    lo=pyautogui.locateCenterOnScreen(r"D:\\project\\miscellaneous\\Lecture_download\\buttons\\algo.png",confidence=0.8)
    pyautogui.click(lo,clicks=2,interval=1)
    time.sleep(5)