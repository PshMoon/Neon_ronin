"""Build the Android version of Neon Ronin from the PC game.

    python make_mobile.py

Reads ../Neon Ronin agents/main.py (the PC game), adds the phone layer (touch stick and buttons, touch layout
editor, touch calibration, tap menus, bundled fonts, Android back button, phone defaults) and writes main.py here.
It also copies the music. After the PC game changes, run it again and push: GitHub builds the APK.
Try the touch controls on the PC with:  python main.py --touch   (the mouse is one finger)
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.join(HERE, '..', 'Neon Ronin agents')
src = open(os.path.join(PC, 'main.py'), encoding='utf-8').read()


def rep(a, b, n=1):
    """Replace exactly n occurrences of a (fails loudly if the PC game changed under this patch)."""
    global src
    c = src.count(a)
    if c != n:
        sys.exit(f"make_mobile: expected {n}x, found {c}x:\n{a[:200]}")
    src = src.replace(a, b)


# ================================================================ header: Android, touch layout, phone defaults
rep("""SAVE_DIR = os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'), 'NeonRonin')""",
    """ANDROID = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_PRIVATE' in os.environ
TOUCH = ANDROID or '--touch' in sys.argv          # on-screen touch controls (--touch: try them on PC with the mouse)
SAVE_DIR = os.path.join(os.environ.get('ANDROID_PRIVATE') or os.environ.get('APPDATA') or os.path.expanduser('~'), 'NeonRonin')""")
rep("""                    'a_kills': False, 'a_money': False, 'diff': 2}""",
    """                    'a_kills': False, 'a_money': False, 'diff': 2,
                    'float_stick': True, 'touch_alpha': .8, 'tcal': None}   # tcal: touch calibration [ax, bx, ay, by]
if ANDROID:                                          # phones: lighter rain, no CRT layer
    DEFAULT_SETTINGS.update(rain=0, crt=False)
# on-screen controls: action -> [x, y, radius] in game pixels (480x270). The player can move/resize them in settings.
DEFAULT_TOUCH = {'stick': [70, 200, 38], 'atk': [400, 218, 26], 'jump': [452, 170, 22], 'dash': [342, 240, 18],
                 'parry': [396, 158, 17], 'skill': [454, 238, 15], 'super': [340, 184, 16], 'use': [288, 238, 14],
                 'pause': [460, 60, 12]}
TOUCH_V = 3                                          # bump when DEFAULT_TOUCH changes: old saved layouts are reset
TOUCH_LABELS = {'atk': "SLASH", 'jump': "JUMP", 'dash': "DASH", 'parry': "PARRY", 'skill': "SKILL",
                'super': "SUPER", 'use': "USE", 'pause': "II", 'stick': ""}
TOUCH_RU = {"SLASH": "УДАР", "JUMP": "ПРЫЖОК", "DASH": "РЫВОК", "PARRY": "БЛОК", "SKILL": "НАВЫК",
            "SUPER": "СУПЕР", "USE": "ИСП."}                 # short Russian names that fit on a round button""")
rep("""scr = pg.display.set_mode((W, H), pg.SCALED | pg.RESIZABLE)""",
    """if not hasattr(pg.transform, 'scale_by'):           # Android's pygame is older than pygame-ce: no scale_by
    pg.transform.scale_by = lambda s_, k: pg.transform.scale(s_, (max(1, int(s_.get_width() * k)), max(1, int(s_.get_height() * k))))
scr = pg.display.set_mode((W, H), pg.SCALED | (pg.FULLSCREEN if ANDROID else pg.RESIZABLE))""")
rep("""pg.mixer.pre_init(""", """if ANDROID:                                          # phones report the accelerometer as a joystick: tilting
    os.environ['SDL_ACCELEROMETER_AS_JOYSTICK'] = '0'  # the phone would press buttons. Turn that off.
pg.mixer.pre_init(""")

# fonts: phones have no Windows fonts. Bundled (SIL OFL): DotGothic16 (pixel, Latin + Cyrillic + Japanese) and
# Oswald (the Impact-like display font, Latin + Cyrillic)
rep('''def pick_font(names, size, bold=True):
    """First installed font from a comma list that has Cyrillic glyphs too (the Russian text needs them)."""''',
    '''def pick_font(names, size, bold=True):
    """First installed font from a comma list that has Cyrillic glyphs too (the Russian text needs them)."""
    if ANDROID or '--phonefonts' in sys.argv:            # phones: the bundled fonts
        disp = 'impact' in names
        path = os.path.join(ASSETS, 'fonts', 'Oswald.ttf' if disp else 'DotGothic16-Regular.ttf')
        if os.path.exists(path):
            f = pg.font.Font(path, max(9, round(size * (.92 if disp else .9))))
            if disp:
                f.set_bold(True)
            return f''')
