from collections import Counter, namedtuple
import configparser
from pprint import pprint
import sys
from typing import List
import pytesseract 
from glob import glob
import time
import cv2
import subprocess
import json
import os
from getpass import getpass
from os import sep
import re

from src import helpers
from src.opencvfilters import OpenCVFilters
from src.peertube_tools import PeertubeUploader, PeertubeChannel
from src.tesseractoperations import TesseractProcessor

if sys.platform == "win32":
    print("changing path")
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

for d in ["cropped_frames", "chapters", "frames"]:
    if not os.path.exists(d):
        os.mkdir(d)

ranks = open("ranks.txt", "r").read().split("\n")
ranks = [f"({r})" for r in ranks]

start_time = time.time()

gpu_preset = ""#"-c:v h264_nvenc -preset fast"

filter_config = OpenCVFilters(json.loads(open("foxhole_greentext.json", "r").read())).config
tesseract_operations = TesseractProcessor(ranks, filter_config)

snip_tuple = namedtuple("SnipPoint", "location seconds_into_video")
chapter_tuple = namedtuple("Chapter", "filename location timestamp")

class Chapter:
    def __init__(self, filename, timestamp, start, end, location):
        self.filename = filename
        self.timestamp = timestamp
        self.start = start
        self.end = end
        self.location = location

    def create_video(self):
        timestamp = helpers.generate_readable_timestamp(self.timestamp)
        new_filename = f'chapters/Foxhole - {self.location} {timestamp}{time.tzname[0]}.mkv'
        command = f'ffmpeg -hwaccel auto -ss {self.start} -i "{self.filename}" -t {self.end-self.start} "{new_filename}" -y'
        print(command)
        subprocess.call(command, shell=True)
        self.chapter_filename = new_filename
        return chapter_tuple(new_filename, self.location, timestamp)
    
    def generate_description(self, playername):
        names = get_names_for_video(self.chapter_filename, playername)
        description = "Players recognised in this video: \n"
        for name in names:
            seconds_into_video = int(names[name].split(sep)[1].split(".")[0])
            description += f'- {name} at {seconds_to_minutes(seconds_into_video)}'
        return description

class RawVideo:
    def __init__(self, filename):
        self.filename = filename

    def create_chapters(self):
        print("CREATING CHAPTERS")
        self.chapters = []
        timestamp = helpers.get_timestamp_from_file(self.filename)
        snip_points = self.extract_and_check_spawn_location()
        print("SNIP POINTS", snip_points)

        for x in range(len(snip_points)-1):
            self.chapters.append(Chapter(self.filename, 
                                         timestamp + snip_points[x].seconds_into_video,
                                         snip_points[x].seconds_into_video,
                                         snip_points[x+1].seconds_into_video,
                                         snip_points[x].location))
            
        return self.chapters


    def extract_and_check_spawn_location(self) -> List[snip_tuple]:
        existing = glob("cropped_frames/*.png")
        [os.remove(e) for e in existing]
        snip_points = [snip_tuple("video start", 0)]
        label_position = "crop=1000:65:512:726"
        command = f'ffmpeg -hwaccel auto -i "{self.filename}" -vf "{label_position}" -r 1 cropped_frames/%08d.png'
        subprocess.call(command, shell=True)
        frames = glob("cropped_frames/????????.png")
        frames.sort()
        cooldown = 0

        for i in range(len(frames)):
            if cooldown < 1:
                img = cv2.imread(frames[i])
                text = pytesseract.image_to_string(img, config =f'--psm 7')
                for place in get_valid_placenames():
                    if place in text:
                        print(frames[i], i, place)
                        cooldown = 30
                        snip_points.append(snip_tuple(place, i))
                        break
            cooldown -= 1
        return snip_points


def get_valid_placenames():
    map_data = json.loads(open("mapData.json").read())
    valid_names = []
    for region in map_data:
        valid_names += [item["text"] for item in region["mapTextItems"] if item["mapMarkerType"] == "Major"]
    return valid_names

def extract_frames(filename):
    #delete frames
    existing = glob("frames/*.png")
    [os.remove(e) for e in existing]
    command = f'ffmpeg -i "{filename}" -r 1 frames/%08d.png'
    subprocess.call(command, shell=True)


def get_names_for_video(filename, playername):
    extract_frames(filename)
    files = glob("frames/????????.png")
    files.sort(reverse=True)
    player_mentions = []
    player_names = {}

    for f in files:
        img = cv2.imread(f)
        img, mask = tesseract_operations.apply_filters(img)
        names = tesseract_operations.scrape_names(img)
        if names: 
            print(f'processing {f}')
            for name in names:
                player_mentions.append(name)
                player_names[name] = f
        pprint(player_names)

    mention_counts = Counter(player_mentions)
    print(player_mentions)
    repeated_mentions = [k for k, v in mention_counts.items() if v > 2]
    player_names = {k: v for k,v in player_names.items() if k in repeated_mentions}
    player_names[playername] = files[-1]
    print(f'processing took {time.time() - start_time} seconds')
    player_names = dict(sorted(player_names.items()))
    return player_names


def seconds_to_minutes(seconds):
    minutes = seconds / 60
    seconds_left = seconds % 60
    return f'{int(minutes)}:{int(seconds_left):02}\n'


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    if "peertube" not in config.sections():
        config["peertube"] = {}
    if "foxhole" not in config.sections():
        config["foxhole"] = {}

    def get_or_ask(parent, field, challenge, input=input):
        if parent.get(field): return parent[field]
        parent[field] = input(challenge)
        return parent[field]

    domain_url = get_or_ask(config["peertube"], "domain_url", "enter peertube domain url: ", input)
    username = get_or_ask(config["peertube"], "username", 'enter peertube username: ', input)
    password = get_or_ask(config["peertube"], "password", "enter peertube password: ", getpass)
    channel_name = get_or_ask(config["peertube"], "channel_name", "enter the name of the target peertube channel: ", input)

    playername = get_or_ask(config["foxhole"], "playername", "enter your foxhole username: ", input)
    print(f'domain is {domain_url}')

    with open("config.ini", "w") as configfile:
        config.write(configfile)
    
    original_filename = sys.argv[1]
    uploader = PeertubeUploader(domain_url, username, password)
    playlist = uploader.create_playlist(f'Foxhole Session {original_filename}')
    channel = PeertubeChannel(domain_url,channel_name=channel_name)

    raw_video = RawVideo(original_filename)
    chapters = raw_video.create_chapters()

    print("CHAPTERS", chapters)

    for chapter in chapters:
        print(chapters)
        print(chapter.__dict__)
        chapter.create_video()
        filename = chapter.chapter_filename
        timestamp = chapter.timestamp
        description = chapter.generate_description(playername)
        video = uploader.upload_file(filename,channel.id,filename.split(sep)[-1].split(".")[0],["foxhole", "gameplay", chapter.location],2,description)
        # pluginData seems to be broken so use originallyPublishedAt for exact start of video for synchronisation
        video.set_property("originallyPublishedAt", timestamp)
        playlist.add_video(video.video_id)
        print(description)
