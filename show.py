import os
import random
import threading 
import time
import socket
import sys
# from bluepy.btle import Scanner, DefaultDelegate
import paho.mqtt.client as mqtt

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


# customize before using!
brokeraddress = "test.mosquitto.org" # you can use this as a test broker, or setup msoquitto on a rpi as an internal broker
mqttclient = "dynaframe1"  # must be unique for each frame...
brokerport = 1883
subscriptionname = "jfarro/house/makerspace/display" # this should be a string that is unique and describes where your frame is


# initial variables
refresh = False  # controls when the frame needs to close aps and start over

imagePath = ""  # path to the current folder of images
webpageEnd = ""  # the 'footer' of the webpage
refreshInterval = 30  # number of seconds between images in a slideshow

# webpageBody is the main template for the http served webpage. This is where you can make that page..prettier
webpageBody = '''
<html>
<head><title>Dynamic Screen Config</title>
<style>
a.button {
 -webkit-appearance: button;
 -moz-appearance: button;
 appearance: button;

 text-decoration: none;
 color: 07183B;
 font-size: 40px;

 background-color: #7A8AAC;
 border: none;
 padding: 10px 16px;
 text-align: left
}
body
{
    background-color: #304573;
}

</style>
</head>
<body>

'''

webpage = webpageBody


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        qs = {}
        refreshfolders()
        path = self.path
        # print("Path is: " + path)
        qs = parse_qs(path)

        for key, value in qs.items():
            print ("- " + key, value)

        if "/?dir" in qs :
            print("Dir is.....! " + qs['/?dir'][0])

            if qs['/?dir'][0] == "exit" :
                os.system("killall -9 feh");
                os.system("killall -9 omxplayer.bin")
                global imagePath
                imagePath = ""
                sys.exit()

            imagePath = qs['/?dir'][0]

        global refresh
        refresh = True
        os.system("killall -9 omxplayer.bin")
        print("HTTPHandler - ImagePath set to: " + imagePath)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(webpage.encode('UTF-8'))
        self.wfile.write(b"<font size='30'><br><br><br>ImagePath is now: <font color='white'>" +
                         imagePath.encode('UTF-8')
                         + b"</color></font></body>")


def refreshfolders():
    global webpageEnd
    webpageEnd = ""
    # add dirs to webpage as links
    folders = os.listdir()
    for folder in folders:
        if os.path.isdir(folder) and ("log" not in folder):
            print("folder found: " + folder)
            webpageEnd += "<a href='?dir=" + folder + "' class='button'>" + folder + "</a><br><br>"
    global webpage
    webpageEnd += "<a href='?dir=exit' class='button'>Exit</a><br><br>"
    webpage = webpageBody + webpageEnd


def getrandomfolder():
    global imagePath
    folders = os.listdir()
    validfolder = False
    while validfolder is False:
        imagePath = random.choice(folders)
        if os.path.isdir(imagePath) and imagePath != "logs":
            validfolder = True
            break


def MQTTSubscribe():
    client = mqtt.Client(mqttclient)    # create new instance
    client.connect(brokeraddress,brokerport)  # connect to broker
    client.subscribe(subscriptionname)  # subscribe
    client.on_message=on_message
    client.on_log=on_log
    client.loop_start()


def on_log(client, userdata, level, buf):
    print("log: ", buf)


def on_message(client, userdata, message):
    print("message received ", str(message.payload.decode("utf-8")))
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)
    global imagePath
    imagePath = str(message.payload.decode("utf-8"))

    global refresh
    refresh = True
    os.system("killall -9 omxplayer.bin");

    print("Imagepath set to: " + imagePath);


getrandomfolder()
print("ImagePath is: " + imagePath)


time.sleep(10.0)
# get local machine ip
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip = s.getsockname()[0]
s.close()

print("Starting server at: " + ip + ":8000")
httpd = HTTPServer((ip, 8000), SimpleHTTPRequestHandler)
thread = threading.Thread(target=httpd.serve_forever)
thread.daemon = True
thread.start()

refreshfolders()


imageCheck = ""
dirs = os.listdir(imagePath)


def refreshPath():
    global dirs
    del dirs
    dirs = os.listdir(imagePath)
    global imageCheck
    imageCheck = imagePath



refreshPath()


# init...clean up any other running instances
os.system("killall -9 feh")
os.system("killall -9 omxplayer.bin")

MQTTSubscribe()

while True:
            for file in dirs:
                print ("Mainloop: Image Path is: " + imagePath + " and has: " + str(len(imagePath)) + " files.")
                file = "./" + imagePath + "/" + file

                if imageCheck != imagePath:
                    print("imageCheck " + imageCheck)
                    print("imagePath " + imagePath)
                    refreshPath()
                    break

                if imagePath == "":
                    quit()

                print("File is: " + file)
                os.system("killall -9 feh")
                os.system("killall -9 omxplayer.bin")

                if file.upper().endswith(".MOV"):
                    os.system('omxplayer ' + file)
                if file.upper().endswith(".MP4"):
                    os.system('omxplayer ' + file)
                if file.upper().endswith(".JPG"):
                    time.sleep(1.0)
                    os.system("DISPLAY=:0.0 feh -x " + file + "&")
                    count = 0
                    print("Showing: " + file)
                    print("refresh is: " + str(refresh))
                    print("refreshInterval is: " + str(refreshInterval))
                    while refresh is False:
                        time.sleep(1.0)
                        print("refresh is: " + str(refresh))
                        print("refreshInterval is: " + str(refreshInterval))
                        count = count + 1
                        if count > refreshInterval:
                            break

                    refresh = False
