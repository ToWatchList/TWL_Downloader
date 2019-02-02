#!/usr/bin/env python
# coding=utf-8
# this script downloads a users latest ToWatchList unwatched videos using youtube-dl
# youtube-dl is available here: http://rg3.github.io/youtube-dl/

import sys, os, shutil
reload(sys)
sys.setdefaultencoding('utf8') # this is a trick to get everything in utf-8, had trouble with funky chars from YouTube without it
import subprocess, os, glob, ConfigParser, requests
# import youtube_dl # TODO: in future do youtube_dl without needing to CLI with subprocess, for now it's more portable as a seperate install
from datetime import datetime
from HTMLParser import HTMLParser
# https://github.com/jcsaaddupuy/python-kodijson
from kodijson import Kodi

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

def findVideoFilesForVideoID(video_id, downloadDir = None, expect1 = False):
    # searching for filenames ending in mkv, mov, mp4, & ebm
    if downloadDir and os.path.isdir(downloadDir):
        foundFiles = glob.glob(os.path.join( downloadDir, '*-%s*[em][pkbo][4vm]' % video_id) )
    else:
        foundFiles = glob.glob('*-%s*[em][pkbo][4vm]' % video_id)
    assert len(foundFiles) <= 1, '\nERROR: found more than one video match for video_id "%s"' % video_id
    if len(foundFiles) == 1: return foundFiles[0]
    if expect1:
        print
        print foundFiles
        sys.exit('ERROR: we expected to find one file here and found none for video_id %s' % video_id)
    return False

def findNFOFilesForVideoID(video_id, downloadDir = None, expect1 = False):
    if downloadDir and os.path.isdir(downloadDir):
        foundFiles = glob.glob(os.path.join( downloadDir, '*-%s*nfo' % video_id) )
    else:
        foundFiles = glob.glob( '*-%s*nfo' % video_id )
    assert len(foundFiles) <= 1, '\nERROR: found more than one NFO match for video_id "%s"' % video_id
    if len(foundFiles) == 1: return foundFiles[0]
    if expect1:
        print
        print foundFiles
        sys.exit('ERROR: we expected to find one file here and found none for video_id %s' % video_id)
    return False

