from __future__ import print_function
from googleapiclient.discovery import build
import random
import datetime
import cv2
import urllib.request
import numpy as np
import time
import threading
import googleapiclient
import google_auth_httplib2
import httplib2
import traceback

def random_date(start, end):
    """
    This function will return a random datetime between two datetime
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + datetime.timedelta(seconds=random_second)


class RandomPhotos:
    def __init__(self, blurry_threshold=900, min_resolution=(1920, 1080), album_filter=[], exclude_categories=['UTILITY', 'RECEIPTS', 'DOCUMENTS'], include_categories=[], min_year=2010, threads=5, queue_min=10):
        self.blurry_threshold = blurry_threshold
        self.min_resolution = min_resolution
        self.album_filter = album_filter
        self.exclude_categories = exclude_categories
        self.include_categories = include_categories
        self.min_year = min_year
        self.queue_min = queue_min

        self.albums = []
        self.photo_queue = []
        self.thread_count = threads
        self.threads = []
        self.running = False
        self.creds = False
        self.last_photo = cv2.imread('placeholder.jpg')
        self.google_photos = False

    def check_auth(self):
        try:
            if not self.creds:
                return False
            else:
                self.authorized_http = google_auth_httplib2.AuthorizedHttp(self.creds, http=httplib2.Http())
                self.google_photos = build('photoslibrary', 'v1', requestBuilder=self.build_request,
                                           http=self.authorized_http,
                                           static_discovery=False)
        except AttributeError:
            return False

        return True

    def build_request(self, http, *args, **kwargs):
        new_http = google_auth_httplib2.AuthorizedHttp(self.creds, http=httplib2.Http())
        return googleapiclient.http.HttpRequest(new_http, *args, **kwargs)

    def run(self):

        self.running = True
        print("Running: %s" % self.running)
        for i in range(0, self.thread_count):
            thread = threading.Thread(target=self.manage_queue)
            print("Starting thread %s" % i)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

        print("Done starting threads")
        print("Running: %s" % self.running)
        return True

    def check_running(self):
        return self.running

    def stop(self):
        self.running = False


    def manage_queue(self):
        while self.running:
            while not self.check_auth() and self.running:
                print("Not authenticated - waiting for auth to begin threads.")
                time.sleep(5)
            if len(self.photo_queue) < self.queue_min and self.check_auth():
                try:
                    print("Queue less than 4, getting another photo")
                    photo_sources = [self.get_random_photo, self.get_random_album_photo]
                    source = random.choice(photo_sources)
                    new_photo = None
                    while new_photo is None:
                        new_photo = source()
                    self.photo_queue.append(new_photo)
                except Exception as err:
                    print(err)
                    traceback.print_exc()
            else:
                time.sleep(random.randint(3, 8))

    def get_photo(self):
        if len(self.photo_queue) > 0:
            self.last_photo = self.photo_queue.pop()
            return self.last_photo
        else:
            return self.last_photo

    def get_albums(self):
        print("Getting albums")
        request = self.google_photos.albums().list()
        while request is not None:
            res = request.execute()
            for album in res['albums']:
                if 'title' in album:
                    self.albums.append(album)
                else:
                    print(album)
            request = self.google_photos.albums().list_next(request, res)
        print("Got %s albums" % len(self.albums))

    def get_random_album_photo(self):
        if len(self.albums) == 0:
            self.get_albums()
            if len(self.albums) == 0:
                raise ValueError("No albums found")

        selected_albums = []
        if len(self.album_filter) > 0:
            for album in self.album_filter:
                try:
                    print(album)
                    match = next((item for item in self.albums if item["title"].lower() == album.lower()), None)
                    if match:
                        selected_albums.append(match)
                except KeyError as err:
                    print(err)
        else:
            selected_albums = self.albums

        print("Selecting random album from %s options" % len(selected_albums))
        album = random.choice(selected_albums)

        body = {"albumId": album['id']}

        photos = []
        request = self.google_photos.mediaItems().search(body=body)
        while request is not None:
            res = request.execute()
            for photo in res['mediaItems']:
                photos.append(photo)
            request = self.google_photos.mediaItems().search_next(request, res)

        result_image = None
        while result_image is None:
            if len(photos) == 0:
                return None

            random_photo = random.choice(photos)

            photos.pop(photos.index(random_photo))

            if random_photo['mediaMetadata']['width'] < random_photo['mediaMetadata']['height']:
                print("Image is vertical")
                print(random_photo['baseUrl'])
                continue

            if int(random_photo['mediaMetadata']['width']) < self.min_resolution[0]:
                print("Image too small")
                continue

            url_response = urllib.request.urlopen(random_photo['baseUrl'])
            img = cv2.imdecode(np.array(bytearray(url_response.read()), dtype=np.uint8), -1)

            laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
            print(laplacian_var)
            if laplacian_var < self.blurry_threshold:
                print("Image blurry")
                continue

            # Get Full Size Image
            url = "%s=w%s-h%s" % (random_photo['baseUrl'], random_photo['mediaMetadata']['width'],
                                  random_photo['mediaMetadata']['height'])
            print(url)
            url_response = urllib.request.urlopen(url)
            img_full = cv2.imdecode(np.array(bytearray(url_response.read()), dtype=np.uint8), -1)
            result_image = img_full
        return result_image

    def get_random_photo(self):
        result_image = None
        while result_image is None:
            currentDateTime = datetime.datetime.now()
            date = currentDateTime.date()
            year = date.strftime("%Y")
            random_date_start = datetime.date(random.randint(self.min_year, int(year)), random.randint(1, 12),
                                              random.randint(1, 28))
            random_date_end = random_date_start + datetime.timedelta(days=365)

            start_year = random_date_start.year
            start_month = random_date_start.month
            start_day = random_date_start.day

            end_year = random_date_start.year
            end_month = random_date_start.month
            end_day = random_date_start.day

            print(random_date_start)
            print(random_date_end)
            body = {"filters": {"mediaTypeFilter": {"mediaTypes": ["PHOTO"]},
                                "contentFilter": {},
                                "dateFilter": {"ranges": [
                                    {"startDate": {"year": start_year, "month": start_month, "day": start_day},
                                     "endDate": {"year": end_year, "month": end_month, "day": end_day}}]}
                                }
                    }
            if self.include_categories:
                body['filters']['contentFilter']['includedContentCategories'] = self.include_categories
            if self.exclude_categories:
                body['filters']['contentFilter']['excludedContentCategories'] = self.exclude_categories

            items = self.google_photos.mediaItems().search(body=body).execute()
            if len(items) == 0:
                print("No photos found for date.")
                continue

            if "mediaItems" in items:
                random_photo = random.choice(items['mediaItems'])
                print(random_photo)
                # Filter for landscape photos

                if random_photo['mediaMetadata']['width'] < random_photo['mediaMetadata']['height']:
                    print("Image is vertical")
                    print(random_photo['baseUrl'])
                    continue

                if int(random_photo['mediaMetadata']['width']) < self.min_resolution[0]:
                    print("Image too small")
                    continue

                url_response = urllib.request.urlopen(random_photo['baseUrl'])
                img = cv2.imdecode(np.array(bytearray(url_response.read()), dtype=np.uint8), -1)

                laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
                print(laplacian_var)
                if laplacian_var < self.blurry_threshold:
                    print("Image blurry")
                    continue

                # Get Full Size Image
                url = "%s=w%s-h%s" % (random_photo['baseUrl'], random_photo['mediaMetadata']['width'],
                                      random_photo['mediaMetadata']['height'])
                print(url)
                url_response = urllib.request.urlopen(url)
                img_full = cv2.imdecode(np.array(bytearray(url_response.read()), dtype=np.uint8), -1)
                result_image = img_full

            time.sleep(2)
        return result_image

if __name__ == "__main__":
    rp = RandomPhotos()
    rp.run()

    image = rp.get_photo()
    cv2.imshow("Photo", image)
    cv2.waitKey(3)
