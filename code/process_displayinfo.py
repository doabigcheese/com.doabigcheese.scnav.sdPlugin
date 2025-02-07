from PIL import Image
import pytesseract
import cv2
import numpy as np
import pyautogui
import time
import math
import os
from tkinter import *
import sys
import winsound

camdir_pitch = int(sys.argv[1])
camdir_roll = int(sys.argv[2])
camdir_yaw = int(sys.argv[3])
camdir_fov = int(sys.argv[4])
target_pitch = int(sys.argv[5])
target_roll = int(sys.argv[6])
target_yaw = int(sys.argv[7])

print("target: ", target_pitch, target_roll, target_yaw)

def create_overlay(x,y):
    root = Tk()
    root.title("overlay")
    #x=3497
    #y=672
    res_x = 3440
    res_y = 1440

    new_x = int(x) #int(x + res_x/2)
    new_y = int(y) #int(res_y/2 - y)
    print("new_x: " ,new_x)
    print("new_y: ", new_y)
    root.geometry(f'20x20+{new_x}+{new_y}')
    # to remove the titalbar
    root.overrideredirect(True)

    # to make the window transparent
    root.attributes("-transparentcolor","red")
    # set bg to red in order to make it transparent
    root.config(bg="red")

    # draw a green crosshair instead of button
    c = Canvas(root, width=20, height=20,bg="red" )
    c.create_line(10, 0, 10, 20, fill="#00FF00", width=2)
    c.create_line(0, 10, 20, 10, fill="#00FF00", width=2)
    c.pack()
    #make window to be always on top
    root.wm_attributes("-topmost", 1)

    def exit_after_10_seconds():
        root.destroy()
        sys.exit()
    print(".")
    root.after(10000, exit_after_10_seconds)
    root.mainloop()
    print("..")
    return

   