rep("""F_JP = pg.font.SysFont("yugothic,msgothic,meiryo", 11, bold=True)
F_JPB = pg.font.SysFont("yugothic,msgothic,meiryo", 16, bold=True)""",
    """F_JP = pick_font("yugothic,msgothic,meiryo", 11) if ANDROID or '--phonefonts' in sys.argv else pg.font.SysFont("yugothic,msgothic,meiryo", 11, bold=True)
F_JPB = pick_font("yugothic,msgothic,meiryo", 16) if ANDROID or '--phonefonts' in sys.argv else pg.font.SysFont("yugothic,msgothic,meiryo", 16, bold=True)""")
rep("""MENU_KEYS = {pg.K_RETURN: ('ok',),""", """MENU_KEYS = {pg.K_AC_BACK: ('back', 'pause'), pg.K_RETURN: ('ok',),""")   # the phone's back button

# settings file: the touch layout and calibration
rep("""    st['kb'], st['pad'] = kb, pad
    return st""", """    st['kb'], st['pad'] = kb, pad
    if not isinstance(st.get('touch_v'), int) or st['touch_v'] < TOUCH_V:   # a layout from an older version: defaults
        st.pop('touch', None)
    st['touch_v'] = TOUCH_V
    touch = {k: list(v) for k, v in DEFAULT_TOUCH.items()}
    if isinstance(st.get('touch'), dict):
        for k, v in st['touch'].items():
            try:
                if k in touch:
                    touch[k] = [float(c) for c in v][:3]
            except (TypeError, ValueError):
                pass
    st['touch'] = touch
    if not (isinstance(st.get('tcal'), list) and len(st['tcal']) == 4):
        st['tcal'] = None
    return st""")

# ================================================================ game state
rep("""        s.click, s.moved = False, False
        if pg.mixer.get_init():""", """        s.click, s.moved = False, False
        s.fingers, s.tedit_sel, s.drag, s.atk_rep = {}, None, None, 0.0   # touch: finger id -> [x, y, control, ...]
        s.ptr = (-99, -99)                                     # touch: where the last tap was (menus read it as the mouse)
        s.touch_map = 'direct' if pg.get_sdl_version() >= (2, 0, 18) else 'window'
        s.fnorm = s.mpos = None                                # this frame's finger-down / fake click (auto calibration)
        if TOUCH:                                              # every menu reads the mouse: on a phone that is the last tap
            pg.mouse.get_pos = lambda: (int(s.ptr[0]), int(s.ptr[1]))
        if pg.mixer.get_init():""")
rep("""        s.new_run()
        s.go('menu')

    def go(s, state, fade=.6):
        s.state, s.state_t, s.sel, s.fade = state, s.t, 0, fade
        menus = ('menu', 'stats', 'settings', 'controls', 'skins', 'exit', 'victory', 'locsel', 'upgrades', 'teleport')""",
    """        s.new_run()
        s.go('menu')
        if ANDROID and not s.settings['tcal']:                 # first launch on a phone: calibrate the touch screen
            s.start_tcal('menu')

    def go(s, state, fade=.6):
        s.state, s.state_t, s.sel, s.fade = state, s.t, 0, fade
        if state != 'play':
            s.fingers = {}                                     # no stuck touch buttons across screens
        menus = ('menu', 'stats', 'settings', 'controls', 'skins', 'exit', 'victory', 'locsel', 'upgrades', 'teleport',
                 'tcal', 'touchedit')""")

