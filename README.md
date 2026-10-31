# Neon Ronin - Android version

The phone version of the game in `..\Neon Ronin agents`. `main.py` here is **generated** - don't edit it by hand:

```
python make_mobile.py
```

reads `..\Neon Ronin agents\main.py` (the PC game), adds the phone layer and writes `main.py` here
(it also copies the music). After the PC game changes: run it again, commit and push - GitHub builds the APK.

On Android it switches on by itself:
- **touch controls**: a stick on the left (floating: it appears under your thumb), buttons on the right
  (SLASH - hold it to keep swinging, JUMP, DASH, PARRY, SUPER, SKILL for skins with a skill, USE, pause)
- slam: stick down + JUMP in the air
- menus: tap once to pick, tap again to open
- **Settings -> Input**: TOUCH LAYOUT (drag a control to move it, tap one and **-** / **+** to resize, RESET, DONE),
  CALIBRATE TOUCH, FLOATING STICK, BUTTON OPACITY
- first launch: touch calibration (tap the centre of two targets)
- fullscreen landscape, the phone's back button works as back / pause, Russian and English
  (bundled fonts: DotGothic16 and Oswald, SIL Open Font License)

## Getting the APK

Every push builds it on GitHub (about 20-40 min). The newest one is always on the
[Releases page](https://github.com/PshMoon/Neon_ronin/releases) - download the `.apk`, open it on the phone,
allow installing from this source. If Android says the app can't be installed, uninstall the old Neon Ronin first
(each build is signed with a new debug key).

## Try the touch controls on PC

```
python main.py --touch
```
The mouse acts as one finger. Add `--phonefonts` to see the phone's fonts.
