import tweepy
import os
import random
import json
import requests
import datetime
from io import BytesIO
from dotenv import load_dotenv
from time import sleep

load_dotenv()

CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SV_API_KEY = os.getenv("STREETVIEW_API")

MDAPI = "https://maps.googleapis.com/maps/api/streetview/metadata?"
SVAPI = "https://maps.googleapis.com/maps/api/streetview?"

def gen_valid_point():
    with open("data/country-grab-bag.json", "r") as f:
        country_grab_bag = json.load(f)

    with open("data/bounding-boxes.json", "r") as f2:
        bounding_boxes = json.load(f2)

    country = random.choice(country_grab_bag)
    print(country)
    country_bounding_box = bounding_boxes[country][1]

    min_lat = country_bounding_box[1]
    max_lat = country_bounding_box[3]
    min_lon = country_bounding_box[0]
    max_lon = country_bounding_box[2]

    random_lat = round(random.uniform(min_lat, max_lat), 6)
    random_lon = round(random.uniform(min_lon, max_lon), 6)

    print(country, random_lat, random_lon)

    return (random_lat, random_lon)

def get_streetview_image(sv_params):
    r = requests.get(SVAPI, params=sv_params)
    
    # the following code is from @fitnr's
    # everylotbot: https://github.com/fitnr/everylotbot
    sv_image = BytesIO()
    
    for chunk in r.iter_content():
        sv_image.write(chunk)

    sv_image.seek(0)
    
    return sv_image

def create_tweet_text(loc, date):
    dt_obj = datetime.datetime.strptime(str(date), '%Y-%m')
    date_text = dt_obj.strftime('%B %Y')
    tweet_text = loc + "\n" + date_text
    return tweet_text

def get_tweet_contents():
    while True:
        coords = gen_valid_point()

        lat = coords[0]
        lon = coords[1]

        loc = str(lat) + "," + str(lon)
        params = {
            "location": loc,
            "key": SV_API_KEY,
            "radius": 10000
        }

        r = requests.get(MDAPI, params=params)

        if r.json()['status'] == "OK":
            print("streetview hit")
            print(r.url)
            
            new_lat = r.json()['location']['lat']
            new_lon = r.json()['location']['lng']
            rounded_lat = round(new_lat, 6)
            rounded_lon = round(new_lon, 6)

            loc = str(new_lat) + "," + str(new_lon)
            loc_txt = str(rounded_lat) + "," + str(rounded_lon)

            date = str(r.json()['date'])
            
            sv_params = {
                "location": loc,
                "heading": 0,
                "size": "800x450",
                "fov": 100,
                "pitch": 90,
                "direction": 0,
                "key": SV_API_KEY
            }
            image = get_streetview_image(sv_params)
            print("streetview image obtained")
            text = create_tweet_text(loc_txt, date)
            break
    
    return (image, text)

def main():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(KEY, SECRET)

    api = tweepy.API(auth)
    
    try:
        api.verify_credentials()
        print("Authentication OK")
    except:
        print("Error during authentication")

    while True:
        try:
            tweet = get_tweet_contents()
            media = api.media_upload('sv.jpg', file=tweet[0])
            api.update_status(status=tweet[1], media_ids=[media.media_id])
            print("tweeted", tweet[1])
            sleep(1800)
        except tweepy.TweepError as e:
            print(e.reason)

main()