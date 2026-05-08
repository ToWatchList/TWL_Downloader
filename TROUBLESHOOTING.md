# Troubleshooting Guide

## Common Issues and Solutions

### Issue: "nsig extraction failed" or "Falling back to generic n function search"

**Root Cause:** YouTube's n-parameter JavaScript challenge has been updated, and yt-dlp's extraction method hasn't been patched yet.

**Quick Fix:**

```bash
# Update yt-dlp to the latest version
pip install -U yt-dlp

# Or rebuild the Docker image
docker build --no-cache -t twl-downloader .
```

**Automatic Fallback:** The downloader now automatically tries the `tv` client when this happens, so you should see the download proceed even with this warning.

**Timeline:** Usually fixed within 24 hours as new yt-dlp versions are released.

---

### Issue: "Some web client https formats have been skipped as they are missing a url. YouTube is forcing SABR streaming"

**Root Cause:** YouTube is using SABR (a custom streaming protocol) for this video/client combination.

**What Happens:** The downloader has multiple fallback strategies:

1. First tries without cookies
2. Then tries with the `tv` client
3. If you have a PO token configured, tries the `mweb` client with your token

**If It Still Fails:** The video is marked as DRM-protected. By default, it's skipped to avoid downloading low-quality versions.

**Solution 1: Try with a PO Token**

If the standard fallbacks don't work, use a PO token with the mweb client:

```bash
# Extract a PO token from YouTube (see README for instructions)
export YOUTUBE_PO_TOKEN="your_po_token_here"
export YOUTUBE_COOKIES_FILE=/config/cookies.txt
```

The downloader will automatically use the mweb client with your PO token when SABR is detected.

**Solution 2: Force Download Anyway**

```bash
SKIP_SABR_DRM_DOWNLOADS=false
```

**Note:** Solution 1 (PO token) is better because it may allow access to better quality formats. Solution 2 will proceed with lower quality.

---

### Issue: "DRM protected" warnings but video should be downloadable

**Root Cause:** YouTube detected a client type that it's restricting access for.

**Solution:** The downloader will automatically retry without cookies. If that fails, it means YouTube is restricting that video on that client.

**If You Still Want to Download:**

```bash
# Allow downloads even when DRM is detected
SKIP_SABR_DRM_DOWNLOADS=false
```

But note: This might result in lower quality than expected.

---

### Issue: Nothing downloading, no clear error message

**Debug Steps:**

1. **Check yt-dlp version:**

   ```bash
   yt-dlp --version
   ```

2. **Test yt-dlp directly:**

   ```bash
   yt-dlp -vU "https://www.youtube.com/watch?v=VIDEO_ID"
   ```

3. **Check logs in Docker:**

   ```bash
   docker logs twl-downloader
   ```

4. **Update everything:**

   ```bash
   pip install -U yt-dlp
   docker build --no-cache -t twl-downloader .
   ```

---

### Issue: Videos download but are corrupted or missing audio

**Possible Causes:**

1. Download was interrupted
2. Post-processing failed
3. Sponsorblock processing issues

**Solutions:**

1. **Check file:** Play it in a media player - does it actually play?

2. **Re-download with `OVERWRITE_NFO_FILES=true`:**

   ```bash
   OVERWRITE_NFO_FILES=true
   ```

3. **Try disabling SponsorBlock processing:**

   ```bash
   SPONSORBLOCK_CATEGORIES=""
   ```

4. **Try disabling sponsor segment removal (if enabled):**

   ```bash
   REMOVE_SPONSOR_SEGMENTS=false
   ```

---

### Issue: "Could not connect to Kodi"

**Root Cause:** Kodi hostname/credentials are incorrect or Kodi is not running.

**Fix:**

1. **Verify Kodi is running:** Check `http://KODI_IP:8080` in your browser

2. **Verify credentials:** Check TWL*KODI*\* environment variables:

   ```bash
   TWL_KODI_HOSTNAME=192.168.1.100
   TWL_KODI_PORT=8080
   TWL_KODI_USER=kodi_user
   TWL_KODI_PASSWORD=kodi_password
   ```

3. **Test the connection manually:**

   ```bash
   curl -u USERNAME:PASSWORD http://HOSTNAME:8080/jsonrpc -d '{"jsonrpc":"2.0","id":1,"method":"JSONRPC.Ping"}'
   ```

