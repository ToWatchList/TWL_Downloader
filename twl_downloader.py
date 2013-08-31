#!/usr/bin/env python
# this script downloads a users latest ToWatchList unwatched videos using youtube-dl
# youtube-dl is available here: http://rg3.github.io/youtube-dl/

import urllib2, base64, simplejson, subprocess, os, glob, ConfigParser, sys

savepath = os.path.expanduser('~/.twl_downloader_settings.cfg')
config = ConfigParser.RawConfigParser()
config.read(savepath)

apiKey = config.get('twl_downloader_settings', 'apiKey')
pathToYouTubeDL = config.get('twl_downloader_settings', 'pathToYouTubeDL')
downloadLocation = config.get('twl_downloader_settings', 'downloadLocation')

TWL_API_URL = "https://towatchlist.com/marks/data.json?since=-48hours&uid=%s" % apiKey

# create the API request
request = urllib2.Request(TWL_API_URL)
# perform the request
result = urllib2.urlopen(request)
# array of the results
myMarks = simplejson.loads(result.read())['marks']

if downloadLocation != 'False':
    # change directory to download location if it was set
    os.chdir(downloadLocation)

for i in xrange(len(myMarks)):
    # skip if it's been marked as watched
    if myMarks[i]['Mark']['watched']:
        print "Watched",myMarks[i]['Mark']['title']
        # it's been marked as watched, delete the local copy
        filesToRemove = glob.glob('*-%s.*' % myMarks[i]['Mark']['video_id'])
        for filename in filesToRemove:
            os.remove(filename)
            print "Removed watched video:",filename
    else:
        # if the file already exists:
        existingFiles = glob.glob('*-%s.*' % myMarks[i]['Mark']['video_id'])
        if len(existingFiles) >= 1:
            print "Already downloaded",myMarks[i]['Mark']['title']
        else:
            # if it hasn't been downloaded or marked watched, try to download it now
            videoURL = myMarks[i]['Mark']['source_url']
            print "Downlading",videoURL
            subprocess.call([pathToYouTubeDL,"-c",videoURL])
    print "---------------------------------"
