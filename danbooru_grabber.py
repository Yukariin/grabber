#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import hashlib
import os
import re
import sys
from functools import partial
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    print("Requests lib was not found!")
    sys.exit(1)


class Grabber(object):
    """Main grabber class"""
    def __init__(self, search_method):
        self.board_url = "http://donmai.us"
        self.search_method = search_method
        self.page_limit = 0
        self.total_post_count = 0
        self.download_count = 0
        self.downloaded_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.quiet = False
        self.pics_dir = os.path.join(os.path.expanduser("~"), "Pictures")

    def downloader(self, file_url, file_name, file_size, md5):
        """Check and download file"""
        file_path = os.path.join(self.pics_dir, file_name)
        def md5sum(file_path):
            """Get file md5"""
            with open(file_path, "rb") as file_to_check:
                hasher = hashlib.md5()
                for buf in iter(partial(file_to_check.read, 128), b""):
                    hasher.update(buf)
            return hasher.hexdigest()

        def get(file_url, file_path):
            """Download file"""
            self.download_count += 1
            r = requests.get(file_url, stream=True)
            if r.status_code == requests.codes.ok:
                print("{}/{}".format(self.download_count,
                                     self.total_post_count),
                      "({}%)".format(round(self.download_count /
                                           (self.total_post_count / 100))),
                      "downloading", file_name)
                with open(file_path, "wb") as f:
                    for block in r.iter_content(1024):
                        if block:
                            f.write(block)
                self.downloaded_count += 1
            else:
                self.error_count += 1
                print("{}/{}".format(self.download_count,
                                     self.total_post_count),
                      "({}%)".format(round(self.download_count /
                                           (self.total_post_count / 100))),
                      file_name, "downloading failed, status code is:",
                      r.status_code)

        if os.path.isfile(file_path):
            if os.path.getsize(file_path) == file_size and \
               md5sum(file_path) == md5:
                self.download_count += 1
                self.skipped_count += 1
                if not self.quiet:
                    print("{}/{}".format(self.download_count,
                                         self.total_post_count),
                          "({}%)".format(round(self.download_count /
                                               (self.total_post_count / 100))),
                          "md5 match! Skipping download.")
            else:
                os.remove(file_path)
                get(file_url, file_path)
        else:
            get(file_url, file_path)

    def parser(self, post):
        """Parse post to get url, tags, etc and start download"""
        file_url = self.board_url + post["file_url"]
        file_ext = post["file_ext"]
        md5 = post["md5"]
        file_size = post["file_size"]
        file_name = "{} - {}.{}".format("Donmai.us", post["id"],
                                        file_ext)

        if not post["is_blacklisted"]:
            self.downloader(file_url, file_name, file_size, md5)

    

    def prepare(self, query, results):
        """Prepare results for parsing"""
        blacklist = "scat comic hard_translated".split()

        self.total_post_count = len(results)
        if blacklist and self.search_method == "tag":
            for tag in query.split():
                if tag in blacklist:
                    blacklist.remove(tag)
        for post in results:
            if "file_url" not in post:
                r = requests.get("{}/posts/{}".format(self.board_url,
                                                      post["id"]))
                if r.status_code == requests.codes.ok:
                    s = re.findall('/data/[0-9a-f]+.[a-z]+', r.text)
                    if s:
                        post["file_url"] = s[0]
                    else:
                        print("Failed get file url!")
                        sys.exit(1)
                else:
                    print("Get page failed, status code is:", r.status_code)
                    sys.exit(1)
            if "file_ext" not in post:
                post["file_ext"] = os.path.splitext(os.path.basename(
                    post["file_url"]))[1].replace(".", "")
            if "md5" not in post:
                post["md5"] = os.path.splitext(os.path.basename(
                    post["file_url"]))[0]

            post["is_blacklisted"] = False
            if blacklist and self.search_method == "tag":
                for tag in blacklist:
                    if tag in post["tag_string"] and \
                            not post["is_blacklisted"]:
                        post["is_blacklisted"] = True
                        self.total_post_count -= 1

    def search(self, query, login=None, password=None):
        """Search and get results"""
        def get_result(query):
            """Getting results"""
            if self.search_method == "post":
                query = "id:" + query
            elif self.search_method == "pool":
                query = "pool:" + query
            prms = {"tags": query, "page": page, "limit": post_limit}

            if (self.search_method == "tag" or self.search_method == "pool") \
               and (page != 1 and not self.quiet):
                print("Please wait, loading page", page)

            if login is not None and password is not None:
                r = requests.get(self.board_url + "/posts.json", params=prms,
                                 auth=(login, password))
            else:
                r = requests.get(self.board_url + "/posts.json", params=prms)
            if r.status_code == requests.codes.ok:
                if "application/json" in r.headers["content-type"]:
                    result = r.json()
                    post_count = len(result)
                    return result, post_count
                else:
                    print("There are no JSON, content type is:",
                          r.headers["content-type"])
                    sys.exit(1)
            else:
                print("Get results failed, status code is:", r.status_code)
                sys.exit(1)

        print("Search:", query)
        page = 1
        post_limit = 200
        results = []
        result, post_count = get_result(query)

        while (not self.page_limit or page < self.page_limit) and \
                post_count == post_limit:
            results += result
            page += 1
            result, post_count = get_result(query)
        if not post_count and not results:
            print("Not found.")
            sys.exit()
        else:
            results += result
            return results

    def start(self, query):
        """Create folder and start parser"""
        query = query.strip()
        if query.startswith("pool:") and self.search_method != "pool":
            self.search_method = "pool"
            query = query.replace("pool:", "")
        elif query.startswith("id:") and self.search_method != "post":
            self.search_method = "post"
            query = query.replace("id:", "")

        results = self.search(query)
        self.prepare(query, results)
        print("Total results:", self.total_post_count)
        
        if not self.quiet:
            a = input("Do you want to continiue?\n")
        else:
            a = "yes"
        if "n" not in a:
            if self.search_method == "tag":
                self.pics_dir = os.path.join(self.pics_dir, query)
            elif self.search_method == "pool":
                self.pics_dir = os.path.join(self.pics_dir, "pool:" + query)
            if not os.path.isdir(self.pics_dir):
                os.makedirs(self.pics_dir)

            with ThreadPoolExecutor(max_workers=10) as e:
                e.map(self.parser, results)
            print("Done! TTL: {}, ERR: {}, OK: {}, SKP: {}"
                  .format(self.total_post_count, self.error_count,
                          self.downloaded_count, self.skipped_count))
        else:
            print("Exit.")
            sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Grabber from danbooru imageboard.")
    parser.add_argument("-n", "--nick", help="set nick for auth")
    parser.add_argument("-p", "--password", help="set pass for auth")
    parser.add_argument("-t", "--tag",
                        help="search tags (standart danbooru format)")
    parser.add_argument("-i", "--post", type=int,
                        help="search post (by danbooru post id)")
    parser.add_argument("-o", "--pool",
                        help="search pool (by danbooru pool id or name)")
    parser.add_argument("-l", "--limit", type=int,
                        help="number of downloaded pages")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet mode")
    parser.add_argument("-u", "--update", help="update downloaded collection",
                        nargs="?", const=os.path.join(os.path.expanduser("~"), "Pictures"))
    parser.add_argument("-d", "--path", help="set path to download")
    args = parser.parse_args()

    def start(query, method="tag"):
        """Creating object, change vars and start search"""
        grabber = Grabber(method)
        if args.limit:
            grabber.page_limit = args.limit
        if args.quiet:
            grabber.quiet = True
        if args.update or args.path:
            grabber.pics_dir = args.update or args.path
        if args.nick and args.password:
            grabber.start(query)
        else:
            grabber.start(query)

    if args.tag:
        start(args.tag)
    elif args.post:
        start(args.post, "post")
    elif args.pool:
        start(args.pool, "pool")
    elif args.update:
        print("Updating!")
        if not args.limit:
            args.limit = 1
        args.quiet = True

        folder_list = sorted([name for name in os.listdir(args.update) if
                             os.path.isdir(os.path.join(args.update, name))])
        if folder_list:
            for name in folder_list:
                print("--------------------------------")
                start(name)
        else:
            print("There no any folder found.")
            sys.exit()
    elif not any(vars(args).values()):
        parser.print_help()