# held: the stick and the held buttons
rep("""                for a in ('jump', 'crouch'):
                    h[a] |= s.pad_down(j, pad.get(a))
            except pg.error:
                pass
        return h""", """                for a in ('jump', 'crouch'):
                    h[a] |= s.pad_down(j, pad.get(a))
            except pg.error:
                pass
        if TOUCH:                                                  # on-screen stick + held buttons
            sr = s.settings['touch']['stick'][2]
            for f in s.fingers.values():
                if f[2] == 'stick':
                    dx, dy = f[0] - f[3], f[1] - f[4]
                    h['left'] |= dx < -sr * .25
                    h['right'] |= dx > sr * .25
                    h['up'] |= dy < -sr * .55 and abs(dy) > abs(dx) * .7
                    h['down'] |= dy > sr * .65 and dy > abs(dx) * 1.2     # strict: a drifting thumb isn't "down"
                elif f[2] == 'jump':
                    h['jump'] = True
        return h""")

# ================================================================ the touch layer (from the first Android version)
TOUCH_CODE = '''
    # ---------- touch controls (Android, or the PC with --touch)
    def to_logical(s, nx, ny):
        """Finger position (0..1) -> game pixels. Newer SDL gives fingers as 0..1 of the game screen ('direct');
        older SDL as 0..1 of the whole window, letterbox bars included ('window'). A calibration beats both."""
        cal = s.settings['tcal']
        if cal:
            return cal[0] * nx + cal[1], cal[2] * ny + cal[3]
        if s.touch_map == 'direct':
            return nx * W, ny * H
        ww, wh = pg.display.get_window_size()
        k = min(ww / W, wh / H)
        return (nx * ww - (ww - W * k) / 2) / k, (ny * wh - (wh - H * k) / 2) / k

    def touch_calibrate(s):
        """Phones also send a fake mouse click for a tap, already mapped to the game screen by SDL.
        When a finger-down and that click arrive together, keep the finger mapping that agrees with it."""
        if s.fnorm is None or s.mpos is None or s.settings['tcal']:
            return
        err = {}
        for mode in ('direct', 'window'):
            s.touch_map = mode
            x, y = s.to_logical(*s.fnorm)
            err[mode] = math.hypot(x - s.mpos[0], y - s.mpos[1])
        s.touch_map = min(err, key=err.get)
        s.fnorm = s.mpos = None

    def touch_event(s, kind, fid, x, y):
        L = s.settings['touch']
        if s.state == 'touchedit':
            s.tedit_event(kind, fid, x, y)
            return
        s.last_input = 'touch'
        if s.state != 'play':                                     # menus: a tap is the mouse moving there and clicking
            if kind == 'down':                                    # (menus pick on the first tap, open on the second)
                s.ptr = (x, y)
                s.moved = s.click = True
                s.act.add('atk')
            return
        if kind == 'up':
            s.fingers.pop(fid, None)
            return
        f = s.fingers.get(fid)
        if kind == 'move':                                        # a finger keeps the control it first pressed
            if f is not None:
                f[0], f[1] = x, y
                if f[2] == 'stick' and s.settings['float_stick']:  # the base trails the thumb: reversing is instant
                    sr = L['stick'][2]
                    d = math.hypot(x - f[3], y - f[4])
                    if d > sr:
                        f[3], f[4] = x - (x - f[3]) * sr / d, y - (y - f[4]) * sr / d
            return
        a = s.touch_button(x, y)
        if a:
            s.fingers[fid] = [x, y, a]
            s.act.add(a)
            s.atk_rep = .32
        elif not any(g[2] == 'stick' for g in s.fingers.values()):
            sx, sy, sr = L['stick']
            if s.settings['float_stick']:
                if x < W * .5:                                    # floating: left half, the stick appears under the thumb
                    s.fingers[fid] = [x, y, 'stick', max(sr, x), max(sr + 20, min(H - sr * .6, y))]
            elif math.hypot(x - sx, y - sy) < sr * 1.6:          # fixed: only around its own spot
                s.fingers[fid] = [x, y, 'stick', sx, sy]

    def touch_button(s, x, y):
        """The button under the finger (a little larger than drawn), or None."""
        hits = [(math.hypot(x - bx, y - by) / br, a) for a, (bx, by, br) in s.settings['touch'].items()
                if a != 'stick' and (a != 'skill' or s.skill()) and math.hypot(x - bx, y - by) < br * 1.3]
        return min(hits)[1] if hits else None

    def touch_tick(s, dt):
        """Holding SLASH keeps swinging."""
        if any(f[2] == 'atk' for f in s.fingers.values()):
            s.atk_rep -= dt
            if s.atk_rep <= 0:
                s.act.add('atk')
                s.atk_rep = .2

    @staticmethod
    def touch_sprite(kind, r, label, state):
        """Pre-drawn translucent control (cached): a whole-screen alpha layer every frame is slow on phones."""
        key = (kind, r, label, state, LANG)
        img = _touch.get(key)
        if img is None:
            r = int(r)
            img = pg.Surface((r * 2 + 2, r * 2 + 2), pg.SRCALPHA)
            c = (r + 1, r + 1)
            if kind == 'knob':
                pg.draw.circle(img, (255, 255, 255, 130 if state else 70), c, r)
            else:
                fill = {'on': (215, 20, 40, 160), 'dim': (20, 10, 30, 40), 'off': (20, 10, 30, 80)}[state]
                pg.draw.circle(img, fill, c, r)
                pg.draw.circle(img, (255, 255, 255, 60 if state == 'dim' else 150), c, r, 2)
                if label:
                    t = F_S.render(TOUCH_RU.get(label, label) if LANG == 'ru' else label, True, WHITE)
                    if t.get_width() > r * 2 - 2:
                        t = pg.transform.smoothscale(t, (r * 2 - 2, max(1, int(t.get_height() * (r * 2 - 2) / t.get_width()))))
                    t.set_alpha(110 if state == 'dim' else 230)
                    img.blit(t, (c[0] - t.get_width() // 2, c[1] - t.get_height() // 2))
            _touch[key] = img = img.convert_alpha()
        return img

    def draw_touch(s):
        """Translucent on-screen controls."""
        L = s.settings['touch']
        al = int(255 * max(.25, s.settings['touch_alpha']))     # BUTTON OPACITY setting
        down = {f[2] for f in s.fingers.values()}
        sx, sy, sr = L['stick']
        kx = ky = None
        for f in s.fingers.values():
            if f[2] == 'stick':
                sx, sy = f[3], f[4]
                kx, ky = f[0], f[1]
        sr = int(sr)
        img = s.touch_sprite('btn', sr, '', 'off' if kx is not None or not s.settings['float_stick'] else 'dim')
        img.set_alpha(al)
        scr.blit(img, (sx - sr - 1, sy - sr - 1))
        if kx is not None:
            d = math.hypot(kx - sx, ky - sy) or 1
            k = min(1, sr / d)
            kx, ky = sx + (kx - sx) * k, sy + (ky - sy) * k
        else:
            kx, ky = sx, sy
        img = s.touch_sprite('knob', int(sr * .45), '', 'stick' in down)
        img.set_alpha(al)
        scr.blit(img, (kx - img.get_width() // 2, ky - img.get_height() // 2))
        p = s.pl
        near = lambda x: abs(p.x + p.w / 2 - x) < 40
        usable = {'super': s.superk >= s.super_need(),
                  'skill': bool(s.skill()) and p.skcd <= 0,
                  'use': bool((s.kiosk and not s.kiosk['used'] and not s.kiosk.get('closed') and near(s.kiosk['x'])) or
                              (s.keydoor and near(s.keydoor['x'])) or
                              (s.door.get('exit') and near(s.door['x'])) or
                              (s.hole and s.hole.get('door') and near(s.hole['x'])))}
        for a, (x, y, r) in L.items():
            if a == 'stick' or (a == 'skill' and not s.skill()):
                continue
            state = 'on' if a in down else ('dim' if not usable.get(a, True) else 'off')
            img = s.touch_sprite('btn', int(r), TOUCH_LABELS[a], state)
            img.set_alpha(al)
            scr.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))

    # ---------- touch layout editor (Settings -> Input -> Touch layout)
    TEDIT_BTNS = (("-", pg.Rect(150, 6, 30, 20)), ("+", pg.Rect(186, 6, 30, 20)), ("RESET", pg.Rect(222, 6, 56, 20)),
                  ("DONE", pg.Rect(284, 6, 56, 20)))

    def tedit_event(s, kind, fid, x, y):
        L = s.settings['touch']
        if kind == 'down':
            for lab, r in s.TEDIT_BTNS:
                if r.collidepoint(x, y):
                    s.tedit_button(lab)
                    return
            best = min((math.hypot(x - bx, y - by) / br, a) for a, (bx, by, br) in L.items())
            if best[0] < 1.4:
                a = best[1]
                s.tedit_sel, s.drag = a, (fid, a, x - L[a][0], y - L[a][1])
                sfx('sel')
        elif kind == 'move' and s.drag and s.drag[0] == fid:
            _, a, ox, oy = s.drag
            r = L[a][2]
            L[a][0], L[a][1] = max(r, min(W - r, x - ox)), max(r + 26, min(H - r, y - oy))
        elif kind == 'up' and s.drag and s.drag[0] == fid:
            s.drag = None
            s.save_settings()

    def tedit_button(s, lab):
        L = s.settings['touch']
        if lab in "-+" and s.tedit_sel:
            r = L[s.tedit_sel][2] * (1.12 if lab == "+" else 1 / 1.12)
            L[s.tedit_sel][2] = max(8.0, min(60.0, r))
        elif lab == "RESET":
            s.settings['touch'] = {k: list(v) for k, v in DEFAULT_TOUCH.items()}
        elif lab == "DONE":
            s.wipe_to(lambda: s.go('settings', 0))
        s.save_settings()
        sfx('sel')

    def st_touchedit(s, dt):
        s.persona_bg(tint=False)
        scr.blit(s.dim, (0, 0))
        L = s.settings['touch']
        s.fingers = {}
        s.draw_touch()
        for a, (x, y, r) in L.items():                              # name tags + selection ring
            if a == s.tedit_sel:
                pg.draw.circle(scr, RED, (int(x), int(y)), int(r + 3), 2)
            if a == 'stick':
                text(tr("MOVE"), F_S, WHITE, x, y - 5, True)
            if a == 'skill' and not s.skill():                      # (shown here even when this skin has no skill)
                img = s.touch_sprite('btn', int(r), TOUCH_LABELS[a], 'dim')
                scr.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
        for lab, r in s.TEDIT_BTNS:
            pg.draw.rect(scr, WHITE if lab == "DONE" else INK, r)
            pg.draw.rect(scr, WHITE, r, 1)
            s.row_text(lab, lab == "DONE", r.centerx - F_S.size(tr(lab))[0] // 2, r.y + 4)
        text(tr("drag to move  -  tap, then - / + to resize"), F_S, (230, 220, 245), W // 2, 32, True)
        if 'back' in s.act:
            s.save_settings()
            s.wipe_to(lambda: s.go('settings', 0))

    # ---------- touch calibration: two taps measure how this phone's touch screen maps onto the game
    TCAL_PTS = ((60, 50), (W - 60, H - 50))

    def start_tcal(s, after):
        s.tcal_raw, s.tcal_after = [], after
        s.go('tcal', 0)

    def tcal_tap(s, nx, ny):
        s.tcal_raw.append((nx, ny))
        sfx('sel')
        if len(s.tcal_raw) < 2:
            return
        (n1x, n1y), (n2x, n2y) = s.tcal_raw
        (x1, y1), (x2, y2) = s.TCAL_PTS
        if abs(n2x - n1x) < .2 or abs(n2y - n1y) < .2:             # taps too close together: try again
            s.tcal_raw = []
            sfx('deny')
            return
        ax, ay = (x2 - x1) / (n2x - n1x), (y2 - y1) / (n2y - n1y)
        s.settings['tcal'] = [ax, x1 - ax * n1x, ay, y1 - ay * n1y]
        s.save_settings()
        sfx('buy')
        nxt = s.tcal_after
        s.wipe_to(lambda: s.go(nxt, 0))

    def st_tcal(s, dt):
        scr.fill((6, 3, 12))
        i = min(len(s.tcal_raw), 1)
        x, y = s.TCAL_PTS[i]
        pulse = 10 + math.sin(s.t * 6) * 3
        pg.draw.circle(scr, RED, (x, y), int(pulse + 6), 2)
        pg.draw.circle(scr, WHITE, (x, y), 3)
        pg.draw.line(scr, WHITE, (x - 18, y), (x - 7, y), 2)
        pg.draw.line(scr, WHITE, (x + 7, y), (x + 18, y), 2)
        pg.draw.line(scr, WHITE, (x, y - 18), (x, y - 7), 2)
        pg.draw.line(scr, WHITE, (x, y + 7), (x, y + 18), 2)
        outlined(tr("TOUCH CALIBRATION"), F_PM, WHITE, W // 2, 104, center=True, r=1)
        text(tr("tap the exact center of the target") + f"  ({i + 1} / 2)", F_S, (230, 220, 245), W // 2, 132, True)
        text(tr("so every button reacts right where you press it"), F_S, (160, 150, 180), W // 2, 148, True)
        if 'back' in s.act:                                     # (phone back button: skip for now)
            s.go(s.tcal_after, 0)

'''
rep("""    def bind_name(s, kind, a):
        if kind == 'kb':""", TOUCH_CODE + """    def bind_name(s, kind, a):
        if TOUCH and s.last_input == 'touch':                    # phones: the on-screen button's name
            lab = TOUCH_LABELS.get(a, a.upper())
            return TOUCH_RU.get(lab, lab) if LANG == 'ru' else lab
        if kind == 'kb':""")
