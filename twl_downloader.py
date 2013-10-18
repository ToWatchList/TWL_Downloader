#!/usr/bin/env python
# this script downloads a users latest ToWatchList unwatched videos using youtube-dl
# youtube-dl is available here: http://rg3.github.io/youtube-dl/

import urllib2, base64, simplejson, subprocess, os, glob, ConfigParser, sys
from datetime import datetime

savepath = os.path.expanduser('~/.twl_downloader_settings.cfg')
config = ConfigParser.RawConfigParser()
config.read(savepath)

apiKey = config.get('twl_downloader_settings', 'apiKey')
pathToYouTubeDL   = config.get('twl_downloader_settings', 'pathToYouTubeDL')
downloadLocation  = config.get('twl_downloader_settings', 'downloadLocation')
refreshTime       = config.get('twl_downloader_settings', 'refreshTime')
refreshTime       = datetime.strptime(refreshTime, '%Y-%m-%d %H:%M:%S.%f')
refreshTimeString = datetime.strftime(refreshTime, '%Y-%m-%dT%H:%M:%SUTC')
# We want something like: 2013-07-07T00:40:37UTC

# Set up a new config file
config = ConfigParser.RawConfigParser()
config.add_section('twl_downloader_settings')
config.set('twl_downloader_settings', 'apiKey',           apiKey)
config.set('twl_downloader_settings', 'pathToYouTubeDL',  pathToYouTubeDL)
config.set('twl_downloader_settings', 'downloadLocation', downloadLocation)
config.set('twl_downloader_settings', 'refreshTime',      datetime.utcnow())

# Writing our config file
with open(savepath, 'wb') as configfile:
    config.write(configfile)

# create our request url
TWL_API_URL = "https://towatchlist.com/marks/data.json?since=%s&uid=%s" % (refreshTimeString, apiKey)

# create the API request
request = urllib2.Request(TWL_API_URL)
# perform the request
result = urllib2.urlopen(request)
# array of the results
myMarks = simplejson.loads(result.read())['marks']

if downloadLocation != 'False':
    # change directory to download location if it was set
    os.chdir(downloadLocation)

print "Syncing ToWatchList with '%s'" % os.getcwd()
print "---------------------------------"

for i in xrange(len(myMarks)):
    # skip if it's been marked as watched
    if (myMarks[i]['Mark']['watched']) or (myMarks[i]['Mark']['delflag']):
        print "Watched/Deleted: '%s'" % myMarks[i]['Mark']['title']
        # it's been marked as watched, delete the local copy
        filesToRemove = glob.glob('*-%s.*' % myMarks[i]['Mark']['video_id'])
        for filename in filesToRemove:
            os.remove(filename)
            print "Removed watched or deleted video: '%s'" % filename
    else:
        # if the file already exists:
        existingFiles = glob.glob('*-%s.*' % myMarks[i]['Mark']['video_id'])
        if len(existingFiles) >= 1:
            print "Already downloaded: '%s'" % myMarks[i]['Mark']['title']
        else:
            # if it hasn't been downloaded or marked watched, try to download it now
            videoURL = myMarks[i]['Mark']['source_url']
            print "Downlading '%s'" % videoURL
            subprocess.call([pathToYouTubeDL,"-c",videoURL])
    print "---------------------------------"