if __name__ == '__main__':

    savepath = os.path.expanduser('~/.twl_downloader_settings.cfg')
    config = ConfigParser.RawConfigParser()
    config.read(savepath)

    apiKey           = config.get('twl_downloader_settings', 'apiKey')
    pathtoyoutubedl  = config.get('twl_downloader_settings', 'pathtoyoutubedl')
    downloadlocation = config.get('twl_downloader_settings', 'downloadlocation')

    # Options added later with auto-set defaults
    try: writenfofiles = config.getboolean('twl_downloader_settings', 'writenfofiles')
    except ConfigParser.NoOptionError: writenfofiles = False

    try: kodihostname = config.get('twl_downloader_settings', 'kodihostname')
    except ConfigParser.NoOptionError: kodihostname = None

    try: kodiport = config.get('twl_downloader_settings', 'kodiport')
    except ConfigParser.NoOptionError: kodiport = None

    try: kodiuser = config.get('twl_downloader_settings', 'kodiuser')
    except ConfigParser.NoOptionError: kodiuser = None

    try: kodipassword = config.get('twl_downloader_settings', 'kodipassword')
    except ConfigParser.NoOptionError: kodipassword = None

    try: downloadtotmp = config.getboolean('twl_downloader_settings', 'downloadtotmp')
    except ConfigParser.NoOptionError: downloadtotmp = True

    # get all the data from the last few days:
    refreshTimeString = '-28days' #alternate relative English string will be parsed by PHP on the server side

    # Set up a new config file
    config = ConfigParser.RawConfigParser()
    config.add_section('twl_downloader_settings')
    config.set('twl_downloader_settings', 'apiKey',           apiKey)
    config.set('twl_downloader_settings', 'pathtoyoutubedl',  pathtoyoutubedl)
    config.set('twl_downloader_settings', 'downloadlocation', downloadlocation)
    config.set('twl_downloader_settings', 'writenfofiles',    writenfofiles)
    config.set('twl_downloader_settings', 'kodihostname',     kodihostname)
    config.set('twl_downloader_settings', 'kodiport',         kodiport)
    config.set('twl_downloader_settings', 'kodiuser',         kodiuser)
    config.set('twl_downloader_settings', 'kodipassword',     kodipassword)
    config.set('twl_downloader_settings', 'downloadtotmp',    downloadtotmp)

    # fix 'None' string -> None
    if apiKey           == 'None': apiKey           = None
    if pathtoyoutubedl  == 'None': pathtoyoutubedl  = None
    if downloadlocation == 'None': downloadlocation = None
    if kodihostname     == 'None': kodihostname     = None
    if kodiport         == 'None': kodiport         = None
    if kodiuser         == 'None': kodiuser         = None
    if kodipassword     == 'None': kodipassword     = None

    # Writing our config file
    with open(savepath, 'wb') as configfile:
        config.write(configfile)

    # get updated marks from the server
    r = requests.get( "https://towatchlist.com/api/v1/marks?since=%s&uid=%s" % (refreshTimeString, apiKey) )
    myMarks = r.json()['marks']

    # change directory to download location
    if downloadtotmp:
        os.chdir('/tmp')
    elif downloadlocation:
        os.chdir(downloadlocation)

    print "Syncing ToWatchList with '%s'" % os.getcwd()
    print "Found %i videos to try downloading." % len(myMarks)
    print "---------------------------------"

    shouldCleanKodi = shouldScanKodi = False

    for i in xrange(len(myMarks)):
        # set some values we'll use below
        videoURL      = myMarks[i]['Mark']['source_url']
        # thumbURL      = myMarks[i]['Mark']['thumb_url'].replace('/default.jpg', '/maxresdefault.jpg').replace('_120x90.jpg', '_1280x720.jpg')
        title         = myMarks[i]['Mark']['title']
        video_id      = myMarks[i]['Mark']['video_id']
        channel_title = myMarks[i]['Mark']['channel_title']
        duration      = int(myMarks[i]['Mark']['duration']) / 60.0
        created       = myMarks[i]['Mark']['created']
        try:    description = strip_tags(myMarks[i]['Mark']['comment'])
        except: description = '-Failed to parse-'

        # skip if it's been marked as watched
        if (myMarks[i]['Mark']['watched']) or (myMarks[i]['Mark']['delflag']):
            # it's been marked as watched, delete the local copy
            for filename in glob.glob( os.path.join( downloadlocation, '*-%s.*' % video_id )):
                os.remove(filename)
                print ("Removed watched or deleted videos & NFOs: '%s'" % filename).encode('utf-8')
                shouldCleanKodi = True
            continue
        else:
            # if the file already exists
            if findVideoFilesForVideoID(video_id, downloadDir = downloadlocation):
                print ("Already downloaded: '%s'" % title).encode('utf-8')
            else:
                # if it hasn't been downloaded or marked watched, try to download it now
                print ( "Downlading %s from %s" % (title, videoURL) ).encode('utf-8')

                # youtube-dl does a good job of getting you the best quality video, but these are some tweaks that helped get my perefered format
                # the -f argument limits things to 1080p (ie no 4K video when possible) and also prefer AVC video when possible (AVC works best for wide support)
                # --merge-output-format FORMAT (perefers mkv as it's flexible & widely supported in Kodi & others)
                subprocessArgs = [pathtoyoutubedl,
                                  str('-f'), str('bestvideo[height<=1080][vcodec*=avc]+bestaudio/best[ext=mp4]/best'),
                                  str('--merge-output-format'), str('mkv'),
                                  videoURL]
                subprocess.call(subprocessArgs)
                shouldScanKodi = True

                if downloadtotmp: # now move files into place
                    foundVideoFile = findVideoFilesForVideoID(video_id, expect1=True)
                    print "Move %s to %s" % (foundVideoFile, downloadlocation)
                    shutil.move(foundVideoFile, downloadlocation)

            if writenfofiles:
                # get info/metadata for file and save it as NFO
                if findNFOFilesForVideoID(video_id, downloadDir = downloadlocation):
                    # print ("Already set NFO metadata for '%s'" % title).encode('utf-8')
                    pass
                else:
                    # create an .nfo metadata file for Kodi etc
                    foundVideoFile = findVideoFilesForVideoID(video_id, downloadDir = downloadlocation, expect1=True)
                    nfoFilePath = os.path.splitext(foundVideoFile)[0] + '.nfo'

                    # we have the default thumbnail url which is lower quality, look up a better one:
                    thumbURL = subprocess.check_output([pathtoyoutubedl, '--get-thumbnail', videoURL]).strip()

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

    if kodihostname:
        #Login with custom credentials
        if not kodiport: kodiport = 8080 # Kodi Web default port
        kodi = Kodi("http://%s:%i/jsonrpc" % (kodihostname, kodiport), kodiuser, kodipassword)
        assert kodi.JSONRPC.Ping()['result'] == 'pong', '\nERROR: bad or response from Kodi (@ %s)' % kodihostname
        if shouldScanKodi or shouldCleanKodi:
            kodi.GUI.ShowNotification({"title":"ToWatchList Downloader", "message":"New videos downloaded, update Kodi library…"})
        if shouldScanKodi:
            print "Scanning Kodi Library (@ %s)" % kodihostname
            kodi.VideoLibrary.Scan()
        if shouldCleanKodi:
            print "Cleaning Kodi Library (@ %s)" % kodihostname
            kodi.VideoLibrary.Clean()
        if not shouldCleanKodi and not shouldScanKodi:
            print "No Scan or Clean of Kodi (@ %s) needed" % kodihostname

# Info/formatting for NFO example
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