rep('''    def handle_event(s, ev):
        """Turn raw keyboard / mouse / gamepad events into actions for this frame."""''',
    '''    def handle_event(s, ev):
        """Turn raw keyboard / mouse / gamepad events into actions for this frame."""
        if TOUCH:
            kinds = {pg.FINGERDOWN: 'down', pg.FINGERMOTION: 'move', pg.FINGERUP: 'up'}
            if ev.type in kinds:
                if s.state == 'tcal':
                    if ev.type == pg.FINGERDOWN:
                        s.tcal_tap(ev.x, ev.y)
                    return
                if ANDROID and ev.type == pg.FINGERDOWN:
                    s.fnorm = (ev.x, ev.y)
                    s.touch_calibrate()
                s.touch_event(kinds[ev.type], ev.finger_id, *s.to_logical(ev.x, ev.y))
                return
            if ev.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION, pg.MOUSEWHEEL):
                if ANDROID and ev.type == pg.MOUSEBUTTONDOWN:
                    s.mpos = ev.pos
                    s.touch_calibrate()
                if not ANDROID and getattr(ev, 'button', 1) == 1:   # PC test mode: the mouse plays one finger
                    mk = {pg.MOUSEBUTTONDOWN: 'down', pg.MOUSEBUTTONUP: 'up'}.get(ev.type)
                    if ev.type == pg.MOUSEMOTION and ev.buttons[0]:
                        mk = 'move'
                    if mk == 'down' and s.state == 'tcal':
                        s.tcal_tap(ev.pos[0] / W, ev.pos[1] / H)
                    elif mk:
                        s.touch_event(mk, 'mouse', *ev.pos)
                return                                              # (phones also send fake mouse events: ignored)
            if ANDROID and ev.type in (pg.JOYDEVICEADDED, pg.JOYDEVICEREMOVED, pg.JOYBUTTONDOWN, pg.JOYBUTTONUP,
                                       pg.JOYHATMOTION, pg.JOYAXISMOTION, pg.JOYBALLMOTION):
                return                                              # (phones: touch only, no sensor "gamepad")''')
