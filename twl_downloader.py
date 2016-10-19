#!/usr/bin/env python
# coding=utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

# this script downloads a users latest ToWatchList unwatched videos using youtube-dl
# youtube-dl is available here: http://rg3.github.io/youtube-dl/
#
# from __future__ import unicode_literals
import urllib2, simplejson, subprocess, os, glob, ConfigParser
# import youtube_dl # TODO: in future do youtube_dl without needing to CLI with subprocess, for now it's more portable as a seperate install
from datetime import datetime
from HTMLParser import HTMLParser

# to strip HTML tags via:
# http://stackoverflow.com/a/925630/1304462
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


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

writeNFOfiles = True

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

def findVideoFilesForVideoID(video_id, expect1 = False):
    # searching for filenames ending in mkv, mov, mp4, & ebm
    foundFiles = glob.glob('*-%s*[em][pkbo][4vm]' % video_id)
    assert len(foundFiles) <= 1, '\nERROR: found more than one video match for video_id "%s"' % video_id
    if len(foundFiles) == 1: return foundFiles[0]
    if expect1: sys.exit('\nERROR: we expected to find one file here and found none for video_id %s' % video_id)
    return False

def findNFOFilesForVideoID(video_id, expect1 = False):
    foundFiles = glob.glob('*-%s*nfo' % video_id)
    assert len(foundFiles) <= 1, '\nERROR: found more than one NFO match for video_id "%s"' % video_id
    if len(foundFiles) == 1: return foundFiles[0]
    if expect1: sys.exit('\nERROR: we expected to find one file here and found none for video_id %s' % video_id)
    return False

for i in xrange(len(myMarks)):
    # set some values we'll use below
    videoURL      = myMarks[i]['Mark']['source_url']
    # thumbURL      = myMarks[i]['Mark']['thumb_url'].replace('/default.jpg', '/maxresdefault.jpg').replace('_120x90.jpg', '_1280x720.jpg')
    title         = myMarks[i]['Mark']['title']
    description   = strip_tags(myMarks[i]['Mark']['comment'])
    video_id      = myMarks[i]['Mark']['video_id']
    channel_title = myMarks[i]['Mark']['channel_title']
    duration      = int(myMarks[i]['Mark']['duration']) / 60.0
    created       = myMarks[i]['Mark']['created']

    # skip if it's been marked as watched
    if (myMarks[i]['Mark']['watched']) or (myMarks[i]['Mark']['delflag']):
        # it's been marked as watched, delete the local copy
        for filename in glob.glob('*-%s.*' % video_id):
            os.remove(filename)
            print ("Removed watched or deleted videos & NFOs: '%s'" % filename).encode('utf-8')
        continue
    else:
        # if the file already exists
        if findVideoFilesForVideoID(video_id):
            print ("Already downloaded: '%s'" % title).encode('utf-8')
        else:
            # if it hasn't been downloaded or marked watched, try to download it now
            print ( "Downlading %s from %s" % (title, videoURL) ).encode('utf-8')

            # youtube-dl does a good job of getting you the best quality video, but these are some tweaks that helped get my perefered format
            # the -f argument limits things to 1080p (ie no 4K video when possible) and also prefer AVC video when possible (AVC is better in Kodi)
            # --merge-output-format FORMAT (perefers mkv as it's flexible & widely supported in Kodi & others)
            subprocessArgs = [pathToYouTubeDL,
                              str('-f'), str('bestvideo[height<=1080][vcodec*=avc]+bestaudio/best[ext=mp4]/best'),
                              str('--merge-output-format'), str('mkv'),
                              videoURL]
            subprocess.call(subprocessArgs)

        if writeNFOfiles:
            # get info/metadata for file and save it as NFO
            if findNFOFilesForVideoID(video_id):
                # print ("Already set NFO metadata for '%s'" % title).encode('utf-8')
                pass
            else:
                # create an .nfo metadata file for Kodi etc
                foundVideoFile = findVideoFilesForVideoID(video_id, expect1=True)
                nfoFilePath = os.path.splitext(foundVideoFile)[0] + '.nfo'

                # we have the default thumbnail url which is lower quality, look up a better one:
                thumbURL = subprocess.check_output([pathToYouTubeDL, '--get-thumbnail', videoURL]).strip()

                with open(nfoFilePath, "w") as nfoF:
                    nfoF.write("<episodedetails>\n")
                    nfoF.write("  <title>%s</title>\n" % title)
                    nfoF.write("  <showtitle>%s</showtitle>\n" % channel_title)
                    nfoF.write("  <aired>%s</aired>\n" % created)
                    nfoF.write("  <plot>%s</plot>\n" % description)
                    nfoF.write("  <runtime>%i</runtime>\n" % round(duration))
                    nfoF.write("  <thumb>%s</thumb>\n" % thumbURL)
                    nfoF.write("  <videourl>%s</videourl>\n" % videoURL)
                    nfoF.write("</episodedetails>\n")

    print "---------------------------------"
# <episodedetails>
#   <title>Moby & The Void Pacific Choir - Are You Lost In The World Like Me (Official Video)</title>
#   <showtitle>Moby VEVO</showtitle>
#   <season>1</season>
#   <episode>1</episode>
#   <uniqueid>5586358</uniqueid>
#   <aired>2016-07-10</aired>
#   <plot>What starts as a perfect night for Pakistani-American student Nasir “Naz” Khan becomes a nightmare when he’s arrested for murder.</plot>
#   <runtime>60</runtime>
#   <displayseason />
#   <displayepisode />
#   <thumb>https://i.ytimg.com/vi/VASywEuqFd8/maxresdefault.jpg</thumb>
#   <watched>false</watched>
#   <credits>Richard Price</credits>
#   <director>Steven Zaillian</director>
#   <rating>8.7</rating>
# </episodedetails>
