import asyncio
from pyppeteer import launch

async def parse_website(xpath_list,url,type,step):
    # URL der Website
    
    # Starten von Pyppeteer und Öffnen einer neuen Seite
    browser = await launch()
    page = await browser.newPage()
    page.setDefaultNavigationTimeout(120000)

    # Website öffnen
    await page.goto(url)

    # Warten auf das Laden der Website (optional)
    # Ändern Sie den Wert von sleep, um die Ladezeit anzupassen
    await asyncio.sleep(5)

    #activate hidden elements 
    if step == 2:
        try:
            print("1")
            button_xpath= "/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[3]/div/div[1]/div[2]/div[1]/div/div/div[1]/div/div[2]/div/span/span"
            await page.waitForXPath(button_xpath)
            print("2")
            button1 = await page.xpath(button_xpath)
            print("3")
            await button1[0].click()
            print("4")
            await page.screenshot(path='screenshot4.png') #optional
            cookiebutton_xpath = "/html/body/div/div/div/div[2]/div/div/div[3]/button[2]/span"
            button3 = await page.xpath(cookiebutton_xpath)
            await button3[0].click()
            await page.screenshot(path='screenshot5.png') #optional
            spoilerwarning_xpath = "/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[3]/div/div[2]/div/div/div[1]/div/div[2]/div/div/div[4]/div/div/div/div[2]/div/div[2]/div"
            button2 = await page.xpath(spoilerwarning_xpath)
            await button2[0].click()
            #await page.waitForNavigation()
            print("5")
            await page.screenshot(path='screenshot6.png') #optional
            print("6")
        except:
            await page.screenshot(path='error_screenshot.png') #optional
    
    # Elemente auswählen
    links = []
    counter = 0
    for xpath in xpath_list:
        matches = await page.xpath(xpath)
        counter = counter + 1
        if counter == 5:
            type = "element.value"
        #print(page.content)

        # Ausgabe der Elemente
        
        for match in matches:
            text = await page.evaluate('(element) => ' + type, match)
            links.append(text)
            print(text)
    
    await browser.close()   
    return links
    
   

# asyncio-Event-Schleife starten und das Parsen der Website ausführen
pois_with_coordinates = []
xpath_list = ["/html/body/div/div/div/div[1]/div[2]/div[2]/div/div/div/div/div/div/form/div[1]/div[2]/div/div/div/div/div/div[1]/div/div[2]/div/a","/html/body/div/div/div/div[1]/div[2]/div[2]/div/div/div/div/div/div/form/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[2]/div/a","/html/body/div/div/div/div[1]/div[2]/div[2]/div/div/div/div/div/div/form/div[1]/div[2]/div/div/div/div/div/div[3]/div/div[2]/div/a","/html/body/div/div/div/div[1]/div[2]/div[2]/div/div/div/div/div/div/form/div[1]/div[2]/div/div/div/div/div/div[4]/div/div[2]/div/a"]
xpath_list_poi = ["/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[6]/div[2]/div","/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[7]/div[2]/div","/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[8]/div[2]/div","/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[1]/header/div/div[1]","/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[1]/div/div/div/div/div[2]/input"]
xpath_test_poi = ["/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div/a"]
                   #/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div[1]/a 1. reihe 1. icon
                   #/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div[2]/a 1. reihe 2. icon
                   #/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div[4]/a 2.reihe 1. icon
             #grid: /html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div/div/div[2]/div[2]/div  /div/a ?
links_to_moons = asyncio.get_event_loop().run_until_complete(parse_website(xpath_list,"https://verseguide.com/location/STANTON","element.href",1))
print(str(len(links_to_moons)))
counter_moons = 0
done_moons = 0 #if you need to start in the middle or so
for element in links_to_moons:                                                  #/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/form/div/div[4]/div/div/div/div/div/div/div[1]/div/div[2]/div[2]/div/div[1]/a
    counter_moons = counter_moons + 1 
    if counter_moons > done_moons:
        pois_from_moon = asyncio.get_event_loop().run_until_complete(parse_website(xpath_test_poi,element,"element.href",2))
        print("len poi: " + str(len(pois_from_moon)))
        for item in pois_from_moon:
            returnvalue = asyncio.get_event_loop().run_until_complete(parse_website(xpath_list_poi,item,"element.textContent",3))
            try:                                                                              #/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[6]/div[2]/div
                x = returnvalue[0].replace(" km","") #asyncio.get_event_loop().run_until_complete(parse_website("/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[6]/div[2]/div",item,"element.textContent"))
                y = returnvalue[1].replace(" km","") #asyncio.get_event_loop().run_until_complete(parse_website("/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[7]/div[2]/div",item,"element.textContent"))
                z = returnvalue[2].replace(" km","") #asyncio.get_event_loop().run_until_complete(parse_website("/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[2]/div[2]/div/div/div[8]/div[2]/div",item,"element.textContent"))
                name= returnvalue[3].strip() #asyncio.get_event_loop().run_until_complete(parse_website("/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[1]/header/div/div[1]",item,"element.textContent"))
                container= returnvalue[4].strip() #asyncio.get_event_loop().run_until_complete(parse_website("/html/body/div/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div[2]/div[1]/div[1]/div/div/div/div/div[2]/input",item,"element.value"))
                
                pois_with_coordinates.append({"Name" : name, "Container" : container, "x" : x,"y" : y,"z" : z})
                dataset = str(x) + "," + str(y) + "," + str(z) + "," + str(name) + "," + str(item) + "," + str(container) + "\n"
                print(dataset)
                with open("table.txt","a") as file:
                    file.write(dataset)
            except:
                print("Error at: "+str(item))
                with open("error.txt","a") as file:
                    file.write(str(item))    
print("done.") 
print(pois_with_coordinates)
     
