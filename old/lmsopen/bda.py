import pyautogui
import time


def openbda():
    pyautogui.scroll(-100) 
    no=pyautogui.locateCenterOnScreen(r"D:\\project\\miscellaneous\\Lecture_download\\buttons\\bda.png",confidence=0.8)
    pyautogui.click(no,clicks=2,interval=1)
    time.sleep(5)
