#todo
# - compare calibration calculation with Tool Jericho to find error
# - get navi data from starmap.space rest api (eg setting in predefined_poi button)
#       OC: https://starmap.space/api/v1/oc/
#       POI:https://starmap.space/api/v1/pois/
#       query e.g. 
#           https://starmap.space/api/v1/oc/index.php?system=Stanton
#           https://starmap.space/api/v1/pois/index.php?planet=Daymar
# 
#       https://starmap.space/api/v3/oc/index.php
#       https://starmap.space/api/v3/pois/index.php
#
# *** debug: http://localhost:23654/
#todo:
#   -automatic title on button based on poi / planet
#   -long press opens up verseguide poi page or starmap.space database view
#   - deactivate activated buttons when selecting new poi
#   - button state when switching pages?
#   - cstone poi details on longpress as well? (parse cstone + calculate xyz from om-distances in matching table )
#   - target OM distances on output button
#   - OCR Camdir:       3028,3 - 3438,18
#   - OCR local xyz:    2955,31 - 3438,44
#   - OCR universe xyz: 3080,45 - 3438,58
#   - OCR servertime:   3192,147 - 3438,158
#   - OCR universetime: 3175,172 - 3438,185
#########################################################################
import random
import requests
import ahk
import time
import re
import webbrowser
import winsound
import subprocess
#import win32com.client
#from playsound import playsound



from math import sqrt, degrees, radians, cos, acos, sin, asin, tan ,atan2, copysign, pi
import pyperclip
import datetime
import json
import os
import csv
import sys
import threading
from queue import Queue
import json
import asyncio
from bs4 import BeautifulSoup
from pyppeteer import launch
from PIL import Image
import pytesseract
import cv2
import numpy as np
import pyautogui
from tkinter import *

northpole_is_om3 = True

from streamdeck_sdk import (
    StreamDeck,
    Action,
    events_received_objs,
    events_sent_objs,
    mixins,
    image_bytes_to_base64,
    logger
)
from streamdeck_sdk.sd_objs import events_received_objs
import settings

queue = Queue()

Container_list = []
Space_POI_list = []
Planetary_POI_list = {}
watch_clipboard_active = False
calibrate_active = False
save_triggered = False
preloaded = False
Destination = []
stop_navithread = False
bearing_button_context = ""
nearest_button_context = ""
daytime_button_context = ""
around_button_context = ""
coords_button_context = ""
save_button_context = ""
oms_button_context = ""
camdir_button_context = ""
sandcavestour_button_context = ""
startnavitoknownpoi_button_context = ""
startnavitosavedpoi_button_context = ""
pi_context = ""
message_pois = ""
datasource = "local" # local or starmap
daytime_toggle = "target"
sandcavetour_active = False
sandcavetour_init_done = False
start_time=0
Destination_queue=[]
knownPlayerX=0
knownPlayerY=0
knownPlayerZ=0
knownPlayerContainername=""
stop_coordinatetimeout = False
CoordinateTimeoutThread = ""
ocr_running = False
stop_threads = False
ocr_button_context = ""
halo_running=False
HALOThread=""
halo_button_context = ""

def check_queue(event):
    logger.debug("check queue entered")
    msg = queue.get()
    logger.debug(msg)
    mother.ws.send(msg)
#old    
def calculate_target_marker(cur_camdir_pitch,cur_camdir_roll,cur_camdir_yaw, camdir_fov):
    global CamDirYaw, CamDirPitch, CamDirRoll
    logger.debug("calculate target marker...")
    ship_orientation = rotation_matrix(cur_camdir_yaw, cur_camdir_pitch, cur_camdir_roll)
    target_vector = rotation_matrix(CamDirYaw, CamDirPitch, CamDirRoll) @ np.array([0, 0, 1])
    fov = camdir_fov  # Sichtfeld in Grad
    resolution = (3440, 1440)
    screen_coords = world_to_screen(target_vector, fov, resolution, np.linalg.inv(ship_orientation))
    logger.debug(f"Ziel auf dem Bildschirm: {screen_coords}")
    logger.debug(f"x waehre: {screen_coords[0]}")
    DrawThread=threading.Thread(target=create_overlay,args=(int(screen_coords[0]),int(screen_coords[1]))) #Prepare a new thread create_overlay(screen_coords[0],screen_coords[1])
    DrawThread.start()
    
def create_overlay(x,y):
    root = Tk()
    root.title("overlay")
    #x=1800
    #y=720
    logger.debug("create_overlay entered...")
    logger.debug(x)
    logger.debug(y)

    res_x = 3440
    res_y = 1440
    if x < 0 or x > res_x or y < 0 or y > res_y:
        return
    else:
        #new_x = int(x + res_x/2)
        #new_y = int(res_y/2 - y)

        root.geometry(f'20x20+{x}+{y}')
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
            #sys.exit()

        root.after(10000, exit_after_10_seconds)
        root.mainloop()
        return
#old
def degrees_to_radians(deg):
    return deg * np.pi / 180
#old
def rotation_matrix(yaw, pitch, roll):
    """
    Erzeugt eine Rotationsmatrix basierend auf Yaw, Pitch und Roll (in Grad).
    """
    yaw = degrees_to_radians(yaw)
    pitch = degrees_to_radians(pitch)
    roll = degrees_to_radians(roll)

    # Rotationsmatrizen für jede Achse
    R_yaw = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw), np.cos(yaw), 0],
        [0, 0, 1]
    ])
    R_pitch = np.array([
        [np.cos(pitch), 0, np.sin(pitch)],
        [0, 1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])
    R_roll = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll), np.cos(roll)]
    ])
    # Gesamte Rotationsmatrix
    return R_yaw @ R_pitch @ R_roll
#old
def world_to_screen(target, fov, resolution, ship_orientation):
    """
    Transformiert eine Zielposition im Weltkoordinatensystem in Bildschirmkoordinaten.
    """
    # Field of View
    fov_x = degrees_to_radians(fov)
    fov_y = fov_x * (resolution[1] / resolution[0])

    # Zielposition relativ zum Raumschiff
    local_target = ship_orientation @ target

    # Perspektivische Projektion
    x = local_target[0] / local_target[2]
    y = local_target[1] / local_target[2]

    # Bildschirmkoordinaten berechnen
    screen_x = (x + np.tan(fov_x / 2)) / (2 * np.tan(fov_x / 2)) * resolution[0]
    screen_y = (1 - (y + np.tan(fov_y / 2)) / (2 * np.tan(fov_y / 2))) * resolution[1]

    return np.array([screen_x, screen_y])


# Funktionen für Rotationsmatrizen
def rotation_matrix_yaw(yaw):
    """Rotationsmatrix für die Yaw-Achse (Z-Achse)"""
    cos_yaw = np.cos(np.radians(yaw))
    sin_yaw = np.sin(np.radians(yaw))
    return np.array([
        [cos_yaw, -sin_yaw, 0],
        [sin_yaw, cos_yaw, 0],
        [0, 0, 1]
    ])

def rotation_matrix_pitch(pitch):
    """Rotationsmatrix für die Pitch-Achse (X-Achse)"""
    cos_pitch = np.cos(np.radians(pitch))
    sin_pitch = np.sin(np.radians(pitch))
    return np.array([
        [1, 0, 0],
        [0, cos_pitch, -sin_pitch],
        [0, sin_pitch, cos_pitch]
    ])

def rotation_matrix_roll(roll):
    """Rotationsmatrix für die Roll-Achse (Y-Achse)"""
    cos_roll = np.cos(np.radians(roll))
    sin_roll = np.sin(np.radians(roll))
    return np.array([
        [cos_roll, 0, sin_roll],
        [0, 1, 0],
        [-sin_roll, 0, cos_roll]
    ])


def project_target_to_screen_with_position(target_coords, spaceship_position, yaw, pitch, roll, fov, screen_width, screen_height):
    """
    Projiziert die Zielkoordinaten unter Berücksichtigung der Position des Raumschiffs auf den Bildschirm.
    :param target_coords: Zielkoordinaten (x, y, z) im Weltkoordinatensystem
    :param spaceship_position: Position des Raumschiffs (xr, yr, zr) im Weltkoordinatensystem
    :param yaw: Drehung um die Z-Achse in Grad
    :param pitch: Drehung um die X-Achse in Grad
    :param roll: Drehung um die Y-Achse in Grad
    :param fov: Sichtfeld in Grad (Horizontal)
    :param screen_width: Bildschirmbreite in Pixel
    :param screen_height: Bildschirmhöhe in Pixel
    :return: (screen_x, screen_y) Bildschirmkoordinaten oder None, wenn Ziel außerhalb des Sichtfeldes liegt
    """
    # Relativkoordinaten berechnen
    relative_coords = target_coords - spaceship_position
    print(relative_coords)
    # Kombinierte Rotationsmatrix
    rotation_matrix = rotation_matrix_yaw(yaw) @ rotation_matrix_pitch(pitch) @ rotation_matrix_roll(roll)
    print(rotation_matrix)
    # Zielkoordinaten in die Kamerakoordinaten transformieren
    target_in_camera_coords = rotation_matrix @ relative_coords
    print("Target in camera coords:")
    print(target_in_camera_coords)
    # Extrahiere die transformierten Koordinaten
    x, y, z = target_in_camera_coords

    # Wenn das Ziel hinter der Kamera liegt, ist es nicht sichtbar
    #if z <= 0:
        #return None

    # Berechnung der Projektion auf die Kameraebene (Perspektivprojektion)
    fov_rad = np.radians(fov)
    tan_half_fov = np.tan(fov_rad / 2)
    aspect_ratio = screen_width / screen_height

    # Projiziere x und y auf die Bildschirmkoordinaten
    screen_x = (x / z) / tan_half_fov * (screen_width / 2)
    screen_y = (y / z) / tan_half_fov * (screen_height / 2)
    print(screen_x)
    print(screen_y)
    # Bildschirmkoordinaten anpassen
    screen_x = screen_width / 2 + screen_x
    screen_y = screen_height / 2 - screen_y  # Y invertieren für Bildschirm-Koordinaten

    # Wenn die Koordinaten außerhalb des Bildschirms liegen, geben wir None zurück
    #if screen_x < 0 or screen_x > screen_width or screen_y < 0 or screen_y > screen_height:
        #return None
    print(screen_x)
    print(screen_y)
    return int(screen_x), int(screen_y)
    
def process_displayinfo(queue):
    global stop_threads,Destination,ocr_button_context,halo_running
    logger.debug("process_displayinfo entered")
    while True:    
        if stop_threads:
            logger.debug("  Exiting loop.")
            break
    #image = 'sc_testbild_ocr.jpg'  # replace with your screenshot path
        try:            
            image = pyautogui.screenshot()
            cur_camdir_pitch,cur_camdir_roll,cur_camdir_yaw, camdir_fov, container, localxyz_x,localxyz_y,localxyz_z, universe_xyz_x,universe_xyz_y,universe_xyz_z = read_screenshot(image)
            logger.debug("going on...")
            if halo_running:
                output = f"UniverseCoordinates_OCR:{str(universe_xyz_x)} {str(universe_xyz_y)} {str(universe_xyz_z)}"
                logger.debug("Output clipboard: " + str(output))
            else:
                output = "LocalCoordinates_OCR:" + str(container) + " " +str(localxyz_x) + " " + str(localxyz_y) + " " + str(localxyz_z)
                logger.debug("Output clipboard: " + str(output))
                spaceship_position = np.array([localxyz_x,localxyz_y,localxyz_z])
                target_coords = np.array([Destination["X"], Destination["Y"], Destination["Z"]])
                result = project_target_to_screen_with_position(target_coords, spaceship_position, cur_camdir_roll, cur_camdir_pitch, cur_camdir_yaw, camdir_fov, 3440, 1440)
                DrawThread=threading.Thread(target=create_overlay,args=(int(result[0]),int(result[1]))) #Prepare a new thread create_overlay(screen_coords[0],screen_coords[1])
                DrawThread.start()
                logger.debug(" DrawThread start()")
            pyperclip.copy(str(output))
            #ocr_button_context.set_state(ocr_button_context.context, 1)
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS) #SystemAsterisk
            #os.system(f"process_displayinfo.py {camdir_pitch} {camdir_roll} {camdir_yaw} {camdir_fov} {} {} {}")
            #calculate_target_marker(cur_camdir_pitch,cur_camdir_roll,cur_camdir_yaw, camdir_fov)          
            time.sleep(5)
        except Exception as e:
            logger.debug("Exception_process_displayinfo " + str(e))
            #ocr_button_context.set_state(ocr_button_context.context, 2)
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS) #SystemAsterisk

