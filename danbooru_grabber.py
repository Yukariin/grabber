#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import hashlib
import os
import sys

from functools import partial
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    print("Requests lib was not found!")
    sys.exit(1)


class Grabber():
    def __init__(self, query, search_method):
        self.board_url = "http://donmai.us"
        self.query = query.strip()
        self.search_method = search_method
        self.login = None
        self.password = None
        self.page = 1
        self.page_limit = 0
        self.post_limit = 200
        self.threads = 10
        self.blacklist = "scat comic hard_translated".split()
        self.total_result = []
        self.total_post_count = 0
        self.download_count = 0
        self.downloaded_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.quiet = False
        self.pic_dir = os.path.expanduser("~") + "/Pictures"
        
        if self.query.startswith("pool:") and self.search_method != "pool":
            self.search_method = "pool"
            self.query = self.query.replace("pool:", "")
        if self.query.startswith("id:") and self.search_method != "post":
            self.search_method = "post"
            self.query = self.query.replace("id:", "")
        
    def downloader(self, file_url, file_name, md5):
        def md5sum(file_name):
            with open(file_name, "rb") as file_to_check:
                hasher = hashlib.md5()
                for buf in iter(partial(file_to_check.read, 128), b""):
                    hasher.update(buf)
            return hasher.hexdigest()
        
        def get(file_url, file_name):
            self.download_count += 1
            r = requests.get(file_url, stream = True)
            if r.status_code == requests.codes.ok:
                print("{}/{}".format(self.download_count, self.total_post_count),
                      "({}%)".format(round(self.download_count/(self.total_post_count/100))),
                      "downloading", file_name)
                with open(file_name, "wb") as f:
                    for block in r.iter_content(1024):
                        if block:
                            f.write(block)
                self.downloaded_count += 1
            else:
                self.error_count += 1
                print("{}/{}".format(self.download_count, self.total_post_count),
                      "({}%)".format(round(self.download_count/(self.total_post_count/100))),
                      file_name, "downloading failed, status code is:", r.status_code)
            
        if os.path.exists(file_name) and os.path.isfile(file_name):
            if md5sum(file_name) == md5:
                self.download_count += 1
                self.skipped_count += 1
                if not self.quiet:
                    print("{}/{}".format(self.download_count, self.total_post_count),
                           "({}%)".format(round(self.download_count/(self.total_post_count/100))),
                           "md5 match! Skipping download.")
            else:
                os.remove(file_name)
                get(file_url, file_name)
        else:
            get(file_url, file_name)
  
    def parser(self, post):
        file_url = self.board_url + post["file_url"]
        file_name = "{} - {}.{}".format("Donmai.us", post["id"], post["file_ext"])
        md5 = post["md5"]
        
        if self.blacklist:
            if not post["is_blacklisted"]:
                self.downloader(file_url, file_name, md5)
        else:
            self.downloader(file_url, file_name, md5)
            
    def prepare(self):
        if self.blacklist:
            if self.search_method == "tag":
                for tag in self.query.split():
                    if tag in self.blacklist:
                        self.blacklist.remove(tag)
            for post in self.total_result:
                post["is_blacklisted"] = False
                if self.search_method == "tag":
                    for tag in self.blacklist:
                        if tag in post["tag_string"] and not post["is_blacklisted"]:
                            post["is_blacklisted"] = True
                            self.total_post_count -= 1
                            
        print("Total results:", self.total_post_count)
        if not self.quiet:
            a = input("Do you want to continiue?\n")
        else:
            a = "yes"
        if "n" not in a:
            if not os.path.exists(self.pic_dir) and not os.path.isdir(self.pic_dir):
                os.mkdir(self.pic_dir)
            os.chdir(self.pic_dir)
            if self.search_method != "post":
                if self.search_method == "tag":
                    folder_name = self.query
                if self.search_method == "pool":
                    folder_name = "pool:{}".format(self.query)
                if not os.path.exists(folder_name) and not os.path.isdir(folder_name):
                    os.mkdir(folder_name)
                os.chdir(folder_name)
                
            with ThreadPoolExecutor(max_workers=self.threads) as e:
                e.map(self.parser, self.total_result)
            print("Done! TTL: {}, ERR: {}, OK: {}, SKP: {}".format(self.total_post_count, self.error_count, self.downloaded_count, self.skipped_count))
        else:
            print("Exit.")
            sys.exit()
    
    def search(self):
        if self.search_method == "tag":
            query = self.query
            if self.page == 1:
                print("Search tag:", self.query)
        if self.search_method == "post":
            query = "id:" + self.query
            if self.page == 1:
                print("Search post with id:", self.query)
        if self.search_method == "pool":
            query = "pool:" + self.query
            if self.page == 1:
                print("Search pool with name/id:", self.query)
        payload = {"tags": query, "page": self.page, "limit": self.post_limit}     
        
        if (self.search_method == "tag" or self.search_method == "pool") and \
           (self.page != 1 and not self.quiet):
               print("Please wait, loading page", self.page)
               
        if self.login is not None and self.password is not None:
            resp = requests.get(self.board_url + "/posts.json", params=payload, auth=(self.login, self.password))
        else:
            resp = requests.get(self.board_url + "/posts.json", params=payload)
        
        if resp.status_code == requests.codes.ok:
            if "application/json" in resp.headers["content-type"]:
                result = resp.json()
            else:
                print("There are no JSON, content type is:", resp.headers["content-type"])
                sys.exit(1)
            post_count = len(result)
            if not post_count and not self.total_result:
                print("Not found.")
                sys.exit()
            if (not self.page_limit or self.page < self.page_limit) and \
                post_count == self.post_limit:
                self.total_result += result
                self.page += 1
                self.search()
            else:
                self.total_result += result
                self.total_post_count = len(self.total_result)
                self.prepare()
        else:
            print("Get results failed, status code is:", resp.status_code)
            sys.exit(1)

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grabber from danbooru imageboard.")
    parser.add_argument("-n", "--nick", help="set nick for auth")
    parser.add_argument("-p", "--password", help="set pass for auth")
    parser.add_argument("-t", "--tag", help="search tags (standart danbooru format)")
    parser.add_argument("-i", "--post", help="search post (by danbooru post id)")
    parser.add_argument("-o", "--pool", help="search pool (by danbooru pool id or name)")
    parser.add_argument("-l", "--limit", help="number of downloaded pages", type=int)
    parser.add_argument("-q", "--quiet", action="store_true", help="quiet mode")
    parser.add_argument("-u", "--update", help="update downloaded collection", nargs="?", const=os.path.expanduser("~") + "/Pictures")
    parser.add_argument("-d", "--path", help="set path to download")
    args = parser.parse_args()

    def start(query, method="tag"):
        grabber = Grabber(query, method)
        if args.nick and args.password:
            grabber.login = args.nick
            grabber.password = args.password
        if args.limit:
            grabber.page_limit = args.limit
        if args.quiet:
            grabber.quiet = True
        if args.update or args.path:
            grabber.pic_dir = args.update or args.path
        grabber.search()

    if args.tag:
       start(args.tag)
    if args.post:
       start(args.post, "post")
    if args.pool:
       start(args.pool, "pool")
    if args.update:
        print("Updating!")
        args.limit = 1
        args.quiet = True
        
        if not args.update.endswith("/"):
            pic_dir = args.update + "/"
        else:
            pic_dir = args.update
        
        folder_list = sorted([name for name in os.listdir(pic_dir) if os.path.isdir(pic_dir + name)])
        if folder_list:
            for name in folder_list:
                print("--------------------------------")
                start(name)
        else:
            print("There no any folders found.")
            sys.exit()
    if not any(vars(args).values()):
        parser.print_help()
            