rep("""_glow, _smoke = {}, {}""", """_glow, _smoke, _touch = {}, {}, {}""")

# ================================================================ play: the controls on screen, held SLASH repeats
rep("""    def st_play(s, dt):
        if getattr(s, 'gifts', None)""", """    def st_play(s, dt):
        if TOUCH:
            s.touch_tick(dt)
        if getattr(s, 'gifts', None)""")
rep("""        if s.superT < 0:
            s.hud()
        s.draw_boss_hud()""", """        if s.superT < 0:
            s.hud()
        s.draw_boss_hud()
        if TOUCH and s.superT < 0:
            s.draw_touch()""")

# ================================================================ menus: first tap picks, second tap opens
rep("""        hov, best = None, 1e9                                            # the one row under the mouse (rows overlap a""",
    """        was = s.sel
        hov, best = None, 1e9                                            # the one row under the mouse (rows overlap a""")
rep("""            if s.click:
                fire = hov
        for i, (lab, _) in enumerate(items):""", """            if s.click and (not TOUCH or hov == was):          # (touch: the first tap only picks it)
                fire = hov
        for i, (lab, _) in enumerate(items):""")
rep("""                if s.click:
                    s.sel, go_in = i, True""", """                if s.click and (not TOUCH or on):
                    s.sel, go_in = i, True""")