4. **Disable Kodi notifications** (if Kodi is not important):

   ```bash
   # Just leave these unset in .env
   TWL_KODI_HOSTNAME=
   ```

---

### Issue: NFO files are malformed or contain bad characters

**Root Cause:** Older versions had XML escaping issues.

**Fix:**

```bash
# Regenerate all NFO files with proper XML escaping
OVERWRITE_NFO_FILES=true
REPROCESS_EXISTING=true
```

Run the downloader once with these settings, then turn them back off.

---

### Issue: Cookies not working

**Verification:**

1. **Check cookie file exists:**

   ```bash
   ls -la /config/cookies.txt
   ```

2. **Verify format:** It should be in Netscape format (plain text):

   ```bash
   head /config/cookies.txt
   # Should show comment lines starting with #
   ```

3. **Re-export cookies:** Use your browser extension to export fresh cookies

4. **Docker volume mapping:** Verify the volume is mounted correctly:

   ```bash
   docker run --rm -v /path/to/cookies:/config twl-downloader \
     ls -la /config/cookies.txt
   ```

---

### Issue: PO Token Not Working or "Invalid PO Token"

**Root Cause:** PO tokens are session-specific and expire after ~24 hours.

**Fix:**

1. **Check if Token is Still Valid:**
   - PO tokens expire quickly (usually 24 hours or less)
   - Extract a fresh token from your browser

2. **Re-Extract the Token:**
   - Follow the manual extraction steps in the [README](./README.md#using-po-tokens-to-bypass-sabr-restrictions)
   - Or use a [PO Token Provider plugin](https://github.com/topics/yt-dlp-pot-provider) for automatic refreshing

3. **Verify Token Format:**
   - Token should be a long alphanumeric string
   - Make sure it's not wrapped in extra quotes

4. **Check Prerequisites:**

   ```bash
   # Both cookies AND PO token are required
   export YOUTUBE_COOKIES_FILE=/config/cookies.txt
   export YOUTUBE_PO_TOKEN="your_token"
   ```

5. **Monitor Logs:**

   ```bash
   # Check if the mweb client with PO token is being attempted
   docker logs twl-downloader | grep -i "mweb\|po_token"
   ```

---

### Issue: "JavaScript runtime not found" or Deno errors

**Root Cause:** Deno installation failed in Docker.

**Fix:**

```bash
# Rebuild without cache
docker build --no-cache -t twl-downloader .

# Verify Deno is installed
docker run --rm twl-downloader deno --version
```

If it still fails, check the Dockerfile build logs:

```bash
docker build -t twl-downloader . 2>&1 | grep -i deno
```

---

### Issue: "Disk full" or write permission errors

**Root Cause:** Download directory is full or doesn't have write permissions.

**Fix:**

1. **Check disk space:**

   ```bash
   df -h /downloads
   du -sh /downloads
   ```

2. **Check permissions:**

   ```bash
   ls -la /downloads
   chmod 755 /downloads  # Add write permission if needed
   ```

3. **Use temp directory:**

   ```bash
   # Ensure temp has enough space
   df -h /tmp
   ```

4. **Clean up space:**

   ```bash
   # Remove old incomplete downloads in temp
   rm -rf /tmp/tmp-twl-*
   ```

---

## Getting Help

If you can't resolve the issue:

1. **Check if it's a known issue:**
   - GitHub Issues: <https://github.com/yt-dlp/yt-dlp/issues>
   - Search for your error message

2. **Collect debugging information:**

   ```bash
   yt-dlp --version
   python --version
   deno --version

   # Try the video URL directly
   yt-dlp -vU "https://www.youtube.com/watch?v=VIDEO_ID"
   ```

3. **Report to yt-dlp if it's a download issue:**
   - Include the verbose output above
   - Include the video URL (if possible)
   - Include your OS and Python version

4. **Check the relevant guides:**
   - For SABR/nsig issues: [SABR-AND-NSIG-GUIDE.md](./SABR-AND-NSIG-GUIDE.md)
   - For EJS issues: [EJS-SETUP.md](./EJS-SETUP.md)
   - For general config: [README.md](./README.md)
