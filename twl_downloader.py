#!/usr/bin/env python
# this script downloads a users latest ToWatchList unwatched videos using youtube-dl
# youtube-dl is available here: http://rg3.github.io/youtube-dl/

from __future__ import unicode_literals
import urllib2, base64, simplejson, subprocess, os, glob, ConfigParser, sys
# import youtube_dl # TODO: in future do youtube_dl without needing to CLI with subprocess, for now it's more portable as a seperate install
from datetime import datetime

savepath = os.path.expanduser('~/.twl_downloader_settings.cfg')
config = ConfigParser.RawConfigParser()
config.read(savepath)

apiKey = config.get('twl_downloader_settings', 'apiKey')
pathToYouTubeDL   = config.get('twl_downloader_settings', 'pathToYouTubeDL')
downloadLocation  = config.get('twl_downloader_settings', 'downloadLocation')

# get all the data from the last few days:
refreshTimeString = '-28days' #alternate relative English string will be parsed by PHP on the server side

# Set up a new config file
config = ConfigParser.RawConfigParser()
config.add_section('twl_downloader_settings')
config.set('twl_downloader_settings', 'apiKey',           apiKey)
config.set('twl_downloader_settings', 'pathToYouTubeDL',  pathToYouTubeDL)
config.set('twl_downloader_settings', 'downloadLocation', downloadLocation)

# Writing our config file
with open(savepath, 'wb') as configfile:
    config.write(configfile)

# create our request url
TWL_API_URL = "https://towatchlist.com/api/v1/marks?since=%s&uid=%s" % (refreshTimeString, apiKey)

# create the headers
headers = {'Accept': 'application/json',}
# create the API request
request = urllib2.Request(TWL_API_URL, None, headers)
# perform the request
result = urllib2.urlopen(request)
# array of the results
myMarks = simplejson.loads(result.read())['marks']

if downloadLocation != 'False':
    # change directory to download location if it was set
    os.chdir(downloadLocation)

print "Syncing ToWatchList with '%s'" % os.getcwd()
print "Found %i videos to try downloading." % len(myMarks)
print "---------------------------------"

for i in xrange(len(myMarks)):
    # skip if it's been marked as watched
    if (myMarks[i]['Mark']['watched']) or (myMarks[i]['Mark']['delflag']):
        # print "Watched/Deleted: '%s'" % myMarks[i]['Mark']['title']
        # it's been marked as watched, delete the local copy
        filesToRemove = glob.glob('*-%s.*' % myMarks[i]['Mark']['video_id'])
        for filename in filesToRemove:
            os.remove(filename)
            print "Removed watched or deleted video: '%s'" % filename
        continue
    else:
        # if the file already exists (searching for filenames ending in mkv, mov, mp4, & ebm):
        existingFiles = glob.glob('*-%s*[em][pkbo][4vm]' % myMarks[i]['Mark']['video_id'])
        if len(existingFiles) >= 1:
            print "Already downloaded: '%s'" % myMarks[i]['Mark']['title']
        else:
            # if it hasn't been downloaded or marked watched, try to download it now
            videoURL = myMarks[i]['Mark']['source_url']
            print "Downlading %s from %s" % (myMarks[i]['Mark']['title'], videoURL)

            if int(myMarks[i]['Mark']['source_site']) == 1: #youtube
                # call youtube-dl to download the file

                # youtube-dl does a good job of getting you the best quality video, but these are some tweaks that helped get my perefered format
                # the -f argument limits things to 1080p (ie no 4K video) and also prefer AVC video when possible (AVC is better in Kodi)
                # --merge-output-format FORMAT (perefers mkv as it's flexible & widely supported in Kodi & others)
                subprocessArgs = [pathToYouTubeDL,
                                  str('-f'), str('bestvideo[height<=1080][vcodec*=avc]+bestaudio/best[ext=mp4]/best'),
                                  str('--merge-output-format'), str('mkv'),
                                  videoURL]
            else: # don't use the format string for Vimeo (or other sources)
                subprocessArgs = [pathToYouTubeDL, videoURL]

            # print "Calling:",subprocessArgs
            subprocess.call(subprocessArgs)

    print "---------------------------------"
