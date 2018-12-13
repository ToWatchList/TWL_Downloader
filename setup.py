#!/usr/bin/env python
# this script helps the user set values for the main script.

import urllib2
import base64
import simplejson
import subprocess
import os
import glob
import sys
import getpass
import ConfigParser
from datetime import datetime, timedelta

# 'which' & 'is_exe' code snipet via:
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python/377028#377028
def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def which(program):
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


print "This script helps set up important values and preferances for the TWL_Downloader."
print " --"
print "Please make sure you have installed the latest copy of youtube-dl before running this setup script."
print "youtube-dl is available via: http://rg3.github.io/youtube-dl/",
if sys.platform == 'darwin':
    print "or via Homebrew at: http://brew.sh (reccomended for Mac users)."
else:
    print ''
print ''

foundPathToYouTubeDL = which('youtube-dl')

if foundPathToYouTubeDL:
    print "Found a copy of youtube-dl at '%s'. Press enter below to accept this default value." % foundPathToYouTubeDL
    pathToYouTubeDL = raw_input("Path to youtube-dl [%s]: " % foundPathToYouTubeDL)
    if not pathToYouTubeDL:
        pathToYouTubeDL = foundPathToYouTubeDL
else:
    print "You'll also need to know the path to its binary (e.g. '/usr/local/bin/youtube-dl')."
    pathToYouTubeDL = raw_input("Path to youtube-dl: ")

if not is_exe(pathToYouTubeDL):
    sys.exit("ERROR: The path you provided '%s' doesn't appear to be a valid executable.\nPlease check that the path resolves and that the permission are set to allow execution." % pathToYouTubeDL)

print "Great, things look good with that path."
print ''
print "For security, your email address and password will not be permanently stored.\nHowever, these values are need to look up your API key."

username = raw_input("ToWatchList.com Email Address: ")
password = getpass.getpass("ToWatchList.com Password: ")

TWL_API_URL = "https://towatchlist.com/api/getkey"
# create the API request
request = urllib2.Request(TWL_API_URL)
# add authorization
base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
request.add_header("Authorization", "Basic %s" % base64string)   
# perform the request
result = urllib2.urlopen(request)
# array of the results
myKey = simplejson.loads(result.read())

if myKey['result'] != '1':
    sys.exit("ERROR: Bad username/password combination.")

apiKey = myKey['key']

print "Super: we've got your current API key."
print ''
print "Finally, the script needs to know where you want your video downloads to be saved."
print "The default behavior puts the files in the current working directory (CWD or PWD) when executed."
print "However, you can change this default by specifying another path below (press enter with no value to accept the defaults)."

doneFlag = False
while not doneFlag:
    downloadLocation = raw_input("Download Path [null for default]: ")
    # expand tilde for user paths
    downloadLocation = os.path.expanduser(downloadLocation)
    if downloadLocation:
        if os.path.isdir(downloadLocation):
            doneFlag = True
            print "Okay, twl_downloader.py will download videos to '%s'." % downloadLocation
        else:
            print "The location specified ('%s') doesn't look like a valid directory. Please try again." % downloadLocation
    else:
        downloadLocation = 'False'
        doneFlag = True
        print "Okay, twl_downloader.py will use the current path when downloading videos."

savepath = os.path.expanduser('~/.twl_downloader_settings.cfg')

# Set up config file
config = ConfigParser.RawConfigParser()
config.add_section('twl_downloader_settings')
config.set('twl_downloader_settings', 'apiKey',           apiKey)
config.set('twl_downloader_settings', 'pathToYouTubeDL',  pathToYouTubeDL)
config.set('twl_downloader_settings', 'downloadLocation', downloadLocation)
# date of -48 hours
config.set('twl_downloader_settings', 'refreshTime',      datetime.utcnow()-timedelta(days=2))

# Writing our config file
with open(savepath, 'wb') as configfile:
    config.write(configfile)

print ''
print "Thanks for setting up TWL_Downloader for ToWatchList!\nYour settings have been saved under '%s'.\nIf you need to change any values may edit them there or run this setup program again.\n" % savepath
print "Finally, please be aware that TWL_Downloader uses an officially unsupported API which may change anytime.\nSee https://github.com/ToWatchList/TWL_Downloader and http://towatchlist.com/api for details."
