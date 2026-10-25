# Neon Ronin - Android version

Same game as the PC version (`main.py` is the same file). On Android it switches on by itself:
- **touch controls**: a joystick on the left, buttons on the right (SLASH, JUMP, DASH, PARRY, SLIDE, SUPER, USE, pause)
- **Settings -> TOUCH LAYOUT**: drag any control to move it, tap one and press **-** / **+** to resize it,
  **RESET** for the default layout, **DONE** to save
- fullscreen landscape, the phone's back button works as back / pause

## Getting the APK (built for free on GitHub's servers)

1. Make a free account on <https://github.com> and click **New repository** (top right **+**).
   Name it `neon-ronin`, choose **Private** or Public, click **Create repository**.
2. On the new repository page click **uploading an existing file**.
3. Open this folder (`neon_ronin_mobile`) in Explorer, select **everything inside it**
   (including the `.github` folder) and drag it onto the upload page. Click **Commit changes**.
4. Open the **Actions** tab. A "Build APK" run starts by itself (first build takes ~20-40 min).
5. When it shows a green tick, open the run, scroll to **Artifacts** and download **NeonRonin-apk**.
   It's a zip - inside is `neonronin-1.0-...-debug.apk`. Put it in this folder if you like.
6. Copy the .apk to your phone and open it. Android will ask to allow installing apps from this source - allow it.

If a run fails (red cross), open it, click the failed step and send me the last lines of the log.

## After changing the game

`main.py` here is a copy of `..\neon_ronin\main.py`. After changes, copy it over again and upload the new
`main.py` to the repository (**Add file -> Upload files**) - GitHub rebuilds the APK automatically.

## Try the touch controls on PC

```
python main.py --touch
```
The mouse acts as one finger.
