#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
from datetime import datetime

import requests
from dateutil import parser


class ArdDownloader():

    BROADCAST_ID_KEY = "documentId"
    JSON_VIDEO_PREFIX = "http://www.ardmediathek.de/play/media/"
    JSON_METADATA_PREFIX = "http://www.ardmediathek.de/play/sola/"
    FORMAT = "MP4"
    QUALITY_KEYS = {'very_high': 3, 'high': 2, 'medium': 1, 'low': 0}
    DOWNLOAD_CHUNK_SIZE = 65536
    BROADCAST_ID_REGEX = re.compile("%s=(\d+)" % BROADCAST_ID_KEY)
    DATE_REGEX = re.compile("\/(\d{4})\/(\d{2})\/?(\d{2})\/")

    def __init__(self, tgt_dir, urls, quality='medium'):
        """
        Initializes downloader with target directory, video quality and list
        of broadcast ids to be downloaded.
        """

        # setting target directory
        self.tgt_dir = tgt_dir

        # setting video quality to be downloaded
        if quality.lower() in self.QUALITY_KEYS:
            self.quality = self.QUALITY_KEYS[quality.lower()]
        else:
            self.quality = 2

        self.broadcast_ids = self.retrieve_broadcast_ids(urls)

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
        json_meta_data = self.retrieve_json_struct(
            "".join((self.JSON_METADATA_PREFIX, broadcast_id)))
        json_video_data = self.retrieve_json_struct(
            "".join((self.JSON_VIDEO_PREFIX, broadcast_id)))

        file_name = self.build_file_name(json_meta_data, json_video_data)
        self.retrieve_video(json_video_data, file_name)

    def retrieve_json_struct(self, json_url):
        """
        Retrieves json struct from specified url.
        """
        r = requests.get(json_url)
        return r.json()

    def retrieve_video(self, json_data, file_name):
        """
        Retrieves actual video data - specified in json struct - to given
        file name.
        """
        media_array = json_data['_mediaArray']
        # finding entry with desired quality
        idx = next(index for (index, d) in enumerate(media_array[-1][
            '_mediaStreamArray']) if d["_quality"] == self.quality)
        vid_url = media_array[-1]['_mediaStreamArray'][idx]['_stream']

        if type(vid_url) is list:
            vid_url = vid_url[0]

        r = requests.get(vid_url, stream=True)
        tgt_bytes = int(r.headers['content-length'])
        tgt_path = os.path.join(self.tgt_dir, file_name)

        with open(tgt_path, 'wb') as handle:
            sum_bytes = 0
            print("Downloading %d kB to %s" % (tgt_bytes / 1024, tgt_path))

            for block in r.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                if not block:  # or sum_bytes > 200000:
                    break
                handle.write(block)
                sum_bytes += self.DOWNLOAD_CHUNK_SIZE
                if sum_bytes > tgt_bytes:
                    sum_bytes = tgt_bytes
                pctg = float(sum_bytes) / tgt_bytes * 100.
                sys.stdout.write(
                    "%d kB downloaded: %.1f%%\r" % (sum_bytes / 1024, pctg))
                sys.stdout.flush()
            else:
                print()

    def build_file_name(self, json_meta_data, json_video_data):
        """
        Builds file name for file to be downloaded from specified json data
        struct.
        """
        arbitrary_stream_url = json_video_data[
            '_mediaArray'][0]['_mediaStreamArray'][0]['_stream']

        match = re.search(self.DATE_REGEX, arbitrary_stream_url)
        if match:
            broadcast_date = parser.parse(
                "%s/%s/%s" % (match.group(1), match.group(2), match.group(3)))
        else:
            broadcast_date = datetime.now()

        broadcast_title = json_meta_data['metadata']['title']
        broadcast_title = broadcast_title.split(
            ",")[0].lower().replace(" ", "_").replace(":", "_")

        return "_".join((
            broadcast_date.strftime("%Y-%m-%d"),
            broadcast_title)) + ".%s" % self.FORMAT.lower()

    def retrieve_broadcast_ids(self, urls):
        """
        Converts items from specified string of urls into valid broadcast ids.
        """
        broadcast_ids = list()

        list_of_urls = [s.strip() for s in urls.split(",")]

        for url in list_of_urls:
            match = re.search(self.BROADCAST_ID_REGEX, url)
            if match:
                broadcast_ids.append(match.group(1))

        return broadcast_ids


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(
        description='Download videos from ARD media library.')
    arg_parser.add_argument(
        '-d', '--directory', dest='tgt_dir', metavar='target_directory',
        required=True, help='Target directory for video downloads.')
    arg_parser.add_argument(
        '-q', '--quality', dest='quality', metavar='video quality',
        required=False, choices=['very_high', 'high', 'medium', 'low'],
        default='medium', help='Quality of downloaded videos')
    arg_parser.add_argument(
        'urls', metavar='video_urls',
        help='Comma-separated list of video urls.')
    args = arg_parser.parse_args()

    dl = ArdDownloader(
        args.tgt_dir, args.urls, quality=args.quality)
    dl.download_all()
