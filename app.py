# importing dependent libraries
from flask import Flask, render_template, url_for
from flask_apscheduler import APScheduler
from picamera2 import Picamera2, Preview
from flask_socketio import SocketIO, emit
import string
import random
import time
import gesture
import requests
import json
import os


# creating flask app object
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)

# luxand face API key from environment variable
LUX_TOKEN = os.environ["LUXAND_TOKEN"]

# gesture sensor object
gsensor = gesture.PAJ7620U2()

#Gesture detection interrupt flag
PAJ_UP				    = 0x01 
PAJ_DOWN			    = 0x02
PAJ_LEFT			    = 0x04 
PAJ_RIGHT			    = 0x08
PAJ_FORWARD		    	= 0x10 
PAJ_BACKWARD		    = 0x20
PAJ_CLOCKWISE			= 0x40
PAJ_COUNT_CLOCKWISE		= 0x80
PAJ_WAVE				= 0x100

# photo path
PHOTO_PATH = "/home/student/room_counter/static/pictures/image.jpg"

# people in room
room_count = 0
people_list = []

# camera object
camera = Picamera2()
camera_config = camera.create_preview_configuration()
camera.configure(camera_config)
camera.start_preview(Preview.NULL)
camera.start()

# method to generate random name
def rand_name(len: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=len))

# method to add new person to database
def add_person(name, image_path, collections = ""):

    # get the image file
    if image_path.startswith("https://"):
        files = {"photos": image_path}
    else:
        files = {"photos": open(image_path, "rb")}
        
    # send post request to the luxand database    
    response = requests.post(
        url="https://api.luxand.cloud/v2/person",
        headers={"token": LUX_TOKEN},
        data={"name": name, "store": "1", "collections": collections},
        files=files,
    )

    if response.status_code == 200:
        person = response.json()

        print(person)

        # if face detection fails, continue
        if person["status"] == "failure":
            return None
        # otherwise print to console, return their id, and it will be added to luxand database
        else:
            print("Added person", name, "with UUID", person["uuid"])
            return person["uuid"]
    
    else:
        print("Can't add person", name, ":", response.text)
        return None

# method to add images for existing person to database
def add_face(person_uuid, image_path):

    # get the image file
    if image_path.startswith("https://"):
        files = {"photo": image_path}
    else:
        files = {"photo": open(image_path, "rb")}

    # send post request to add image
    response = requests.post(
        url="https://api.luxand.cloud/v2/person/%s" % person_uuid,
        headers={"token": LUX_TOKEN},
        data={"store": "1"},
        files=files
    )

# method to recognize a face
def recognize_face(image_path):

    # request URL and headers
    url = "https://api.luxand.cloud/photo/search/v2"
    headers = {"token": LUX_TOKEN}

    # get image path
    if image_path.startswith("https://"):
        files = {"photo": image_path}
    else:
        files = {"photo": open(image_path, "rb")}

    # send post request
    response = requests.post(url, headers=headers, files=files)
    result = json.loads(response.text)

    if response.status_code == 200:
        return response.json()
    else:
        print("Can't recognize people:", response.text)
        return None

# threading method to read gestures and do the database stuff
def run_gesture():

    global room_count 
    global people_list

    # read the gesture
    g = gsensor.check_gesture()

    # if they are walking in
    if g == PAJ_DOWN:
        camera.capture_file(PHOTO_PATH)

        # see if face is recognized
        l = recognize_face(PHOTO_PATH)
        print(l)

        if len(l) and l != None:
            # add face to database to improve accuracy
            add_face(l[0]["uuid"], PHOTO_PATH)

            os.rename(PHOTO_PATH, "/home/student/room_counter/static/pictures/" + l[0]["uuid"] + ".jpg")

            # add one person to the room
            room_count += 1

            people_list.append(l[0]["uuid"] + ".jpg")


        # if not then add person to database
        else:
            print("test")
            name = rand_name(10)
            print(name)
            x = add_person(name, PHOTO_PATH)

            # if adding was successful
            if x != None:
                
                # rename photo to uuid
                os.rename(PHOTO_PATH, "/home/student/room_counter/static/pictures/" + x + ".jpg")

                # add photo to list to display
                people_list.append(x + ".jpg")

                # add one person to the room
                room_count += 1

        # update the website with roomcount and image
        socketio.emit("reload", {"data": True})


    # if they are walking out 
    elif g == PAJ_UP:
        camera.capture_file(PHOTO_PATH)

        # see if face is recognized
        l = recognize_face(PHOTO_PATH)
        print(l)

        if len(l) and l != None:
            # add face to database to improve accuracy
            add_face(l[0]["uuid"], PHOTO_PATH)

            # remove photo from display list
            try:
                people_list.remove(l[0]["uuid"] + ".jpg")
                room_count -= 1
            except:
                print("Photo not found")
                pass

            

        # update the website with roomcount and images
        socketio.emit("reload", {"data": True})

    socketio.emit("counter", {"count": room_count})


# route to home page
@app.route("/")
def main():

    global people_list

    # Define the absolute path to the images folder
    image_folder = "/home/student/room_counter/static/pictures"

    # Filter and generate URLs for the specific images
    images = [url_for("static", filename=f"pictures/{img}") for img in people_list if os.path.exists(os.path.join(image_folder, img))]

    return render_template("home.html", images=images)


# main code 
if __name__ == "__main__":

    scheduler = APScheduler()
    scheduler.add_job(func=run_gesture, trigger="interval", id="job", seconds=0.1, max_instances=10)
    scheduler.start()

    # run the flask app
    app.run(host = "0.0.0.0", port=5000)
