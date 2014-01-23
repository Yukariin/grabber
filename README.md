Grabber: save images from any donmai.us imageboards locally
=======

This script help  store images from any [donmai.us][3] imageboards to your hard drive.
Supports search by tags, pools (name/id) and post (id).

Usage examples:

    danbooru_grabber -t "tag1 tag2"
    
search and download images with *"tag1 tag2"* tags

    danbooru_grabber -l "123"
    
search and download images from pool with *"123"* id

    danbooru_grabber -i "12345"
    
search and download image with *"12345"* id

    danbooru_grabber -n nick -p password -t "tag1"
    
search tags with using authorisation (by default not using) as user *"nick"* and password *"password"*

For more options/queries see script help, donmai.us [API docs][1] and [cheatsheet][2]

[1]:http://danbooru.donmai.us/wiki_pages/43568
[2]:http://danbooru.donmai.us/wiki_pages/43049
[3]:http://danbooru.donmai.us
    