def get_xy_target_marker(camdir_pitch: int,camdir_roll:int ,camdir_yaw: int,camdir_fov:float,target_pitch:int, target_roll:int, target_yaw:int):
       
    screenwidth  = 3440
    screenheight = 1440
    legacy = True
    print(camdir_pitch,camdir_roll,camdir_yaw,camdir_fov,target_pitch, target_roll, target_yaw)
    if legacy:
        #Graupunkt:  Calculation LEGACY works for pitch and yaw if roll is zero

        #subtract players camdir from destinations camdir
        relativePitch = (target_pitch - camdir_pitch) 
        relativeYaw = (target_yaw - camdir_yaw)  / 2.5
        #relativeRoll = target_roll - camdir_roll
        
        
        centerX=screenwidth / 2
        centerY=screenheight / 2

        # apply fov scaling
        scaleFactorYaw = screenwidth / camdir_fov 
        scaleFactorPitch = screenheight / camdir_fov
        
        # final position of the marker based on calculations
        targetX = centerX - (relativeYaw * scaleFactorYaw)
        targetY = centerY - (relativePitch * scaleFactorPitch) 
        print("targetX_legacy: " + str(targetX))
        print("targetY_legacy: " + str(targetY))
        
    
    else:
        #Graupunkt:  HERE THE ROLLING ISSUE IS SOLVED, BUT THE SCALE FOR YAW AND PITCH ARE ONLY MINIMAL
        #            AND the pitch is on point, but yaw is like 15° off to the left
        #subtract players camdir from destinations camdir
        relativePitch = (target_pitch - camdir_pitch) 
        print("relativePitch: " + str(relativePitch))
        relativeYaw = (target_yaw - camdir_yaw)#  / 2.5
        print("relativeYaw: " + str(relativeYaw))

        relativeRoll = target_roll - camdir_roll
        print("relativeRoll: "+str(relativeRoll))

        # Calculate screen projection center
        centerX=screenwidth / 2
        centerY=screenheight / 2
        #test
        relativePitchOffset = relativePitch / camdir_fov
        relativeYawOffset = relativeYaw / camdir_fov
        pixelOffsetX = relativeYawOffset * screenwidth * -1
        print("pixeloffsetX: ",pixelOffsetX)
        pixelOffsetY = relativePitchOffset * screenheight * -1
        print("PixelOffsets: ",pixelOffsetX,pixelOffsetY)
        targetX = centerX + pixelOffsetX
        targetY = centerY - pixelOffsetY
        print("targetX_test: " + str(targetX))
        print("targetY_test: " + str(targetY))
        
        # Adjust scaling factors based on FOV
        # apply fov scaling
        scaleFactorYaw = (screenwidth / 2) / camdir_fov 
        scaleFactorPitch = (screenheight / 2) / camdir_fov
        

        # Convert degrees to radians for trigonometric calculations
        relativePitchRad = math.radians(relativePitch)
        relativeYawRad = math.radians(relativeYaw)
        relativeRollRad = math.radians(relativeRoll)

        # Apply roll transformation to adjust pitch and yaw
        adjustedPitch = math.cos(relativeRollRad) * relativePitchRad - math.sin(relativeRollRad) * relativeYawRad
        adjustedYaw   = math.sin(relativeRollRad) * relativePitchRad + math.cos(relativeRollRad) * relativeYawRad

        # Convert adjusted angles back to degrees
        adjustedPitchDeg = math.degrees(adjustedPitch)
        adjustedYawDeg = math.degrees(adjustedYaw)
        print(adjustedPitchDeg,adjustedYawDeg)
        # Normalize adjusted angles for screen projection
        #$normalizedPitch = $adjustedPitch / ([Math]::PI / 2)  # Normalize to -1 to 1 (Pitch ranges -90 to 90 degrees)
        #$normalizedYaw = $adjustedYaw / [Math]::PI            # Normalize to -1 to 1 (Yaw ranges -180 to 180 degrees
        
        # Normalize adjusted angles for screen projection
        normalizedPitch = adjustedPitchDeg / 180  # Normalize to -1 to 1 (Pitch ranges -180 to 180 degrees)
        normalizedYaw = adjustedYawDeg / 180      # Normalize to -1 to 1 (Yaw ranges -180 to 180 degrees)
        print(normalizedPitch,normalizedYaw)
        # Project to screen coordinates
        targetX = centerX + (normalizedYaw * scaleFactorYaw)
        targetY = centerY - (normalizedPitch * scaleFactorPitch)  # Invert Y-axis for screen coordinates

        print("targetX: " + str(targetX))
        print("targetY: " + str(targetY))   


        #if targetX > (screenwidth / 2) * 0.7:
        #    targetX = 0
        #    print("reset X - boundary!")
        #if targetY > (screenheight / 2) * 0.7:
        #    targetY = 0    
        #    print("reset Y - boundary!")

            # Display marker
    return targetX, targetY

while True:    
    #image = 'sc_testbild_ocr.jpg'  # replace with your screenshot path
    try:
        
        print("CAMDIR:", camdir_pitch,camdir_roll,camdir_yaw,camdir_fov)
        print("LOCALXYZ:", localxyz_x,localxyz_y,localxyz_z)
        print("UNIVERSE XYZ:", universe_xyz_x,universe_xyz_y,universe_xyz_z)


        #calculate projected xy coordinates for target marker
        #eg. benny henge from om-6 yela static test
        #camdir_pitch = 10
        #camdir_roll = 0
        #camdir_yaw = 140
        #camdir_fov = 60        
        # test it with a known target which have a QT marker in sight

        x,y=get_xy_target_marker(camdir_pitch,camdir_roll,camdir_yaw,camdir_fov,target_pitch, target_roll, target_yaw)
        print(x,y)
        winsound.PlaySound("*", winsound.SND_ALIAS)
        create_overlay(x,y)
        
        time.sleep(10)
        sys.exit()
        
    except Exception as e:
        print("Exception_ " + str(e))
        

    time.sleep(5)