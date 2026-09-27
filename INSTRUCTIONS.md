# Download Canvas Videos in Batches

1. Place `canvas_videos.py` on your Desktop or in another desired directory.

2. In Terminal, change to that directory. For example, if the script is on your Desktop:

   ```sh
   cd ~/Desktop
   ```

3. The first time, run these installation commands:

   ```sh
   python3 -m venv .video-venv
   source .video-venv/bin/activate
   python -m pip install playwright
   python -m playwright install chromium
   ```

   Each time you open a new Terminal session, change to the script's directory and activate the environment again:

   ```sh
   source .video-venv/bin/activate
   ```

4. To download a batch starting from a particular lesson, copy that lesson's Canvas page URL. This script supports Penn Canvas course `1942808`.

5. Run the following command, replacing `STARTING_LESSON_URL_HERE` with the copied URL:

   ```sh
   python canvas_videos.py --start "STARTING_LESSON_URL_HERE" --count 8 --workers 3
   ```

   `--count 8` checks eight consecutive course items, including the starting lesson. Non-video items count toward this total, so the batch may contain fewer than eight videos. `--workers 3` allows up to three downloads at a time.

6. A separate browser window opens. Complete Penn login and MFA, then wait until the lesson video appears. Return to Terminal and press Enter.

   The script downloads videos with an enabled Panopto Download button and skips items without one. Files are saved in a `canvas_videos` folder inside your current Terminal directory. If you ran the command from your Desktop, the folder will be on your Desktop.

   Rerun the command to retry failed downloads. Previously completed downloads are skipped automatically.
