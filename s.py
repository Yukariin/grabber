#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests


if __name__ == "__main__":
    for i in range(1, 100):
      params = {"mid": i}
      r = requests.get("http://www.ite.com.tw/en/product/view", params=params)
      if "IT87" in r.text:
          print(r.url)
      
 
