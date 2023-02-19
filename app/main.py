from flask import Flask, make_response, redirect, url_for, request
from random_photos import RandomPhotos
import cv2
import google_auth
import os
from dotenv import load_dotenv
import sys

load_dotenv()

app = Flask(__name__)
PASSWORD = os.environ.get("PASSWORD", default=False)
app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)
rp = RandomPhotos()

app.register_blueprint(google_auth.app)

rp.run()


@app.route("/random_image.jpg")
def get_image():
    auth_images()
    if PASSWORD:
        if request.args.get('password', default=None, type=str) != PASSWORD:
            return('Invalid password')
    img = rp.get_photo()
    ret, jpeg = cv2.imencode('.jpg', img)
    response = make_response(jpeg.tobytes())
    response.headers['Content-Type'] = 'image/png'
    return response

@app.route("/status")
def queue_status():
    return "Current queue contains %s photos" % len(rp.photo_queue)

def auth_images():
    if rp.check_running():
        print("Is running")
        if not rp.creds:
            print("no rp creds")
            if google_auth.is_logged_in():
                print("Is logged in")
                rp.creds = google_auth.build_credentials()
                rp.check_auth()
            else:
                return redirect(url_for('google_auth.login'))
        else:
            return True
    else:
        print("Service not running")

@app.route("/")
def index():
    if google_auth.is_logged_in():
        print("Logged in!")
        return redirect(url_for('get_image'))
    return redirect(url_for('google_auth.login'))


@app.route('/shutdown')
def shutdown():

    if PASSWORD:
        if request.args.get('password', default=None, type=str) != PASSWORD:
            return('Invalid password')
    print("Shut down")
    rp.stop()
    sys.exit()
    os.exit(0)
    return

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8040)
