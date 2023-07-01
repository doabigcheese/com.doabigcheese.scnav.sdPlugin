#todo
# - compare calibration calculation with Tool Jericho to find error
# - get navi data from starmap.tk rest api (eg setting in predefined_poi button)
#       OC: https://starmap.tk/api/v1/oc/
#       POI:https://starmap.tk/api/v1/pois/
#       query e.g. 
#           https://starmap.tk/api/v1/oc/index.php?system=Stanton
#           https://starmap.tk/api/v1/pois/index.php?planet=Daymar
# 
#
# *** debug: http://localhost:23654/
#todo:
#   -automatic title on button based on poi / planet
#   -long press opens up verseguide poi page or starmap.tk database view
#   - deactivate activated buttons when selecting new poi
#   - button state when switching pages?
#########################################################################
import random
import requests
import ahk
import time
import re

from math import sqrt, degrees, radians, cos, acos, sin, asin, tan ,atan2, copysign, pi
import pyperclip
import datetime
import json
import os
import csv
import sys
import threading
import json


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
sandcavestour_button_context = ""
startnavitoknownpoi_button_context = ""
startnavitosavedpoi_button_context = ""
pi_context = ""
message_pois = ""
datasource = "starmap" # local or starmap
daytime_toggle = "target"
sandcavetour_active = False
sandcavetour_init_done = False
start_time=0
Destination_queue=[]
knownPlayerX=0
knownPlayerY=0
knownPlayerZ=0
knownPlayerContainername=""


def linebreak_title(newtitle):
    i = 9
    #logger.debug(newtitle)
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
    #logger.debug(tmp_1)
    return tmp_1 + tmp_2 + tmp_3

def updatecoordinates():
    #logger.debug(f"Update entered.")
    ahk.send_input('{Enter}')
    time.sleep(0.5)
    ahk.send_input("/showlocation")
    time.sleep(0.2)
    ahk.send_input('{Enter}')

def save_poi():
    global save_triggered,watch_clipboard_active,mother
    
    #logger.debug(f"Save entered.")
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
    
    return local_rotated_coordinates


def get_lat_long_height(X : float, Y : float, Z : float, Container : dict):
    Radius = Container["Body Radius"]
    
    Radial_Distance = sqrt(X**2 + Y**2 + Z**2)
    
    Height = Radial_Distance - Radius

    #Latitude
    try :
        Latitude = degrees(asin(Z/Radial_Distance))
    except :
        Latitude = 0
    
    try :
        Longitude = -1*degrees(atan2(X, Y))
    except :
        Longitude = 0
    
    return [Latitude, Longitude, Height]

def get_sandcaves_sorted(X : float, Y : float, Z : float, Container:dict):
    global datasource
    Distances_to_POIs = []
    logger.debug("gss_1")
    #logger.debug(str(Container))
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
            #logger.debug("Vector_POI: " + str(Vector_POI))

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
    Distances_to_POIs = []
    logger.debug("rdq_1")
    #logger.debug(str(Container))
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
        #logger.debug("Nearest QTmarker to Cave:"+str(Nearest_POI_to_singleCave))
        logger.debug("append next")
        Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI, "nextQTMarkerDistance" : Nearest_POI_to_singleCaveDistance, "X": POI["X"], "Y": POI["Y"], "Z": POI["Z"], "Container": POI['Container'], "QTMarker": POI['QTMarker'] })
        logger.debug("append done")
    
    Player_to_Sandcaves_sorted= sorted(Distances_to_POIs, key=lambda k: k['Distance'])
    Sandcaves_to_QTMarker_sorted = sorted(Distances_to_POIs, key=lambda k: k['nextQTMarkerDistance'])
    
    logger.debug("final player2sandcaves sorted:"+str(Player_to_Sandcaves_sorted))
    logger.debug("final sandcaves2QT sorted:"+str(Sandcaves_to_QTMarker_sorted))
    
    if Player_to_Sandcaves_sorted[0]["Distance"] > Sandcaves_to_QTMarker_sorted[0]["nextQTMarkerDistance"]:
        logger.debug("QTMarker Sandcave is next")
        return Sandcaves_to_QTMarker_sorted
    else:
        logger.debug("Sandcave without QT is next")
        return Player_to_Sandcaves_sorted
      
    
    