def read_screenshot(image_path):
    # Define the regions of interest (ROI) in the image
    roi_camdir = [3028, 3, 3438, 18]
    roi_localxyz = [2955, 31, 3438, 44]
    roi_universe_xyz = [3080, 45, 3438, 58]
    roi_servertime = [3192, 147, 3438, 158]
    roi_universetime = [3175, 172, 3438, 185]

    # Read image from path using OpenCV library
    #image = cv2.imread(image_path) #png in filesystem
    image = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR) #screenshot
    #cv2.imwrite('test.png', image) #debug

    # Upscale each ROI to improve OCR accuracy
    camdir_image_upscaled = cv2.resize(image[roi_camdir[1]:roi_camdir[3], roi_camdir[0]:roi_camdir[2]], None, fx=3, fy=3)
    localxyz_image_upscaled = cv2.resize(image[roi_localxyz[1]:roi_localxyz[3], roi_localxyz[0]:roi_localxyz[2]], None, fx=3, fy=3)
    universe_xyz_image_upscaled = cv2.resize(image[roi_universe_xyz[1]:roi_universe_xyz[3], roi_universe_xyz[0]:roi_universe_xyz[2]], None, fx=3, fy=3)
    #servertime_image_upscaled = cv2.resize(image[roi_servertime[1]:roi_servertime[3], roi_servertime[0]:roi_servertime[2]], None, fx=2, fy=2)
    #universetime_image_upscaled = cv2.resize(image[roi_universetime[1]:roi_universetime[3], roi_universetime[0]:roi_universetime[2]], None, fx=2, fy=2)

    
    # Preprocess each ROI to improve OCR accuracy
    camdir_gray = cv2.cvtColor(camdir_image_upscaled, cv2.COLOR_BGR2GRAY)
    localxyz_gray = cv2.cvtColor(localxyz_image_upscaled, cv2.COLOR_BGR2GRAY)
    universe_xyz_gray = cv2.cvtColor(universe_xyz_image_upscaled, cv2.COLOR_BGR2GRAY)
    #servertime_gray = cv2.cvtColor(servertime_image_upscaled, cv2.COLOR_BGR2GRAY)
    #universetime_gray = cv2.cvtColor(universetime_image_upscaled, cv2.COLOR_BGR2GRAY)
   
    # Perform OCR on each ROI
    try:
        camdir_text = pytesseract.image_to_string(camdir_gray, lang='eng', config='--oem 3 --psm 6')
        logger.debug(camdir_text)
        localxyz_text = pytesseract.image_to_string(localxyz_gray, lang='eng', config='--oem 3 --psm 6')
        logger.debug(localxyz_text)
        universe_xyz_text = pytesseract.image_to_string(universe_xyz_gray, lang='eng', config='--oem 3 --psm 6')
        #universe_xyz_text = "0 0 0"
        #servertime_text = pytesseract.image_to_string(servertime_gray, lang='eng', config='--oem 3 --psm 6')
        #universetime_text = pytesseract.image_to_string(universetime_gray, lang='eng', config='--oem 3 --psm 6')

        # CamDir: -17 -2 75 FOV: 50 Focal: 3.00 FStop: 64.0
        camdir_array = camdir_text.split() 
        logger.debug(camdir_array)
        re_number_camdir = re.compile(r"[+-]?([0-9]+)")
        re_number = re.compile(r"[+-]?([0-9]*[.])?[0-9]+")
        
        camdir_array[1] = re_number_camdir.findall(str(camdir_array[1]))[0]
        camdir_array[2] = re_number_camdir.findall(str(camdir_array[2]))[0]
        camdir_array[3] = re_number_camdir.findall(str(camdir_array[3]))[0]
        camdir_array[5] = re_number_camdir.findall(str(camdir_array[5]))[0]
        logger.debug(camdir_array)
        #Zone: OOC Stanton 2c Yela Pos: -626.6130km 135.8162km -1753.85m
        localxyz_array = localxyz_text.split()
        logger.debug(localxyz_array)
        logger.debug(universe_xyz_text)

        
        try:
            if "m" in str(localxyz_array[-3]) and not "km" in str(localxyz_array[-3]):
                logger.debug(localxyz_array[-3])
                localxyz_array[-3]=float(str(localxyz_array[-3]).replace("m","")) * 0.001 #convert in km
            elif "km" in localxyz_array[-3]:
                localxyz_array[-3]=float(str(localxyz_array[-3]).replace("km",""))

            if "m" in str(localxyz_array[-2]) and not "km" in str(localxyz_array[-2]):
                localxyz_array[-2]=float(str(localxyz_array[-2]).replace("m","")) * 0.001 #convert in km
            elif "km" in localxyz_array[-2]:
                localxyz_array[-2]=float(str(localxyz_array[-2]).replace("km",""))
            if "m" in str(localxyz_array[-1]) and not "km" in str(localxyz_array[-1]):
                localxyz_array[-1]=float(str(localxyz_array[-1]).replace("m","")) * 0.001 #convert in km
            elif "km" in localxyz_array[-1]:
                localxyz_array[-1]=float(str(localxyz_array[-1]).replace("km",""))

            localxyz_array[-3] = re_number.findall(str(localxyz_array[-3]))[0]
            localxyz_array[-2] = re_number.findall(str(localxyz_array[-2]))[0]
            localxyz_array[-1] = re_number.findall(str(localxyz_array[-1]))[0]
            logger.debug(localxyz_array)
        except Exception as e:
            logger.debug(f"localxyz: {e}")

        # Pos: -19022757.8983km -2613374.9914km -1753.85m
        try:
            universe_xyz_array = universe_xyz_text.split()
            logger.debug(universe_xyz_array)
            if "m" in universe_xyz_array[-3] and not "km" in universe_xyz_array[-3]:
                universe_xyz_array[-3]=str(float(universe_xyz_array[-3].replace("m","")) * 0.001) #convert in km
            elif "km" in universe_xyz_array[-3]:
                universe_xyz_array[-3]=str(float(universe_xyz_array[-3].replace("km","")))
            if "m" in universe_xyz_array[-2] and not "km" in universe_xyz_array[-2]:
                universe_xyz_array[-2]=str(float(universe_xyz_array[-2].replace("m","")) * 0.001) #convert in km
            elif "km" in universe_xyz_array[-2]:
                universe_xyz_array[-2]=str(float(universe_xyz_array[-2].replace("km","")))
            if "m" in universe_xyz_array[-1] and not "km" in universe_xyz_array[-1]:
                universe_xyz_array[-1]=str(float(universe_xyz_array[-1].replace("m","")) * 0.001) #convert in km     
            elif "km" in universe_xyz_array[-1]:
                universe_xyz_array[-1]=str(float(universe_xyz_array[-1].replace("km","")))
            logger.debug(universe_xyz_array)
        except Exception as e:
            logger.debug(f"universe_xyz: {e}")

        
        logger.debug(f"camdir: {int(camdir_array[1])},{int(camdir_array[2])},{int(camdir_array[3])},{float(camdir_array[5])}")
        logger.debug(f"localxyz: {localxyz_array[-5]},{float(localxyz_array[-3])},{float(localxyz_array[-2])},{float(localxyz_array[-1])}")
        logger.debug(f"universe: {float(universe_xyz_array[-3])},{float(universe_xyz_array[-2])},{float(universe_xyz_array[-1])}")

        return_value = f"{str(int(camdir_array[1]))},{int(camdir_array[2])},{int(camdir_array[3])}, {float(camdir_array[5])}, {localxyz_array[-5]}, {float(localxyz_array[-3])},{float(localxyz_array[-2])},{float(localxyz_array[-1])}, {float(universe_xyz_array[-3])},{float(universe_xyz_array[-2])},{float(universe_xyz_array[-1])}"
        logger.debug("return value:")
        logger.debug(return_value)


        return int(camdir_array[1]),int(camdir_array[2]),int(camdir_array[3]), float(camdir_array[5]), localxyz_array[-5], float(localxyz_array[-3]),float(localxyz_array[-2]),float(localxyz_array[-1]), float(universe_xyz_array[-3]),float(universe_xyz_array[-2]),float(universe_xyz_array[-1])

    except Exception as e:
        logger.debug(f"Exception read_screenshot: {e}")
        #pass

def linebreak_title(newtitle):
    i = 9
    #old#logger.debug(newtitle)
    tmp_1=""
    tmp_2=""
    tmp_3=""
    if len(newtitle) > i:
        tmp_1 = newtitle[:i] + '\n' # + newtitle[i:]
        if len(newtitle) > (2 * i):
            tmp_2 = newtitle[i:(2*i)] + '\n'
            if len(newtitle) > (3 * i):
                tmp_3 = newtitle[(2*i):(3*i)]
            else:
                tmp_3 = newtitle[(2*i):]
        else:
            tmp_2 =  newtitle[i:]      
    else:
        tmp_1 = newtitle            
    #old#logger.debug(tmp_1)
    return tmp_1 + tmp_2 + tmp_3

def coordinatetimeout():
    global stop_coordinatetimeout
    logger.debug("coordinatetimeout_start")
    time.sleep(5)
    if stop_coordinatetimeout == False:
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
        logger.debug("Timeout fired")
    else:
        logger.debug("no timeout")
        
def cancel_quantumdrive():
    #ahk.send_input('{LButton}') 
    ahk.send('{LButton down}')
    time.sleep(1)
    ahk.send('{LButton up}')
    

def cyclic_showlocation(queue):
    global halo_running,stop_threads
    logger.debug("Entered cyclic_showlocation")
    while halo_running:
        if stop_threads:
            logger.debug("Stopping cyclic_showlocation...")
            break
        updatecoordinates()
        time.sleep(5)

def updatecoordinates():
    #old#logger.debug(f"Update entered.")
    global mother,oms_button_context,stop_coordinatetimeout,CoordinateTimeoutThread,halo_running
    logger.debug("showlocation")
    CoordinateTimeoutThread=threading.Thread(target=coordinatetimeout) #Prepare a new thread
    stop_coordinatetimeout = False
    CoordinateTimeoutThread.start()
    ahk.send_input('{Enter}')
    time.sleep(0.5)
    ahk.send_input("/")
    time.sleep(0.2)
    ahk.send_input("showlocation")
    time.sleep(0.2)
    ahk.send_input('{Enter}')
    if not halo_running:
        message_oms = json.dumps({"event": "setTitle",
                                                "context": oms_button_context,
                                                "payload": {
                                                    "title": get_om_distances(),
                                                    "target": 0,
                                                }
                                            })   
        mother.ws.send(message_oms)
    
    
def save_poi():
    global save_triggered,watch_clipboard_active,mother
    
    #old#logger.debug(f"Save entered.")
    if watch_clipboard_active == True:
        save_triggered = True
        updatecoordinates()
    else:
        message_saved_nok = json.dumps({"event": "showAlert",
                                        "context": save_button_context
                                    })
        mother.ws.send(message_saved_nok)      
    #if navigation is active it saves current coordinates
    

def vector_norm(a):
    """Returns the norm of a vector"""
    return sqrt(a["X"]**2 + a["Y"]**2 + a["Z"]**2)

def vector_product(a, b):
    """Returns the dot product of two vectors"""
    return a["X"]*b["X"] + a["Y"]*b["Y"] + a["Z"]*b["Z"]

def angle_between_vectors(a, b):
    """Function that returns an angle in degrees between 2 vectors"""
    try :
        angle = degrees(acos(vector_product(a, b) / (vector_norm(a) * vector_norm(b))))
    except ZeroDivisionError:
        angle = 0.0
    return angle

def rotate_point_2D(Unrotated_coordinates, angle):
    Rotated_coordinates = {}
    logger.debug("unrotated_x: "+str(Unrotated_coordinates["X"]))
    logger.debug("Angle: "+ str(angle))
    logger.debug("unrotated_y: "+str(Unrotated_coordinates["Y"]))
    Rotated_coordinates["X"] = Unrotated_coordinates["X"] * cos(angle) - Unrotated_coordinates["Y"]*sin(angle)
    logger.debug("calc:"+str(Rotated_coordinates["X"]))
    Rotated_coordinates["Y"] = Unrotated_coordinates["X"] * sin(angle) + Unrotated_coordinates["Y"]*cos(angle)
    Rotated_coordinates["Z"] = Unrotated_coordinates["Z"]
    logger.debug("calc_return:"+str(Rotated_coordinates))
    return (Rotated_coordinates)

def get_local_rotated_coordinates(Time_passed : float, X : float, Y : float, Z : float, Actual_Container : dict):
    
    try:
        Rotation_speed_in_degrees_per_second = 0.1 * (1/Actual_Container["Rotation Speed"])
    except ZeroDivisionError:
        Rotation_speed_in_degrees_per_second = 0
    
    Rotation_state_in_degrees = ((Rotation_speed_in_degrees_per_second * Time_passed) + Actual_Container["Rotation Adjust"]) % 360
    
    local_unrotated_coordinates = {
        "X": X - Actual_Container["X"],
        "Y": Y - Actual_Container["Y"],
        "Z": Z - Actual_Container["Z"]
    }
    
    local_rotated_coordinates = rotate_point_2D(local_unrotated_coordinates, radians(-1*Rotation_state_in_degrees))
    logger.debug("rotate: " + str(X))
    logger.debug("rotate: " + str(Y))
    logger.debug("rotate: " + str(Z))
    logger.debug(local_rotated_coordinates)
    return local_rotated_coordinates

def calc_eulerangels_planet(Time_passed : float, X : float, Y : float, Z : float, dest_X : float, dest_Y : float, dest_Z : float, Actual_Container : dict):
    deltaX = dest_X - X
    deltaY = dest_Y - Y
    deltaZ = dest_Z - Z
    #current cycle in degrees

    try:
        Rotation_speed_in_degrees_per_second = 0.1 * (1/Actual_Container["Rotation Speed"])
    except ZeroDivisionError:
        Rotation_speed_in_degrees_per_second = 0
    
    OCCurrentCycleDegLive = ((Rotation_speed_in_degrees_per_second * Time_passed) + Actual_Container["Rotation Adjust"]) % 360

    
    logger.debug(X)
    logger.debug(Y)
    logger.debug(Z)
    logger.debug(dest_X)
    logger.debug(dest_Y)
    logger.debug(dest_Z)
    logger.debug(Actual_Container["Rotation Adjust"])

    #yaw
    yaw = degrees(atan2(deltaY,deltaX))
    logger.debug("Yaw: " + str(yaw))
    if yaw > 90 :
        final_yaw = yaw - 270
    else:
        final_yaw = yaw + 90
    #pitch
    distanceXY = sqrt(deltaX**2 + deltaY**2)
    pitch  = degrees(atan2(deltaZ,distanceXY))
    logger.debug("Pitch: " + str(pitch))
    if pitch < 0:
        final_pitch = -180 - pitch
    else:
        final_pitch = 180 - pitch

    #roll
    roll  = 0
    
    correction = -360 + Actual_Container["Rotation Adjust"]
    if (OCCurrentCycleDegLive -90 + yaw) > 180:
        final_yaw = yaw + OCCurrentCycleDegLive - 450 + correction
    elif (OCCurrentCycleDegLive - 90 + yaw) < -180:
        final_yaw = yaw + OCCurrentCycleDegLive + 270 + correction
    else:
        final_yaw = yaw + OCCurrentCycleDegLive - 90 + correction

    logger.debug("final_yaw: " + str(final_yaw))
    # (234): Yaw: 141.28478066993233
    #(242): Pitch: 0.8336950267047344
    # Pitch_final: 179.16630497329527
    #Yaw_final: -128.71521933006767
    return (final_yaw,pitch,roll)
    

def get_lat_long_height(X : float, Y : float, Z : float, Container : dict):
    global northpole_is_om3
    Radius = Container["Body Radius"]
    logger.debug(X)
    logger.debug(Y)
    logger.debug(Z)
    logger.debug(Container)
    Radial_Distance = sqrt(X**2 + Y**2 + Z**2)
    
    Height = Radial_Distance - Radius

    #Latitude
    try :
        Latitude = degrees(asin(Z/Radial_Distance))
        LatitudeOM3 = degrees(asin(Y/Radial_Distance))
    except :
        Latitude = 0
        LatitudeOM3 = 0
    
    try :
        Longitude = -1*degrees(atan2(X, Y))
        LongitudeOM3 = -1*degrees(atan2(X, Z))
    except :
        Longitude = 0
        LongitudeOM3 = 0
    if northpole_is_om3:
        logger.debug("OM3 set as northpole")
        Latitude = LatitudeOM3
        Longitude = LongitudeOM3
    return [Latitude, Longitude, Height]

