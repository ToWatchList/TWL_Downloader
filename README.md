ToWatchList Downloader
======================
ToWatchList Downloader or `twl_downloader.py` is Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com)

Requirements
------------
- [ToWatchList.com](https://towatchlist.com) account
- Python 2.7 or later - The scripts have been tested on Python 2.7.3 on Linux, and 2.7.5 on Mac.
- [youtube-dl](http://rg3.github.io/youtube-dl/) - Must be the latest version

Getting Started
---------------
After installing [youtube-dl](http://rg3.github.io/youtube-dl/), run the `setup.py` script.  It will walk though saving your API key and other options.

Once you're happy with the setup options. Try running `twl_downloader.py` to make sure it works. It should download any videos that were added to your ToWatchList in the last 10 days the first time it is run (after that it only downloads changes since the last execution time).

It's recommended you set up a cron job (or similar tool) to start `twl_downloader.py` regularly.  This keeps your local videos up to date with your ToWatchList since the script will also delete local videos you've marked as watched on the website or app.

Tips & Suggestions
------------------
It's important to keep [youtube-dl](http://rg3.github.io/youtube-dl/) updated regularly because it can break if YouTube or Vimeo change things around.  In my experience this hasn't been a frequent problem but when it occurred [youtube-dl](http://rg3.github.io/youtube-dl/) was updated rapidly to fix any issues.  So I suggest using [HomeBrew](http://brew.sh) (on the Mac) or just [youtube-dl's self updater](https://github.com/rg3/youtube-dl/blob/master/README.md#options) (with the `-U` CLI option) to to keep things up to date. You probably want to put the update command into a cron job of it's own.

On a related note, it's really great to point a TV interface like [Kodi](http://kodi.tv) (formally XBMC) at your download folder. The script can even write out appropreate metadata for thumbnails and descriptions for Kodi. This allows you to browse & watch all your to watch videos locally with no buffering or ads.  This is actually the original intent the script.

Disclaimers & Other Info
--------------------------
These scripts use some of the private APIs from ToWatchList, which may change at any time. This includes:

1.  Minor adjustments to syntax and data in provided by the API (this shouldn't affect these scripts)
2.  Bandwidth & polling limits to prevent abuse (this shouldn't affect normal use)
3.  The full data API may require a small monthly or yearly fee as part of subscription to ToWatchList's 'Pro' features

That said, I'm the the developer of ToWatchList and use these scripts every day.  So I plan to keep them updated if anything changes that would break them.

Please see the [ToWatchList API Page](http://towatchlist.com/api) for more API details and [contact me](http://towatchlist.com/pages/contact) with any questions.