def get_closest_POI(X : float, Y : float, Z : float, Container : dict, Quantum_marker : bool = False):
    
    Distances_to_POIs = []
    
    for POI in Container["POI"]:
        #logger.debug("processing: "+str(Container["POI"][POI]))
        Vector_POI = {
            "X": abs(X - Container["POI"][POI]["X"]),
            "Y": abs(Y - Container["POI"][POI]["Y"]),
            "Z": abs(Z - Container["POI"][POI]["Z"])
        }
        #logger.debug("Vector_POI: " + str(Vector_POI))

        Distance_POI = vector_norm(Vector_POI)
        
        #logger.debug("Quantum_marker: " + str(Quantum_marker))
        #logger.debug("Quantum_marker POI: " + str(Container["POI"][POI]["QTMarker"]))

        if Quantum_marker and Container["POI"][POI]["QTMarker"] == "TRUE" or not Quantum_marker:
            Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI})
            #logger.debug("Added to closest POI list: "+str(POI)+" with "+str(Distance_POI))
    #logger.debug("final:"+str(Distances_to_POIs))
    Target_to_POIs_Distances_Sorted = sorted(Distances_to_POIs, key=lambda k: k['Distance'])
    logger.debug("final sorted:"+str(Target_to_POIs_Distances_Sorted))
    return Target_to_POIs_Distances_Sorted



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
        qw, qx, qy, qz = Container["qw"], Container["qx"], Container["qy"], Container["qz"]
        logger.debug("27.3")        
        # Stanton X Y Z coordinates in refrence of the center of the container
        bsx = ((1-(2*qy**2)-(2*qz**2))*(sx-bx))+(((2*qx*qy)-(2*qz*qw))*(sy-by))+(((2*qx*qz)+(2*qy*qw))*(sz-bz))
        bsy = (((2*qx*qy)+(2*qz*qw))*(sx-bx))+((1-(2*qx**2)-(2*qz**2))*(sy-by))+(((2*qy*qz)-(2*qx*qw))*(sz-bz))
        bsz = (((2*qx*qz)-(2*qy*qw))*(sx-bx))+(((2*qy*qz)+(2*qx*qw))*(sy-by))+((1-(2*qx**2)-(2*qy**2))*(sz-bz))
        
        # Solar Declination of Stanton
        Solar_declination = degrees(acos((((sqrt(bsx**2+bsy**2+bsz**2))**2)+((sqrt(bsx**2+bsy**2))**2)-(bsz**2))/(2*(sqrt(bsx**2+bsy**2+bsz**2))*(sqrt(bsx**2+bsy**2)))))*copysign(1,bsz)
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
        #logger.debug(f"Error in sunrise/sunset calculations: \n{e}\nValues were:\n-X : {X}\n-Y : {Y}\n-Z : {Z}\n-Latitude : {Latitude}\n-Longitude : {Longitude}\n-Height : {Height}\n-Container : {Container['Name']}\n-Star : {Star['Name']}")
        #sys.stdout.flush()
        return ["Unknown", "Unknown", 0]



def get_current_container(X : float, Y : float, Z : float):
    global Database
    #logger.debug(f"get " + str(X))
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