def get_sandcaves_sorted(X : float, Y : float, Z : float, Container:dict):
    global datasource
    Distances_to_POIs = []
    logger.debug("gss_1")
    #old#logger.debug(str(Container))
    logger.debug(str(datasource))
    logger.debug("Player: "+str(X)+","+str(Y)+","+str(Z) )
    for POI in Container["POI"]:
        logger.debug("loop POI: " + str(POI))
        if "Sand Cave" in str(Container["POI"][POI]['Classification']): #'Classification': 'Sand Cave
            logger.debug("processing: "+str(Container["POI"][POI]))
            Vector_POI = {
            "X": abs(X - Container["POI"][POI]["X"]),
            "Y": abs(Y - Container["POI"][POI]["Y"]),
            "Z": abs(Z - Container["POI"][POI]["Z"])
            }
            #old#logger.debug("Vector_POI: " + str(Vector_POI))

            Distance_POI = vector_norm(Vector_POI)
            #and calculate for every sand cave next QT marker distance
            Cave_to_POIs_Distances_Sorted = get_closest_POI(Container["POI"][POI]["X"], Container["POI"][POI]["Y"], Container["POI"][POI]["Z"], Container, True)
            Nearest_POI_to_singleCave = Cave_to_POIs_Distances_Sorted[0]
            logger.debug("Nearest QTmarker to Cave:"+str(Nearest_POI_to_singleCave))
            Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI, "nextQTMarkerDistance" : Nearest_POI_to_singleCave["Distance"], "X": Container["POI"][POI]['X'], "Y": Container["POI"][POI]['Y'], "Z": Container["POI"][POI]['Z'], "Container": Container["POI"][POI]['Container'], "QTMarker": Container["POI"][POI]['QTMarker'] })
    
            #Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI, "X": Container["POI"][POI]['X'], "Y": Container["POI"][POI]['Y'], "Z": Container["POI"][POI]['Z'], "Container": Container["POI"][POI]['Container'], "QTMarker": Container["POI"][POI]['QTMarker'] })
    logger.debug("all POIs processed.")
    if len(Distances_to_POIs) == 0:
        return Distances_to_POIs
    else:
        Player_to_Sandcaves_sorted = sorted(Distances_to_POIs, key=lambda k: k['Distance'])
        logger.debug("sorted to distance.")
        logger.debug(str(Distances_to_POIs))
        Sandcaves_to_QTMarker_sorted = sorted(Distances_to_POIs, key=lambda k: k['nextQTMarkerDistance'])
        logger.debug("sorted to QTMarker distance")
        logger.debug(str(Sandcaves_to_QTMarker_sorted))
        if Player_to_Sandcaves_sorted[0]["Distance"] > Sandcaves_to_QTMarker_sorted[0]["nextQTMarkerDistance"]:
            logger.debug("QTMarker Sandcave is next")
            return Sandcaves_to_QTMarker_sorted
        else:
            logger.debug("Sandcave without QT is next")
            return Player_to_Sandcaves_sorted
    
        
def reorder_Destination_queue(X : float, Y : float, Z : float, queue:dict): 
    global Destination_queue
    Distances_to_POIs = []
    logger.debug("rdq_1")
    #old#logger.debug(str(Container))
    logger.debug("Player: "+str(X)+","+str(Y)+","+str(Z) )
    for POI in queue:
        logger.debug("loop Cave: " + str(POI))

        Vector_POI = {
        "X": abs(X - POI["X"]),
        "Y": abs(Y - POI["Y"]),
        "Z": abs(Z - POI["Z"])
        }
        logger.debug("Vector_POI: " + str(Vector_POI))

        Distance_POI = vector_norm(Vector_POI)
        #and calculate for every sand cave next QT marker distance
        #Cave_to_POIs_Distances_Sorted = get_closest_POI(Container["POI"][POI]["X"], Container["POI"][POI]["Y"], Container["POI"][POI]["Z"], Container, True)
        Nearest_POI_to_singleCaveDistance = POI["nextQTMarkerDistance"]
        #old#logger.debug("Nearest QTmarker to Cave:"+str(Nearest_POI_to_singleCave))
        logger.debug("append next")
        Distances_to_POIs.append({"Name" : POI["Name"], "Distance" : Distance_POI, "nextQTMarkerDistance" : Nearest_POI_to_singleCaveDistance, "X": POI["X"], "Y": POI["Y"], "Z": POI["Z"], "Container": POI['Container'], "QTMarker": POI['QTMarker'] })
        logger.debug("append done")
    
    Player_to_Sandcaves_sorted= sorted(Distances_to_POIs, key=lambda k: k['Distance'])
    Sandcaves_to_QTMarker_sorted = sorted(Distances_to_POIs, key=lambda k: k['nextQTMarkerDistance'])
    
    logger.debug("final player2sandcaves sorted:"+str(Player_to_Sandcaves_sorted))
    logger.debug("final sandcaves2QT sorted:"+str(Sandcaves_to_QTMarker_sorted))
    
    if Player_to_Sandcaves_sorted[0]["Distance"] > Sandcaves_to_QTMarker_sorted[0]["nextQTMarkerDistance"]:
        logger.debug("QTMarker Sandcave is next: " + str(Player_to_Sandcaves_sorted[0]["Distance"]) + " vs "+str(Sandcaves_to_QTMarker_sorted[0]["nextQTMarkerDistance"]))
        Destination_queue = Sandcaves_to_QTMarker_sorted
    else:
        logger.debug("Sandcave without QT is next: " + str(Player_to_Sandcaves_sorted[0]["Distance"]) + " vs "+str(Sandcaves_to_QTMarker_sorted[0]["nextQTMarkerDistance"]))
        Destination_queue =  Player_to_Sandcaves_sorted
      
    
    
def get_closest_POI(X : float, Y : float, Z : float, Container : dict, Quantum_marker : bool = False):
    
    Distances_to_POIs = []
    
    for POI in Container["POI"]:
        #old#logger.debug("processing: "+str(Container["POI"][POI]))
        Vector_POI = {
            "X": abs(X - Container["POI"][POI]["X"]),
            "Y": abs(Y - Container["POI"][POI]["Y"]),
            "Z": abs(Z - Container["POI"][POI]["Z"])
        }
        #old#logger.debug("Vector_POI: " + str(Vector_POI))

        Distance_POI = vector_norm(Vector_POI)
        
        #old#logger.debug("Quantum_marker: " + str(Quantum_marker))
        #old#logger.debug("Quantum_marker POI: " + str(Container["POI"][POI]["QTMarker"]))

        if Quantum_marker and Container["POI"][POI]["QTMarker"] == "TRUE" or not Quantum_marker:
            Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI, "X" : Container["POI"][POI]["X"], "Y" : Container["POI"][POI]["Y"], "Z" : Container["POI"][POI]["Z"]})
            #old#logger.debug("Added to closest POI list: "+str(POI)+" with "+str(Distance_POI))
    #old#logger.debug("final:"+str(Distances_to_POIs))
    Target_to_POIs_Distances_Sorted = sorted(Distances_to_POIs, key=lambda k: k['Distance'])
    logger.debug("final sorted:"+str(Target_to_POIs_Distances_Sorted))
    return Target_to_POIs_Distances_Sorted


    
def get_om_distances():
    global Database,Destination
    
    current_container = Destination["Container"]
    X = Destination["X"]
    Y = Destination["Y"]
    Z = Destination["Z"]
    Vector_POI = {
        "X": abs(X - 0),
        "Y": abs(Y - 0),
        "Z": abs(Z - Database["Containers"][current_container]["OM Radius"])
    }
    Distance_OM_1 = vector_norm(Vector_POI)
    Vector_POI = {
        "X": abs(X - 0),
        "Y": abs(Y - 0),
        "Z": abs(Z - (-1 * Database["Containers"][current_container]["OM Radius"]))
    }
    Distance_OM_2 = vector_norm(Vector_POI)
    
    Vector_POI = {
        "X": abs(X - 0),
        "Y": abs(Y - Database["Containers"][current_container]["OM Radius"]),
        "Z": abs(Z - 0)
    }
    Distance_OM_3 = vector_norm(Vector_POI)
    Vector_POI = {
        "X": abs(X - 0),
        "Y": abs(Y - (-1 * Database["Containers"][current_container]["OM Radius"])),
        "Z": abs(Z - 0)
    }
    Distance_OM_4 = vector_norm(Vector_POI)
    Vector_POI = {
        "X": abs(X - Database["Containers"][current_container]["OM Radius"]),
        "Y": abs(Y - 0),
        "Z": abs(Z - 0)
    }
    Distance_OM_5 = vector_norm(Vector_POI)
    Vector_POI = {
        "X": abs(X - (-1 * Database["Containers"][current_container]["OM Radius"])),
        "Y": abs(Y - 0),
        "Z": abs(Z - 0)
    }
    Distance_OM_6 = vector_norm(Vector_POI)
    return f"OM1: {round(Distance_OM_1,1)}\nOM2: {round(Distance_OM_2,1)}\nOM3: {round(Distance_OM_3,1)}\nOM4: {round(Distance_OM_4,1)}\nOM5: {round(Distance_OM_5,1)}\nOM6: {round(Distance_OM_6,1)}"

    #return "OM1: n/a\nOM2: n/a\nOM3: n/a\nOM4: n/a\nOM5: n/a\nOM6: n/a"

