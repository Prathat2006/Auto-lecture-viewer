import pyautogui
from dotenv import load_dotenv
import os
import time
import algo
import stats
import bda
import lana
from AppOpener import open

load_dotenv()

class openlmsnow():
    def __init__(self):
         password = os.environ.get('PASSWORD')
         if password:
             self.openapp()
             self.openprofilecoord()
             self.openlms()
             self.inputpassword(password) #pass the password here
             time.sleep(5)
 
         else:
             print("Error: PASSWORD environment variable not set.")

    def getlocations(self):
        time.sleep(5)
        p=pyautogui.position()
        print(p)
    def openapp(self):
        open("google chrome")
        time.sleep(3)

    def openprofile(self):
        po=pyautogui.locateCenterOnScreen(r"buttons\\profilec.png",confidence=0.8)
        pyautogui.click(po,clicks=2,interval=1)

    def openprofilecoord(self):
        x=717
        y=670
        pyautogui.moveTo(x,y,1)
        pyautogui.doubleClick(x,y)

    def openlms(self):
        x=187
        y=30
        pyautogui.moveTo(x,y,3)
        pyautogui.doubleClick(x,y)
    def inputpassword(self,password):
        x=1255
        y=665
        pa=pyautogui.locateCenterOnScreen(r"buttons\\pass.png",confidence=0.8)
        pyautogui.click(pa)
        pyautogui.typewrite(password)
        pyautogui.press('enter')
        time.sleep(7)

# def main():
#     openlmsnow()
# if __name__ == "__main__":
#     main()