def watch_clipboard():
    logger.debug(f"Watch Clipboard entered.")
    global save_button_context,save_triggered,Database,Container_list,Space_POI_list,Planetary_POI_list,watch_clipboard_active,Destination,stop_navithread,bearing_button_context,daytime_button_context,nearest_button_context,around_button_context,mother,coords_button_context,calibrate_active,daytime_toggle,sandcavetour_active,sandcavestour_button_context,sandcavetour_init_done,Destination_queue,knownPlayerX,knownPlayerY,knownPlayerZ,knownPlayerContainername
    watch_clipboard_active = True
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
    except:
        logger.debug("Error: Could not get time from NTP server")
        sys.stdout.flush()
        time_offset = 0

    logger.debug("Time offset: " + str(time_offset))
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


        #If clipboard content hasn't changed
        if new_clipboard == Old_clipboard or new_clipboard == "":

            #Wait some time
            time.sleep(1/5)


        #If clipboard content has changed
        else :
            Old_clipboard = new_clipboard
            #logger.debug(new_clipboard)
            New_time = time.time() + time_offset

            #If it contains some coordinates
            if new_clipboard.startswith("Coordinates:"):
                #split the clipboard in sections
                new_clipboard_splitted = new_clipboard.replace(":", " ").split(" ")


                #get the 3 new XYZ coordinates
                New_Player_Global_coordinates = {}
                New_Player_Global_coordinates['X'] = float(new_clipboard_splitted[3])/1000
                New_Player_Global_coordinates['Y'] = float(new_clipboard_splitted[5])/1000
                New_Player_Global_coordinates['Z'] = float(new_clipboard_splitted[7])/1000
                #search in the Databse to see if the player is ina Container
                Actual_Container = get_current_container(New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"])
                knownPlayerContainername=Actual_Container['Name']
                #logger.debug("Actual Container: " +str(Actual_Container))
                      
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
                            
                            logger.debug("Destination set to: " + str(Destination))
                            message_tour = json.dumps({"event": "setTitle",
                                                "context": sandcavestour_button_context,
                                                "payload": {
                                                    "title": linebreak_title("NEXT ("+str(tourlenght)+")\n" + str(Destination['Name'])),
                                                    "target": 0,
                                                }
                                            })
                            mother.ws.send(message_tour)
                            logger.debug("s3")
                            sandcavetour_init_done = True
                            logger.debug("Init done")
                    else:
                        logger.debug("Init already done...")
                
                if Destination != []: #(sandcavetour_active and sandcavetour_init_done) or not sandcavetour_active:        
                    #---------------------------------------------------New target local coordinates----------------------------------------------------
                    #Grab the rotation speed of the container in the Database and convert it in degrees/s
                    Target = Destination
                    logger.debug("Target set:"+str(Target))
                    #logger.debug("Target = " +str(Target))
                    logger.debug("Target Name = " +str(Target["Container"]))
                    #logger.debug("Database: "+str(Database))
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
                    if Actual_Container == Target["Container"]:
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
                            "Distance" : 0
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




                    #----------------------------------------------------------Heading--------------------------------------------------------------
                    
                    bearingX = cos(radians(target_Latitude)) * sin(radians(target_Longitude) - radians(player_Longitude))
                    bearingY = cos(radians(player_Latitude)) * sin(radians(target_Latitude)) - sin(radians(player_Latitude)) * cos(radians(target_Latitude)) * cos(radians(target_Longitude) - radians(player_Longitude))

                    Bearing = (degrees(atan2(bearingX, bearingY)) + 360) % 360

                    logger.debug("28_1")
                    logger.debug("1:"+str(Target["X"]))
                    logger.debug("2:"+str(Target["Y"]))
                    logger.debug("3:"+str(Target["Z"]))
                    logger.debug("4:"+str(target_Latitude))
                    logger.debug("5:"+str(target_Longitude))
                    logger.debug("6:"+str(target_Height))
                    #logger.debug("7:"+str(Database["Containers"][Target["Container"]]))
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
                    
                    
                    message_bearing = json.dumps({"event": "setTitle",
                                            "context": bearing_button_context,
                                            "payload": {
                                                "title": f"HEADING\n{round(Bearing, 0)}°\n{round(New_Distance_to_POI_Total, 1)} km",
                                                "target": 0,
                                            }
                                        })
                    logger.debug("31")
                    #logger.debug("31.1:"+str(Target_to_POIs_Distances_Sorted))
                    #logger.debug("31.2:"+str(Target_to_POIs_Distances_Sorted[0]['Distance']))
                    if Target_to_POIs_Distances_Sorted:
                        next_poi_name = Target_to_POIs_Distances_Sorted[0]['Name']
                        next_poi_distance = Target_to_POIs_Distances_Sorted[0]['Distance']
                    else:
                        next_poi_name = "n/a"
                        next_poi_distance = 0     
                    message_nearest = json.dumps({"event": "setTitle",
                                            "context": nearest_button_context,
                                            "payload": {
                                                "title": "NEXT\n" + linebreak_title(next_poi_name) + f"\n{round(next_poi_distance, 1)} km",
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
                    mother.ws.send(message_bearing)
                    #logger.debug("send bearing: " + message_bearing)
                    mother.ws.send(message_nearest)
                    #logger.debug("send nearest: " + message_nearest)
                    mother.ws.send(message_daytime)
                    #logger.debug("send daytime: " + message_daytime)
                    mother.ws.send(message_around)
                    #logger.debug("send around: " + message_around)
                    mother.ws.send(message_coords)
                    #logger.debug("send coords: " + message_coords)

                    #logger.debug("send data: " + message)
                    
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
                        logger.debug("Rotation for "+str(Actual_Container['Name'])+" calibrated from "+str(Database["Containers"][Target["Container"]]["Rotation Adjust"])+"° to "+str(FinalRotationAdjustment)+"° by "+str(RotationSpeedAdjustment)+". Please replace the value manually in the Database.json")
                        with open("calibrationdata.txt", "a") as myfile:
                                myfile.write(str(Actual_Container['Name']) + ": "+str(FinalRotationAdjustment))
                                myfile.write("\n")
                                
                    if save_triggered == True:
                        save_triggered = False
                        #logger.debug("Saving Location to file...")
                        timestamp=datetime.datetime.utcnow()
                        poi_name=str(Actual_Container['Name']) + "_" + str(int(Player_to_POIs_Distances_Sorted[0]['Distance'])) + "km_next_to_" + str(Player_to_POIs_Distances_Sorted[0]['Name']) + "_" + str(timestamp)
                        #logger.debug(poi_name)
                        save_data = Actual_Container['Name'] + "," + str(round(New_player_local_rotated_coordinates['X'], 3)) + "," + str(round(New_player_local_rotated_coordinates['Y'], 3)) + "," + str(round(New_player_local_rotated_coordinates['Z'], 3)) + "," + poi_name.replace(" ","_").replace(":","_").replace(".","_")
                        #logger.debug(save_data)
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
                
NaviThread=threading.Thread(target=watch_clipboard)



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
            #logger.debug(str(Database))
            #logger.debug(str(Container_list))
        except:
            logger.debug(f"Database.json not found.")
                
    if datasource == "starmap":
        try:
            logger.debug("Starmap.tk as datasource...")
            url = "https://starmap.tk/api/v1/oc/index.php?system=Stanton"
            response = requests.get(url)
            ##logger.debug("Response: " + str(response.status_code))
            if response.status_code == 200:  # Erfolgreiche Anfrage
                #logger.debug(str(response.text))
                #cleanresponse = re.findall('[{.*}]', response.text)
                data = response.json()  # JSON-Daten aus der Antwort extrahieren
                # Mit den erhaltenen Daten arbeiten
                #logger.debug("data:" + str(data))
                #logger.debug('00')
                tdata=str(data).replace("\'","\"").replace("None","0")
                counter = 0
                new_tdata = ""
                for letter in tdata:
                    counter = counter + 1
                    if letter == "{":
                        letter = "\"oc_" + str(counter) + "\":{"
                    new_tdata = new_tdata + letter
                tdata=new_tdata.replace("[","{\"Containers\":{").replace("]","}}").replace("Microtech","microTech").replace("Stanton Star","Stanton")
                #logger.debug('01')
                #logger.debug(str(tdata))
                tmpdata = json.loads(tdata) #lets convert to internal layout
                #tmpdata=data
                #logger.debug('0')
                #logger.debug(str(tmpdata))
                for container_name in tmpdata['Containers']:
                    tmpdata['Containers'][container_name]['Name'] = tmpdata['Containers'][container_name].pop('Planet')
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
                for old_container_name in tmpdata['Containers']:
                    if old_container_name.startswith("oc_"): 
                        new_name = tmpdata['Containers'][old_container_name]['Name']
                        logger.debug("old : "+ str(old_container_name) + " - new_name: " + str(new_name))
                        tmpdata['Containers'][new_name] = tmpdata['Containers'].pop(old_container_name)
                
                
                #logger.debug('1')
                #logger.debug(str(tmpdata))
                #logger.debug('2')
                #data = json.loads(str(tmpdata))
                #logger.debug('3')
                #logger.debug(str(data))
                #logger.debug('4')
                #Aufbau: Database->Containers->abc->Name:abc
                Database = tmpdata
                #logger.debug(str(Database["Containers"]))
                for i in Database["Containers"]:
                    #logger.debug(i)
                    Container_list.append(Database["Containers"][i]["Name"])
                #logger.debug(str(Container_list))    
               
            else:
                print("Fehler beim Abrufen der Daten. Statuscode:", response.status_code)
            
            logger.debug("getting POIs for merge from starmap...")
            url = "https://starmap.tk/api/v1/pois"
            response = requests.get(url)
            if response.status_code == 200:  # Erfolgreiche Anfrage
                data = response.json()  # JSON-Daten aus der Antwort extrahieren
                logger.debug(str(data))
                tdata=str(data).replace("\'s","s").replace("\'","\"").replace("None","0")
                #logger.debug("tdata: "+str(tdata))

                tmpdata = json.loads(tdata) #lets convert to internal layout
                #logger.debug("tmpdata: " + str(tmpdata))
                
                

                for entry in tmpdata:
                    entry['Name'] = entry.pop('PoiName')
                    entry['Container'] = entry.pop('Planet')
                    entry['X'] = entry.pop('XCoord')
                    entry['Y'] = entry.pop('YCoord')
                    entry['Z'] = entry.pop('ZCoord')
                    if entry['QTMarker'] == 1:
                        entry['QTMarker'] = "TRUE"
                    else:
                        entry['QTMarker'] = "FALSE" 
                    logger.debug("entry: "+str(entry))
                    
                    if entry['Container'] != "" and entry['Container'] in Container_list:
                        Database['Containers'][entry['Container']]['POI'][entry['Name']] = entry
                    
                #logger.debug("tmpdata_after convert: " + str(tmpdata))
                
            #logger.debug("Database: "+str(Database))    
                
            preloaded = True
            
        except Exception as e:
            logger.debug("Starmap Datasource error: " + str(e))    
        


logger.debug("Going for preload...")
preload_poi_data()

def reset_buttons():
    global mother
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
    
    mother.ws.send(message_bearing)
    
    mother.ws.send(message_nearest)
    
    mother.ws.send(message_daytime)
    
    mother.ws.send(message_coords)
    
       

class StartNavi(Action):
    UUID = "com.doabigcheese.scnav.startnavi"
    global watch_clipboard_active,preloaded,mother,message_pois


    def on_key_up(self, obj: events_received_objs.KeyUp):
        # For Debuggin, generate kind of random Coordinates

        #pyperclip.copy("Coordinates: x:12792704755.989153 y:-74801598.619366 z:50267." + str(random.randint(0,50))) #Magda
        pyperclip.copy("Coordinates: x:-18930612193.865963 y:-2609992498.331003 z:-232631." + str(random.randint(0,50))) #Daymar
        mother=self
        if(message_pois != ""):
            logger.debug("Sending: " + str(message_pois))
            mother.ws.send(message_pois)

class Calibrate(Action):
    UUID = "com.doabigcheese.scnav.calibrate"

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global preloaded,mother,NaviThread,calibrate_active,watch_clipboard_active,stop_navithread
        if preloaded == False:
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
            NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            self.set_state(obj.context, 0)
            
                    
         
  
             
class Bearing(Action):
    UUID = "com.doabigcheese.scnav.bearing"
    
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #logger.debug(f"willapear_debug: " + str(obj.context))
        global bearing_button_context
        bearing_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass
        
 
class Nearest(Action):
    UUID = "com.doabigcheese.scnav.nearest"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #logger.debug(f"willapear_debug: " + str(obj.context))
        global nearest_button_context
        nearest_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass 
        #global nearest_button_context
        #logger.debug(f"self: " + str(self))
        
        #self.set_title(nearest_button_context,
        #        events_sent_objs.SetTitlePayload(
        #            title="nearest:\nMining Area 141\n(15 km)",
        #            target=0 #sw and hw
        #        )
        #    )   
        
class Daytime(Action):
    UUID = "com.doabigcheese.scnav.daytime"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #logger.debug(f"willapear_debug: " + str(obj.context))
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
        #logger.debug(f"willapear_debug: " + str(obj.context))
        global coords_button_context
        coords_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):   
        pass 
    
class Around(Action):
    UUID = "com.doabigcheese.scnav.around"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #logger.debug(f"willapear_debug: " + str(obj.context))
        global around_button_context
        around_button_context = obj.context
    

    def on_key_up(self, obj: events_received_objs.KeyUp):
        pass        

class UpdateCurrentLocation(Action):
    UUID = "com.doabigcheese.scnav.updatecurrentlocation"
    def on_key_down(self, obj: events_received_objs.KeyDown):
        pass

    def on_key_up(self, obj: events_received_objs.KeyUp):
        
        #logger.debug(f"Update pressed.")
        updatecoordinates()
            
class SaveLocation(Action):
    UUID = "com.doabigcheese.scnav.save"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        #logger.debug(f"willapear_debug: " + str(obj.context))
        global save_button_context
        save_button_context = obj.context

    def on_key_up(self, obj: events_received_objs.KeyUp):
        global mother
        mother=self
        #logger.debug(f"Save pressed.")
        save_poi()        

class StartNaviToSavedPOI(Action):
    UUID = "com.doabigcheese.scnav.savedpoi"
    def on_will_appear(self, obj:events_received_objs.WillAppear):
        logger.debug(f"SAVEDPOI willapear_debug: " + str(obj.context))
        
        global message_pois,Database,Container_list,Space_POI_list,Planetary_POI_list,preloaded,mother,pi_context,startnavitosavedpoi_button_context
        startnavitosavedpoi_button_context = obj.context
        mother=self
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
        x = obj.payload.settings.get("x")
        y = obj.payload.settings.get("y")
        z = obj.payload.settings.get("z")
        

        #logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
        Destination = {
                'Name': 'Custom POI', 
                'Container': container,
                'X': x, 
                'Y': y, 
                'Z': z, 
                "QTMarker": "FALSE"
            }
        if watch_clipboard_active == False:
            mother=self
            NaviThread.start()
            self.set_state(obj.context, 1)

        else:
            stop_navithread = True
            NaviThread.join()
            stop_navithread = False
            NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            #NaviThread.start()
            self.set_state(obj.context, 0)
            #logger.debug(f"...and restarted")
        

            
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
            
    def on_key_up(self, obj: events_received_objs.KeyUp):
        global Destination,Database,preloaded,NaviThread,watch_clipboard_active,stop_navithread,mother,datasource
        tmpdatasource = datasource
        datasource = obj.payload.settings.get("datasource")
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
            #logger.debug(f"start:" + str(container) + " - " + str(poi))
            
            Destination = Database["Containers"][container]["POI"][poi]
            
            
        
        if datasource == 'starmap' :
            container = obj.payload.settings.get("container")
            x = obj.payload.settings.get("x")
            y = obj.payload.settings.get("y")
            z = obj.payload.settings.get("z")
            

            #logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
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
            NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            #NaviThread.start()
            self.set_state(obj.context, 0)
            #logger.debug(f"...and restarted")

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
                Destination_queue.pop(0) #remove 1st element from destinationlist
                #re_sort the queue:
                reorder_Destination_queue(knownPlayerX,knownPlayerY,knownPlayerZ,Destination_queue)
                Destination = Destination_queue[0]
                logger.debug("s2")
                tourlenght = len(Destination_queue)
                logger.debug("Destination set to: " + str(Destination))
                message_tour = json.dumps({"event": "setTitle",
                                    "context": sandcavestour_button_context,
                                    "payload": {
                                        "title": linebreak_title("NEXT ("+str(tourlenght)+")\n" + str(Destination['Name'])),
                                        "target": 0,
                                    }
                                })
                self.ws.send(message_tour)
                self.set_state(obj.context, 1)
                updatecoordinates()
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
                NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
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
        x = obj.payload.settings.get("x")
        y = obj.payload.settings.get("y")
        z = obj.payload.settings.get("z")
        

        #logger.debug(f"start:" + str(container) + " - " + str(x) + " - " + str(y) + " - " + str(z) + ".")
        Destination = {
                'Name': 'Custom POI', 
                'Container': container,
                'X': x, 
                'Y': y, 
                'Z': z, 
                "QTMarker": "FALSE"
            }
        if watch_clipboard_active == False:
            mother=self
            NaviThread.start()
            self.set_state(obj.context, 1)

        else:
            stop_navithread = True
            NaviThread.join()
            stop_navithread = False
            NaviThread=threading.Thread(target=watch_clipboard) #Prepare a new thread
            logger.debug(f"...stopped")
            reset_buttons()
            watch_clipboard_active = False
            #NaviThread.start()
            self.set_state(obj.context, 0)
            #logger.debug(f"...and restarted")




if __name__ == '__main__':
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
            
        ],
        log_file=settings.LOG_FILE_PATH,
        log_level=settings.LOG_LEVEL,
        log_backup_count=1,
    ).run()
