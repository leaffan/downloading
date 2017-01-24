#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
from urllib.parse import urlparse, parse_qs
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

    def __init__(self, tgt_dir, language='de', quality='low'):
        # setting target directory
        self.tgt_dir = tgt_dir

        # setting video quality to be downloaded
        if quality.lower() in self.QUALITY_KEYS:
            self.quality = self.QUALITY_KEYS[quality.lower()]
        else:
            self.quality = 'MQ'

        # setting video language to be downloaded
        if language.lower() == 'fr':
            self.language = '2'
        else:
            self.language = '1'

        # combining key
        self.video_key = "_".join((
            self.PROTOCOL, self.FORMAT, self.quality, self.language))

    def download(self, url):
        """
        Downloads video from specified url.
        """
        # retrieving json struct with video information
        json_data = self.retrieve_json_struct(url)
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
        # retrieving broadcast title
        broadcast_title = json_data['videoJsonPlayer']['VST']['VNA']
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
            print("+ Downloading %d kB to %s:" % (tgt_bytes / 1024, tgt_path))

            for block in r.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                if not block:
                    break
                handle.write(block)
                sum_bytes += self.DOWNLOAD_CHUNK_SIZE
                pctg = float(sum_bytes) / tgt_bytes * 100.
                sys.stdout.write(
                    "%d kB downloaded: %.1f%%\r" % (sum_bytes / 1024, pctg))
                sys.stdout.flush()
            else:
                print()

    def retrieve_json_struct(self, url):
        """
        Retrieves json struct with all necessary information for video dowload
        from specified url.
        """
        broadcast_id = self.retrieve_broadcast_id(url)
        json_url = "".join((self.JSON_PREFIX, broadcast_id, self.JSON_SUFFIX))
        r = requests.get(json_url)
        return r.json()

    def retrieve_broadcast_id(self, url):
        """
        Retrieves broadcast id from specified url.
        """
        url_query_component = urlparse(url).query
        try:
            broadcast_id = parse_qs(
                url_query_component)[self.BROADCAST_ID_KEY].pop()
        except KeyError:
            return None
        return broadcast_id


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description='Download videos from ARTE media library.')
    arg_parser.add_argument('-d', '--directory', dest='tgt_dir', metavar='target_directory', required=True, help='Target directory for video downloads.')
    arg_parser.add_argument('urls_or_media_ids', metavar='video_urls/media_ids', help='Comma-separated list of video urls or media ids.')

    args = arg_parser.parse_args()

    sys.exit()

    tgt_dir = r"D:\dlds\vi"

    urls = list()
    urls.append("http://www.arte.tv/guide/de/plus7/?em=063711-001")
    urls.append("http://www.arte.tv/guide/de/plus7/?em=067846-011")

    dl = ArtePlus7Downloader(tgt_dir)

    for url in urls:
        dl.download(url)
