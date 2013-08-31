ToWatchList Downloader
======================

ToWatchList Downloader or `twl_downloader.py` is Python script to automate downloading videos from ToWatchList.com

Requirements
------------
- Python 2.7 or later - The scripts have been tested on Python 2.7.3 on Linux, and 2.7.5 on Mac.
- [youtube-dl](http://rg3.github.io/youtube-dl/) - Must be the latest version

Getting Started
---------------

After installing [youtube-dl](http://rg3.github.io/youtube-dl/), run the `setup.py` script.  It will walk though saving your API key and other options.

Once you're happy with the setup options. Try running `twl_downloader.py` to make sure it works. It should download any videos that were added to your ToWatchList in the last 48 hours.

It's recommended you set up a cron job (or similar tool) to start `twl_downloader.py` regularly.  This keeps your local videos up to date with your ToWatchList since the script will also delete local videos you've marked as watched.

Tips & Suggestions
------------------
It's important to keep [youtube-dl](http://rg3.github.io/youtube-dl/) updated regularly because it can break if things are changed too frequently.  In my experience this hasn't been a frequent problem but when it occurred [youtube-dl](http://rg3.github.io/youtube-dl/) was updated rapidly to fix any issues.  So I suggest using [pip](http://www.pip-installer.org/) or [HomeBrew](http://brew.sh) (on the Mac) to install and update [youtube-dl](http://rg3.github.io/youtube-dl/) regularly and easily.  You might even put the updates command on a cron job of it's own.

On a related note, it's really great to point a TV interface like [XBMC](http://xbmc.org) at your download folder.  This allows you to browse & watch all your to watch videos locally with no buffering.  This is actually the original intent the script.

Disclaimers & Other Info
--------------------------

These scripts use some of the private APIs from ToWatchList, which may change at any time.  In fact, they probably will change in the future a few ways:

1.  Minor adjustments to syntax and data in provided by the API (this shouldn't affect these scripts)
2.  Bandwidth & polling limits to prevent abuse (this shouldn't affect normal use)
3.  The full data API may require a small monthly or yearly fee as part of subscription to ToWatchList's 'Pro' features

Please see the [ToWatchList API Page](http://towatchlist.com/api) for more API details.