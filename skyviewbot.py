#!/opt/miniconda3/envs/skyviewbot/python
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

# twitter API keys
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
# streetview API key
SV_API_KEY = os.getenv("STREETVIEW_API")
# path for cron
PATH = os.getenv("ABS_PATH")

# streetview metadata API
MDAPI = "https://maps.googleapis.com/maps/api/streetview/metadata?"
# streetview API
SVAPI = "https://maps.googleapis.com/maps/api/streetview?"

def gen_valid_point():
    # list of country codes with decent street view coverage by area, 
    # ex. russia is represented many times whereas japan is not. 
    # this is to try to align a country's land area with the 
    # probability of choosing it
    country_list_json = PATH + "data/country-grab-bag.json"
    with open(country_list_json, "r") as f:
        country_grab_bag = json.load(f)

    # lat lon bounding boxes for each country
    bounding_boxes_json = PATH + "data/bounding-boxes.json"
    with open(bounding_boxes_json, "r") as f2:
        bounding_boxes = json.load(f2)

    # choose a random country code (skewed toward larger countries)
    # tbh should be skewed based on streetview imagery, but w/e
    country = random.choice(country_grab_bag)

    # get bounding box
    country_bounding_box = bounding_boxes[country][1]

    min_lat = country_bounding_box[1]
    max_lat = country_bounding_box[3]
    min_lon = country_bounding_box[0]
    max_lon = country_bounding_box[2]

    # pick a random location within the country's bounding box
    random_lat = round(random.uniform(min_lat, max_lat), 6)
    random_lon = round(random.uniform(min_lon, max_lon), 6)

    print(country, random_lat, random_lon)

    return (random_lat, random_lon)

# note: image is never saved locally, just sent to twitter
def get_streetview_image(sv_params):
    r = requests.get(SVAPI, params=sv_params)
    
    # the following code is from @fitnr's
    # everylotbot: https://github.com/fitnr/everylotbot
    sv_image = BytesIO()
    
    for chunk in r.iter_content():
        sv_image.write(chunk)

    sv_image.seek(0)
    
    return sv_image

# convert date object to text
def create_tweet_text(loc, date):
    dt_obj = datetime.datetime.strptime(str(date), '%Y-%m')
    date_text = dt_obj.strftime('%B %Y')
    tweet_text = loc + "\n" + date_text
    return tweet_text

def get_tweet_contents():
    while True:
        # random point within a country's bounding box
        coords = gen_valid_point()

        lat = coords[0]
        lon = coords[1]

        loc = str(lat) + "," + str(lon)
        params = {
            "location": loc,
            "key": SV_API_KEY,
            "radius": 10000
        }

        # check if imagery exists within 10,000 m of the 
        # selected point using metadata API
        r = requests.get(MDAPI, params=params)

        # if it does, get imagery
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
                "fov": 120,
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

    # tweet sky view image
    tweet = get_tweet_contents()
    media = api.media_upload('sv.jpg', file=tweet[0])
    api.update_status(status=tweet[1], media_ids=[media.media_id])
    print("tweeted", tweet[1])

main()