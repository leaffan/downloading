#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
from datetime import datetime

import requests
from dateutil import parser


class ArtePlus7Downloader():

    BROADCAST_ID_KEY = 'em'
    JSON_PREFIX = 'http://arte.tv/papi/tvguide/videos/stream/player/D/'
    JSON_SUFFIX = '_PLUS7-D/ALL/ALL.json'
    PROTOCOL = "HTTP"
    FORMAT = "MP4"
    QUALITY_KEYS = {'high': 'SQ', 'medium': 'MQ', 'low': 'EQ'}
    DOWNLOAD_CHUNK_SIZE = 65536
    BROADCAST_ID_REGEX = re.compile("\d{6}\-\d{3}")

    def __init__(self, tgt_dir, urls_media_ids, language='de', quality='low'):
        # setting target directory
        self.tgt_dir = tgt_dir

        # retrieving broadcast ids from specified string with urls and/or
        # broadcast ids
        self.broadcast_ids = self.retrieve_broadcast_ids(urls_media_ids)

        # setting video quality to be downloaded
        if quality.lower() in self.QUALITY_KEYS:
            self.quality = self.QUALITY_KEYS[quality.lower()]
        else:
            self.quality = 'MQ'

        # setting video language to be downloaded
        if language.lower() == 'de':
            self.language = '1'
        else:
            self.language = '2'

        # combining quality and language to unique key
        self.video_key = "_".join((
            self.PROTOCOL, self.FORMAT, self.quality, self.language))

    def download_all(self):
        """
        Downloads videos for all registered broadcast ids.
        """
        for broadcast_id in self.broadcast_ids:
            self.download(broadcast_id)

    def download(self, broadcast_id):
        """
        Downloads video for specified broadcast id.
        """
        # retrieving json struct with video information
        json_data = self.retrieve_json_struct(broadcast_id)

        if 'custom_msg' in json_data['videoJsonPlayer']:
            print(
                "+ Unable to retrieve video information for broadcast_id %s"
                % broadcast_id)
            return

        # setting up local file name for downloaded video
        file_name = self.build_file_name(json_data)
        # downloading video to local file
        self.retrieve_video(json_data, file_name)

    def build_file_name(self, json_data):
        """
        Builds file name for file to be downloaded from specified json data
        struct.
        """
        # first trying to retrieve broadcast date
        try:
            broadcast_date = parser.parse(
                json_data['videoJsonPlayer']['VDA'], dayfirst=True)
        # otherwise using current date
        except:
            broadcast_date = datetime.now()

        # trying to retrieve broadcast title
        try:
            broadcast_title = json_data['videoJsonPlayer']['VST']['VNA']
        # otherwise using alternative broadcast_title
        except:
            broadcast_title = json_data['videoJsonPlayer']['VTI']
            broadcast_title = broadcast_title.lower().replace(" ", "_")

        # combining broadcast date and title to resulting title
        return "_".join((
            broadcast_date.strftime("%Y-%m-%d"),
            broadcast_title)) + ".%s" % self.FORMAT.lower()

    def retrieve_video(self, json_data, file_name):
        """
        Retrieves actual video data - specified in json struct - to given
        file name.
        """
        # retrieving video url
        vid_url = json_data['videoJsonPlayer']['VSR'][self.video_key]['url']
        # connecting to video url
        r = requests.get(vid_url, stream=True)
        tgt_bytes = int(r.headers['content-length'])
        tgt_path = os.path.join(self.tgt_dir, file_name)

        # downloading video data
        with open(tgt_path, 'wb') as handle:
            sum_bytes = 0
            print("+ Downloading %d kB to %s" % (tgt_bytes / 1024, tgt_path))

            for block in r.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                if not block:  # or sum_bytes > 500000:
                    break
                handle.write(block)
                sum_bytes += self.DOWNLOAD_CHUNK_SIZE
                pctg = float(sum_bytes) / tgt_bytes * 100.
                sys.stdout.write(
                    "%d kB downloaded: %.1f%%\r" % (sum_bytes / 1024, pctg))
                sys.stdout.flush()
            else:
                print()

    def retrieve_json_struct(self, broadcast_id):
        """
        Retrieves json struct with all necessary information for video dowload
        from specified url.
        """
        json_url = "".join((self.JSON_PREFIX, broadcast_id, self.JSON_SUFFIX))
        r = requests.get(json_url)
        return r.json()

    def retrieve_broadcast_ids(self, urls_or_ids):
        """
        Converts items from specified string into valid broadcast ids.
        """
        broadcast_ids = list()

        raw_urls_or_ids = [s.strip() for s in urls_or_ids.split(",")]

        for url_or_id in raw_urls_or_ids:
            match = re.search(self.BROADCAST_ID_REGEX, url_or_id)
            if match:
                broadcast_ids.append(match.group(0))

        return broadcast_ids


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(
        description='Download videos from ARTE media library.')
    arg_parser.add_argument(
        '-d', '--directory', dest='tgt_dir', metavar='target_directory',
        required=True, help='Target directory for video downloads.')
    arg_parser.add_argument(
        'urls_or_media_ids', metavar='video_urls/media_ids',
        help='Comma-separated list of video urls or media ids.')
    args = arg_parser.parse_args()

    dl = ArtePlus7Downloader(args.tgt_dir, args.urls_or_media_ids)
    dl.download_all()
