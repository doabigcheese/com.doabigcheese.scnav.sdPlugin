# com.doabigcheese.scnav.sdPlugin
An standalone plugin for planetary navigation in StarCitizen

# For Installation
Precondition: python >= 3.8 installed, windows only \
Manual: \
Copy the folder com.doabigcheese.scnav.sdPlugin to your Streamdeck Plugin Directory \
e.g. should end up here: %appdata%\Elgato\StreamDeck\Plugins\ \
restart the Stream Deck Software 

Automatic: \
Download the latest release and doubleclick on the file - Stream Deck Software should do the rest.

# For Deinstallation
In Stream Deck Software just rightlick inside SCNAV in right hand menu and press uninstall

# Features
"Update Location" Button will send /showlocation to the Chat (Chat have to be visible) \
POI Buttons can be predefined with a Location you want to navigate to \
The Output Buttons will display the information as soon as you start the navigation to a POI (press POI button), and then start updating current coordinates with "Update Location" button \
If the POI Button is defined with a POI from starmap.tk, then a longpress on it can open a browser window with this POI on verseguide.com
Sandcave Tours button can help you exploring Sand Caves to find rare ores... just start it with a single press when you are e.g. on Daymar, then hit the update location button and it will indicate where to go \
It will show you the amount of caves on this moon, and if you should do a quantumdrive first or fly directly \
Longpress (> 2 sec) on this button will delete the current sandcave destination and move on to the next in queue (all are sorted for minimal fly time) \
shortpress will deactivate Sandcave Tours again \
Save button will save your current location to a custom list \
With the custom poi button you can then select one of your saved locations to be set as new destination. \
CamDir let you find e.b. Benny Henge quicker, as it gives you a direction (idea and code adapted from Project Jericho, Graupunkt) (r_displayinfo 2 have to be enabled)


![alt text](https://github.com/doabigcheese/com.doabigcheese.scnav.sdplugin/blob/master/Screenshot1.jpg?raw=true)
