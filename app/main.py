from flask import Flask, make_response, redirect, url_for, request
from random_photos import RandomPhotos
import cv2
import google_auth
import os
from dotenv import load_dotenv
import sys
import logging
from functools import wraps
from flask import g, request, redirect, url_for
try:
    from cStringIO import StringIO      # Python 2
except ImportError:
    from io import StringIO

log_stream = StringIO()


load_dotenv()

app = Flask(__name__)
PASSWORD = os.environ.get("PASSWORD", default=False)
app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)
LOG_LEVEL = os.environ.get("LOG_LEVEL", default=False)

if not LOG_LEVEL:
    LOG_LEVEL = logging.ERROR
elif LOG_LEVEL.lower() == "debug":
    LOG_LEVEL = logging.DEBUG
elif LOG_LEVEL.lower() == "info":
    LOG_LEVEL = logging.INFO
elif LOG_LEVEL.lower() == "warning":
    LOG_LEVEL = logging.WARNING
elif LOG_LEVEL.lower() == "error":
    LOG_LEVEL = logging.ERROR

rp = RandomPhotos()

app.register_blueprint(google_auth.app)

rp.run()




def check_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.args.get('password', default=None, type=str) != PASSWORD:
            logger.debug("Invalid password")
            return "No"
        return f(*args, **kwargs)
    return decorated_function


@app.route("/random_image.jpg")
@check_password
def get_image():
    logger.debug("Getting image")
    auth_images()
    img = rp.get_photo()
    ret, jpeg = cv2.imencode('.jpg', img)
    response = make_response(jpeg.tobytes())
    response.headers['Content-Type'] = 'image/png'
    return response

@app.route("/status")
@check_password
def status():
    logs = "<br>".join(log_stream.getvalue().replace(PASSWORD, '************').splitlines()[-40:])
    return "Collector Running: %s<br><br>Photo Queue Size: %s photos<br><br>Session Logged in: %s<br><br>Collector Logged In: %s<br><br>Threads: %s<br><br>Logs:<br>%s" % (rp.check_running(), len(rp.photo_queue), google_auth.is_logged_in(), rp.check_auth(), len(rp.threads), logs)

def auth_images():
    if rp.check_running():
        logger.debug("Is running")
        if not rp.creds:
            logger.debug("no rp creds")
            if google_auth.is_logged_in():
                logger.debug("Is logged in")
                rp.creds = google_auth.build_credentials()
                rp.check_auth()
            else:
                return redirect(url_for('google_auth.login'))
        else:
            return True
    else:
        logger.error("Service not running")

@app.route("/unauthorize")
def unauthorize():
    rp.creds = False
    return "Success"

@app.route("/authorize")
def authorize():
    rp.creds = google_auth.build_credentials()
    rp.check_auth()
    return "Success"

@app.route("/")
def index():
    if google_auth.is_logged_in():
        logger.debug("Logged in!")
        return redirect(url_for('get_image'))
    return redirect(url_for('google_auth.login'))


@app.route('/shutdown')
def shutdown():

    if PASSWORD:
        if request.args.get('password', default=None, type=str) != PASSWORD:
            return('Invalid password')
    logger.debug("Shut down")
    rp.stop()
    sys.exit()
    os.exit(0)
    return

if __name__ == "__main__":

    logging.basicConfig(stream=log_stream, level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)



    if LOG_LEVEL == logging.DEBUG:
        app.run(host='0.0.0.0', port=8040, debug=True)
    else:
        app.run(host='0.0.0.0', port=8040)
