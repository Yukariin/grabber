#!/bin/bash

for tag in $(ls -d ~/Pictures/*/ | cut -f 5 -d '/')
do
    echo "----------------------"
    python ~/grabber/danbooru_grabber.py -q -t "$tag"
done