def get_closest_oms(X : float, Y : float, Z : float, Container : dict):
    Closest_OM = {}
    
    if X >= 0:
        Closest_OM["X"] = {"OM" : Container["POI"]["OM-5"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-5"]["X"], "Y" : Y - Container["POI"]["OM-5"]["Y"], "Z" : Z - Container["POI"]["OM-5"]["Z"]})}
    else:
        Closest_OM["X"] = {"OM" : Container["POI"]["OM-6"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-6"]["X"], "Y" : Y - Container["POI"]["OM-6"]["Y"], "Z" : Z - Container["POI"]["OM-6"]["Z"]})}
    if Y >= 0:
        Closest_OM["Y"] = {"OM" : Container["POI"]["OM-3"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-3"]["X"], "Y" : Y - Container["POI"]["OM-3"]["Y"], "Z" : Z - Container["POI"]["OM-3"]["Z"]})}
    else:
        Closest_OM["Y"] = {"OM" : Container["POI"]["OM-4"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-4"]["X"], "Y" : Y - Container["POI"]["OM-4"]["Y"], "Z" : Z - Container["POI"]["OM-4"]["Z"]})}
    if Z >= 0:
        Closest_OM["Z"] = {"OM" : Container["POI"]["OM-1"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-1"]["X"], "Y" : Y - Container["POI"]["OM-1"]["Y"], "Z" : Z - Container["POI"]["OM-1"]["Z"]})}
    else:
        Closest_OM["Z"] = {"OM" : Container["POI"]["OM-2"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-2"]["X"], "Y" : Y - Container["POI"]["OM-2"]["Y"], "Z" : Z - Container["POI"]["OM-2"]["Z"]})}

    return Closest_OM



def get_sunset_sunrise_predictions(X : float, Y : float, Z : float, Latitude : float, Longitude : float, Height : float, Container : dict, Star : dict, Time_passed_since_reference_in_seconds):
    try :
        logger.debug("27.1")
        # Stanton X Y Z coordinates in refrence of the center of the system
        sx, sy, sz = Star["X"], Star["Y"], Star["Z"]
        
        # Container X Y Z coordinates in refrence of the center of the system
        bx, by, bz = Container["X"], Container["Y"], Container["Z"]
        
        # Rotation speed of the container
        rotation_speed = Container["Rotation Speed"]
        logger.debug("27.2")        
        # Container qw/qx/qy/qz quaternion rotation 
        qw, qx, qy, qz = float(Container["qw"]), float(Container["qx"]), float(Container["qy"]), float(Container["qz"])
        logger.debug(Container)
        logger.debug("27.3")        
        # Stanton X Y Z coordinates in refrence of the center of the container
        bsx = ((1-(2*qy**2)-(2*qz**2))*(sx-bx))+(((2*qx*qy)-(2*qz*qw))*(sy-by))+(((2*qx*qz)+(2*qy*qw))*(sz-bz))
        logger.debug("27.3_1") 
        bsy = (((2*qx*qy)+(2*qz*qw))*(sx-bx))+((1-(2*qx**2)-(2*qz**2))*(sy-by))+(((2*qy*qz)-(2*qx*qw))*(sz-bz))
        logger.debug("27.3_2") 
        bsz = (((2*qx*qz)-(2*qy*qw))*(sx-bx))+(((2*qy*qz)+(2*qx*qw))*(sy-by))+((1-(2*qx**2)-(2*qy**2))*(sz-bz))
        logger.debug("27.3_3") 
        # Solar Declination of Stanton
        Solar_declination = degrees(acos((((sqrt(bsx**2+bsy**2+bsz**2))**2)+((sqrt(bsx**2+bsy**2))**2)-(bsz**2))/(2*(sqrt(bsx**2+bsy**2+bsz**2))*(sqrt(bsx**2+bsy**2)))))*copysign(1,bsz)
        logger.debug("27.3_4") 
        logger.debug(f"sunrise/sunset calculations: \nValues were:\n-X : {X}\n-Y : {Y}\n-Z : {Z}\n-Latitude : {Latitude}\n-Longitude : {Longitude}\n-Height : {Height}\n-Container : {Container['Name']}\n-Star : {Star['Name']}")
       
        logger.debug("27.4")        
        # Radius of Stanton
        StarRadius = Star["Body Radius"] # OK
        logger.debug("27.5")        
        # Apparent Radius of Stanton
        Apparent_Radius = degrees(asin(StarRadius/(sqrt((bsx)**2+(bsy)**2+(bsz)**2))))
        logger.debug("27.6")        
        # Length of day is the planet rotation rate expressed as a fraction of a 24 hr day.
        LengthOfDay = 3600*rotation_speed/86400
        logger.debug("27.7")        
        
        
        # A Julian Date is simply the number of days and fraction of a day since a specific event. (01/01/2020 00:00:00)
        JulianDate = Time_passed_since_reference_in_seconds/(24*60*60) # OK
        
        # Determine the current day/night cycle of the planet.
        # The current cycle is expressed as the number of day/night cycles and fraction of the cycle that have occurred
        # on that planet since Jan 1, 2020 given the length of day. While the number of sunrises that have occurred on the 
        # planet since Jan 1, 2020 is interesting, we are really only interested in the fractional part.
        try :
            CurrentCycle = JulianDate/LengthOfDay
        except ZeroDivisionError :
            CurrentCycle = 1
        
        
        # The rotation correction is a value that accounts for the rotation of the planet on Jan 1, 2020 as we don’t know
        # exactly when the rotation of the planet started.  This value is measured and corrected during a rotation
        # alignment that is performed periodically in-game and is retrieved from the navigation database.
        RotationCorrection = Container["Rotation Adjust"]
        logger.debug("27.8")        
        # CurrentRotation is how far the planet has rotated in this current day/night cycle expressed in the number of
        # degrees remaining before the planet completes another day/night cycle.
        CurrentRotation = (360-(CurrentCycle%1)*360-RotationCorrection)%360
        
        
        # Meridian determine where the star would be if the planet did not rotate.
        # Between the planet and Stanton there is a plane that contains the north pole and south pole
        # of the planet and the center of Stanton. Locations on the surface of the planet on this plane
        # experience the phenomenon we call noon.
        Meridian = degrees( (atan2(bsy,bsx)-(pi/2)) % (2*pi) )
        
        # Because the planet rotates, the location of noon is constantly moving. This equation
        # computes the current longitude where noon is occurring on the planet.
        SolarLongitude = CurrentRotation-(0-Meridian)%360
        if SolarLongitude>180:
            SolarLongitude = SolarLongitude-360
        elif SolarLongitude<-180:
            SolarLongitude = SolarLongitude+360
        
        logger.debug("27.9")        
        
        # The difference between Longitude and Longitude360 is that for Longitude, Positive values
        # indicate locations in the Eastern Hemisphere, Negative values indicate locations in the Western
        # Hemisphere.
        # For Longitude360, locations in longitude 0-180 are in the Eastern Hemisphere, locations in
        # longitude 180-359 are in the Western Hemisphere.
        Longitude360 = Longitude%360 # OK
        
        # Determine correction for location height
        ElevationCorrection = degrees(acos(Container["Body Radius"]/(Container["Body Radius"]))) if Height<0 else degrees(acos(Container["Body Radius"]/(Container["Body Radius"]+Height)))
        
        # Determine Rise/Set Hour Angle
        # The star rises at + (positive value) rise/set hour angle and sets at - (negative value) rise/set hour angle
        # Solar Declination and Apparent Radius come from the first set of equations when we determined where the star is.
        RiseSetHourAngle = degrees(acos(-tan(radians(Latitude))*tan(radians(Solar_declination))))+Apparent_Radius+ElevationCorrection
        logger.debug("27.10")        
        # Determine the current Hour Angle of the star
        
        # Hour Angles between 180 and the +Rise Hour Angle are before sunrise.
        # Between +Rise Hour angle and 0 are after sunrise before noon. 0 noon,
        # between 0 and -Set Hour Angle is afternoon,
        # between -Set Hour Angle and -180 is after sunset.
        
        # Once the current Hour Angle is determined, we now know the actual angle (in degrees)
        # between the position of the star and the +rise hour angle and the -set hour angle.
        HourAngle = (CurrentRotation-(Longitude360-Meridian)%360)%360
        if HourAngle > 180:
            HourAngle = HourAngle - 360
        
        
        # Determine the planet Angular Rotation Rate.
        # Angular Rotation Rate is simply the Planet Rotation Rate converted from Hours into degrees per minute.
        # The Planet Rotation Rate is datamined from the game files.
        try :
            AngularRotationRate = 6/rotation_speed # OK
        except ZeroDivisionError :
            AngularRotationRate = 0
        
        
        if AngularRotationRate != 0 :
            midnight = (HourAngle + 180) / AngularRotationRate
            
            morning = (HourAngle - (RiseSetHourAngle+12)) / AngularRotationRate
            if HourAngle <= RiseSetHourAngle+12:
                morning = morning + LengthOfDay*24*60
            
            sunrise = (HourAngle - RiseSetHourAngle) / AngularRotationRate
            if HourAngle <= RiseSetHourAngle:
                sunrise = sunrise + LengthOfDay*24*60
            
            noon = (HourAngle - 0) / AngularRotationRate
            if HourAngle <= 0:
                noon = noon + LengthOfDay*24*60
            
            sunset = (HourAngle - -1*RiseSetHourAngle) / AngularRotationRate
            if HourAngle <= -1*RiseSetHourAngle:
                sunset = sunset + LengthOfDay*24*60
            
            evening = (HourAngle - (-1*RiseSetHourAngle-12)) / AngularRotationRate
            if HourAngle <= -1*(RiseSetHourAngle-12):
                evening = evening + LengthOfDay*24*60
        else :
            midnight = 0
            morning = 0
            sunrise = 0
            noon = 0
            sunset = 0
            evening = 0
        
        
        
        
        if 180 >= HourAngle > RiseSetHourAngle+12:
            state_of_the_day = "After midnight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif RiseSetHourAngle+12 >= HourAngle > RiseSetHourAngle:
            state_of_the_day = "Morning Twilight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif RiseSetHourAngle >= HourAngle > 0:
            state_of_the_day = "Morning"
            next_event = "Sunset"
            next_event_time = sunset
        elif 0 >= HourAngle > -1*RiseSetHourAngle:
            state_of_the_day = "Afternoon"
            next_event = "Sunset"
            next_event_time = sunset
        elif -1*RiseSetHourAngle >= HourAngle > -1*RiseSetHourAngle-12:
            state_of_the_day = "Evening Twilight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif -1*RiseSetHourAngle-12 >= HourAngle >= -180:
            state_of_the_day = "Before midnight"
            next_event = "Sunrise"
            next_event_time = sunrise
        
        if AngularRotationRate == 0 :
            next_event = "N/A"
        
        return [state_of_the_day, next_event, next_event_time]
    
    except Exception as e:
        logger.debug(f"Error in sunrise/sunset calculations: \n{e}\nValues were:\n-X : {X}\n-Y : {Y}\n-Z : {Z}\n-Latitude : {Latitude}\n-Longitude : {Longitude}\n-Height : {Height}\n-Container : {Container['Name']}\n-Star : {Star['Name']}")
        #sys.stdout.flush()
        return ["Unknown", "Unknown", 0]



def get_current_container(X : float, Y : float, Z : float):
    global Database
    #old#logger.debug(f"get " + str(X))
    Actual_Container = {
        "Name": "None",
        "X": 0,
        "Y": 0,
        "Z": 0,
        "Rotation Speed": 0,
        "Rotation Adjust": 0,
        "OM Radius": 0,
        "Body Radius": 0,
        "POI": {}
    }
    for i in Database["Containers"] :
        Container_vector = {"X" : Database["Containers"][i]["X"] - X, "Y" : Database["Containers"][i]["Y"] - Y, "Z" : Database["Containers"][i]["Z"] - Z}
        if vector_norm(Container_vector) <= 3 * Database["Containers"][i]["OM Radius"]:
            Actual_Container = Database["Containers"][i]
    return Actual_Container

def watch_clipboard(queue):
    logger.debug(f"Watch Clipboard entered.")
    global clipboard_contains_universexyz,halo_running,save_button_context,save_triggered,Database,Container_list,Space_POI_list,Planetary_POI_list,watch_clipboard_active,Destination,stop_navithread,bearing_button_context,daytime_button_context,nearest_button_context,around_button_context,mother,coords_button_context,calibrate_active,daytime_toggle,sandcavetour_active,sandcavestour_button_context,sandcavetour_init_done,Destination_queue,knownPlayerX,knownPlayerY,knownPlayerZ,knownPlayerContainername,stop_coordinatetimeout,CoordinateTimeoutThread,northpole_is_om3,camdir_button_context,CamDirYaw, CamDirPitch, CamDirRoll
    watch_clipboard_active = True
    old_direction = ""
    #mother=threading.main_thread()

    #Test DATA
    #Destination = Database["Containers"]["Crusader"]["POI"]["August Dunlow Spaceport"]
    

    #Sets some variables
    Reference_time_UTC = datetime.datetime(2020, 1, 1)
    Epoch = datetime.datetime(1970, 1, 1)
    Reference_time = (Reference_time_UTC - Epoch).total_seconds()

    try :
        import ntplib
        c = ntplib.NTPClient()
        response = c.request('europe.pool.ntp.org', version=3)
        server_time = response.tx_time
        
        time_offset = response.offset
    except Exception as e:
        logger.debug("Error: Could not get time from NTP server:" + str(e))
        sys.stdout.flush()
        time_offset = 0

    logger.debug("Time offset (eigentlich): " + str(time_offset))
    time_offset = 0
    Old_clipboard = ""

    Old_player_Global_coordinates = {}
    for i in ["X", "Y", "Z"]:
        Old_player_Global_coordinates[i] = 0.0

    Old_player_local_rotated_coordinates = {}
    for i in ["X", "Y", "Z"]:
        Old_player_local_rotated_coordinates[i] = 0.0

    Old_Distance_to_POI = {}
    for i in ["X", "Y", "Z"]:
        Old_Distance_to_POI[i] = 0.0

    Old_container = {
        "Name": "None",
        "X": 0,
        "Y": 0,
        "Z": 0,
        "Rotation Speed": 0,
        "Rotation Adjust": 0,
        "OM Radius": 0,
        "Body Radius": 0,
        "POI": {}
    }
    Old_time = time.time()
    #Reset the clipboard content
    pyperclip.copy("")
    while True:
        
        if stop_navithread:
            watch_clipboard_active = False
            logger.debug(f"NaviThread stopping...")
            break

        #Get the new clipboard content
        new_clipboard = pyperclip.paste()
        #logger.debug(str(new_clipboard))


        #If clipboard content hasn't changed
        if new_clipboard == Old_clipboard or new_clipboard == "":

            #Wait some time
            time.sleep(1/5)


        #If clipboard content has changed
        else :
            logger.debug("New clipboard: " + str(new_clipboard))
            #stop_coordinatetimeout = True
            #CoordinateTimeoutThread.join()
            Old_clipboard = new_clipboard
            logger.debug("...")
            New_time = time.time() + time_offset

            #If it contains some coordinates
            if new_clipboard.startswith("Coordinates:") or new_clipboard.startswith("LocalCoordinates_OCR:") or new_clipboard.startswith("UniverseCoordinates_OCR:"):
                #split the clipboard in sections
                clipboard_contains_localxyz = False
                clipboard_contains_universexyz = False
                if new_clipboard.startswith("LocalCoordinates_OCR:"):
                    clipboard_contains_localxyz = True
                    logger.debug("new local ocr coordinates found")
                elif new_clipboard.startswith("UniverseCoordinates_OCR:"):
                    clipboard_contains_universexyz = True   
                    logger.debug("...")
                
                    
                #Coordinates: x:12792440814.115870 y:-74248558.612950 z:97041.278879
                #LocalCoordinates_OCR:Magda 800 600 200
                #UniverseCoordinates_OCR:-19023230.1716 -2614361.5286 3.68077
                logger.debug(clipboard_contains_localxyz)
                logger.debug(clipboard_contains_universexyz)
                new_clipboard_splitted = new_clipboard.replace(":", " ").split(" ")
                logger.debug("...")
                logger.debug(f"clipboard_contains_localxyz {clipboard_contains_localxyz},clipboard_contains_universexyz {clipboard_contains_universexyz}")

                if not clipboard_contains_localxyz and not clipboard_contains_universexyz and not halo_running:
                    #get the 3 new XYZ coordinates
                    logger.debug("...")
                    New_Player_Global_coordinates = {}
                    New_Player_Global_coordinates['X'] = float(new_clipboard_splitted[3])/1000
                    New_Player_Global_coordinates['Y'] = float(new_clipboard_splitted[5])/1000
                    New_Player_Global_coordinates['Z'] = float(new_clipboard_splitted[7])/1000
                    #search in the Databse to see if the player is ina Container
                    Actual_Container = get_current_container(New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"])
                    knownPlayerContainername=Actual_Container['Name']
                    logger.debug("Actual Container: " +str(Actual_Container))
                        
                    if calibrate_active:
                        logger.debug("Calibrate active")
                        ContainerName = Actual_Container['Name']
                        Destination = Database["Containers"][ContainerName]["POI"]["OM-3"]
                        logger.debug("...setting Destination to " + str(Destination))
                    #---------------------------------------------------New player local coordinates----------------------------------------------------
                    #Time passed since the start of game simulation
                    Time_passed_since_reference_in_seconds = New_time - Reference_time
                    
                    New_player_local_rotated_coordinates = get_local_rotated_coordinates(Time_passed_since_reference_in_seconds, New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"], Actual_Container)

                    logger.debug("1")
                    logger.debug("Sandcavetour_active: " + str(sandcavetour_active))
                    knownPlayerX=New_player_local_rotated_coordinates["X"]
                    knownPlayerY=New_player_local_rotated_coordinates["Y"]
                    knownPlayerZ=New_player_local_rotated_coordinates["Z"]
                elif clipboard_contains_localxyz:
                    logger.debug("...")
                    logger.debug(new_clipboard_splitted)
                    knownPlayerX=float(new_clipboard_splitted[2])
                    New_player_local_rotated_coordinates["X"] = knownPlayerX
                    knownPlayerY=float(new_clipboard_splitted[3])
                    New_player_local_rotated_coordinates["Y"] = knownPlayerY
                    knownPlayerZ=float(new_clipboard_splitted[4])
                    New_player_local_rotated_coordinates["Z"] = knownPlayerZ
                    knownPlayerContainername=new_clipboard_splitted[1]
                

                    Actual_Container = {
                        "Name": "None",
                        "X": 0,
                        "Y": 0,
                        "Z": 0,
                        "Rotation Speed": 0,
                        "Rotation Adjust": 0,
                        "OM Radius": 0,
                        "Body Radius": 0,
                        "POI": {}
                    }
                    for i in Database["Containers"] :
                        if knownPlayerContainername == Database["Containers"][i]['Name']:
                            Actual_Container = Database["Containers"][i]
                            logger.debug("Actual_container set to " + str(knownPlayerContainername))
                            logger.debug(Actual_Container)
                else: #universe coordinates
                    logger.debug("...else")
                    logger.debug(new_clipboard_splitted)
                    
                    New_Player_Global_coordinates = {}
                    if clipboard_contains_universexyz:
                        New_Player_Global_coordinates['X'] = float(new_clipboard_splitted[1])
                        New_Player_Global_coordinates['Y'] = float(new_clipboard_splitted[2])
                        New_Player_Global_coordinates['Z'] = float(new_clipboard_splitted[3])
                    else:
                        New_Player_Global_coordinates['X'] = float(new_clipboard_splitted[3])/1000
                        New_Player_Global_coordinates['Y'] = float(new_clipboard_splitted[5])/1000
                        New_Player_Global_coordinates['Z'] = float(new_clipboard_splitted[7])/1000
                    logger.debug(New_Player_Global_coordinates)
                    #Destination = Stanton Sun "X": 136049.87,"Y": 1294427.4, "Z": 2923345.368
                    Target={}
                    Delta_Distance_to_POI = {}
                    New_Distance_to_POI = {}
                    logger.debug("...")
                    Target['X']=136049
                    Target['Y']=1294427
                    Target['Z']=2923345
                    logger.debug(Target)
                    for i in ['X', 'Y', 'Z']:
                        logger.debug(i)
                        logger.debug(Target[i])
                        logger.debug(New_Player_Global_coordinates[i])
                        New_Distance_to_POI[i] = abs(Target[i] - New_Player_Global_coordinates[i])
                        logger.debug(New_Distance_to_POI[i])
                    New_Distance_to_POI_Total = vector_norm(New_Distance_to_POI)
                    logger.debug("...")
                    logger.debug(f"Distance to Sun: {str(int(New_Distance_to_POI_Total))}") #Distance to Sun: 3 201 923
                    
                    if int(New_Distance_to_POI_Total) > 20407000:
                        direction=1
                        
                        logger.debug("go inwards")
                        if direction != old_direction and old_direction != "":
                            direction=3
                            logger.debug("Moved too far!")
                            #cancel QT as we moved to far
                            cancel_quantumdrive()
                            logger.debug("...")
                    elif int(New_Distance_to_POI_Total) < 20230000:
                        direction=2
                        logger.debug("go outwards")
                        if direction != old_direction and old_direction != "":
                            logger.debug("...")
                            direction=3
                            logger.debug("Moved too far!")
                            #cancel QT as we moved to far
                            cancel_quantumdrive()
                    
                    if int(New_Distance_to_POI_Total) > 20230000 and int(New_Distance_to_POI_Total) < 20407000:
                        #cancel QT as we are in Band4
                        logger.debug("Band4 arrived!")
                        cancel_quantumdrive()
                        logger.debug("...")

                    else:
                        logger.debug("...")
                        #Calc Distance
                        #---------------------------------------------------Delta Distance to POI-----------------------------------------------------------
                        #get the real old distance between the player and the target
                        Old_Distance_to_POI_Total = vector_norm(Old_Distance_to_POI)                    
                        #get the 3 XYZ distance travelled since last update
                        Delta_Distance_to_POI = {}
                        for i in ["X", "Y", "Z"]:
                            Delta_Distance_to_POI[i] = New_Distance_to_POI[i] - Old_Distance_to_POI[i]
                        #get the real distance travelled since last update
                        Delta_Distance_to_POI_Total = New_Distance_to_POI_Total - Old_Distance_to_POI_Total
                        #---------------------------------------------------Estimated time of arrival to POI------------------------------------------------
                        #get the time between the last update and this update
                        Delta_time = New_time - Old_time
                        #get the time it would take to reach destination using the same speed
                        try :
                            Band4Distance = 20318500 # + - 88500
                            Estimated_time_of_arrival = (Delta_time*New_Distance_to_POI_Total)/abs(Delta_Distance_to_POI_Total - Band4Distance)
                            logger.debug(f"Estimated_time_of_arrival: {str(int(Estimated_time_of_arrival))}")
                        except ZeroDivisionError:
                            Estimated_time_of_arrival = 0.00
                        #prepare history cycle    
                        for i in ["X", "Y", "Z"]:
                            Old_player_Global_coordinates[i] = New_Player_Global_coordinates[i]

                        for i in ["X", "Y", "Z"]:
                            Old_Distance_to_POI[i] = New_Distance_to_POI[i]
                        Old_time = New_time
                        old_direction = direction
                        logger.debug("...")
                        message_time = json.dumps({"event": "setTitle",
                                            "context": halo_button_context,
                                            "payload": {
                                                "title": f"\n\n\n\nETA: {str(int(Estimated_time_of_arrival))} s",
                                                "target": 0,
                                            }
                                        })
                        logger.debug("...")
                        mother.send(message_time)
                        mother.set_state(halo_button_context, direction)
                        logger.debug("done halo loop")
                        #Direction to fly
                        

                if sandcavetour_active == True:
                    logger.debug("Sandcavetour active, current container: " + str(Actual_Container['Name']))
                    if sandcavetour_init_done == False:
                        ContainerName = Actual_Container['Name']
                        logger.debug("...init not done yet")
                        #find all Sancaves in current container
                        Destination_queue = get_sandcaves_sorted(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Database["Containers"][ContainerName])
                        logger.debug("s1")
                        tourlenght = len(Destination_queue)
                        if tourlenght == 0:
                            logger.debug("No sand caves found on current container")
                            message_saved_nok = json.dumps({"event": "showAlert",
                                        "context": sandcavestour_button_context
                                    })
                            mother.ws.send(message_saved_nok)    
                        else:    
                            logger.debug("s2")
                            Destination = Destination_queue[0]
                            if Destination['Distance'] < Destination['nextQTMarkerDistance']:
                                next_hint = "(fly "+str(int(Destination['Distance']))+")"
                            else:
                                next_hint = "(QT "+str(int(Destination['nextQTMarkerDistance'])) +")"
                            logger.debug("Destination set to: " + str(Destination))
                            message_tour = json.dumps({"event": "setTitle",
                                                "context": sandcavestour_button_context,
                                                "payload": {
                                                    "title": linebreak_title("NEXT ("+str(tourlenght)+")" + next_hint + "\n" + str(Destination['Name'])),
                                                    "target": 0,
                                                }
                                            })
                            mother.ws.send(message_tour)
                            logger.debug("s3")
                            sandcavetour_init_done = True
                            logger.debug("Init done")
                    else:
                        logger.debug("Init already done...")
                logger.debug("...")
                if Destination != []: #(sandcavetour_active and sandcavetour_init_done) or not sandcavetour_active:        
                    #---------------------------------------------------New target local coordinates----------------------------------------------------
                    #Grab the rotation speed of the container in the Database and convert it in degrees/s
                    Target = Destination
                    logger.debug("Target set:"+str(Target))
                    #old#logger.debug("Target = " +str(Target))
                    logger.debug("Target Name = " +str(Target["Container"]))
                    #old#logger.debug("Database: "+str(Database))
                    target_Rotation_speed_in_hours_per_rotation = Database["Containers"][Target["Container"]]["Rotation Speed"]
                    logger.debug("rotspeed: " + str(target_Rotation_speed_in_hours_per_rotation))
                    try:
                        target_Rotation_speed_in_degrees_per_second = 0.1 * (1/target_Rotation_speed_in_hours_per_rotation)
                    except ZeroDivisionError:
                        target_Rotation_speed_in_degrees_per_second = 0
                    logger.debug("11")
                    #Get the actual rotation state in degrees using the rotation speed of the container, the actual time and a rotational adjustment value
                    target_Rotation_state_in_degrees = ((target_Rotation_speed_in_degrees_per_second * Time_passed_since_reference_in_seconds) + Database["Containers"][Target["Container"]]["Rotation Adjust"]) % 360
                    logger.debug("12")
                    logger.debug("Rot in degrees: " + str(target_Rotation_state_in_degrees))
                    logger.debug("Target: "+str(Target))
                    #get the new player rotated coordinates
                    target_rotated_coordinates = rotate_point_2D(Target, radians(target_Rotation_state_in_degrees))

                    logger.debug("2")


                    #-------------------------------------------------player local Long Lat Height--------------------------------------------------
                    
                    if Actual_Container['Name'] != "None":
                        player_Latitude, player_Longitude, player_Height = get_lat_long_height(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container)
                    
                    #-------------------------------------------------target local Long Lat Height--------------------------------------------------
                    target_Latitude, target_Longitude, target_Height = get_lat_long_height(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]])

                    logger.debug("3")

                    #---------------------------------------------------Distance to POI-----------------------------------------------------------------
                    New_Distance_to_POI = {}
                    logger.debug("Target Container: "+str(Target["Container"]))
                    logger.debug("Actual Container: "+str(Actual_Container))
                    logger.debug("Destination:" + str(Destination))
                    if Actual_Container["Name"] == Target["Container"]:
                        logger.debug("Actual Container = Target")
                        for i in ["X", "Y", "Z"]:
                            New_Distance_to_POI[i] = abs(Target[i] - New_player_local_rotated_coordinates[i])
                    
                    
                    else:
                        for i in ["X", "Y", "Z"]:
                            New_Distance_to_POI[i] = abs((target_rotated_coordinates[i] + Database["Containers"][Target["Container"]][i]) - New_Player_Global_coordinates[i])
                    logger.debug("4")
                    #get the real new distance between the player and the target
                    New_Distance_to_POI_Total = vector_norm(New_Distance_to_POI)
                    logger.debug("5")
                    if New_Distance_to_POI_Total <= 100:
                        New_Distance_to_POI_Total_color = "#00ff00"
                    elif New_Distance_to_POI_Total <= 1000:
                        New_Distance_to_POI_Total_color = "#ffd000"
                    else :
                        New_Distance_to_POI_Total_color = "#ff3700"

                    logger.debug("6")
                    #---------------------------------------------------Delta Distance to POI-----------------------------------------------------------
                    #get the real old distance between the player and the target
                    Old_Distance_to_POI_Total = vector_norm(Old_Distance_to_POI)
                    logger.debug("7")



                    #get the 3 XYZ distance travelled since last update
                    Delta_Distance_to_POI = {}
                    for i in ["X", "Y", "Z"]:
                        Delta_Distance_to_POI[i] = New_Distance_to_POI[i] - Old_Distance_to_POI[i]
                    logger.debug("8")
                    #get the real distance travelled since last update
                    Delta_Distance_to_POI_Total = New_Distance_to_POI_Total - Old_Distance_to_POI_Total
                    logger.debug("9")
                    if Delta_Distance_to_POI_Total <= 0:
                        Delta_distance_to_poi_color = "#00ff00"
                    else:
                        Delta_distance_to_poi_color = "#ff3700"



                    #---------------------------------------------------Estimated time of arrival to POI------------------------------------------------
                    #get the time between the last update and this update
                    Delta_time = New_time - Old_time
                    logger.debug("10")

                    #get the time it would take to reach destination using the same speed
                    try :
                        Estimated_time_of_arrival = (Delta_time*New_Distance_to_POI_Total)/abs(Delta_Distance_to_POI_Total)
                        logger.debug("11")
                    except ZeroDivisionError:
                        Estimated_time_of_arrival = 0.00



                    #----------------------------------------------------Closest Quantumable POI--------------------------------------------------------
                    if Target["QTMarker"] == "FALSE":
                        logger.debug("11.5")
                        Target_to_POIs_Distances_Sorted = get_closest_POI(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]], True)
                        logger.debug("11.6")
                        logger.debug(str(Target_to_POIs_Distances_Sorted))
                    
                    else :
                        logger.debug("11.7")
                        Target_to_POIs_Distances_Sorted = [{
                            "Name" : "POI itself",
                            "Distance" : 0,
                            "X" : Target["X"],
                            "Y" : Target["Y"],
                            "Z" : Target["Z"]
                        }]
                        logger.debug("11.8")

                    logger.debug("12")
                    #----------------------------------------------------Player Closest POI--------------------------------------------------------
                    Player_to_POIs_Distances_Sorted = get_closest_POI(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container, False)

                    logger.debug("13")
                    #-------------------------------------------------------3 Closest OMs to player---------------------------------------------------------------
                    #player_Closest_OM = get_closest_oms(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container)
                    player_Closest_OM = "n/a"
                    logger.debug("14_disabled")

                    #-------------------------------------------------------3 Closest OMs to target---------------------------------------------------------------
                    #target_Closest_OM = get_closest_oms(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]])
                    target_Closest_OM="n/a"               
                    logger.debug("15_disabled")

                    #----------------------------------------------------Course Deviation to POI--------------------------------------------------------
                    #get the vector between current_pos and previous_pos
                    Previous_current_pos_vector = {}
                    for i in ['X', 'Y', 'Z']:
                        Previous_current_pos_vector[i] = New_player_local_rotated_coordinates[i] - Old_player_local_rotated_coordinates[i]

                    logger.debug("16")
                    #get the vector between current_pos and target_pos
                    Current_target_pos_vector = {}
                    for i in ['X', 'Y', 'Z']:
                        Current_target_pos_vector[i] = Target[i] - New_player_local_rotated_coordinates[i]

                    logger.debug("17")
                    #get the angle between the current-target_pos vector and the previous-current_pos vector
                    Total_deviation_from_target = angle_between_vectors(Previous_current_pos_vector, Current_target_pos_vector)

                    logger.debug("18")
                    if Total_deviation_from_target <= 10:
                        Total_deviation_from_target_color = "#00ff00"
                    elif Total_deviation_from_target <= 20:
                        Total_deviation_from_target_color = "#ffd000"
                    else:
                        Total_deviation_from_target_color = "#ff3700"

                    logger.debug("19")
                    #----------------------------------------------------------Flat_angle--------------------------------------------------------------
                    previous = Old_player_local_rotated_coordinates
                    current = New_player_local_rotated_coordinates


                    #Vector AB (Previous -> Current)
                    previous_to_current = {}
                    for i in ["X", "Y", "Z"]:
                        previous_to_current[i] = current[i] - previous[i]
                    logger.debug("20")
                    #Vector AC (C = center of the planet, Previous -> Center)
                    previous_to_center = {}
                    for i in ["X", "Y", "Z"]:
                        previous_to_center[i] = 0 - previous[i]
                    logger.debug("21")
                    #Vector BD (Current -> Target)
                    current_to_target = {}
                    for i in ["X", "Y", "Z"]:
                        current_to_target[i] = Target[i] - current[i]
                    logger.debug("22")
                        #Vector BC (C = center of the planet, Current -> Center)
                    current_to_center = {}
                    for i in ["X", "Y", "Z"]:
                        current_to_center[i] = 0 - current[i]

                    logger.debug("23")

                    #Normal vector of a plane:
                    #abc : Previous/Current/Center
                    n1 = {}
                    n1["X"] = previous_to_current["Y"] * previous_to_center["Z"] - previous_to_current["Z"] * previous_to_center["Y"]
                    n1["Y"] = previous_to_current["Z"] * previous_to_center["X"] - previous_to_current["X"] * previous_to_center["Z"]
                    n1["Z"] = previous_to_current["X"] * previous_to_center["Y"] - previous_to_current["Y"] * previous_to_center["X"]
                    logger.debug("24")
                    #acd : Previous/Center/Target
                    n2 = {}
                    n2["X"] = current_to_target["Y"] * current_to_center["Z"] - current_to_target["Z"] * current_to_center["Y"]
                    n2["Y"] = current_to_target["Z"] * current_to_center["X"] - current_to_target["X"] * current_to_center["Z"]
                    n2["Z"] = current_to_target["X"] * current_to_center["Y"] - current_to_target["Y"] * current_to_center["X"]
                    logger.debug("25")
                    Flat_angle = angle_between_vectors(n1, n2)
                    logger.debug("26")

                    if Flat_angle <= 10:
                        Flat_angle_color = "#00ff00"
                    elif Flat_angle <= 20:
                        Flat_angle_color = "#ffd000"
                    else:
                        Flat_angle_color = "#ff3700"
                        
                    logger.debug("1:"+str(Target["X"]))
                    logger.debug("2:"+str(Target["Y"]))
                    logger.debug("3:"+str(Target["Z"]))
                    logger.debug("4:"+str(target_Latitude))
                    logger.debug("5:"+str(target_Longitude))
                    logger.debug("6:"+str(target_Height))
                    logger.debug("4:"+str(player_Latitude))
                    logger.debug("5:"+str(player_Longitude))
                    logger.debug("6:"+str(player_Height))




                    #----------------------------------------------------------Heading--------------------------------------------------------------
                    
                    bearingX = cos(radians(target_Latitude)) * sin(radians(target_Longitude) - radians(player_Longitude))
                    bearingY = cos(radians(player_Latitude)) * sin(radians(target_Latitude)) - sin(radians(player_Latitude)) * cos(radians(target_Latitude)) * cos(radians(target_Longitude) - radians(player_Longitude))
                    if northpole_is_om3:
                        logger.debug("om3 as northbpole bearing")
                        Bearing = 360 - ((degrees(atan2(bearingX, bearingY)) + 360) % 360)
                    else:
                        Bearing = (degrees(atan2(bearingX, bearingY)) + 360) % 360

                    


                    logger.debug("28_1")
                    #----------------------------------------------------------CamDir-------------------------
                    CamDirYaw, CamDirPitch, CamDirRoll = calc_eulerangels_planet(Time_passed_since_reference_in_seconds, knownPlayerX,knownPlayerY,knownPlayerZ,Target["X"],Target["Y"],Target["Z"],Actual_Container)
                    logger.debug("Pitch_final: " +str(CamDirPitch))
                    logger.debug("Yaw_final: " +str(CamDirYaw))


                    #old#logger.debug("7:"+str(Database["Containers"][Target["Container"]]))
                    logger.debug("8:"+str(Database["Containers"]["Stanton"]))
                    logger.debug("9:"+str(Time_passed_since_reference_in_seconds))


                    #-------------------------------------------------Sunrise Sunset Calculation----------------------------------------------------
                    player_state_of_the_day, player_next_event, player_next_event_time = get_sunset_sunrise_predictions(
                        New_player_local_rotated_coordinates["X"], 
                        New_player_local_rotated_coordinates["Y"], 
                        New_player_local_rotated_coordinates["Z"], 
                        player_Latitude, 
                        player_Longitude, 
                        player_Height, 
                        Actual_Container, 
                        Database["Containers"]["Stanton"],
                        Time_passed_since_reference_in_seconds
                    )
                    logger.debug("28")                
                    target_state_of_the_day, target_next_event, target_next_event_time = get_sunset_sunrise_predictions(
                        Target["X"], 
                        Target["Y"], 
                        Target["Z"], 
                        target_Latitude, 
                        target_Longitude, 
                        target_Height, 
                        Database["Containers"][Target["Container"]], 
                        Database["Containers"]["Stanton"],
                        Time_passed_since_reference_in_seconds
                    )

                    logger.debug("29")
                    #------------------------------------------------------------Backend to Frontend------------------------------------------------------------
                    try:
                        new_data = {
                            "updated" : f"{time.strftime('%H:%M:%S', time.localtime(time.time()))}",
                            "target" : Target['Name'],
                            "player_actual_container" : Actual_Container['Name'],
                            "target_container" : Target['Container'],
                            "player_x" : round(New_player_local_rotated_coordinates['X'], 3),
                            "player_y" : round(New_player_local_rotated_coordinates['Y'], 3),
                            "player_z" : round(New_player_local_rotated_coordinates['Z'], 3),
                            "player_long" : f"{round(player_Longitude, 2)}°",
                            "player_lat" : f"{round(player_Latitude, 2)}°",
                            "player_height" : f"{round(player_Height, 1)} km",
                            #"player_OM1" : f"{player_Closest_OM['Z']['OM']['Name']} : {round(player_Closest_OM['Z']['Distance'], 3)} km",
                            #"player_OM2" : f"{player_Closest_OM['Y']['OM']['Name']} : {round(player_Closest_OM['Y']['Distance'], 3)} km",
                            #"player_OM3" : f"{player_Closest_OM['X']['OM']['Name']} : {round(player_Closest_OM['X']['Distance'], 3)} km",
                            "player_closest_poi" : f"{Player_to_POIs_Distances_Sorted[0]['Name']} : {round(Player_to_POIs_Distances_Sorted[0]['Distance'], 3)} km",
                            "player_state_of_the_day" : f"{player_state_of_the_day}", 
                            "player_next_event" : f"{player_next_event}", 
                            "player_next_event_time" : f"{time.strftime('%H:%M:%S', time.localtime(New_time + player_next_event_time*60))}",
                            "target_x" : Target["X"],
                            "target_y" : Target["Y"],
                            "target_z" : Target["Z"],
                            "target_long" : f"{round(target_Longitude, 2)}°",
                            "target_lat" : f"{round(target_Latitude, 2)}°",
                            "target_height" : f"{round(target_Height, 1)} km",
                            #"target_OM1" : f"{target_Closest_OM['Z']['OM']['Name']} : {round(target_Closest_OM['Z']['Distance'], 3)} km",
                            #"target_OM2" : f"{target_Closest_OM['Y']['OM']['Name']} : {round(target_Closest_OM['Y']['Distance'], 3)} km",
                            #"target_OM3" : f"{target_Closest_OM['X']['OM']['Name']} : {round(target_Closest_OM['X']['Distance'], 3)} km",
                            "target_closest_QT_beacon" : f"{Target_to_POIs_Distances_Sorted[0]['Name']} : {round(Target_to_POIs_Distances_Sorted[0]['Distance'], 3)} km",
                            "target_state_of_the_day" : f"{target_state_of_the_day}", 
                            "target_next_event" : f"{target_next_event}", 
                            "target_next_event_time" : f"{time.strftime('%H:%M:%S', time.localtime(New_time + target_next_event_time*60))}",
                            "distance_to_poi" : f"{round(New_Distance_to_POI_Total, 3)} km",
                            "distance_to_poi_color" : New_Distance_to_POI_Total_color,
                            "delta_distance_to_poi" : f"{round(abs(Delta_Distance_to_POI_Total), 3)} km",
                            "delta_distance_to_poi_color" : Delta_distance_to_poi_color,
                            "total_deviation" : f"{round(Total_deviation_from_target, 1)}°",
                            "total_deviation_color" : Total_deviation_from_target_color,
                            "horizontal_deviation" : f"{round(Flat_angle, 1)}°",
                            "horizontal_deviation_color" : Flat_angle_color,
                            "heading" : f"{round(Bearing, 1)}°",
                            "ETA" : f"{str(datetime.timedelta(seconds=round(Estimated_time_of_arrival, 0)))}"
                        }
                    except Exception as e:
                        logger.debug("error: "+str(e)
                                    )
                    logger.debug("30")
                    logger.debug(f"{round(Bearing, 0)}°")
                    logger.debug(f"{round(New_Distance_to_POI_Total, 1)} km")
                    
                    logger.debug("xyz qtmarker: " + str(Target_to_POIs_Distances_Sorted[0]))
                    logger.debug(Target_to_POIs_Distances_Sorted[0]["X"])
                    logger.debug(Target_to_POIs_Distances_Sorted[0]["Y"])
                    logger.debug(Target_to_POIs_Distances_Sorted[0]["Z"])
                    logger.debug(Actual_Container)
                    qtmarker_Latitude, qtmarker_Longitude, qtmarker_Height = get_lat_long_height(Target_to_POIs_Distances_Sorted[0]["X"], Target_to_POIs_Distances_Sorted[0]["Y"], Target_to_POIs_Distances_Sorted[0]["Z"], Actual_Container)
                    logger.debug("30_1")
                    bearingX_qtmarker = cos(radians(target_Latitude)) * sin(radians(target_Longitude) - radians(qtmarker_Longitude))
                    logger.debug("30_2")
                    bearingY_qtmarker = cos(radians(qtmarker_Latitude)) * sin(radians(target_Latitude)) - sin(radians(qtmarker_Latitude)) * cos(radians(target_Latitude)) * cos(radians(target_Longitude) - radians(qtmarker_Longitude))
                    logger.debug("30_3")
                    Bearing_qtmaker = (degrees(atan2(bearingX_qtmarker, bearingY_qtmarker)) + 360) % 360
                    logger.debug("30_4")
                    message_bearing = json.dumps({"event": "setTitle",
                                            "context": bearing_button_context,
                                            "payload": {
                                                "title": f"HEADING\n{round(Bearing, 0)}°\n{round(New_Distance_to_POI_Total, 1)} km",
                                                "target": 0,
                                            }
                                        })
                    logger.debug("31")
                    #old#logger.debug("31.1:"+str(Target_to_POIs_Distances_Sorted))
                    #old#logger.debug("31.2:"+str(Target_to_POIs_Distances_Sorted[0]['Distance']))
                    if Target_to_POIs_Distances_Sorted:
                        next_poi_name = Target_to_POIs_Distances_Sorted[0]['Name']
                        next_poi_distance = Target_to_POIs_Distances_Sorted[0]['Distance']
                    else:
                        next_poi_name = "n/a"
                        next_poi_distance = 0
                    
                    #CamDirPitch, CamDirYaw, CamDirRoll
                    message_camdir = json.dumps({"event": "setTitle",
                                            "context": camdir_button_context,
                                            "payload": {
                                                "title": "CamDir:\n" + f"{round(CamDirPitch,0)}\n{round(CamDirRoll,0)}\n{round(CamDirYaw,0)}",
                                                "target": 0,
                                            }
                                        })   
                    message_oms = json.dumps({"event": "setTitle",
                                            "context": oms_button_context,
                                            "payload": {
                                                "title": get_om_distances(),
                                                "target": 0,
                                            }
                                        })   
                    message_nearest = json.dumps({"event": "setTitle",
                                            "context": nearest_button_context,
                                            "payload": {
                                                "title": "NEXT\n" + linebreak_title(next_poi_name) + f"\n{round(next_poi_distance, 1)} km\n{round(Bearing_qtmaker, 0)}°",
                                                "target": 0,
                                            }
                                        })
                    logger.debug("32")
                    message_daytime = json.dumps({"event": "setTitle",
                                            "context": daytime_button_context,
                                            "payload": {
                                                "title": f"Target:\n{target_next_event}:\n{time.strftime('%H:%M:%S', time.localtime(New_time + target_next_event_time*60))}",
                                                "target": 0,
                                            }
                                        })
                    logger.debug("32.5")
                    if daytime_toggle == "player":
                        message_daytime = json.dumps({"event": "setTitle",
                                                "context": daytime_button_context,
                                                "payload": {
                                                    "title": f"Player:\n{player_next_event}:\n{time.strftime('%H:%M:%S', time.localtime(New_time + player_next_event_time*60))}",
                                                    "target": 0,
                                                }
                                            })    
                    logger.debug("33")
                    message_around = json.dumps({"event": "setTitle",
                                            "context": around_button_context,
                                            "payload": {
                                                "title": "AROUND\n" + linebreak_title(Player_to_POIs_Distances_Sorted[0]['Name']) + f"\n{round(Player_to_POIs_Distances_Sorted[0]['Distance'], 1)} km",
                                                "target": 0,
                                            }
                                        })
                    logger.debug("34")
                    message_coords = json.dumps({"event": "setTitle",
                                            "context": coords_button_context,
                                            "payload": {
                                                "title": "COORDS\nX: " + str(round(New_player_local_rotated_coordinates['X'], 3)) + "\nY: " + str(round(New_player_local_rotated_coordinates['Y'], 3)) + "\nZ: " + str(round(New_player_local_rotated_coordinates['Z'], 3)),
                                                "target": 0,
                                            }
                                        })
                    logger.debug("35")
                    #speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    #speaker.Speak(str(round(Bearing, 0))+" Degree and "+str(round(New_Distance_to_POI_Total, 1))+"Kilometer to go")
                    mother.ws.send(message_oms)
                    mother.send(message_oms)
                    mother.ws.send(message_bearing)
                    logger.debug("send bearing: " + message_bearing)
                    mother.ws.send(message_nearest)
                    logger.debug("send nearest: " + message_nearest)
                    mother.ws.send(message_daytime)
                    logger.debug("send daytime: " + message_daytime)
                    mother.ws.send(message_around)
                    logger.debug("send around: " + message_around)
                    mother.ws.send(message_coords)
                    logger.debug("send coords: " + message_coords)
                    mother.ws.send(message_camdir)
                    logger.debug("send camdir: " + message_camdir)

                    #subprocess.run(['python', 'process_displayinfo.py',int(CamDirPitch),int(CamDirRoll),int(CamDirYaw)])
                    #old#logger.debug("mother:")
                    #old#logger.debug(mother)
                    #queue.put(message_bearing)
                    #mother.event_generate("<<check_queue>>")
                    
    
                    #old#logger.debug("send data: " + message)
                    
                    if calibrate_active:
                        logger.debug("Calculating calibration...")
                        logger.debug("OM Radius, später *2 *pi: " + str(Database["Containers"][Actual_Container['Name']]["OM Radius"]))
                        #Logic taken from Jericho Tool (c) Graupunkt
                        Circumference360Degrees = pi * 2 * float(Database["Containers"][Actual_Container['Name']]["OM Radius"]) * 1000
                        logger.debug("Circumference360Degrees: "+str(Circumference360Degrees))
                        #Very high or low values are presented by ps as scientific results, therefore we force the nubmer (decimal) and limit it to 7 digits after comma
                        #Multiplied by 1000 to convert km into m and invert it to correct the deviation
                        RotationSpeedAdjustment = round((New_player_local_rotated_coordinates['X'] * 1000 * 360 / Circumference360Degrees),7) * -1
                        logger.debug("New player local rotatet x: "+ str(New_player_local_rotated_coordinates['X']) + " RotationsSpeedAdjustment: "+str(RotationSpeedAdjustment))
                        #GET Adjustment for Rotationspeed 
                        FinalRotationAdjustment = Database["Containers"][Target["Container"]]["Rotation Adjust"] + RotationSpeedAdjustment #-replace(",",".")
                        logger.debug("FinalRotationAdjustment: "+str(FinalRotationAdjustment))
                        #WRITE CHANGES TO OBJECT CONTAINER
                        #(Get-Content $OcCsvPath).replace(($CurrentDetectedOCADX -replace(",",".")), $FinalRotationAdjustment) | Set-Content $OcCsvPath
                        calmessage="Rotation for "+str(Actual_Container['Name'])+" calibrated from "+str(Database["Containers"][Target["Container"]]["Rotation Adjust"])+"° to "+str(FinalRotationAdjustment)+"° by "+str(RotationSpeedAdjustment)+". Please replace the value manually in the Database.json"
                        logger.debug(calmessage)
                        with open("calibrationdata.txt", "a") as myfile:
                                myfile.write(str(Actual_Container['Name']) + ": "+str(FinalRotationAdjustment))
                                myfile.write("\n")
                                myfile.write(calmessage)
                                myfile.write("\n")
                                
                    if save_triggered == True:
                        save_triggered = False
                        #old#logger.debug("Saving Location to file...")
                        timestamp=datetime.datetime.utcnow()
                        poi_name=str(Actual_Container['Name']) + "_" + str(int(Player_to_POIs_Distances_Sorted[0]['Distance'])) + "km_next_to_" + str(Player_to_POIs_Distances_Sorted[0]['Name']) + "_" + str(timestamp)
                        #old#logger.debug(poi_name)
                        save_data = Actual_Container['Name'] + "," + str(round(New_player_local_rotated_coordinates['X'], 3)) + "," + str(round(New_player_local_rotated_coordinates['Y'], 3)) + "," + str(round(New_player_local_rotated_coordinates['Z'], 3)) + "," + poi_name.replace(" ","_").replace(":","_").replace(".","_")
                        #old#logger.debug(save_data)
                        with open("saved_pois.txt", "a") as sfile:
                                sfile.write(save_data)
                                sfile.write("\n")
                        message_saved_ok = json.dumps({"event": "showOk",
                                            "context": save_button_context
                                        })
                        mother.ws.send(message_saved_ok)       

                    #---------------------------------------------------Update coordinates for the next update------------------------------------------
                    for i in ["X", "Y", "Z"]:
                        Old_player_Global_coordinates[i] = New_Player_Global_coordinates[i]

                    for i in ["X", "Y", "Z"]:
                        Old_player_local_rotated_coordinates[i] = New_player_local_rotated_coordinates[i]

                    for i in ["X", "Y", "Z"]:
                        Old_Distance_to_POI[i] = New_Distance_to_POI[i]

                    Old_time = New_time

                    #-------------------------------------------------------------------------------------------------------------------------------------------
                    #winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
                else:
                    logger.debug("Destination was empty, but ok if Halo active.")
                
NaviThread=threading.Thread(target=watch_clipboard,args=(queue,))



def get_script_path():
            return os.path.dirname(os.path.realpath(sys.argv[0]))

def preload_poi_data():
    global Database,Container_list,Space_POI_list,Planetary_POI_list,preloaded,mother,pi_context,startnavitosavedpoi_button_context,datasource
    logger.debug("Entered preload")
    if datasource == "local":
        try:
            with open(get_script_path() + '\Database.json') as f:
                Database = json.load(f)

            for i in Database["Containers"]:
                Container_list.append(Database["Containers"][i]["Name"])

            for poi in Database["Space_POI"]:
                Space_POI_list.append(poi)

            for container_name in Database["Containers"]:
                Planetary_POI_list[container_name] = []
                for poi in Database["Containers"][container_name]["POI"]:
                    Planetary_POI_list[container_name].append(poi)
            preloaded = True
            logger.debug(f"Preloaded TRUE")
            #old#logger.debug(str(Database))
            #old#logger.debug(str(Container_list))
        except:
            logger.debug(f"Database.json not found.")
                
    if datasource == "starmap":
        try:
            logger.debug("starmap.space as datasource...")
            url = "https://starmap.space/api/v2/oc/index.php?system=Stanton"
            response = requests.get(url)
            ##old#logger.debug("Response: " + str(response.status_code))
            if response.status_code == 200:  # Erfolgreiche Anfrage
                logger.debug(str(response.text))
                #cleanresponse = re.findall('[{.*}]', response.text)
                data = response.json()  # JSON-Daten aus der Antwort extrahieren
                # Mit den erhaltenen Daten arbeiten
                #old#logger.debug("data:" + str(data))
                logger.debug('00')
                tdata=str(data).replace("\'","\"").replace("None","0")
                counter = 0
                new_tdata = ""
                for letter in tdata:
                    counter = counter + 1
                    if letter == "{":
                        letter = "\"oc_" + str(counter) + "\":{"
                    new_tdata = new_tdata + letter
                tdata=new_tdata.replace("[","{\"Containers\":{").replace("]","}}").replace("Stanton Star","Stanton")
                logger.debug('01')
                #old#logger.debug(str(tdata))
                tmpdata = json.loads(tdata) #lets convert to internal layout
                #tmpdata=data
                logger.debug('0')
                logger.debug(str(tmpdata))
                for container_name in tmpdata['Containers']:
                    logger.debug(container_name)
                    tmpdata['Containers'][container_name]['Name'] = tmpdata['Containers'][container_name].pop('ObjectContainer')
                    tmpdata['Containers'][container_name]["X"] = tmpdata['Containers'][container_name].pop("XCoord")
                    tmpdata['Containers'][container_name]["X"] = tmpdata['Containers'][container_name]["X"] * 0.001
                    tmpdata['Containers'][container_name]["Y"] = tmpdata['Containers'][container_name].pop("YCoord")
                    tmpdata['Containers'][container_name]["Y"] = tmpdata['Containers'][container_name]["Y"] * 0.001
                    tmpdata['Containers'][container_name]["Z"] = tmpdata['Containers'][container_name].pop("ZCoord")
                    tmpdata['Containers'][container_name]["Z"] = tmpdata['Containers'][container_name]["Z"] * 0.001
                    tmpdata['Containers'][container_name]["Rotation Speed"] = tmpdata['Containers'][container_name].pop("RotationSpeedX")
                    tmpdata['Containers'][container_name]["Rotation Adjust"] = tmpdata['Containers'][container_name].pop("RotationAdjustmentX")
                    tmpdata['Containers'][container_name]["OM Radius"] = tmpdata['Containers'][container_name].pop("OrbitalMarkerRadius") # * 0.001 rechnen
                    tmpdata['Containers'][container_name]["OM Radius"] = tmpdata['Containers'][container_name]["OM Radius"] * 0.001
                    tmpdata['Containers'][container_name]["Body Radius"] = tmpdata['Containers'][container_name].pop("BodyRadius") # * 0.001 rechnen
                    tmpdata['Containers'][container_name]["Body Radius"] = tmpdata['Containers'][container_name]["Body Radius"] * 0.001
                    #RotQuatW': 1, 'RotQuatX': 0, 'RotQuatY': 0, 'RotQuatZ'
                    tmpdata['Containers'][container_name]["qw"] = tmpdata['Containers'][container_name].pop("RotQuatW")
                    tmpdata['Containers'][container_name]["qx"] = tmpdata['Containers'][container_name].pop("RotQuatX")
                    tmpdata['Containers'][container_name]["qy"] = tmpdata['Containers'][container_name].pop("RotQuatY")
                    tmpdata['Containers'][container_name]["qz"] = tmpdata['Containers'][container_name].pop("RotQuatZ")
                    tmpdata['Containers'][container_name]['POI'] = {}
                logger.debug(tmpdata['Containers'])
                
                modified_data = {v['Name']: v for k, v in tmpdata['Containers'].items()}
                logger.debug(modified_data)
                tmpdata['Containers'] = modified_data
                
                #for old_container_name in tmpdata['Containers']:
                    
                #    if old_container_name.startswith("oc_"): 
                #        new_name = tmpdata['Containers'][old_container_name]['Name']
                #        logger.debug("old : "+ str(old_container_name) + " - new_name: " + str(new_name))
                #        tmpdata['Containers'][new_name] = tmpdata['Containers'].pop(old_container_name)
                
                
                logger.debug('1_')
                #old#logger.debug(str(tmpdata))
                #old#logger.debug('2')
                #data = json.loads(str(tmpdata))
                #old#logger.debug('3')
                #old#logger.debug(str(data))
                #old#logger.debug('4')
                #Aufbau: Database->Containers->abc->Name:abc
                Database = tmpdata
                #old#logger.debug(str(Database["Containers"]))
                for i in Database["Containers"]:
                    logger.debug(i)
                    Container_list.append(Database["Containers"][i]["Name"])
                #old#logger.debug(str(Container_list))    
               
            else:
                logger.debug("Fehler beim Abrufen der Daten. Statuscode:", response.status_code)
            
            logger.debug("getting POIs for merge from starmap...")
            url = "https://starmap.space/api/v2/pois"
            response = requests.get(url)
            if response.status_code == 200:  # Erfolgreiche Anfrage
                data = response.json()  # JSON-Daten aus der Antwort extrahieren
                #old#logger.debug("0")
                tdata=str(data).replace("\'s ","s ").replace("\'s\"","s\"").replace("\'","\"").replace("None","0")
                #old#logger.debug("tdata: "+str(tdata))
                #old#logger.debug("00")
                #old#logger.debug(tdata[3105:3115])

                tmpdata = json.loads(tdata) #lets convert to internal layout
                #old#logger.debug("tmpdata: " + str(tmpdata))
                
                

                for entry in tmpdata:
                    logger.debug(str(entry))
                    if entry['System'] == "Stanton":
                        entry['Name'] = entry.pop('PoiName')
                        #old#logger.debug(entry['Name'])
                        entry['Container'] = entry.pop('Planet')
                        #old#logger.debug("1")
                        entry['X'] = entry.pop('XCoord')
                        #old#logger.debug("1")
                        entry['Y'] = entry.pop('YCoord')
                        #old#logger.debug("1")
                        entry['Z'] = entry.pop('ZCoord')
                        #old#logger.debug("1")
                        if entry['QTMarker'] == 1:
                            entry['QTMarker'] = "TRUE"
                        else:
                            entry['QTMarker'] = "FALSE" 
                        #old#logger.debug("done entry")
                        
                        if entry['Container'] != "" and entry['Container'] in Container_list:
                            Database['Containers'][entry['Container']]['POI'][entry['Name']] = entry
                        else:
                            logger.debug("Also not added: " + str(entry))
                    else:
                        logger.debug("entry not added as not Stanton System: " + str(entry))    
                
                #old#logger.debug("Database: "+str(Database['Containers'])) 
                #add OM Markerss
                #for planet in Database['Containers']:
                #    logger.debug("adding om marker for: " + str(planet['Name']))
                #    oms={"OM-1": {
                #            "Name": "OM-1",
                #            "Container": planet['Name'],
                #            "X": 0.0,
                #            "Y": 0.0,
                #            "Z": float(Database['Containers'][planet['Name']]['OM Radius']),
                #            "qw": 0.0,
                #            "qx": 0.0,
                #            "qy": 0.0,
                #            "qz": 0.0,
                #            "QTMarker": "TRUE"
                #        }}
                #    logger.debug(str(oms))
                #    Database['Containers'][planet['Name']]['POI'].append(oms)
                   #Database['Containers'][container_name]["OM Radius"] 
                #old#logger.debug("tmpdata_after convert: " + str(tmpdata))
                
            #old#logger.debug("Database: "+str(Database))    
                
            preloaded = True
            
        except Exception as e:
            logger.debug("Starmap Datasource error: " + str(e))    
        


logger.debug("Going for preload...")
preload_poi_data()


def open_verseguideinfo(X:float, Y:float, Z:float, Containername):
    logger.debug("Verseguide info ...")
    logger.debug("received: "+ str(Containername) +", " + str(X)+", " + str(Y)+", " + str(Z))
    #Wala, -42.545, 279.059, 19.438
    #-42.55,279.06,19.44,Samson & Son's Salvage Center,https://verseguide.com/location/STANTON/3B/779syls06EI6X3THjEEJJoH6k5mQqk8sKlLrLkRFONdvd2UQIcJqVlURWIFtv588TLk8vlQ9TI5INaSqvoOYlIdW3,Wala

    with open("table.txt", "r") as file:
        for line in file:
            values = line.strip().split(",") 

            if ( abs(float(X) - float(values[0])) <= 0.5) and  ( abs(float(Y) - float(values[1])) <= 0.5) and ( abs(float(Z) - float(values[2])) <= 0.5) and (Containername == values[5]):
                logger.debug("Longpress verseguide: " + str(line.strip()))
                webbrowser.open(str(values[4])) 
                break
            else:
                logger.debug("Longpress, but no match: "+str(values[0]) + ","+str(values[1]) + ","+str(values[2]) + ","+str(values[5]) )    
        
    
    
def reset_buttons():
    global mother,bearing_button_context,nearest_button_context,daytime_button_context,coords_button_context,oms_button_context,camdir_button_context
    message_camdir = json.dumps({"event": "setTitle",
                                        "context": camdir_button_context,
                                        "payload": {
                                            "title": f"Camdir:\n---\n---\n---",
                                            "target": 0,
                                        }
                                    })
    message_bearing = json.dumps({"event": "setTitle",
                                        "context": bearing_button_context,
                                        "payload": {
                                            "title": f"HEADING\n---°\n--- km",
                                            "target": 0,
                                        }
                                    })
    message_nearest = json.dumps({"event": "setTitle",
                            "context": nearest_button_context,
                            "payload": {
                                "title": "NEXT\n---\n--- km",
                                "target": 0,
                            }
                        })
    message_daytime = json.dumps({"event": "setTitle",
                            "context": daytime_button_context,
                            "payload": {
                                "title": "Day/Night\n--:--:--",
                                "target": 0,
                            }
                        })
    message_coords = json.dumps({"event": "setTitle",
                            "context": coords_button_context,
                            "payload": {
                                "title": "COORDS\n---",
                                "target": 0,
                            }
                        })
    message_oms = json.dumps({"event": "setTitle",
                                        "context": oms_button_context,
                                        "payload": {
                                            "title": "OM1: ---\nOM2: ---\nOM3: ---\nOM4: ---\nOM5: ---\nOM6: ---",
                                            "target": 0,
                                        }
                                    })
    mother.ws.send(message_bearing)
    
    mother.ws.send(message_nearest)
    
    mother.ws.send(message_daytime)
    
    mother.ws.send(message_coords)
    
    mother.ws.send(message_oms)

    mother.ws.send(message_camdir)

       

class StartNavi(Action):
    UUID = "com.doabigcheese.scnav.startnavi"
    global watch_clipboard_active,preloaded,mother,message_pois


    def on_key_up(self, obj: events_received_objs.KeyUp):
        global Destination, Database,CoordinateTimeoutThread,stop_coordinatetimeout
        CoordinateTimeoutThread=threading.Thread(target=coordinatetimeout) #Prepare a new thread
        stop_coordinatetimeout = False
        CoordinateTimeoutThread.start()
        current_container = Destination["Container"]
        #old#logger.debug(str(Database["Containers"][current_container]))
        
        body_radius = Database["Containers"][current_container]["Body Radius"] * 1000
        x = Database["Containers"][current_container]["X"] * 1000 +body_radius/2 + 50
        y = Database["Containers"][current_container]["Y"] * 1000 +body_radius/2 +50
        z = Database["Containers"][current_container]["Z"] * 1000 + body_radius/2 + 10
        # For Debuggin, generate kind of random Coordinates

        #pyperclip.copy("Coordinates: x:12792704755.989153 y:-74801598.619366 z:50267." + str(random.randint(0,50))) #Magda
        #pyperclip.copy("Coordinates: x:-18930612193.865963 y:-2609992498.331003 z:-232631." + str(random.randint(0,50))) #Daymar
        #pyperclip.copy("Coordinates: x:-18930612188.865963 y:-2609992608.331003 z:-232124." + str(random.randint(0,50))) #Daymar nähe Sandcave 2.1
        #pyperclip.copy("Coordinates: x:12850214070.308863 y:5692.311180 z:1243548." + str(random.randint(0,50))) #Hurston
        coordinaten="Coordinates: x:"+str(x)+" y:"+str(y)+" z:"+str(z)+ str(random.randint(0,50))
        pyperclip.copy(coordinaten)
        logger.debug("Sending to clipboard: "+ coordinaten)
        mother=self
        if(message_pois != ""):
            logger.debug("Sending: " + str(message_pois))
            mother.ws.send(message_pois)

class Calibrate(Action):
    UUID = "com.doabigcheese.scnav.calibrate"

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global preloaded,mother,NaviThread,calibrate_active,watch_clipboard_active,stop_navithread,datasource
        datasource = "local"
        preloaded = False
        preload_poi_data()
        if watch_clipboard_active == False:
            mother=self
            calibrate_active = True
            NaviThread.start()
            self.set_state(obj.context, 1)
        else:
            stop_navithread = True
            NaviThread.join()
            stop_navithread = False
            calibrate_active = False
            NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            self.set_state(obj.context, 0)
            
                    

class CamDir(Action):
    UUID = "com.doabigcheese.scnav.camdir"  
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global camdir_button_context
        camdir_button_context = obj.context

class OMs(Action):
    UUID = "com.doabigcheese.scnav.oms"  
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global oms_button_context
        oms_button_context = obj.context
                 
class Bearing(Action):
    UUID = "com.doabigcheese.scnav.bearing"
    
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global bearing_button_context
        bearing_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass
        
 
class Nearest(Action):
    UUID = "com.doabigcheese.scnav.nearest"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global nearest_button_context
        nearest_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass 
        #global nearest_button_context
        #old#logger.debug(f"self: " + str(self))
        
        #self.set_title(nearest_button_context,
        #        events_sent_objs.SetTitlePayload(
        #            title="nearest:\nMining Area 141\n(15 km)",
        #            target=0 #sw and hw
        #        )
        #    )   
        
class Daytime(Action):
    UUID = "com.doabigcheese.scnav.daytime"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global daytime_button_context
        daytime_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):   
        global daytime_toggle
        
        if daytime_toggle == "target":
            daytime_toggle = "player"
            
        else:
            daytime_toggle = "target"
        self.show_ok(obj.context) 

class Coords(Action):
    UUID = "com.doabigcheese.scnav.coords"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global coords_button_context
        coords_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):   
        pass 
    
class Around(Action):
    UUID = "com.doabigcheese.scnav.around"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global around_button_context
        around_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass        

class UpdateCurrentLocation(Action):
    UUID = "com.doabigcheese.scnav.updatecurrentlocation"
    def on_key_down(self, obj: events_received_objs.KeyDown):
        pass

    def on_key_up(self, obj: events_received_objs.KeyUp):
        
        #old#logger.debug(f"Update pressed.")
        updatecoordinates()
            
class SaveLocation(Action):
    UUID = "com.doabigcheese.scnav.save"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #old#logger.debug(f"willapear_debug: " + str(obj.context))
        global save_button_context
        save_button_context = obj.context

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global mother
        mother=self
        #old#logger.debug(f"Save pressed.")
        save_poi()        

class StartNaviToSavedPOI(Action):
    UUID = "com.doabigcheese.scnav.savedpoi"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        logger.debug(f"SAVEDPOI willapear_debug: " + str(obj.context))
        
        global message_pois,Database,Container_list,Space_POI_list,Planetary_POI_list,preloaded,mother,pi_context,startnavitosavedpoi_button_context
        startnavitosavedpoi_button_context = obj.context
        mother=self
        mother.bind("<<check_queue>>",check_queue)
        if preloaded == False:
            preload_poi_data()
        try:
            with open('saved_pois.txt') as g:
                custom = 1
                saved_payload = []
                logger.debug(f"saved_pois loading entered....")
                for line in g:
                    inhalt = line.split(",")
                    tmp_container=inhalt[0]
                    tmp_x=float(inhalt[1])
                    tmp_y=float(inhalt[2])
                    tmp_z=float(inhalt[3])
                    try:
                        pre_name=inhalt[4]
                        mapping = dict.fromkeys(range(32)) #remove unwanted control characters
                        tmp_name = pre_name.translate(mapping)
                    except:
                        tmp_name = "Custom_" + str(custom)
                    
                    #{'Name': 'Security Post Prashad', 'Container': 'Daymar', 'X': -223.514, 'Y': 65.899, 'Z': 181.092, 'qw': 0.0, 'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'QTMarker': 'TRUE'}
                    tmp_poi={'Name': tmp_name, 'Container': tmp_container, 'X': tmp_x, 'Y': tmp_y, 'Z': tmp_z, 'qw': 0.0, 'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'QTMarker': 'FALSE'}
                    #Database["Containers"][tmp_container]["POI"][tmp_name]=tmp_poi
                    #Planetary_POI_list[tmp_container].append(tmp_name)
                    saved_payload.append(tmp_poi)
                    logger.debug("Added from saved_POIs: " + tmp_name)
                    
                    custom = custom + 1  
        except:
            logger.debug("No saved_pois.txt found or some error happened.")            
        
        
        logger.debug("json: " + str(saved_payload))
        try:
            message_pois = json.dumps({"event": "sendToPropertyInspector",
                        "context": startnavitosavedpoi_button_context,
                        "payload":  str(saved_payload)
                        
                    })
            logger.debug("message_pois: "+ str(message_pois))
            mother.ws.send(message_pois)
                    
                    
        except Exception as e:
            logger.debug("sendToPropertyInspector error happened: " + str(e) )
            
    def on_property_inspector_did_appear(self, obj:events_received_objs.PropertyInspectorDidAppear):
        #return super().on_property_inspector_did_appear(obj)   
        mother.ws.send(message_pois)
        logger.debug("Sent saved message_POIs")     
            
    def on_key_up(self, obj: events_received_objs.KeyUp):
        global Destination,Database,preloaded,NaviThread,watch_clipboard_active,stop_navithread,mother
        if preloaded == False:
            preload_poi_data()
        container = obj.payload.settings.get("container")
        x = float(obj.payload.settings.get("x"))
        y = float(obj.payload.settings.get("y"))
        z = float(obj.payload.settings.get("z"))
        

        #old#logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
        Destination = {
                'Name': 'Custom POI', 
                'Container': container,
                'X': x, 
                'Y': y, 
                'Z': z, 
                "QTMarker": "FALSE"
            }
        logger.debug("Destination set: " + str(Destination))
        if watch_clipboard_active == False:
            mother=self
            NaviThread.start()
            self.set_state(obj.context, 1)

        else:
            stop_navithread = True
            NaviThread.join()
            stop_navithread = False
            NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            #NaviThread.start()
            self.set_state(obj.context, 0)
            #old#logger.debug(f"...and restarted")
        

            
class StartNaviToKnownPOI(Action):
    UUID = "com.doabigcheese.scnav.poi"
    
    #detect longpress
    #https://verseguide.com/location/STANTON
    #<a href="/location/STANTON/II#Crusader" class="text-none animateMe pa-0 v-tab" tabindex="0" aria-selected="false" role="tab">
    #-> alle location links scrapen
    # x-box / y-box /z-box :<i aria-hidden="true" class="v-icon notranslate mdi mdi-alpha-x-box-outline theme--dark" style="font-size: 18px;"></i>
    # km : <div class="v-list-item__subtitle">-259.27 km</div>
    
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        
        global startnavitoknownpoi_button_context,preloaded,mother
        startnavitoknownpoi_button_context = obj.context
        mother=self
        if preloaded == False:
            preload_poi_data()

    
    def onPropertyInspectorDidAppear(self,obj:events_received_objs.PropertyInspectorDidAppear):
        global pi_context,preloaded
        pi_context = obj.context
        if preloaded == False:
            preload_poi_data()
    
    def on_key_down(self, obj: events_received_objs.KeyDown):
        global start_time
        #check if longpress
        start_time = time.time()
                
    def on_key_up(self, obj: events_received_objs.KeyUp):
        global Destination,Database,preloaded,NaviThread,watch_clipboard_active,stop_navithread,mother,datasource,start_time
        tmpdatasource = datasource
        datasource = obj.payload.settings.get("datasource")
        if datasource == None:
            datasource = tmpdatasource
            
        end_time = time.time()
        time_lapsed = end_time - start_time
        logger.debug("longpresstimer: " + str(time_lapsed))
        if time_lapsed > 2: #longpress
            
            logger.debug("Longpress detected")
            logger.debug("info:"+ str(self.info))
            if datasource == 'starmap' :
                container = obj.payload.settings.get("container")
                x = obj.payload.settings.get("x")
                y = obj.payload.settings.get("y")
                z = obj.payload.settings.get("z")
                open_verseguideinfo(x,y,z,container)
            else:
                logger.debug("open verseguide works only with starmap as datasource...") 
                self.show_alert(obj.context)   
            
        else:    
            logger.debug("Datasource from button: "+str(datasource))
            if tmpdatasource != datasource:
                preload_poi_data()
            else:
                logger.debug("...same datasource as before ")    
            if preloaded == False:
                preload_poi_data()
                
            if datasource == "local":
                container = obj.payload.settings.get("container")
                poi = obj.payload.settings.get("poi")
                #old#logger.debug(f"start:" + str(container) + " - " + str(poi))
                
                Destination = Database["Containers"][container]["POI"][poi]
                logger.debug("Destination set to: "+ str(Destination))
                
                
            
            if datasource == 'starmap' :
                container = obj.payload.settings.get("container")
                x = obj.payload.settings.get("x")
                y = obj.payload.settings.get("y")
                z = obj.payload.settings.get("z")
                

                logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
                Destination = {
                        'Name': 'Predefined POI from Starmap', 
                        'Container': container,
                        'X': float(x), 
                        'Y': float(y), 
                        'Z': float(z), 
                        "QTMarker": "FALSE"
                    }
            
            if watch_clipboard_active == False:
                mother=self
                NaviThread.start()
                self.set_state(obj.context, 1)

            else:
                stop_navithread = True
                try:
                    NaviThread.join()
                except:
                    logger.debug("Cannot join thread")
                    watch_clipboard_active = False
                stop_navithread = False
                NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread
                logger.debug(f"...stopped")
                reset_buttons()
                watch_clipboard_active = False
                #NaviThread.start()
                self.set_state(obj.context, 0)
                #old#logger.debug(f"...and restarted")

class ocr(Action):
    UUID = "com.doabigcheese.scnav.ocr"
    def on_key_down(self, obj: events_received_objs.KeyDown):
        global start_time
        #check if longpress
        start_time = time.time()

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global ocr_running,OCRThread,stop_threads,ocr_button_context
        ocr_button_context = obj.context
        end_time = time.time()
        time_lapsed = end_time - start_time
        if time_lapsed > 2:
            logger.debug("Longpress detected")
            if ocr_running:
                try:
                    stop_threads = True
                    OCRThread.join()
                except:
                    pass
                ocr_running = False
                self.set_state(obj.context, 0)
                logger.debug(f"...stopped")
        if ocr_running:
            try:
                stop_threads = True
                OCRThread.join()
            except:
                pass
            ocr_running = False
            self.set_state(obj.context, 0)
            logger.debug(f"...stopped")
        else:
            stop_threads = False
            OCRThread=threading.Thread(target=process_displayinfo,args=(queue,)) #Prepare a new thread
            ocr_running=True
            self.set_state(obj.context, 1)
            OCRThread.start()

class halo(Action):
    UUID = "com.doabigcheese.scnav.halo"

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global ocr_running,halo_running,OCRThread,stop_threads,mother,halo_button_context,stop_navithread,NaviThread,watch_clipboard_active
        halo_button_context = obj.context
        if halo_running == False:
            logger.debug("if halo")
            halo_running = True
            stop_threads = False
            if watch_clipboard_active == False:
                mother=self
                NaviThread.start()
            #OCRThread=threading.Thread(target=process_displayinfo,args=(queue,)) #Prepare a new thread
            #ocr_running=True
            HALOThread=threading.Thread(target=cyclic_showlocation,args=(queue,))
            logger.debug("Starting halo thread...")
            HALOThread.start()
            self.set_state(obj.context, 1)
            #OCRThread.start()
        else:
            logger.debug("else halo")
            halo_running = False
            try:
                logger.debug("Stopping halo thread...")
                stop_threads = True
                HALOThread.join()
                OCRThread.join()
            except:
                pass
            ocr_running = False
            stop_navithread = True
            try:
                NaviThread.join()
            except:
                logger.debug("Cannot join thread")
            watch_clipboard_active = False
            self.set_state(obj.context, 0)
            NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread



class Sandcavestour(Action):
    UUID = "com.doabigcheese.scnav.sandcavestour"
    
    def on_key_down(self, obj: events_received_objs.KeyDown):
        global start_time
        #check if longpress
        start_time = time.time()
        
    def on_key_up(self, obj: events_received_objs.KeyUp):
        global preloaded,mother,NaviThread,sandcavetour_active,watch_clipboard_active,stop_navithread,sandcavestour_button_context,start_time,sandcavetour_init_done,Destination_queue,Destination,knownPlayerContainername,datasource
        logger.debug(f"Sandcavetour button pressed...")
        end_time = time.time()
        time_lapsed = end_time - start_time
        sandcavestour_button_context= obj.context
        logger.debug("longpresstimer: " + str(time_lapsed))
        if time_lapsed > 2:
            logger.debug("Longpress detected")
            if sandcavetour_active == True:
                #Destination_tmp = Destination 
                Destination_queue.pop(0) #remove 1st element from destinationlist
                #re_sort the queue:
                #reorder_Destination_queue(Destination_tmp["X"],Destination_tmp["Y"],Destination_tmp["Z"],Destination_queue)
                reorder_Destination_queue(knownPlayerX,knownPlayerY,knownPlayerZ,Destination_queue)
                logger.debug(str(Destination_queue))
                Destination = Destination_queue[0]
                
                logger.debug("s2")
                tourlenght = len(Destination_queue)
                logger.debug("Destination set to: " + str(Destination))
                if Destination['Distance'] < Destination['nextQTMarkerDistance']:
                    next_hint = "(fly "+str(int(Destination['Distance']))+")"
                else:
                    next_hint = "(QT "+str(int(Destination['nextQTMarkerDistance'])) +")"
                #with open("sandcavetour.txt","a") as file:
                #    file.write(next_hint + "  " + str(Destination) + "\n")
                message_tour = json.dumps({"event": "setTitle",
                                    "context": sandcavestour_button_context,
                                    "payload": {
                                        "title": linebreak_title("NEXT ("+str(tourlenght)+")" + next_hint  + "\n" + str(Destination['Name'])),
                                        "target": 0,
                                    }
                                })
                self.ws.send(message_tour)
                self.set_state(obj.context, 1)
                #updatecoordinates()
                
                
                #stop_navithread = True
                #NaviThread.join()
                #stop_navithread = False
                #NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
                #NaviThread.start()
                
        if time_lapsed <= 2:
            if datasource == "local":
                datasource="starmap"
                preloaded = False
                
            if preloaded == False:
                logger.debug("preload...")
                preload_poi_data()
            if watch_clipboard_active == False:
                logger.debug("datasourceinfo: "+str(datasource))
                mother=self
                
                sandcavetour_active = True
                NaviThread.start()
                self.set_state(obj.context, 1)
                message_tour = json.dumps({"event": "setTitle",
                                    "context": sandcavestour_button_context,
                                    "payload": {
                                        "title": "Sandcave Tour\n(started)",
                                        "target": 0,
                                    }
                                })
                self.ws.send(message_tour)
                
            else:
                stop_navithread = True
                try:
                    NaviThread.join()
                except:
                    logger.debug("Cannot join thread")
                    watch_clipboard_active = False
                stop_navithread = False
                sandcavetour_active = False
                Destination_queue = []
                sandcavetour_init_done = False
                NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread
                logger.debug(f"...stopped")
                reset_buttons()
                self.set_state(obj.context, 0)
            
    
class StartNaviToCustomPOI(Action):
    UUID = "com.doabigcheese.scnav.custompoi"
    def on_key_up(self, obj: events_received_objs.KeyUp):
        global Destination,Database,preloaded,NaviThread,watch_clipboard_active,stop_navithread,mother
        if preloaded == False:
            preload_poi_data()
        container = obj.payload.settings.get("container")
        x = float(obj.payload.settings.get("x"))
        y = float(obj.payload.settings.get("y"))
        z = float(obj.payload.settings.get("z"))
        

        #old#logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
        Destination = {
                'Name': 'Custom POI', 
                'Container': container,
                'X': x, 
                'Y': y, 
                'Z': z, 
                "QTMarker": "FALSE"
            }
        logger.debug("Custom Destination set to: "+str(Destination))
        if watch_clipboard_active == False:
            mother=self
            logger.debug(mother)
            NaviThread.start()
            self.set_state(obj.context, 1)

        else:
            stop_navithread = True
            NaviThread.join()
            stop_navithread = False
            NaviThread=threading.Thread(target=watch_clipboard,args=(queue,)) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            #NaviThread.start()
            self.set_state(obj.context, 0)
            #old#logger.debug(f"...and restarted")
            




if __name__ == '__main__':
    #StreamDeck.bind("<<check_queue>>",check_queue)
    StreamDeck(
        actions=[
            UpdateCurrentLocation(),
            StartNaviToSavedPOI(),
            SaveLocation(),
            StartNavi(),
            Bearing(),
            StartNaviToKnownPOI(),
            StartNaviToCustomPOI(),
            Nearest(),
            Daytime(),
            Around(),
            Coords(),
            Calibrate(),
            Sandcavestour(),
            OMs(),
            CamDir(),
            ocr(),
            halo(),
            
        ],
        log_file=settings.LOG_FILE_PATH,
        log_level=settings.LOG_LEVEL,
        log_backup_count=1,
    ).run()