rep("""                if s.click and r.collidepoint(mx, my):
                    s.sel = i
                    s.change_setting(rows[i], -1 if arrows and lb.collidepoint(mx, my) else 1)""",
    """                if s.click and r.collidepoint(mx, my) and (not TOUCH or on):
                    s.sel = i
                    s.change_setting(rows[i], -1 if arrows and lb.collidepoint(mx, my) else 1)""")
rep("""            if s.click and r.collidepoint(mx, my) and not pk:
                s.sel, fire = i, True""", """            if s.click and r.collidepoint(mx, my) and not pk and (not TOUCH or on):
                s.sel, fire = i, True""")

# ================================================================ settings: the touch rows (Input), no PC-only rows on phones
rep("""                if row[2] == 'admin' and s.settings.get('admin'):   # the admin list drops down under its switch
                    out += ADMIN_ROWS
        return out""", """                if row[2] == 'admin' and s.settings.get('admin'):   # the admin list drops down under its switch
                    out += ADMIN_ROWS
        if ANDROID:                                             # (no window, no key bindings, no gamepad on a phone)
            out = [r for r in out if r[2] not in ('fullscreen', 'rumble') and r[1] != 'CONTROLS']
        if TOUCH and s.SET_CATS[ci][0] == 'INPUT':
            out += [('', 'TOUCH LAYOUT', 'touchedit', 'action'), ('', 'CALIBRATE TOUCH', 'tcal', 'action'),
                    ('', 'FLOATING STICK', 'float_stick', 'toggle'), ('', 'BUTTON OPACITY', 'touch_alpha', 'slider')]
        return out""")
