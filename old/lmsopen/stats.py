import pyautogui
import time


def openstats():
    pyautogui.scroll(-100) 
    no=pyautogui.locateCenterOnScreen(r"D:\\project\\miscellaneous\\Lecture_download\\buttons\\stats.png",confidence=0.8)
    pyautogui.click(no,clicks=2,interval=1)
    time.sleep(5)



