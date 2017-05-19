#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

import requests
import json

from dateutil.parser import parse
from lxml import html


class ZdfDownloader():

    QUALITY_KEYS = ['veryhigh', 'high', 'low']
    BROADCAST_BASE_URL = (
        "https://api.zdf.de/tmd/2/ngplayer_2_3/vod/ptmd/mediathek/")
    TGT_MIME_TYPE = 'video/mp4'
    DOWNLOAD_CHUNK_SIZE = 524288

    def __init__(self, tgt_dir, urls, quality='high'):
        # setting target directory
        self.tgt_dir = tgt_dir
        # setting urls for videos to be downloaded
        self.urls = [url.strip() for url in urls.split(",")]
        # setting video quality to be downloaded
        if quality.lower() in self.QUALITY_KEYS:
            self.quality = quality.lower()
        else:
            self.quality = 'high'

    def download_all(self):
        """
        Downloads videos for all specified urls.
        """
        for url in self.urls:
            self.retrieve_content_json_url(url)
            self.retrieve_broadcast_id()
            self.retrieve_video_url()
            file_name = self.build_file_name()
            self.retrieve_video(self.vid_url, file_name)

    def create_auth_headers(self):
        self.auth_headers = {'Api-Auth': " ".join(
            ("Bearer", self.auth_api_token))}

    def retrieve_content_json_url(self, url):
        """
        Retrieves url to json page with video meta data. Additionally retrieves
        authorization token to be applied when accessing urls further on.
        """
        req = requests.get(url)
        doc = html.fromstring(req.text)
        # authorization api token and url to json page are contained by a
        # json structure inside a div tag attribute value
        raw_broadcast_info = doc.xpath(
            "//article[@class='b-video-module']/descendant::div" +
            "[@class='b-playerbox b-ratiobox js-rb-live']/@data-zdfplayer-jsb")
        raw_broadcast_info = raw_broadcast_info.pop(0).strip()
        raw_broadcast_info = json.loads(raw_broadcast_info)

        # retrieving actual json page url and authorization api token
        self.content_json_url = raw_broadcast_info['content']
        self.auth_api_token = raw_broadcast_info['apiToken']
        # setting up authorization headers
        self.create_auth_headers()

    def retrieve_broadcast_id(self):
        """
        Retrieves broadcast id for video to be downloaded.
        """
        req = requests.get(self.content_json_url, headers=self.auth_headers)
        jdata = req.json()
        # best way to retrieve broadcast is via tracking attributes for video
        # to be downloaded
        self.broadcast_id = jdata['tracking']['nielsen']['content']['uurl']
        # broadcast date
        self.broadcast_date = parse(jdata['editorialDate'])

    def retrieve_video_url(self):
        """
        Retrieves url to actual video file to be downloaded
        """
        # setting url to json page containing actual stream information
        url = "".join((self.BROADCAST_BASE_URL, self.broadcast_id))
        req = requests.get(url, headers=self.auth_headers)
        jdata = req.json()
        for variant in jdata['priorityList']:
            # multiple video formats are available
            for vid_format in variant['formitaeten']:
                # choosing target video format
                if vid_format['mimeType'] == self.TGT_MIME_TYPE:
                    # multiple qualities are available
                    for quality in vid_format['qualities']:
                        # choosing target video quality
                        if quality['quality'] == self.quality:
                            self.vid_url = quality['audio']['tracks'][0]['uri']
                            break

    def build_file_name(self):
        """
        Builds target file name.
        """
        # setting up a file name containing broadcast date and id
        basename = "_".join((
            self.broadcast_date.strftime("%Y-%m-%d"), self.broadcast_id))
        return ".".join((basename, 'mp4'))

    def retrieve_video(self, vid_url, file_name):
        """
        Retrieves actual video data and downloads it to specified file name in
        class-wide target directory.
        """
        # connecting to video url
        req = requests.get(vid_url, stream=True)
        tgt_bytes = int(req.headers['content-length'])
        tgt_path = os.path.join(self.tgt_dir, file_name)

        # downloading video data
        with open(tgt_path, 'wb') as handle:
            sum_bytes = 0
            print("+ Downloading %d kB to %s" % (tgt_bytes / 1024, tgt_path))

            for block in req.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                if not block:  # or sum_bytes > 5000000:
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


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(
        description='Download videos from ZDF media library.')
    arg_parser.add_argument(
        '-d', '--directory', dest='tgt_dir', metavar='target_directory',
        required=True, help='Target directory for video downloads.')
    arg_parser.add_argument(
        '-q', '--quality', dest='quality', metavar='video quality',
        required=False, choices=['veryhigh', 'high', 'low'], default='high',
        help='Quality of downloaded videos')
    arg_parser.add_argument(
        'urls', metavar='video_urls',
        help='Comma-separated list of video urls.')
    args = arg_parser.parse_args()

    dl = ZdfDownloader(args.tgt_dir, args.urls, quality=args.quality)
    dl.download_all()