rep("""        elif kind == 'action' and key == 'teleport':            # admin: pick a location / district / boss to jump to""",
    """        elif kind == 'action' and key == 'touchedit':           # move / resize the on-screen controls
            sfx('sel')
            s.set_keep = True
            s.tedit_sel = None
            s.wipe_to(lambda: s.go('touchedit', 0))
            return
        elif kind == 'action' and key == 'tcal':                # measure the touch screen again
            sfx('sel')
            s.set_keep = True
            s.start_tcal('settings')
            return
        elif kind == 'action' and key == 'teleport':            # admin: pick a location / district / boss to jump to""")
rep("""            return ">>" if key == 'teleport' else tr("DO IT")""",
    """            return ">>" if key in ('teleport', 'touchedit', 'tcal') else tr("DO IT")""")
rep("""        ok = os.path.exists(os.path.join(ASSETS, 'level.mp3'))""",
    """        ok = ANDROID or os.path.exists(os.path.join(ASSETS, 'level.mp3'))""")

# the "[USE] OPEN KIOSK" tags: translate the label too
rep('        txt = f"[{key}] {label}"', '        txt = f"[{key}] {tr(label)}"')

# the version line on the main menu says which game this is: the agents version, Android, built on <date>
import datetime
rep('VERSION = "v3: 10 districts, bosses, Russian"',
    f'VERSION = "agents version - Android {datetime.date.today():%Y-%m-%d}"')

# ================================================================ Russian text for the new lines
rep("""    "SPIRITS": "ОДЕРЖИМЫЕ",""", """    "TOUCH LAYOUT": "РАСКЛАДКА КНОПОК", "CALIBRATE TOUCH": "КАЛИБРОВКА ЭКРАНА", "FLOATING STICK": "ПЛАВАЮЩИЙ СТИК",
    "BUTTON OPACITY": "ПРОЗРАЧНОСТЬ КНОПОК", "TOUCH CALIBRATION": "КАЛИБРОВКА ЭКРАНА", "MOVE": "ХОД",
    "tap the exact center of the target": "нажми точно в центр мишени",
    "so every button reacts right where you press it": "чтобы кнопки срабатывали ровно там, где жмёшь",
    "drag to move  -  tap, then - / + to resize": "тяни - сдвинуть,  нажми и -/+ - размер",
    "RESET": "СБРОС",
    "SPIRITS": "ОДЕРЖИМЫЕ",""")

open(os.path.join(HERE, 'main.py'), 'w', encoding='utf-8').write(src)

# ================================================================ assets: the music (level.wav is not used by the game)
os.makedirs(os.path.join(HERE, 'assets'), exist_ok=True)
for name in ('menu.wav', 'calm.wav', 'fight.wav'):          # (no mp3: buildozer.spec packs png, wav, ttf)
    a, b = os.path.join(PC, 'assets', name), os.path.join(HERE, 'assets', name)
    if os.path.exists(a) and (not os.path.exists(b) or os.path.getsize(a) != os.path.getsize(b)):
        shutil.copy2(a, b)
print("make_mobile: main.py written for Android (" + str(len(src)) + " bytes)")
