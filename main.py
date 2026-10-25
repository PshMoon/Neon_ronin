"""NEON RONIN - a tiny cyberpunk-Tokyo action platformer (pygame-ce)."""
import json
import math
import os
import random
import sys
from array import array

import pygame as pg

W, H = 480, 270                 # internal pixel resolution (scaled up to the window)
GY, LW, GRAV = 212, 3200, 950   # ground y, level width, gravity
FLOOR = H - GY                  # height of the reflective street
EXIT_X = 40                     # the door at the start of every district (closes behind you)
END_X = LW - 90                 # the red torii at the end of every district
JUMP_V, PAD_V = 353, 640        # jump ~66 px high (80% of the old 82 px)
ANDROID = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_PRIVATE' in os.environ
TOUCH = ANDROID or '--touch' in sys.argv          # on-screen touch controls (--touch: try them on PC with the mouse)
SAVE_DIR = os.path.join(os.environ.get('ANDROID_PRIVATE') or os.environ.get('APPDATA') or os.path.expanduser('~'), 'NeonRonin')
SAVE = os.path.join(SAVE_DIR, 'stats.json')
SETTINGS_FILE = os.path.join(SAVE_DIR, 'settings.json')
ASSETS = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'assets')
DEFAULT_SETTINGS = {'master': .8, 'music': .6, 'sfx': .8, 'fullscreen': False, 'shake': True,
                    'rain': 1, 'crt': True, 'rumble': True}
RAIN_LEVELS = (("LIGHT", 35), ("MEDIUM", 70), ("HEAVY", 120))
# on-screen controls: action -> [x, y, radius] in game pixels (480x270). The player can move/resize them in settings.
DEFAULT_TOUCH = {'stick': [64, 206, 36], 'atk': [394, 222, 22], 'jump': [444, 188, 20], 'dash': [344, 238, 16],
                 'parry': [394, 170, 16], 'crouch': [448, 244, 14], 'super': [344, 190, 15], 'use': [296, 238, 13],
                 'pause': [462, 58, 11]}
TOUCH_LABELS = {'atk': "SLASH", 'jump': "JUMP", 'dash': "DASH", 'parry': "PARRY", 'crouch': "SLIDE",
                'super': "SUPER", 'use': "USE", 'pause': "II", 'stick': ""}

pg.mixer.pre_init(44100, -16, 2, 512)
pg.init()
if not hasattr(pg.transform, 'scale_by'):           # older pygame builds (e.g. on Android) lack scale_by
    pg.transform.scale_by = lambda s_, k: pg.transform.scale(s_, (max(1, int(s_.get_width() * k)), max(1, int(s_.get_height() * k))))
scr = pg.display.set_mode((W, H), pg.SCALED | (pg.FULLSCREEN if ANDROID else pg.RESIZABLE))
pg.display.set_caption("Neon Ronin")
clock = pg.time.Clock()


def load_font(sysnames, size, bold=False, file=None):
    """Bundled font if present (Android has no Windows fonts), else the system font."""
    path = os.path.join(ASSETS, 'fonts', file) if file else None
    if path and os.path.exists(path):
        return pg.font.Font(path, size)
    return pg.font.SysFont(sysnames, size, bold=bold)


PIX, DISP = 'DotGothic16-Regular.ttf', 'Anton-Regular.ttf'
F_S = load_font("consolas", 10, True, PIX)
F_M = load_font("consolas", 14, True, PIX)
F_JP = load_font("yugothic,msgothic,meiryo", 11, True, PIX)
F_JPB = load_font("yugothic,msgothic,meiryo", 16, True, PIX)
F_P = load_font("impact,arialblack", 28, file=DISP)     # Persona-style display fonts
F_PB = load_font("impact,arialblack", 40, file=DISP)
F_PM = load_font("impact,arialblack", 20, file=DISP)
F_PS = load_font("impact,arialblack", 15, file=DISP)
scr.fill((4, 2, 8))                                       # loading screen while the sound effects are synthesized
_ld = F_PM.render("NEON RONIN", True, (255, 255, 255))
scr.blit(_ld, (W // 2 - _ld.get_width() // 2, H // 2 - 20))
scr.blit(F_S.render("loading...", True, (200, 190, 230)), (W // 2 - 24, H // 2 + 8))
pg.display.flip()
SUPER_CUT, SUPER_T = .35, 1.0                                        # super: camera-dive length, total length

# ---- rebindable controls. Keyboard: action -> key. Xbox pad: action -> button index or trigger ('LT'/'RT').
BIND_ACTIONS = [('left', "MOVE LEFT"), ('right', "MOVE RIGHT"), ('up', "AIM UP"), ('down', "AIM DOWN / SLAM"),
                ('jump', "JUMP"), ('atk', "SLASH"), ('dash', "DASH"), ('crouch', "CROUCH / SLIDE"),
                ('parry', "PARRY"), ('super', "SUPER"), ('use', "USE"), ('pause', "PAUSE")]
DEFAULT_KB = {'left': pg.K_a, 'right': pg.K_d, 'up': pg.K_w, 'down': pg.K_s, 'jump': pg.K_SPACE, 'atk': pg.K_j,
              'dash': pg.K_LSHIFT, 'crouch': pg.K_LCTRL, 'parry': pg.K_k, 'super': pg.K_q, 'use': pg.K_e, 'pause': pg.K_ESCAPE}
DEFAULT_PAD = {'jump': 0, 'atk': 2, 'crouch': 1, 'use': 3, 'super': 4, 'parry': 5, 'dash': 'RT', 'pause': 7}
PAD_NAMES = {0: 'A', 1: 'B', 2: 'X', 3: 'Y', 4: 'LB', 5: 'RB', 6: 'VIEW', 7: 'MENU', 8: 'LS', 9: 'RS', 'LT': 'LT', 'RT': 'RT'}
# keys that always work in menus, whatever the bindings
MENU_KEYS = {pg.K_RETURN: ('ok',), pg.K_KP_ENTER: ('ok',), pg.K_SPACE: ('ok',), pg.K_ESCAPE: ('back', 'pause'),
             pg.K_BACKSPACE: ('back',), pg.K_UP: ('up',), pg.K_DOWN: ('down',), pg.K_LEFT: ('left',), pg.K_RIGHT: ('right',),
             pg.K_AC_BACK: ('back', 'pause')}                   # Android back button
MENU_HINT = ("W/S select   ENTER confirm   F11 fullscreen", "D-PAD select   A confirm   B back")
RED, WHITE, INK = (215, 20, 40), (255, 255, 255), (10, 8, 12)

# "{NAME}" is replaced with the player's chosen name
DIALOG = [
    ("{NAME}", "...Where am I?"),
    ("VOICE", "Neo-Tokyo. Shinjuku, Sector 9. The rain never stops here."),
    ("VOICE", "Five districts stand between you and the way out. The doors close behind you."),
    ("VOICE", "Coins of light lie scattered across the rooftops. Gold... and the rare mythic ones."),
    ("{NAME}", "And the ones with swords?"),
    ("VOICE", "The Shogun's ronin, his oni and his shinobi. Cut them down."),
]
LEVELS = 5                                  # districts per run (bosses can hook in per level later)
PHRASES = ["The rain remembers every blade.", "Neon bleeds. You don't.", "Deeper into Shinjuku...",
           "The Shogun is watching.", "Steel sings in the dark.", "No way back. Only forward.",
           "Every door closes behind you.", "The city hums a funeral song.", "Your blade is still thirsty.",
           "Masks in the alleys. Eyes on the roofs.", "Breathe. Draw. Cut.", "The night is long. Longer still.",
           "Somewhere a bell rings for the fallen.", "Even the neon is afraid of you now."]
VICTORY_LINES = ["You've done it.", "Five districts. Five doors. All of them behind you now.",
                 "The rain stops - just for a moment.", "The Shogun will remember this name."]
BUFFS = {   # id: (title, description, colour)
    'vital': ("VITAL SPIRIT", "+1 max HP and heal fully", (255, 70, 100)),
    'edge': ("RAZOR EDGE", "+1 damage on every slash", (230, 230, 255)),
    'swift': ("WIND STEP", "Run 15% faster", (80, 255, 170)),
    'ghost': ("GHOST DASH", "Dash recharges 40% faster", (0, 230, 255)),
    'magnet': ("COIN MAGNET", "Coins fly to you from afar", (255, 205, 50)),
    'vamp': ("BLOOD OATH", "Heal 1 HP every 8 kills", (220, 30, 60)),
    'storm': ("STORM HEART", "Super charges twice as fast", (170, 90, 255)),
    'iron': ("IRON WILL", "Parry window +60%", (190, 200, 220)),
    'greed': ("GOLD RUSH", "Gold coins are worth 2", (255, 170, 40)),
}
KEY_BUFF = ('key', "EXIT KEY", "Leave the run now and keep your coins", (255, 60, 60))
JP_V = ["酒", "龍", "夜", "電", "忍", "鬼", "寿司", "拉麺", "未来", "東京", "侍", "桜", "新宿"]
JP_H = ["トーキョー", "ネオン", "カフェ", "ホテル", "カラオケ", "パチンコ"]
JP_SHOP = ["居酒屋", "ラーメン", "寿司", "薬", "バー", "質屋"]
NEON = [(255, 40, 140), (0, 230, 255), (255, 200, 60), (170, 80, 255), (80, 255, 160)]

# ---- character palettes (pixel-art style: base / shade / light, dark outline, back-light rim)
def samurai(kimono, kimono_d, kimono_l, hakama, hakama_d, accent, rim, rim2, hair, hood, mask, skin=(196, 150, 128),
            hair_down=(18, 14, 24)):
    """Player palette: hooded samurai (hood + face mask, long hair spilling out), kimono, wide hakama."""
    # hooded=False: the original samurai look (headband + ponytail) everywhere; hood colours kept for later use
    hair = hair_down
    return dict(sc=1, head='samurai', weapon='katana', blade=16, skirt=True, sheath=True, hakama=True, hooded=False,
                skin=skin, coat=kimono, coat_d=kimono_d, coat_l=kimono_l, arm=kimono, arm_d=kimono_d,
                pants=hakama, pants_d=hakama_d, boot=(28, 24, 30), boot_d=(18, 15, 20), glove=skin,
                glove_d=tuple(int(c * .75) for c in skin), belt=accent, scarf=accent, hair=hair,
                hood=hood, hood_l=tuple(min(255, c + 40) for c in hood), mask=mask, hair_down=hair_down,
                eye=(255, 255, 255), eyeglow=tuple(c // 5 for c in accent), line=(8, 5, 14), rim=rim, rim2=rim2,
                hilt=accent)


SKINS = {   # id: (name, price, palette)  - more skins can simply be added here
    'shadow': ("SHADOW SAMURAI", 0, samurai((40, 28, 60), (26, 18, 40), (110, 74, 170), (28, 22, 42), (18, 14, 28),
                                            (150, 80, 230), (200, 160, 255), (100, 70, 160),
                                            hair=(236, 62, 112), hood=(34, 34, 60), mask=(24, 28, 44))),
    'white': ("WHITE SAMURAI", 150, samurai((226, 222, 232), (172, 166, 184), (255, 255, 255), (196, 190, 204), (140, 134, 150),
                                            (210, 30, 44), (255, 210, 220), (170, 120, 140),
                                            hair=(222, 40, 58), hood=(214, 212, 224), mask=(40, 36, 46),
                                            hair_down=(235, 235, 240))),
    'crimson': ("CRIMSON SAMURAI", 250, samurai((34, 22, 28), (22, 14, 18), (150, 34, 46), (26, 18, 22), (16, 10, 14),
                                                (225, 30, 44), (255, 130, 140), (140, 50, 60),
                                                hair=(160, 22, 36), hood=(30, 18, 24), mask=(20, 12, 16))),
}
PAL_P = SKINS['shadow'][2]
PAL_E = {
    # grounded looks: muted cloth, real skin tones, soft city back-light, no glowing eyes
    'ronin': dict(sc=1, head='hat', weapon='katana', blade=14, skirt=True, skin=(156, 116, 94), straw=(158, 128, 84), straw_d=(112, 88, 56),
                  coat=(60, 56, 78), coat_d=(42, 38, 56), coat_l=(96, 90, 116), pants=(48, 46, 52), pants_d=(32, 30, 36),
                  boot=(30, 26, 26), boot_d=(20, 17, 17), glove=(156, 116, 94), glove_d=(112, 82, 66), belt=(118, 34, 40),
                  eye=(30, 20, 20), eyeglow=(0, 0, 0), line=(12, 8, 12), rim=(196, 186, 214), rim2=(104, 96, 124), hilt=(40, 40, 46)),
    'oni': dict(sc=1.3, head='oni', weapon='club', blade=22, skirt=False, skin=(150, 112, 92), mask=(150, 34, 34),
                coat=(42, 42, 50), coat_d=(28, 28, 34), coat_l=(84, 84, 96), arm=(42, 42, 50), arm_d=(28, 28, 34),
                pants=(36, 34, 40), pants_d=(24, 22, 28), boot=(26, 22, 22), boot_d=(18, 15, 15), glove=(60, 50, 46), glove_d=(40, 34, 30),
                belt=(128, 36, 36), eye=(30, 20, 20), eyeglow=(0, 0, 0), line=(10, 8, 10), rim=(200, 180, 180), rim2=(110, 96, 96)),
    'ninja': dict(sc=.9, head='mask', weapon=None, blade=0, skirt=False, coat=(40, 42, 50), coat_d=(28, 30, 36), coat_l=(72, 76, 88),
                  pants=(34, 36, 44), pants_d=(24, 26, 32), boot=(18, 18, 22), boot_d=(12, 12, 16), glove=(34, 36, 44), glove_d=(24, 26, 32),
                  belt=(140, 34, 44), scarf=(140, 34, 44), eye=(190, 186, 170), eyeglow=(0, 0, 0), line=(8, 8, 12),
                  rim=(180, 186, 210), rim2=(96, 100, 120)),
}
def shade_pal(S, k=.55):
    """Darker copy of a palette, for characters moving in the background plane."""
    return {key: (tuple(int(c * k) for c in v) if isinstance(v, tuple) and len(v) == 3 else v) for key, v in S.items()}


PAL_BACK = {k: shade_pal(v) for k, v in PAL_E.items()}
STAT_ROWS = [("TOTAL KILLS", 'kills'), ("COINS EARNED", 'coins'), ("MYTHIC COINS", 'mythic'),
             ("TIME PLAYED", 'time'), ("RUNS SURVIVED", 'runs'), ("DISTRICTS CLEARED", 'levels'),
             ("DEATHS", 'deaths'), ("BEST RUN", 'best'), ("PARRIES", 'parries'), ("SUPERS", 'supers'),
             ("ONI SLAIN", 'oni'), ("SHINOBI SLAIN", 'shinobi'), ("GROUND SLAMS", 'slams')]
PROFILE_DEFAULTS = {'name': "NAMELESS", 'wallet': 0, 'skins': ['shadow'], 'skin': 'shadow'}
NAMES = ["KAGE", "RYU", "HAYATE", "KENSHIN", "AKAME", "SHIRO", "TSUKI", "RAIDEN", "YORU", "KAZE", "JIN", "MUSASHI"]


def R(a, b):
    return random.uniform(a, b)


def lerp(a, b, k):
    return a + (b - a) * k


def ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


def ov(a, b):
    return a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]


def fmt_time(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec // 60 % 60, sec % 60
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


# ---------------------------------------------------------------- persistent stats
def load_stats():
    """Stats + profile (name, coin wallet, owned/equipped skins) live in one save file."""
    st = {k: 0 for _, k in STAT_ROWS}
    st.update({k: (list(v) if isinstance(v, list) else v) for k, v in PROFILE_DEFAULTS.items()})
    try:
        with open(SAVE, encoding='utf-8') as fh:
            st.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return st


def save_stats(st, path=SAVE):
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
    except OSError:
        pass


def load_settings():
    st = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as fh:
            st.update(json.load(fh))
    except (OSError, ValueError):
        pass
    kb, pad = dict(DEFAULT_KB), dict(DEFAULT_PAD)       # bindings saved as {action: key/button}
    kb.update({k: int(v) for k, v in st.get('kb', {}).items() if k in kb})
    pad.update({k: (v if v in ('LT', 'RT') else int(v)) for k, v in st.get('pad', {}).items() if k in DEFAULT_PAD})
    st['kb'], st['pad'] = kb, pad
    touch = {k: list(v) for k, v in DEFAULT_TOUCH.items()}       # on-screen control layout
    touch.update({k: [float(c) for c in v][:3] for k, v in st.get('touch', {}).items() if k in touch})
    st['touch'] = touch
    return st


# ---------------------------------------------------------------- sound
def synth(d, vol, *layers):
    """Tiny layered synth. Each layer: (wave, f0, f1, gain, decay, lowpass, start).
    wave: sin/sq/saw/noise, f0->f1 exponential pitch sweep, lowpass 0..1 (lower = darker)."""
    fr, _, ch = pg.mixer.get_init()
    n = int(fr * d)
    out = [0.0] * n
    for wave_, f0, f1, gain, decay, lpf, start in layers:
        s0, ph, lpv = int(start * fr), 0.0, 0.0
        ratio = f1 / f0
        for i in range(s0, n):
            t = (i - s0) / fr
            ph += f0 * ratio ** ((i - s0) / (n - s0)) / fr
            if wave_ == 'sin':
                v = math.sin(6.2832 * ph)
            elif wave_ == 'sq':
                v = 1.0 if ph % 1 < .5 else -1.0
            elif wave_ == 'saw':
                v = 2 * (ph % 1) - 1
            else:
                v = random.uniform(-1, 1)
            lpv += (v - lpv) * lpf
            out[i] += lpv * min(1, t * 500) * math.exp(-t * decay) * gain
    a = array('h')
    for v in out:
        a.extend([int(math.tanh(v) * vol * 32767)] * ch)
    return pg.mixer.Sound(buffer=a.tobytes())


def L_(wave_, f0, f1=None, gain=1.0, decay=8.0, lpf=1.0, start=0.0):
    return (wave_, f0, f1 or f0, gain, decay, lpf, start)


try:
    SFX = {
        'slash': synth(.15, .3, L_('noise', 1, decay=18, lpf=.35), L_('sin', 1800, 500, .25, 25)),
        'eslash': synth(.17, .25, L_('noise', 1, decay=14, lpf=.2), L_('sin', 900, 280, .25, 18)),
        'hit': synth(.18, .5, L_('sin', 170, 45, 1.2, 14), L_('noise', 1, gain=.7, decay=120, lpf=.6)),
        'kill': synth(.38, .5, L_('sin', 130, 32, 1.2, 7), L_('noise', 1, gain=.8, decay=10, lpf=.25),
                      L_('sq', 90, 40, .3, 12, .1)),
        'coin': synth(.22, .16, L_('sq', 1319, gain=.5, decay=18, lpf=.5), L_('sq', 1976, gain=.5, decay=14, lpf=.5, start=.05)),
        'myth': synth(.5, .2, *[L_('sin', f, decay=9, start=i * .05) for i, f in enumerate((1047, 1319, 1568, 2093))],
                      L_('sq', 4186, gain=.12, decay=6, lpf=.3, start=.15)),
        'hurt': synth(.3, .35, L_('sq', 260, 90, 1, 8, .3), L_('noise', 1, gain=.6, decay=15, lpf=.4)),
        'jump': synth(.12, .2, L_('sin', 220, 520, .8, 18), L_('noise', 1, gain=.3, decay=40, lpf=.15)),
        'land': synth(.09, .2, L_('sin', 120, 60, 1, 30), L_('noise', 1, gain=.4, decay=50, lpf=.2)),
        # footsteps per surface: wet street, stone roofs, metal platforms, wooden tiles
        'step_water': synth(.09, .09, L_('noise', 1, gain=.7, decay=35, lpf=.5), L_('sin', 900, 300, .15, 40)),
        'step_stone': synth(.05, .09, L_('noise', 1, gain=.6, decay=70, lpf=.3), L_('sin', 150, 90, .4, 50)),
        'step_metal': synth(.12, .07, L_('sin', 820, decay=30, gain=.5), L_('sin', 1370, decay=40, gain=.3),
                            L_('noise', 1, gain=.4, decay=90, lpf=.5)),
        'step_wood': synth(.07, .1, L_('sin', 260, 180, .7, 45), L_('noise', 1, gain=.4, decay=70, lpf=.2)),
        # Sekiro-style deflect: sharp inharmonic steel ring over a hard transient
        'parry': synth(.9, .42, L_('noise', 1, gain=1.4, decay=90, lpf=.9), L_('sin', 1240, decay=6), L_('sin', 1835, gain=.8, decay=7),
                       L_('sin', 2745, gain=.6, decay=9), L_('sin', 3910, gain=.4, decay=12), L_('sin', 420, gain=.5, decay=14)),
        'block': synth(.3, .25, L_('noise', 1, gain=.8, decay=40, lpf=.6), L_('sin', 980, decay=14), L_('sin', 1510, gain=.5, decay=16)),
        'charge': synth(.5, .2, L_('saw', 60, 240, .6, 1.5, .08), L_('sin', 300, 1200, .4, 2)),
        'super': synth(.9, .55, L_('noise', 1, gain=1, decay=5, lpf=.35), L_('sin', 1600, 120, .5, 4), L_('sin', 90, 30, 1.2, 3.5)),
        'unsheathe': synth(.35, .2, L_('noise', 1, gain=.5, decay=8, lpf=.6), L_('sin', 2400, 3600, .3, 6), L_('sin', 5200, gain=.15, decay=10)),
        'door': synth(.7, .4, L_('noise', 1, gain=.6, decay=5, lpf=.06), L_('sin', 70, 45, 1, 6), L_('noise', 1, gain=.8, decay=30, lpf=.3, start=.45)),
        'gate': synth(.8, .38, L_('saw', 120, 40, .5, 5, .2), L_('sq', 880, 220, .25, 6, .3), L_('noise', 1, gain=.7, decay=25, lpf=.4, start=.3)),
        'kiosk': synth(.5, .16, L_('sin', 1568, decay=6), L_('sin', 2093, decay=6, start=.08), L_('sin', 2637, decay=5, start=.16)),
        'buy': synth(.45, .2, *[L_('sq', f, gain=.4, decay=10, lpf=.4, start=i * .06) for i, f in enumerate((988, 1319, 1568, 1976))]),
        'deny': synth(.2, .2, L_('sq', 180, 140, .6, 10, .3)),
        'hood': synth(.35, .25, L_('noise', 1, gain=.9, decay=7, lpf=.18), L_('noise', 1, gain=.4, decay=12, lpf=.5, start=.08)),
        'glint': synth(.6, .16, L_('sin', 3520, decay=6), L_('sin', 5274, gain=.5, decay=8), L_('sin', 7040, gain=.25, decay=12)),
        'dash': synth(.24, .26, L_('noise', 1, decay=9, lpf=.5), L_('sin', 900, 200, .3, 12)),
        'ping': synth(.35, .2, L_('sin', 2100, decay=12), L_('sin', 2900, gain=.6, decay=16), L_('sin', 4200, gain=.3, decay=25)),
        'throw': synth(.09, .2, L_('noise', 1, decay=30, lpf=.5), L_('sin', 1300, 1900, .3, 30)),
        'slam': synth(.7, .55, L_('sin', 110, 28, 1.3, 4.5), L_('noise', 1, gain=.9, decay=6, lpf=.12),
                      L_('noise', 1, gain=.5, decay=40, lpf=.7)),
        'boom': synth(.5, .45, L_('noise', 1, decay=6, lpf=.18), L_('sin', 200, 40, 1, 8)),
        'pad': synth(.3, .22, L_('sin', 180, 900, 1, 6), L_('sq', 360, 1800, .25, 10, .2)),
        'crack': synth(.18, .25, L_('noise', 1, decay=25, lpf=.8), L_('noise', 1, decay=25, lpf=.3, start=.05)),
        'wipe': synth(.3, .2, L_('noise', 1, gain=.7, decay=3, lpf=.3), L_('sin', 300, 2400, .3, 4)),
        'sel': synth(.06, .15, L_('sq', 880, gain=.5, decay=40, lpf=.4), L_('sin', 1760, gain=.3, decay=50)),
    }
except Exception:
    SFX = {}


def sfx(n):
    if n in SFX:
        SFX[n].play()


# ---------------------------------------------------------------- drawing helpers
_glow, _smoke = {}, {}


def glow(surf, x, y, r, col, flat=1.0):
    key = (r, col, flat)
    g = _glow.get(key)
    if g is None:
        g = pg.Surface((r * 2, r * 2))
        for i in range(r, 0, -1):
            k = (1 - i / r) ** 2
            pg.draw.circle(g, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (r, r), i)
        if flat != 1.0:
            g = pg.transform.smoothscale(g, (r * 2, max(2, int(r * 2 * flat))))
        _glow[key] = g
    surf.blit(g, (int(x) - g.get_width() // 2, int(y) - g.get_height() // 2), special_flags=pg.BLEND_RGB_ADD)


def smoke_img(r, a, col):
    key = (r, a, col)
    img = _smoke.get(key)
    if img is None:
        img = pg.Surface((r * 2 + 2, r * 2 + 2), pg.SRCALPHA)
        pg.draw.circle(img, col + (a,), (r + 1, r + 1), r)
        pg.draw.circle(img, tuple(min(255, c + 40) for c in col) + (a,), (r + 1 - r // 3, r + 1 - r // 3), max(1, r // 2))
        _smoke[key] = img
    return img


def qcol(col, k):
    """colour scaled by k, quantised so the glow cache stays small"""
    k = round(max(0, min(1, k)) * 8) / 8
    return (int(col[0] * k), int(col[1] * k), int(col[2] * k))


def hue(h, v=1.0):
    c = pg.Color(0)
    c.hsva = (h % 360, 80, 100, 100)
    return (int(c.r * v), int(c.g * v), int(c.b * v))


def text(s, f, col, x, y, center=False, surf=None):
    surf = surf or scr
    img = f.render(s, False, col)
    if center:
        x -= img.get_width() // 2
    surf.blit(f.render(s, False, (0, 0, 0)), (x + 1, y + 1))
    surf.blit(img, (x, y))


def outlined(s, f, col, x, y, line=INK, center=False, r=2):
    img = f.render(s, False, col)
    sh = f.render(s, False, line)
    if center:
        x -= img.get_width() // 2
    for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r), (r, r)):
        scr.blit(sh, (x + dx, y + dy))
    scr.blit(img, (x, y))


def ransom(txt, x, y, fonts, seed, t, center=False, tilt=-5.0):
    """Persona-style ransom-note lettering: every letter on its own tilted card."""
    rnd = random.Random(seed)
    styles = [(WHITE, INK), (INK, WHITE), (WHITE, RED), (INK, WHITE), (WHITE, INK)]
    pieces = []
    for i, ch in enumerate(txt):
        if ch == ' ':
            pieces.append(None)
            continue
        fg, bg = styles[rnd.randrange(len(styles))]
        f = fonts[rnd.randrange(len(fonts))]
        g = f.render(ch, False, fg)
        box = pg.Surface((g.get_width() + 6, g.get_height() + 2), pg.SRCALPHA)
        box.fill(bg + (255,))
        box.blit(g, (3, 1))
        ang = tilt + rnd.uniform(-11, 11) + math.sin(t * 2.3 + i * 1.9) * 2.5
        pieces.append((pg.transform.rotate(box, ang), rnd.uniform(-4, 4)))
    total = sum(p[0].get_width() - 4 if p else 9 for p in pieces)
    cx = x - total // 2 if center else x
    for p in pieces:
        if p is None:
            cx += 9
            continue
        img, jy = p
        scr.blit(img, (cx, y + jy - img.get_height() // 2))
        cx += img.get_width() - 4


def star(cx, cy, r, a, col):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * .42
        aa = a + i * math.pi / 5
        pts.append((cx + math.cos(aa) * rr, cy + math.sin(aa) * rr))
    pg.draw.polygon(scr, col, pts)


def arc(col, cx, cy, r, center, spread, w):
    pg.draw.arc(scr, col, (cx - r, cy - r, r * 2, r * 2), center - spread, center + spread, w)


def sil_poly(D, pts, dark, rim):
    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
        pg.draw.polygon(D, rim, [(x + dx, y + dy) for x, y in pts])
    pg.draw.polygon(D, dark, pts)


def rot(pts, cx, cy, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def wrap(txt, f, w):
    out, cur = [], ''
    for wd in txt.split():
        t = (cur + ' ' + wd).strip()
        if f.size(t)[0] > w:
            out.append(cur)
            cur = wd
        else:
            cur = t
    return out + [cur]


def vgrad_rect(surf, r, top, bottom):
    for y in range(r.height):
        k = y / max(1, r.height - 1)
        surf.fill([int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)], (r.x, r.y + y, r.width, 1))


def vgrad(surf, stops):
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        for y in range(y0, y1):
            k = (y - y0) / max(1, y1 - y0)
            surf.fill([int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3)], (0, y, surf.get_width(), 1))


def layer_w(f):
    return int((LW - W) * f) + W + 20


# ---------------------------------------------------------------- poses
# Limb angles are measured from "straight down", positive = towards the facing direction.
# The sword angle is in world terms: 0 = forward, +pi/2 = down, -pi/2 = up.
def P_(lean, legs, arms, sword, **kw):
    d = dict(lean=lean, legs=legs, arms=arms, sword=sword, coat=0.0)
    d.update(kw)
    return d


def blend(A, B, k):
    """Smoothly move pose A towards pose B (gives every move its transition frames)."""
    out = {}
    for key, b in B.items():
        a = A.get(key, b)
        if key in ('legs', 'arms'):
            out[key] = [(lerp(a[i][0], b[i][0], k), lerp(a[i][1], b[i][1], k)) for i in (0, 1)]
        else:
            out[key] = lerp(a, b, k)
    return out


def pose_idle(t):
    b = math.sin(t * 2.5)
    return P_(.06 + b * .02, [(.2, .04), (-.16, -.04)], [(.14 + b * .05, .45), (.3, 1.0 + b * .05)], 1.0 + b * .04, coat=b * .6)


def pose_run(ph, amp=1.0):
    """Katana Zero style sprint: deep forward lean, long strides, heels kicking high, blade trailing behind."""
    legs = []
    for i in (0, 1):
        a = ph + i * math.pi
        th = math.sin(a) * 1.15 * amp
        kick = max(0, -math.cos(a))
        legs.append((th, th - (.2 + 1.9 * kick) * amp))
    sw = math.sin(ph)
    arms = [(-.9 * amp - .35 * sw * amp, -.35), (-1.25 * amp + .1 * sw, -.8 * amp)]
    return P_(.62 * amp + .04 - abs(sw) * .05, legs, arms, 2.95, coat=4.5 * amp + math.sin(ph * 2) * 1.5)


def pose_jog(ph, amp=1.0):
    legs, arms = [], []
    for i in (0, 1):
        a = ph + i * math.pi
        th = math.sin(a) * .95 * amp
        legs.append((th, th - (.25 + 1.2 * max(0, -math.cos(a))) * amp))
        u = -math.sin(a) * .9 * amp
        arms.append((u, u + .9))
    return P_(.32 * amp + .04, legs, arms, 2.6, coat=math.sin(ph * 2) * 1.5 + 3 * amp)


def pose_jump(vy):
    if vy < 0:
        return P_(.12, [(1.0, -.2), (-.2, -1.0)], [(-.9, -.3), (.7, 1.4)], 2.2, coat=-2)
    return P_(.05, [(.45, .25), (-.35, -1.0)], [(-2.1, -1.7), (-1.3, -.7)], 1.6, coat=3)


POSE_CROUCH = P_(.5, [(1.35, -.9), (.55, -1.6)], [(.7, 1.4), (1.0, 1.7)], .25, coat=1)
POSE_SLIDE = P_(-.75, [(1.55, 1.55), (.45, -1.1)], [(-1.3, -.9), (-2.1, -1.7)], 3.0, coat=5)
POSE_DASH = P_(1.0, [(-1.0, -1.7), (.55, -.4)], [(-1.7, -1.4), (-1.5, -1.2)], 3.1, coat=7)
POSE_SLAM = P_(.15, [(1.3, -.5), (.9, -1.3)], [(.6, .3), (.4, .2)], math.pi / 2, coat=-3)
POSE_HURT = P_(-.5, [(.4, .3), (-.4, -.6)], [(-2.3, -2.8), (-1.9, -2.4)], -1.0, coat=2)
POSE_SKID = P_(-.35, [(.95, .6), (-.5, -.3)], [(-.6, -.2), (.9, 1.3)], 1.2, coat=-3)
POSE_START = P_(.65, [(-.7, -1.3), (.75, -.3)], [(.9, 1.3), (-1.0, -.4)], 2.6, coat=4)
POSE_TURN = P_(-.2, [(.5, .1), (-.3, -.6)], [(-.4, 0), (.4, .9)], 1.6, coat=-4)
POSE_PARRY = P_(-.12, [(.55, .1), (-.45, -.35)], [(.9, 1.7), (1.2, 2.1)], -1.15, coat=-2, hot=.35)
POSE_INSPECT = P_(.05, [(.2, .04), (-.16, -.04)], [(1.0, 2.2), (1.25, 2.35)], -.05, hot=.25, hood=0.0)
POSE_FACEGUARD = P_(.02, [(.22, .05), (-.18, -.05)], [(.4, 1.6), (1.9, 3.0)], -1.6, hot=.2)   # blade up before the face
# portrait like the reference: turned a little toward the camera, blade held up beside the face
POSE_PORTRAIT = P_(.0, [(.25, .05), (-.25, -.05)], [(.35, .9), (2.05, 2.85)], -1.5, hot=.2, front=1.0)
IDLE_ANIMS = {'inspect': 2.6, 'wipe': 2.6, 'look': 2.8, 'sit': 4.5, 'hood': 1.8}   # name: duration (s)


def pose_idle_anim(name, k, t):
    """Little things the samurai does when you leave him standing for a while."""
    b = math.sin(t * 2.5)
    if name == 'inspect':                                   # holds the blade up and looks along it
        return dict(POSE_INSPECT, hood=1.0, sword=-.05 + math.sin(t * 1.5) * .06)
    if name == 'wipe':                                      # runs his hand along the blade
        s_ = math.sin(k * math.pi * 3)
        return P_(.08, [(.2, .04), (-.16, -.04)], [(1.0 + .45 * s_, 2.0 + .3 * s_), (1.0, 2.2)], -.02, hot=.25)
    if name == 'look':                                      # shades his eyes and scans the rooftops
        return P_(.04 + b * .02, [(.25, .05), (-.2, -.05)], [(.2, .5), (1.7, 3.3)], 1.0)
    if name == 'sit':                                       # sits down on his heels to rest
        e = ease(min(1, k * 5)) * ease(min(1, (1 - k) * 5))
        return P_(lerp(.06, .3, e) + b * .02, [(lerp(.2, 1.55, e), lerp(.04, -.3, e)), (lerp(-.16, 1.4, e), lerp(-.04, -.5, e))],
                  [(lerp(.14, .7, e), lerp(.45, 1.5, e)), (lerp(.3, .8, e), lerp(1.0, 1.6, e))], 1.0)
    return dict(POSE_HOODUP, hood=1.0)                      # tugs his hood down
POSE_HOODUP = P_(-.05, [(.2, .04), (-.16, -.04)], [(-2.3, -3.0), (-2.6, -3.15)], .9, hood=0.0)   # reaching back for the hood
POSE_SHOW = P_(0.0, [(.25, .05), (-.22, -.05)], [(.3, .6), (.9, 1.9)], -.9, hot=.2)


def swing(k):
    """Attack timing curve: short anticipation (pull back), fast cut, then a settling follow-through."""
    if k < .18:
        return -.12 * ease(k / .18)
    if k < .55:
        return -.12 + 1.12 * ease((k - .18) / .37)
    return 1 + .04 * math.sin((k - .55) / .45 * math.pi)


def pose_super(k):
    """Super: haul the blade up over the shoulder from the back, then one huge forward cut."""
    if k < .4:
        e = ease(k / .4)
        return P_(lerp(.05, -.25, e), [(.6, .1), (-.6, -.4)], [(-.6, -.2), (lerp(.3, -3.0, e), lerp(.9, -3.3, e))],
                  lerp(2.9, -2.2, e), coat=-2, hot=1)
    e = ease(min(1, (k - .4) / .15))
    return P_(lerp(-.25, .55, e), [(-.9, -1.3), (1.0, .4)], [(-1.2, -.8), (lerp(-3.0, 1.6, e), lerp(-3.3, 1.5, e))],
              lerp(-2.2, .9, e), coat=6, hot=1)


def with_attack(P, d, k, step=1):
    e = swing(k) if step != 3 else ease(k)
    P = dict(P)
    if d == 'up':
        P['arms'] = [(.3, .6), (lerp(1.2, -2.9, e), lerp(1.4, -3.0, e))]
        P['sword'] = lerp(.7, -2.6, e)
        P['lean'] -= .1
    elif d == 'down':
        P['arms'] = [(-1.0, -.6), (lerp(-2.4, .5, e), lerp(-2.2, .9, e))]
        P['sword'] = lerp(-1.3, 2.3, e)
        P['lean'] += .2
    elif step == 2:                     # reverse rising slash
        P['arms'] = [(-.4, 0), (lerp(1.5, -2.1, e), lerp(1.7, -2.4, e))]
        P['sword'] = lerp(1.1, -1.6, e)
        P['lean'] += .2
    elif step == 3:                     # finisher: a small draw back, then a light thrust
        if k < .3:
            w = ease(k / .3)
            P['arms'] = [(-.4, 0), (lerp(.4, -.7, w), lerp(.8, -.2, w))]
            P['sword'] = lerp(.2, -.2, w)
            P['lean'] -= .1 * w
        else:
            w = ease((k - .3) / .25)
            P['arms'] = [(-.4 - .5 * w, -.4 * w), (lerp(-.7, 1.55, w), lerp(-.2, 1.5, w))]
            P['sword'] = lerp(-.2, 0.0, w)
            P['lean'] += .32 * w
            P['legs'] = [(lerp(P['legs'][0][0], -.6, w), lerp(P['legs'][0][1], -.9, w)),
                         (lerp(P['legs'][1][0], .6, w), lerp(P['legs'][1][1], .3, w))]
    else:                               # step 1: big downward cut
        P['arms'] = [(-.5, -.1), (lerp(-2.5, 1.55, e), lerp(-2.8, 1.45, e))]
        P['sword'] = lerp(-2.0, .85, e)
        P['lean'] += .25
    P['hot'] = 1 - k
    return P


def pose_activity(e, t):
    """Enemy routines before they spot you: walking, standing guard, tea, phone, smoking, chatting, dozing, meditating."""
    a, k, b = e.act, e.actT, math.sin(t * 2 + e.anim)
    stand = [(.2, .04), (-.16, -.04)]
    sit = [(1.55, -.3), (1.4, -.5)]
    if a == 'walk':
        return dict(pose_jog(e.anim, min(1, abs(e.vx) / 90) * .7), nowep=1.0, sword=.9)
    if a in ('tea', 'smoke'):                               # cup / cigarette to the mouth every few seconds
        sip = (k % 3.5) < 1.0
        return P_(.05 + b * .02, stand, [(.3, .8), (1.9, 3.15) if sip else (.9, 1.9)], .9, nowep=1.0)
    if a == 'phone':                                        # hand at the ear, shifting weight
        return P_(.04 + b * .03, stand, [(.25 + b * .1, .6), (2.1, 3.4)], .9, nowep=1.0)
    if a == 'talk':                                         # gesturing while talking
        g = math.sin(t * 3 + e.anim)
        return P_(.06, stand, [(.2, .5), (.9 + .5 * g, 1.8 + .6 * math.sin(t * 4 + e.anim))], .9, nowep=1.0)
    if a == 'sleep':                                        # sitting, head down, breathing slowly
        return P_(.45 + math.sin(t * 1.2 + e.anim) * .04, sit, [(.6, 1.3), (.7, 1.4)], .9, nowep=1.0)
    if a == 'meditate':
        return P_(.02 + b * .01, sit, [(.5, 1.8), (.5, 1.8)], .9, nowep=1.0)
    return P_(.04 + b * .02, stand, [(.5, 2.4), (.6, 2.5)], .9, nowep=1.0)   # 'guard': arms folded


def pose_enemy(e, t):
    if e.trav == 'climb':                                 # hand over hand up the back of the building
        a = e.anim
        return P_(-.05, [(.8 + .4 * math.sin(a), -.7), (.3 - .4 * math.sin(a), -1.1)],
                  [(-2.9 + .35 * math.sin(a), -3.0), (-2.6 - .35 * math.sin(a), -2.9)], 1.4)
    if e.trav == 'grab':                                    # hanging from the roof edge
        sw = math.sin(t * 5) * .06
        return P_(sw, [(.12 + sw, .05), (-.1 + sw, .12)], [(-3.0, -3.1), (-2.95, -3.05)], 1.5)
    if e.trav == 'pull':                                    # hauling up over the edge
        return P_(.35, [(1.3, -1.0), (1.0, -1.5)], [(-1.0, .6), (-.8, .8)], 1.5)
    if e.trav == 'drop':
        return pose_jump(e.vy)
    if e.hurt > 0:
        return P_(-.5, [(.4, .2), (-.3, -.5)], [(-1.5, -1.0), (-2.2, -1.8)], -1.0)
    if e.st == 'stun':                                      # staggered, guard broken
        sw = math.sin(t * 7) * .12
        return P_(-.45 + sw, [(.5, .3), (-.5, -.4)], [(-1.9, -1.4), (-1.2 + sw, -.4)], 2.3)
    if e.st == 'notice':                                    # startled: "?!" and a step back, weapon not out yet
        return P_(-.3, [(.45, .1), (-.45, -.5)], [(-1.0, -.6), (-1.3, -.9)], .6, nowep=1.0)
    if e.st == 'calm':                                      # off duty: what they do before they see you
        return pose_activity(e, t)
    if e.st == 'wind':
        k = 1 - max(0.0, e.t) / e.wind
        if e.kind == 'ninja':
            return P_(-.1, [(.5, 0), (-.4, -.3)], [(.3, .6), (-2.2 - .4 * k, -1.8)], 0)
        shake = math.sin(t * 60) * .05 * k
        return P_(-.2 * k, [(.5, .1), (-.35, -.4)], [(-.5, -.2), (-2.2 - .6 * k + shake, -2.6 - .4 * k)], -2.2 - .5 * k + shake)
    if e.st == 'slash':
        return P_(.45, [(-.7, -.9), (.9, .4)], [(-.4, 0), (1.4, 1.5)], .6)
    if e.throwT > 0:
        return P_(.3, [(.4, 0), (-.3, -.4)], [(-.6, -.2), (1.6, 1.6)], 0)
    if abs(e.vx) > 5 and e.g:
        P = pose_jog(e.anim, min(1, abs(e.vx) / 90))
        P['sword'] = .9
        return P
    P = pose_idle(t + e.anim)
    P['sword'] = .6
    return P


# ---------------------------------------------------------------- pixel-art character painter
def rope(D, ch, anchor, f, seg, col, widths, t, org, sag=.6):
    """A trailing rope (scarf / hair) simulated in world space so it lags behind movement."""
    ch[0] = [anchor[0] + org[0], anchor[1] + org[1]]
    for i in range(1, len(ch)):
        px, py = ch[i - 1]
        c = ch[i]
        c[0] += (px - f * seg - c[0]) * .35
        c[1] += (py + sag + math.sin(t * 9 + i) * .7 - c[1]) * .35
        ddx, ddy = c[0] - px, c[1] - py
        d = math.hypot(ddx, ddy) or 1
        if d > seg:
            c[0], c[1] = px + ddx / d * seg, py + ddy / d * seg
    pts = [(c[0] - org[0], c[1] - org[1]) for c in ch]
    for i in range(len(pts) - 1):
        pg.draw.line(D, col, pts[i], pts[i + 1], widths[min(i, len(widths) - 1)])


def paint(D, ax, ay, f, P, S, t, chains, org):
    """Paint a character (feet at ax, ay) into sprite surface D. Returns eye/blade info."""
    if S.get('hooded') and P.get('hood', 1) < .5 and not P.get('front'):   # hood down: the original samurai look
        S = dict(S, hooded=False, hair=S['hair_down'])
    sc = S['sc']
    th = sh = 6 * sc
    to, ua, fa = 8.5 * sc, 5 * sc, 5 * sc
    lw = max(2, int(3 * sc))
    legs, arms = P['legs'], P['arms']
    hip = (ax, ay - max(th * math.cos(a) + sh * math.cos(b) for a, b in legs))
    dx, dy = f * math.sin(P['lean']), -math.cos(P['lean'])
    nx, ny = -dy, dx
    neck = (hip[0] + dx * to, hip[1] + dy * to)
    sho = (hip[0] + dx * to * .82, hip[1] + dy * to * .82)
    hr = {'hood': 5.5, 'hat': 4.2, 'oni': 4.8, 'mask': 4.4, 'samurai': 4.6}[S['head']] * sc
    hc = (neck[0] + dx * hr * .75, neck[1] + dy * hr * .75)
    arm, arm_d = S.get('arm', S['coat']), S.get('arm_d', S['coat_d'])
    sam = S['head'] == 'samurai'
    lwl = lw + 1 if S.get('hakama') else lw                         # wide hakama legs / kimono sleeves

    def lim(base, a1, l1, a2, l2):
        k = (base[0] + f * math.sin(a1) * l1, base[1] + math.cos(a1) * l1)
        return k, (k[0] + f * math.sin(a2) * l2, k[1] + math.cos(a2) * l2)

    def cap(a, b, w, col):
        pg.draw.line(D, col, a, b, w)
        pg.draw.circle(D, col, a, w / 2)
        pg.draw.circle(D, col, b, w / 2)

    if chains:
        if 'hair' in chains and sam and S.get('hooded'):            # long hair flowing out of the hood
            rope(D, chains['hair'], (hc[0] - f * hr * .7, hc[1] + 1.5), f, 2.8 * sc, S['hair'], (3, 3, 2, 2, 1), t, org, 2.6)
        elif 'hair' in chains and sam:                              # ponytail from the topknot
            rope(D, chains['hair'], (hc[0] - f * 2 * sc, hc[1] - hr), f, 2.6 * sc, S['hair'], (3, 3, 2, 2, 1), t, org, 2.2)
        elif 'hair' in chains:
            rope(D, chains['hair'], (hc[0] - f * 3 * sc, hc[1] - 1), f, 2.6 * sc, S['hair'], (3, 2, 2, 1), t, org, .9)
        if 'scarf' in chains:                                       # samurai: headband tails / others: scarf
            anchor = (hc[0] - f * hr * .85, hc[1] - 1.5) if sam else neck
            rope(D, chains['scarf'], anchor, f, 3 * sc, S['scarf'], (2, 2, 1, 1, 1) if sam else (3, 3, 2, 2, 1), t, org,
                 2.4 if sam else .6)
        if 'band' in chains:
            rope(D, chains['band'], (hc[0] - f * hr, hc[1] - 2.5), f, 2.4 * sc, S['belt'], (1,), t, org, .3)

    sheathed = S.get('sheath') and P.get('hot', 0) <= 0
    if sheathed:                                                    # katana sheathed across the back
        fx_, fy_ = nx * f, ny * f                                   # towards the chest
        base = (neck[0] - fx_ * 3 * sc + dx * 2 * sc, neck[1] - fy_ * 3 * sc + dy * 2 * sc)
        hilt = (base[0] - fx_ * 3 * sc + dx * 6 * sc, base[1] - fy_ * 3 * sc + dy * 6 * sc)   # pokes up behind the hood
        tip = (hip[0] - fx_ * 11 * sc - dx * 5 * sc, hip[1] - fy_ * 11 * sc - dy * 5 * sc)     # sticks out behind the hip
        pg.draw.line(D, (40, 18, 30), base, tip, 3)
        pg.draw.line(D, (120, 64, 86), base, tip, 1)
        pg.draw.line(D, S['hilt'], base, hilt, 3)
        D.fill((220, 182, 82), (base[0], base[1], 1, 1))
    k, e = lim(sho, arms[0][0], ua, arms[0][1], fa)                 # back arm
    cap(sho, k, lwl, arm_d)
    cap(k, e, lw, arm_d)
    pg.draw.circle(D, S['glove_d'], e, lw / 2 + .6)
    k, e = lim(hip, legs[0][0], th, legs[0][1], sh)                 # back leg
    cap(hip, k, lwl, S['pants_d'])
    cap(k, e, lwl, S['pants_d'])
    cap((lerp(k[0], e[0], .5), lerp(k[1], e[1], .5)), e, lw, S['boot_d'])
    cap(e, (e[0] + f * 2.5 * sc, e[1]), lw, S['boot_d'])
    wh, ws = 2.8 * sc, 3.6 * sc
    front = P.get('front', 0) > .5                                  # turned a little toward the camera (portraits)
    if front:
        wh, ws = wh * 1.3, ws * 1.35
    if S['skirt']:                                                # coat tail sways with motion
        cw = P.get('coat', 0)
        a, b = (hip[0] + nx * wh, hip[1] + ny * wh), (hip[0] - nx * wh, hip[1] - ny * wh)
        if S.get('hakama'):                                         # long pleated hakama flaring with motion
            back, front = (hip[0] - f * (5 + cw * 1.1) * sc, hip[1] + 9 * sc), (hip[0] + f * 4 * sc, hip[1] + 8.5 * sc)
            pg.draw.polygon(D, S['pants_d'], [a, b, back, front] if f > 0 else [a, b, front, back])
            for kk in (.3, .65):
                pg.draw.line(D, S['pants'], hip, (lerp(back[0], front[0], kk), lerp(back[1], front[1], kk)))
        else:
            back, front = (hip[0] - f * (4 + cw) * sc, hip[1] + 7 * sc), (hip[0] + f * 3 * sc, hip[1] + 6.5 * sc)
            pg.draw.polygon(D, S['coat_d'], [a, b, back, front] if f > 0 else [a, b, front, back])
            pg.draw.line(D, S['coat'], hip, ((back[0] + front[0]) / 2, (back[1] + front[1]) / 2))
    torso = [(hip[0] + nx * wh, hip[1] + ny * wh), (neck[0] + nx * ws, neck[1] + ny * ws),
             (neck[0] - nx * ws, neck[1] - ny * ws), (hip[0] - nx * wh, hip[1] - ny * wh)]
    pg.draw.polygon(D, S['coat'], torso)
    pg.draw.line(D, S['coat_l'], (hip[0] + nx * f * wh * .7, hip[1] + ny * f * wh * .7),
                 (neck[0] + nx * f * ws * .7, neck[1] + ny * f * ws * .7))
    pg.draw.line(D, S['belt'], (hip[0] + nx * wh, hip[1] + ny * wh - 1), (hip[0] - nx * wh, hip[1] - ny * wh - 1), 2)
    if sam:                                                         # kimono collar (crossed lapels)
        pg.draw.line(D, S['coat_l'], neck, (lerp(neck[0], hip[0], .55) + nx * f * 1.5, lerp(neck[1], hip[1], .55) + ny * f * 1.5))
    k, e = lim(hip, legs[1][0], th, legs[1][1], sh)                 # front leg
    cap(hip, k, lwl, S['pants'])
    cap(k, e, lwl, S['pants'])
    cap((lerp(k[0], e[0], .5), lerp(k[1], e[1], .5)), e, lw, S['boot'])
    cap(e, (e[0] + f * 2.5 * sc, e[1]), lw, S['boot'])
    D.fill(S['coat_l'], (k[0], k[1] - 1, 1, 1))

    head = S['head']
    if head == 'samurai' and S.get('hooded') and front:             # 3/4 front view: both eyes, centred mask
        pg.draw.circle(D, S['hood'], (hc[0] - f * .3, hc[1] - .6), hr + 1.4)
        pg.draw.polygon(D, S['hood'], [(hc[0] - f * 2, hc[1] - hr), (hc[0] - f * (hr + 3), hc[1] + 1), (hc[0] - f * 2.5, hc[1] + 3)])
        a0, a1 = (0.4, 2.6) if f > 0 else (.55, 2.75)
        pg.draw.arc(D, S['hood_l'], (hc[0] - f * .3 - hr - 1.4, hc[1] - .6 - hr - 1.4, (hr + 1.4) * 2, (hr + 1.4) * 2), a0, a1, 1)
        fc = (hc[0] + f * .8, hc[1] + .8)
        pg.draw.circle(D, S['skin'], fc, hr - 1.5)
        pg.draw.polygon(D, S['mask'], [(fc[0] - 3, fc[1] + .2), (fc[0] + 3, fc[1] + .2), (fc[0] + 2.4, fc[1] + 3), (fc[0] - 2.4, fc[1] + 3)])
        D.fill((220, 220, 230), (fc[0] - .5, fc[1] + 1.4, 1, 1))
        pg.draw.line(D, S['hair'], (fc[0] - 3, fc[1] - 3.2), (fc[0] + 3, fc[1] - 2.6), 2)                     # fringe
        for sg in (-1, 1):
            pg.draw.line(D, S['hair'], (fc[0] + sg * 3.2, fc[1] - 2.4), (fc[0] + sg * 3.8, fc[1] + 2.5), 1)   # side locks
            D.fill(S['eye'], (fc[0] + sg * 1.5 - .5, fc[1] - 1.1, 1, 1))
        eye = (fc[0] + f * 1.5, fc[1] - 1.1)
    elif head == 'samurai' and S.get('hooded') and P.get('hood', 1) >= .5:   # hood up, face mask, hair spilling out
        pg.draw.circle(D, S['hood'], (hc[0] - f * .8, hc[1] - .6), hr + 1.3)
        tip = (hc[0] - f * (hr + 4 + P.get('coat', 0) * .35) * sc, hc[1] - 1 + math.sin(t * 6) * .6)
        pg.draw.polygon(D, S['hood'], [(hc[0] - f * 1, hc[1] - hr), tip, (hc[0] - f * 2, hc[1] + 2.5)])
        a0, a1 = (0.2, 1.6) if f > 0 else (1.55, 2.95)
        pg.draw.arc(D, S['hood_l'], (hc[0] - f * .8 - hr - 1.3, hc[1] - .6 - hr - 1.3, (hr + 1.3) * 2, (hr + 1.3) * 2), a0, a1, 1)
        pg.draw.circle(D, S['skin'], (hc[0] + f * 1.4, hc[1] + .9), hr - 1.9)
        pg.draw.polygon(D, S['mask'], [(hc[0] - f * .3, hc[1] + 1.2), (hc[0] + f * (hr - .2), hc[1] + .9),
                                        (hc[0] + f * (hr - 1.2), hc[1] + 3.6), (hc[0] + f * .6, hc[1] + 3.8)])
        D.fill((220, 220, 230), (hc[0] + f * 2.6 - .5, hc[1] + 2, 1, 1))                   # mask teeth
        pg.draw.line(D, S['hair'], (hc[0] + f * .2, hc[1] - hr + 1.6), (hc[0] + f * (hr - .3), hc[1] - .4), 2)   # fringe
        pg.draw.line(D, S['hair'], (hc[0] + f * (hr - .8), hc[1] - 1.2), (hc[0] + f * (hr + .3), hc[1] + 3), 1)  # side lock
        D.fill(S['eye'], (hc[0] + f * 2.5 - .5, hc[1] - .2, 1, 1))
        eye = (hc[0] + f * 2.5, hc[1] - .2)
    elif head == 'samurai':                                         # hood down: hair cap + topknot, face, headband
        pg.draw.circle(D, S['hair'], (hc[0] - f * 1.2, hc[1] - 1), hr)
        pg.draw.circle(D, S['skin'], (hc[0] + f * .9, hc[1] + .7), hr - 1.2)
        for sx_, sy_ in ((-2.5, -1), (-.5, -1.6), (1.5, -1)):                                                 # spiky hair
            bx_, by_ = hc[0] + f * sx_, hc[1] - hr + 1.5
            pg.draw.polygon(D, S['hair'], [(bx_ - 1.5, by_), (bx_ + 1.5, by_), (bx_ - f * 1.5, by_ - 2.6 + sy_)])
        pg.draw.circle(D, S['hair'], (hc[0] - f * 2.2, hc[1] - hr - .3), 1.8 * sc)                           # topknot
        pg.draw.line(D, S['belt'], (hc[0] - f * (hr - .5), hc[1] - 1.8), (hc[0] + f * (hr - 1), hc[1] - 1.4), 2)  # headband
        D.fill(S['eye'], (hc[0] + f * 2.4 - .5, hc[1] + .3, 1, 1))
        D.fill((30, 20, 30), (hc[0] + f * 2.4 - .5, hc[1] + 1.3, 1, 1))
        eye = (hc[0] + f * 2.4, hc[1] + .3)
    elif head == 'hood':                                            # the entity: deep hood, void face, glowing eyes
        pg.draw.circle(D, S['hood'], hc, hr)
        tip = (hc[0] - f * (hr + 4 + P.get('coat', 0) * .4) * sc, hc[1] - 1 + math.sin(t * 6) * .6)
        pg.draw.polygon(D, S['hood'], [(hc[0] - f * 2 * sc, hc[1] - hr + 1), tip, (hc[0] - f * sc, hc[1] + 2)])
        a0, a1 = (0.1, 1.7) if f > 0 else (1.45, 3.05)
        pg.draw.arc(D, S['hood_l'], (hc[0] - hr, hc[1] - hr, hr * 2, hr * 2), a0, a1, 1)
        fx = hc[0] + f * 1.8 * sc
        pg.draw.ellipse(D, (6, 4, 12), (fx - 3 * sc, hc[1] - 2.2 * sc, 6 * sc, 5.5 * sc))
        D.fill(S['eye'], (fx + f * .4 - .5, hc[1] - .5, 1, 2))
        D.fill(S['eye'], (fx + f * 2.3 - .5, hc[1] - .5, 1, 2))
        eye = (fx + f * 1.4, hc[1])
    elif head == 'hat':
        pg.draw.circle(D, S['skin'], hc, hr)
        D.fill(S['eye'], (hc[0] + f * 2 - .5, hc[1] + .5, 2, 1))
        brim = hc[1] - 1.5 * sc
        pts = [(hc[0] - 11 * sc, brim + 1.5), (hc[0] - 2 * sc, brim - 6 * sc), (hc[0] + 2 * sc, brim - 6 * sc), (hc[0] + 11 * sc, brim + 1.5)]
        pg.draw.polygon(D, S['straw'], pts)
        for kx in (-6, -2.5, 1, 4.5):
            pg.draw.line(D, S['straw_d'], (hc[0] + kx * .35 * sc, brim - 5.5 * sc), (hc[0] + kx * sc, brim + 1))
        pg.draw.line(D, S['straw_d'], pts[0], pts[3])
        pg.draw.line(D, (44, 26, 26), (hc[0] - hr + 1, brim + 2), (hc[0] + hr - 1, brim + 2))
        eye = (hc[0] + f * 2.5, hc[1] + 1)
    elif head == 'oni':                                             # armoured enforcer: kabuto helmet + red oni menpo
        pg.draw.circle(D, S['skin'], (hc[0] + f * .5, hc[1] + .5), hr - .6)
        pg.draw.polygon(D, S['coat'], [(hc[0] - hr - 1, hc[1] + 1), (hc[0] - hr + 1, hc[1] - hr + .5), (hc[0], hc[1] - hr - 1.5),
                                       (hc[0] + hr - 1, hc[1] - hr + .5), (hc[0] + hr + 1, hc[1] - 1), (hc[0] - f * (hr + 2), hc[1] + 3)])
        pg.draw.line(D, S['coat_l'], (hc[0] - hr + 1, hc[1] - hr + 1), (hc[0] + hr - 1, hc[1] - hr + 1))
        for sg in (-1, 1):                                          # small gilded crest horns
            pg.draw.line(D, (190, 160, 80), (hc[0] + sg * 1.5, hc[1] - hr - 1), (hc[0] + sg * 3.5 * sc, hc[1] - hr - 4.5 * sc), 1)
        pg.draw.polygon(D, S['mask'], [(hc[0] - f * .5, hc[1] + .6), (hc[0] + f * (hr + .4), hc[1] + .2),
                                       (hc[0] + f * (hr - .5), hc[1] + 3.6), (hc[0] + f * .8, hc[1] + 4.2)])
        D.fill((225, 220, 205), (hc[0] + f * 2.2 - 1, hc[1] + 2.6, 3, 1))
        D.fill(S['eye'], (hc[0] + f * 2.6 - .5, hc[1] - .6, 1, 1))
        eye = (hc[0] + f * 2.6, hc[1] - .6)
    else:                                                           # shinobi mask
        pg.draw.circle(D, S['coat'], hc, hr)
        pg.draw.line(D, S['coat_l'], (hc[0] - hr + 1, hc[1] + 1.5), (hc[0] + hr - 1, hc[1] + 1.5), 2)
        pg.draw.line(D, S['belt'], (hc[0] - hr, hc[1] - 2.5), (hc[0] + hr, hc[1] - 2.5))
        D.fill(S['eye'], (hc[0] + f * 1.5 - .5, hc[1] - 1, 3, 1))
        eye = (hc[0] + f * 2.5, hc[1] - 1)

    k, e = lim(sho, arms[1][0], ua, arms[1][1], fa)                 # front arm + weapon
    cap(sho, k, lwl, arm)
    cap(k, e, lw, arm)
    pg.draw.circle(D, S['glove'], e, lw / 2 + .6)
    blade = tip = None
    sa = P['sword']
    vx, vy = f * math.cos(sa), math.sin(sa)
    px, py = -vy, vx
    nowep = P.get('nowep', 0) > .5                                  # off duty: weapon put away
    if S['weapon'] == 'katana' and not sheathed and not nowep:
        L = S['blade']
        tip = (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, S['hilt'], (e[0] - vx * 4, e[1] - vy * 4), e, 2)
        pg.draw.line(D, (220, 182, 82), (e[0] + px * 1.6, e[1] + py * 1.6), (e[0] - px * 1.6, e[1] - py * 1.6))
        pg.draw.line(D, (168, 178, 198), e, tip, 2)
        pg.draw.line(D, (246, 250, 255), (e[0] + px * .6, e[1] + py * .6), (tip[0] + px * .6, tip[1] + py * .6))
        blade = ((e[0] + tip[0]) / 2, (e[1] + tip[1]) / 2)
    elif S['weapon'] == 'club' and not nowep:
        L = S['blade']
        mid, end = (e[0] + vx * 5, e[1] + vy * 5), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (52, 36, 30), (e[0] - vx * 3, e[1] - vy * 3), mid, 2)
        pg.draw.line(D, (74, 54, 46), mid, end, 5)
        for kk in range(8, int(L), 4):
            for sg in (-1, 1):
                D.fill((200, 200, 212), (e[0] + vx * kk + px * 2 * sg, e[1] + vy * kk + py * 2 * sg, 1, 1))
        blade = ((e[0] + end[0]) / 2, (e[1] + end[1]) / 2)
    return {'eye': eye, 'blade': blade, 'hand': e, 'hc': hc,
            'tip': tip if S['weapon'] == 'katana' and not sheathed and not nowep else None}


# ---------------------------------------------------------------- small shapes
def four_star(T, x, y, r, col):
    pg.draw.polygon(T, col, [(x, y - r), (x + r * .22, y - r * .22), (x + r, y), (x + r * .22, y + r * .22),
                             (x, y + r), (x - r * .22, y + r * .22), (x - r, y), (x - r * .22, y - r * .22)])


# ---------------------------------------------------------------- baked backgrounds
def windows(surf, x, top, w, bottom, step, chance, cols, dim=2):
    for wy in range(top + 5, bottom - 4, step):
        for wx in range(x + 3, x + w - 4, step - 1):
            if random.random() < chance:
                c = random.choice(cols)
                surf.fill([v // dim for v in c], (wx, wy, 2, 2))


def bake():
    L = {}
    sky = pg.Surface((W, H))
    vgrad(sky, [(0, (5, 3, 20)), (100, (34, 12, 66)), (GY, (210, 70, 130)), (H, (210, 70, 130))])
    for _ in range(70):
        sky.set_at((random.randint(0, W - 1), random.randint(0, 90)), (90, 80, 140))
    mx, my = int(W * .74), 62
    glow(sky, mx, my, 95, (70, 30, 75))
    pg.draw.circle(sky, (250, 228, 240), (mx, my), 24)
    for _ in range(5):
        pg.draw.circle(sky, (225, 200, 220), (mx + random.randint(-14, 14), my + random.randint(-14, 14)), random.randint(2, 5))
    L['sky'] = sky

    far = pg.Surface((layer_w(.15), H), pg.SRCALPHA)       # far skyline + Tokyo Tower
    x = -10
    while x < far.get_width():
        w, h = random.randint(16, 40), random.randint(50, 140)
        top = GY - h
        pg.draw.rect(far, (44, 18, 78), (x, top, w, H - top))
        windows(far, x, top, w, GY, 4, .3, [(255, 160, 210), (255, 230, 200)], 2)
        if random.random() < .3:
            far.fill((255, 40, 40), (x + w // 2, top - 1, 1, 1))
        x += w + random.randint(0, 4)
    tx, ty = int(far.get_width() * .3), GY - 10
    glow(far, tx, ty - 90, 70, (90, 30, 10))
    pg.draw.polygon(far, (220, 70, 30), [(tx - 18, ty), (tx - 3, ty - 150), (tx + 3, ty - 150), (tx + 18, ty)])
    for i in range(10):
        yy, hw = ty - i * 15, 18 - i * 1.5
        pg.draw.line(far, (120, 30, 20), (tx - hw, yy), (tx + hw - 3, yy - 15))
        pg.draw.line(far, (120, 30, 20), (tx + hw, yy), (tx - hw + 3, yy - 15))
    for dy, dw in ((55, 12), (105, 7)):
        far.fill((255, 235, 210), (tx - dw, ty - dy, dw * 2, 4))
    pg.draw.line(far, (240, 240, 240), (tx, ty - 150), (tx, ty - 178))
    far.fill((255, 50, 50), (tx, ty - 179, 1, 2))
    L['far'] = far

    mid = pg.Surface((layer_w(.4), H), pg.SRCALPHA)        # towers, neon signs, billboards
    x = -10
    while x < mid.get_width():
        w, h = random.randint(35, 70), random.randint(90, 175)
        top = GY - h
        pg.draw.rect(mid, (22, 9, 40), (x, top, w, H - top))
        pg.draw.line(mid, (60, 30, 90), (x, top), (x + w, top))
        windows(mid, x, top, w, GY, 5, .28, [(255, 200, 130), (130, 220, 255), (255, 120, 190), (255, 255, 230)], 2)
        if random.random() < .5:
            ax = x + random.randint(4, w - 4)
            pg.draw.line(mid, (22, 9, 40), (ax, top), (ax, top - random.randint(8, 22)))
        r = random.random()
        if r < .5:
            txt, col = random.choice(JP_V), random.choice(NEON)
            sx, sy = x + random.randint(3, max(4, w - 17)), top + random.randint(8, 30)
            hh = len(txt) * 13 + 6
            glow(mid, sx + 7, sy + hh // 2, 26, tuple(c // 3 for c in col))
            pg.draw.rect(mid, (20, 5, 25), (sx, sy, 14, hh))
            pg.draw.rect(mid, col, (sx, sy, 14, hh), 1)
            for i, ch in enumerate(txt):
                s = F_JP.render(ch, False, col)
                mid.blit(s, (sx + 7 - s.get_width() // 2, sy + 3 + i * 13))
        elif r < .8:
            txt = random.choice(JP_H)
            c1, c2 = random.sample(NEON, 2)
            bw = min(w - 6, F_JP.size(txt)[0] + 10)
            bx, by = x + (w - bw) // 2, top + random.randint(10, 40)
            glow(mid, bx + bw // 2, by + 8, 30, tuple(c // 3 for c in c1))
            for i in range(bw):
                k = i / bw
                pg.draw.line(mid, [int(c1[j] * (1 - k) * .5 + c2[j] * k * .5) for j in range(3)], (bx + i, by), (bx + i, by + 15))
            text(txt, F_JP, (255, 255, 255), bx + bw // 2, by + 1, True, mid)
        x += w + random.randint(2, 12)
    L['mid'] = mid

    near = pg.Surface((layer_w(.7), H), pg.SRCALPHA)       # street: shop fronts, noren, vending machines
    x = -10
    while x < near.get_width():
        w, h = random.randint(45, 85), random.randint(45, 95)
        top = GY - h
        pg.draw.rect(near, (12, 5, 22), (x, top, w, H - top))
        windows(near, x, top, w, GY - 30, 7, .15, [(255, 190, 120), (200, 230, 255)], 2)
        wc = random.choice([(255, 180, 110), (255, 140, 160), (160, 220, 255)])
        glow(near, x + w // 2, GY - 12, 30, tuple(c // 4 for c in wc))
        pg.draw.rect(near, [c // 2 for c in wc], (x + 4, GY - 22, w - 8, 18))
        nc = random.choice([(110, 20, 30), (30, 30, 90), (20, 20, 20)])
        for nx in range(x + 5, x + w - 6, 7):
            pg.draw.rect(near, nc, (nx, GY - 22, 6, 7))
        sign, col = random.choice(JP_SHOP), random.choice(NEON)
        sw = F_JP.size(sign)[0] + 6
        sx = x + (w - sw) // 2
        glow(near, sx + sw // 2, GY - 31, 22, tuple(c // 3 for c in col))
        pg.draw.rect(near, (10, 3, 15), (sx, GY - 38, sw, 14))
        pg.draw.rect(near, col, (sx, GY - 38, sw, 14), 1)
        near.blit(F_JP.render(sign, False, col), (sx + 3, GY - 37))
        if random.random() < .35:
            vx = x + w - 10
            glow(near, vx + 4, GY - 9, 16, (20, 50, 60))
            pg.draw.rect(near, (190, 235, 255), (vx, GY - 18, 8, 18))
            pg.draw.rect(near, (40, 120, 200), (vx + 1, GY - 16, 6, 8))
        x += w + random.randint(0, 10)
    L['near'] = near

    haze = pg.Surface((W, H), pg.SRCALPHA)
    for y in range(GY - 90, GY):
        haze.fill((255, 70, 150, int(55 * ((y - GY + 90) / 90) ** 2)), (0, y, W, 1))
    L['haze'] = haze

    floor = pg.Surface((W, FLOOR), pg.SRCALPHA)
    for y in range(FLOOR):
        floor.fill((4, 2, 12, int(70 + 120 * (y / FLOOR))), (0, y, W, 1))
    L['floor'] = floor

    beam = pg.Surface((240, 34))
    for x in range(240):
        k, hw = 1 - x / 240, 1 + x * .07
        pg.draw.line(beam, (int(34 * k), int(26 * k), int(55 * k)), (x, 17 - hw), (x, 17 + hw))
    L['beam'] = beam

    cone = pg.Surface((90, 100))
    for y in range(100):
        k, hw = (1 - y / 100) * .7 + .3, 4 + y * .42
        pg.draw.line(cone, (int(34 * k), int(22 * k), int(10 * k)), (45 - hw, y), (45 + hw, y))
    L['cone'] = cone

    fg = pg.Surface((layer_w(1.25), 60), pg.SRCALPHA)      # foreground cables
    x = 0
    while x < fg.get_width():
        x2 = x + random.randint(110, 180)
        y1, y2, sag = random.randint(0, 12), random.randint(0, 12), random.randint(14, 30)
        pts = [(x + (x2 - x) * k / 20, y1 + (y2 - y1) * k / 20 + math.sin(k / 20 * math.pi) * sag) for k in range(21)]
        pg.draw.lines(fg, (6, 2, 10), False, pts, 2)
        if random.random() < .4:
            hx, hy = pts[10]
            pg.draw.line(fg, (6, 2, 10), (hx, hy), (hx, hy + 8))
            pg.draw.rect(fg, (6, 2, 10), (hx - 5, hy + 8, 10, 14))
            pg.draw.rect(fg, random.choice(NEON), (hx - 5, hy + 8, 10, 14), 1)
        x = x2
    L['fg'] = fg

    over = pg.Surface((W, H), pg.SRCALPHA)
    for y in range(0, H, 2):
        over.fill((0, 0, 0, 22), (0, y, W, 1))
    for i in range(30):
        pg.draw.rect(over, (0, 0, 0, int(110 * (1 - i / 30) ** 2)), (i, i, W - 2 * i, H - 2 * i), 1)
    L['over'] = over

    # Persona-style menu overlay: red slab with halftone, black stripe, white edge
    pr = pg.Surface((W, H), pg.SRCALPHA)
    edge = lambda y: 300 - y / H * 120
    pg.draw.polygon(pr, (205, 16, 38, 238), [(0, 0), (300, 0), (180, H), (0, H)])
    for y in range(0, H, 5):
        for x in range(0, int(edge(y)), 5):
            r = .3 + 2.1 * (x / 300) ** 1.6
            pg.draw.circle(pr, (120, 0, 18, 255), (x + (y // 5 % 2) * 2.5, y), r)
    pg.draw.polygon(pr, (12, 6, 12, 240), [(306, 0), (348, 0), (228, H), (186, H)])
    pg.draw.line(pr, (255, 255, 255, 255), (350, 0), (230, H), 2)
    L['p_red'] = pr
    return L


# ---------------------------------------------------------------- world objects
class Plat:
    def __init__(s, x, y, w, kind='static', ground=False):
        s.x = s.x0 = x
        s.y = s.y0 = y
        s.w, s.kind, s.ground = w, kind, ground
        s.dx = s.dy = s.vy = 0.0
        s.deco, s.props, s.win = None, [], []
        s.ph, s.amp, s.spd, s.axis = R(0, 6), 0.0, 0.0, 'x'
        s.crumbleT, s.fallT, s.appear, s.solid = -1.0, 0.0, 0.0, True


class Body:
    def __init__(s, x, y, w, h):
        s.x, s.y, s.w, s.h = x, y, w, h
        s.vx = s.vy = 0.0
        s.g, s.plat, s.face = False, None, 1

    def rect(s):
        return (s.x, s.y, s.w, s.h)

    def phys(s, dt, plats, maxfall=600):
        if s.g and s.plat is not None and s.plat.solid:        # ride moving platforms
            s.x += s.plat.dx
            s.y += s.plat.dy
        s.vy = min(s.vy + GRAV * dt, maxfall)
        s.x = max(0, min(LW - s.w, s.x + s.vx * dt))
        pb = s.y + s.h
        s.y += s.vy * dt
        s.g = False
        if s.vy >= 0:  # one-way platforms: only land from above
            for p in plats:
                if p.solid and s.x + s.w > p.x and s.x < p.x + p.w and pb <= p.y + 1 + max(0, -p.dy) and s.y + s.h >= p.y:
                    s.y, s.vy, s.g, s.plat = p.y - s.h, 0, True, p
                    break


class Player(Body):
    def __init__(s):
        super().__init__(110, GY - 28, 12, 28)
        s.hp = s.maxhp = 5
        for a in ('inv', 'atk', 'acd', 'slide', 'dash', 'dcd', 'landT', 'slamT', 'runph', 'cwin', 'skidT', 'turnT', 'startT',
                  'atkT', 'parry', 'pcd', 'runk', 'idleT', 'idle_animT'):
            setattr(s, a, 0.0)
        s.crouch = s.dead = s.slam = s.launched = False
        s.stepn, s.idle_anim = 0, None
        s.airdash, s.was_g, s.swing, s.atkdir, s.step = True, True, set(), 'side', 1
        s.chains = {'scarf': [[s.x, s.y] for _ in range(7)], 'hair': [[s.x, s.y] for _ in range(6)]}
        s.pose = pose_idle(0)


KINDS = {  # w, h, hp, speed, windup, reach, damage
    'ronin': (12, 28, 2, 1.0, .45, 30, 1),
    'oni': (18, 37, 5, .65, .75, 44, 2),
    'ninja': (11, 25, 1, 1.15, .35, 0, 1),
}
ACTIVITIES = {'ronin': ('walk', 'guard', 'tea', 'phone', 'smoke', 'sleep'), 'oni': ('walk', 'guard', 'tea', 'sleep'),
              'ninja': ('walk', 'guard', 'meditate', 'phone')}
TALK_LINES = ["Rain again...", "The Shogun pays well.", "Did you hear that?", "My feet are killing me.",
              "Ramen after the shift?", "...heh.", "Quiet night.", "Who's up on the roofs?", "I hate this district."]
PHONE_LINES = ["Yes, boss.", "No sign of him.", "...uh-huh.", "I'll call you back.", "Tell her I'm working late.",
               "The rain? Still raining."]


class Enemy(Body):
    def __init__(s, x, plat, kind):
        w, h, s.hp, s.spd, s.wind, s.reach, s.dmg = KINDS[kind]
        super().__init__(x, plat.y - h, w, h)
        s.kind, s.maxhp, s.home = kind, s.hp, plat
        s.st, s.t = 'calm', R(1, 3)                                # unaware until they see or hear you
        s.act, s.actT, s.say = random.choice(ACTIVITIES[kind]), R(0, 3), None
        s.hurt = s.cd = s.kb = s.alert = s.throwT = 0.0
        s.dead = s.hit = False
        s.face = random.choice((-1, 1))
        s.anim = R(0, 6)
        s.chains = {'scarf': [[x, s.y] for _ in range(6)], 'band': [[x, s.y] for _ in range(4)]} if kind == 'ninja' else None
        s.pose = pose_idle(0)
        # navigation between rooftops: while climbing/dropping the enemy is in the background plane
        s.trav, s.travT, s.navp, s.navx, s.navcd, s.dropy = None, 0.0, None, None, 0.0, 0.0


# ---------------------------------------------------------------- game
class Game:
    def __init__(s):
        s.L = bake()
        s.stats = load_stats()
        s.dim = pg.Surface((W, H), pg.SRCALPHA)
        s.dim.fill((5, 0, 10, 170))
        s.menu_dim = pg.Surface((W, H), pg.SRCALPHA)
        s.menu_dim.fill((5, 0, 10, 120))
        s.red = pg.Surface((W, H), pg.SRCALPHA)
        s.red.fill((120, 0, 20, 110))
        s.black = pg.Surface((W, H))
        s.spr = pg.Surface((96, 96), pg.SRCALPHA)
        s.trail_layer = pg.Surface((W, H))
        s.punch, s.tilt, s.enter_cam = 0.0, 0.0, 0.0  # anime camera: push-in, tilt (degrees), district-start pull-back
        s.tip_scr = s.hand_scr = None
        s.dark = pg.Surface((W, H), pg.SRCALPHA)
        s.dark.fill((0, 0, 6, 255))
        s.port_chains = {'scarf': [[48, 60] for _ in range(7)], 'hair': [[48, 55] for _ in range(6)]}
        s.settings = load_settings()
        s.joys, s.axis_state, s.fs_on, s.music_now = {}, {}, False, None
        s.layers, s.layer_ch, s.intensity = None, None, 0.0
        s.act, s.pending, s.last_input = set(), set(), 'kb'
        s.capture, s.typing, s.name_buf = None, False, ''     # rebinding a control / typing the name
        s.col, s.denyT, s.skin_chains = 0, -9.0, {}
        s.fingers, s.tedit_sel, s.drag = {}, None, None        # touch: finger id -> [x, y, control]
        s.touch_layer = pg.Surface((W, H), pg.SRCALPHA)
        s.rain = []
        s.apply_settings()
        s.splash = []
        s.t, s.dt, s.fade, s.selT = 0.0, 1 / 60, 1.0, 0.0
        s.wipe, s.wipe_fn = 0.0, None
        s.train, s.trainT, s.blimp, s.lightT, s.lightning = None, 4.0, 0.0, R(8, 16), 0.0
        s.click, s.moved = False, False
        if pg.mixer.get_init():
            pg.mixer.set_num_channels(32)
            pg.mixer.set_reserved(2)                         # channels 0+1: the two music layers
        s.new_run()
        s.go('menu')

    def go(s, state, fade=.6):
        s.state, s.state_t, s.sel, s.fade = state, s.t, 0, fade
        if state != 'play':
            s.fingers = {}                                     # no stuck touch buttons across screens
        menus = ('menu', 'stats', 'settings', 'controls', 'skins', 'exit', 'victory')
        s.play_music('menu' if state in menus else 'fight')

    # ---------- settings, music, input
    def apply_settings(s):
        st = s.settings
        vol = st['master'] * st['sfx']
        for snd in SFX.values():
            snd.set_volume(vol)
        s.music_volume()
        n = RAIN_LEVELS[st['rain']][1]
        s.rain = (s.rain + [[R(0, W), R(0, H), R(4, 9), R(250, 380)] for _ in range(n)])[:n]
        if st['fullscreen'] != s.fs_on:
            try:
                pg.display.toggle_fullscreen()
                s.fs_on = st['fullscreen']
            except pg.error:
                st['fullscreen'] = s.fs_on

    def save_settings(s):
        save_stats(s.settings, SETTINGS_FILE)

    def music_volume(s):
        if not pg.mixer.get_init():
            return
        k = .35 if getattr(s, 'state', '') in ('pause', 'kiosk') else 1.0
        base = s.settings['master'] * s.settings['music'] * k
        pg.mixer.music.set_volume(base)
        if s.layer_ch:                                          # adaptive soundtrack: metal swells in when you fight
            it = getattr(s, 'intensity', 0.0)
            s.layer_ch[0].set_volume(base * (1 - .65 * it))
            s.layer_ch[1].set_volume(base * (.08 + .92 * it))

    def play_music(s, name):
        if name == s.music_now or not pg.mixer.get_init():
            s.music_volume()
            return
        if name == 'fight':                                     # gameplay: two synced layers (calm + combat)
            if s.layers is None:
                try:
                    s.layers = (pg.mixer.Sound(os.path.join(ASSETS, 'calm.wav')),
                                pg.mixer.Sound(os.path.join(ASSETS, 'fight.wav')))
                except (pg.error, FileNotFoundError):
                    s.layers = False
            if s.layers:
                pg.mixer.music.fadeout(500)
                s.layer_ch = (pg.mixer.Channel(0), pg.mixer.Channel(1))
                for ch, snd in zip(s.layer_ch, s.layers):
                    ch.play(snd, loops=-1, fade_ms=900)
                s.music_now = name
                s.music_volume()
                return
        elif s.layer_ch:
            for ch in s.layer_ch:
                ch.fadeout(600)
            s.layer_ch = None
        path = os.path.join(ASSETS, name + '.wav')
        if os.path.exists(path):
            try:
                pg.mixer.music.load(path)
                pg.mixer.music.play(-1, fade_ms=900)
                s.music_now = name
            except pg.error:
                pass
        s.music_volume()

    def rumble(s, low, high, ms):
        if s.settings['rumble']:
            for j in s.joys.values():
                try:
                    j.rumble(low, high, ms)
                except (pg.error, AttributeError):
                    pass

    @staticmethod
    def pad_down(j, b):
        if b in ('LT', 'RT'):
            ax = 4 if b == 'LT' else 5
            return j.get_numaxes() > ax and j.get_axis(ax) > .3
        return b is not None and b < j.get_numbuttons() and bool(j.get_button(b))

    def held(s):
        """What is held right now, from keyboard (with the player's bindings) + every connected gamepad."""
        k, kb, pad = pg.key.get_pressed(), s.settings['kb'], s.settings['pad']
        h = {a: bool(k[kb[a]]) for a in ('left', 'right', 'up', 'down', 'jump', 'crouch')}
        for a, key in (('left', pg.K_LEFT), ('right', pg.K_RIGHT), ('up', pg.K_UP), ('down', pg.K_DOWN)):
            h[a] |= bool(k[key])
        for j in s.joys.values():
            try:
                lx, ly = j.get_axis(0), j.get_axis(1)
                hat = j.get_hat(0) if j.get_numhats() else (0, 0)
                h['left'] |= lx < -.4 or hat[0] < 0
                h['right'] |= lx > .4 or hat[0] > 0
                h['up'] |= ly < -.55 or hat[1] > 0
                h['down'] |= ly > .55 or hat[1] < 0
                for a in ('jump', 'crouch'):
                    h[a] |= s.pad_down(j, pad.get(a))
            except pg.error:
                pass
        if TOUCH:                                                  # on-screen stick + held buttons
            sx, sy, sr = s.settings['touch']['stick']
            for x, y, owner in s.fingers.values():
                if owner == 'stick':
                    dx, dy = x - sx, y - sy
                    h['left'] |= dx < -sr * .3
                    h['right'] |= dx > sr * .3
                    h['up'] |= dy < -sr * .5
                    h['down'] |= dy > sr * .5
                elif owner in ('jump', 'crouch'):
                    h[owner] = True
        return h

    # ---------- touch controls (Android, or the PC with --touch)
    @staticmethod
    def to_logical(nx, ny):
        """Finger position (0..1 of the window) -> game pixels, accounting for the letterbox bars."""
        ww, wh = pg.display.get_window_size()
        k = min(ww / W, wh / H)
        return (nx * ww - (ww - W * k) / 2) / k, (ny * wh - (wh - H * k) / 2) / k

    def touch_event(s, kind, fid, x, y):
        L = s.settings['touch']
        if s.state == 'touchedit':
            s.tedit_event(kind, fid, x, y)
            return
        if kind == 'up':
            s.fingers.pop(fid, None)
            return
        if kind == 'move':
            if fid in s.fingers:
                s.fingers[fid][:2] = [x, y]
            return
        if s.state != 'play':                                     # menus use the tap as a normal click
            return
        s.last_input = 'touch'
        sx, sy, sr = L['stick']
        if math.hypot(x - sx, y - sy) < sr * 1.8 and not any(f[2] == 'stick' for f in s.fingers.values()):
            s.fingers[fid] = [x, y, 'stick']
            return
        best = min((math.hypot(x - bx, y - by) / br, a) for a, (bx, by, br) in L.items() if a != 'stick')
        if best[0] < 1.3:                                         # nearest button under the finger
            s.fingers[fid] = [x, y, best[1]]
            s.act.add(best[1])

    def draw_touch(s):
        """Translucent on-screen controls."""
        L, lay = s.settings['touch'], s.touch_layer
        lay.fill((0, 0, 0, 0))
        down = {f[2] for f in s.fingers.values()}
        sx, sy, sr = L['stick']
        pg.draw.circle(lay, (20, 10, 30, 70), (sx, sy), sr)
        pg.draw.circle(lay, (255, 255, 255, 110), (sx, sy), sr, 2)
        kx, ky = sx, sy
        for x, y, owner in s.fingers.values():
            if owner == 'stick':
                d = math.hypot(x - sx, y - sy) or 1
                k = min(1, sr / d)
                kx, ky = sx + (x - sx) * k, sy + (y - sy) * k
        pg.draw.circle(lay, (255, 255, 255, 120 if 'stick' in down else 70), (kx, ky), sr * .45)
        p = s.pl
        usable = {'super': s.superk >= s.super_need(),
                  'use': bool((s.kiosk and not s.kiosk['used'] and abs(p.x - s.kiosk['x']) < 40) or
                              (s.keydoor and abs(p.x - s.keydoor['x']) < 40))}
        for a, (x, y, r) in L.items():
            if a == 'stick':
                continue
            on = a in down
            dim = not usable.get(a, True)
            fill = (215, 20, 40, 150) if on else ((20, 10, 30, 40) if dim else (20, 10, 30, 80))
            pg.draw.circle(lay, fill, (x, y), r)
            pg.draw.circle(lay, (255, 255, 255, 60 if dim else 150), (x, y), r, 2)
            img = F_S.render(TOUCH_LABELS[a], True, WHITE)
            img.set_alpha(110 if dim else 230)
            lay.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
        scr.blit(lay, (0, 0))

    # ---------- touch layout editor (Settings -> Touch layout)
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
                pg.draw.circle(scr, RED, (x, y), r + 3, 2)
            if a == 'stick':
                text("MOVE", F_S, WHITE, x, y - 5, True)
        for lab, r in s.TEDIT_BTNS:
            pg.draw.rect(scr, WHITE if lab == "DONE" else INK, r)
            pg.draw.rect(scr, WHITE, r, 1)
            s.row_text(lab, lab == "DONE", r.centerx - F_S.size(lab)[0] // 2, r.y + 4)
        text("drag a control to move it  -  tap one, then - / + to resize", F_S, (230, 220, 245), W // 2, 32, True)
        if 'back' in s.act:
            s.save_settings()
            s.wipe_to(lambda: s.go('settings', 0))

    def tapped(s):
        """Confirm / skip text: a key, a pad button, or a tap / click."""
        return bool(s.act & {'ok', 'jump', 'atk'}) or s.click

    def bind_name(s, kind, a):
        if kind == 'kb':
            name = pg.key.name(s.settings['kb'][a]).upper() or '?'
            return name.replace('LEFT ', '').replace('RIGHT ', 'R') if len(name) > 6 else name
        return PAD_NAMES.get(s.settings['pad'].get(a), '-')

    def handle_event(s, ev):
        """Turn raw keyboard / mouse / gamepad / touch events into actions for this frame."""
        if TOUCH:
            kinds = {pg.FINGERDOWN: 'down', pg.FINGERMOTION: 'move', pg.FINGERUP: 'up'}
            if ev.type in kinds:
                s.touch_event(kinds[ev.type], ev.finger_id, *s.to_logical(ev.x, ev.y))
                return
            if not ANDROID:                                         # PC test mode: the mouse plays one finger
                mk = {pg.MOUSEBUTTONDOWN: 'down', pg.MOUSEBUTTONUP: 'up'}.get(ev.type)
                if ev.type == pg.MOUSEMOTION and ev.buttons[0]:
                    mk = 'move'
                if mk and getattr(ev, 'button', 1) == 1:
                    s.touch_event(mk, 'mouse', *ev.pos)
            if ev.type == pg.MOUSEBUTTONDOWN:                       # taps work as clicks in menus, never as attacks
                s.click = ev.button == 1
                return
        if ev.type == pg.KEYDOWN:
            s.last_input = 'kb'
            if s.capture:                                        # waiting for a new key binding
                kind, a = s.capture
                if kind == 'kb' and (ev.key != pg.K_ESCAPE or a == 'pause'):
                    s.settings['kb'][a] = ev.key
                    s.save_settings()
                    sfx('buy')
                s.capture = None
                return
            if s.typing:                                         # editing the player's name
                if ev.key == pg.K_BACKSPACE:
                    s.name_buf = s.name_buf[:-1]
                elif ev.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_ESCAPE):
                    s.finish_name(ev.key != pg.K_ESCAPE)
                return
            s.act.update(a for a, key in s.settings['kb'].items() if key == ev.key)
            s.act.update(MENU_KEYS.get(ev.key, ()))
            if ev.key == s.settings['kb']['atk']:
                s.act.add('ok')
            if ev.key == pg.K_F11:
                s.settings['fullscreen'] = not s.settings['fullscreen']
                s.apply_settings()
                s.save_settings()
        elif ev.type == pg.TEXTINPUT and s.typing:
            for ch in ev.text.upper():
                if (ch.isalnum() or ch in " -_.") and len(s.name_buf) < 12:
                    s.name_buf += ch
        elif ev.type == pg.MOUSEBUTTONDOWN:
            if ev.button == 1:
                s.click = True
                s.act.add('atk')
            elif ev.button == 3:
                s.act.add('parry')
            s.last_input = 'kb'
        elif ev.type == pg.MOUSEMOTION:
            s.moved = True
        elif ev.type == pg.JOYDEVICEADDED:
            j = pg.joystick.Joystick(ev.device_index)
            s.joys[j.get_instance_id()] = j
        elif ev.type == pg.JOYDEVICEREMOVED:
            s.joys.pop(ev.instance_id, None)
        elif ev.type == pg.JOYBUTTONDOWN:
            s.last_input = 'pad'
            if s.capture:
                if s.capture[0] == 'pad':
                    s.settings['pad'][s.capture[1]] = ev.button
                    s.save_settings()
                    sfx('buy')
                s.capture = None
                return
            s.act.update(a for a, b in s.settings['pad'].items() if b == ev.button)
            s.act.update({0: ('ok',), 1: ('back',), 7: ('pause',)}.get(ev.button, ()))
        elif ev.type == pg.JOYHATMOTION:
            hx, hy = ev.value
            for cond, a in ((hy > 0, 'up'), (hy < 0, 'down'), (hx < 0, 'left'), (hx > 0, 'right')):
                if cond:
                    s.act.add(a)
            s.last_input = 'pad'
        elif ev.type == pg.JOYAXISMOTION:
            # sticks/triggers become "pressed" actions when they cross a threshold (menus, dash)
            key = (ev.instance_id, ev.axis)
            v = ev.value
            if ev.axis in (0, 1):
                state = 0 if abs(v) < .5 else (1 if v > 0 else -1)
                if state and s.axis_state.get(key, 0) != state:
                    s.act.add({(0, -1): 'left', (0, 1): 'right', (1, -1): 'up', (1, 1): 'down'}[(ev.axis, state)])
                    s.last_input = 'pad'
                s.axis_state[key] = state
            elif ev.axis in (4, 5):                              # triggers act like buttons 'LT' / 'RT'
                on, code = v > .3, ('LT' if ev.axis == 4 else 'RT')
                if on and not s.axis_state.get(key):
                    s.last_input = 'pad'
                    if s.capture and s.capture[0] == 'pad':
                        s.settings['pad'][s.capture[1]] = code
                        s.save_settings()
                        s.capture = None
                        sfx('buy')
                    else:
                        s.act.update(a for a, b in s.settings['pad'].items() if b == code)
                s.axis_state[key] = on

    def wipe_to(s, fn):
        """Persona-style red slash transition; fn runs when the screen is covered."""
        if s.wipe_fn is None:
            s.wipe, s.wipe_fn = 0.0, fn
            sfx('wipe')

    # ---------- runs and levels
    def new_run(s):
        """A run = LEVELS districts in a row. Coins are only kept if you survive (or leave with an exit key)."""
        s.lvl, s.score, s.kills, s.gtime, s.run_done = 1, 0, 0, 0.0, False
        s.runst = {'mythic': 0, 'oni': 0, 'shinobi': 0, 'slams': 0, 'parries': 0, 'supers': 0, 'levels': 0}
        s.buffs, s.maxhp, s.hp_keep, s.superk, s.vampk = {}, 5, 5, 0.0, 0
        s.end_kind = 'victory'
        s.build_level()
        s.start_level()

    def start_level(s):
        p = s.pl
        if s.lvl == 1:                            # opening: manga panel (blade, hood up), dialog, camera pulls back
            p.x, p.face = 110, 1
            s.cine_t, s.dl, s.dc, s.cine_phase, s.cine_out = 0.0, 0, 0.0, 'inspect', 0.0
            p.pose = dict(POSE_INSPECT)
            s.go('cine', 1.0)
        else:                                     # walk in from the left; a neon shinobi gate slams shut behind
            p.x, p.face = -16, 1
            s.enterT, s.enter_cam = 1.3, 1.6
            s.go('play', 1.0)

    def buff(s, b):
        return s.buffs.get(b, 0)

    def pal(s, skin=None):
        """Palette of the equipped (or given) skin."""
        return SKINS.get(skin or s.stats['skin'], SKINS['shadow'])[2]

    def super_need(s):
        return 10 if s.buff('storm') else 20

    def build_level(s):
        G = Plat(-50, GY, LW + 100, ground=True)
        s.plats, s.pads, s.vents = [G], [], list(range(330, LW - 100, 270))

        s.towers, s.scaffolds, s.strings, s.sakuras = [], [], [], []

        def st(x, y, w):
            p = Plat(x, y, w)
            if random.random() < .3:
                p.deco = (random.choice(JP_V[:8]), random.choice(NEON))
            for _ in range(random.choice((0, 1, 1, 2))):
                kind = random.choice(('ac', 'tank', 'ant', 'sign', 'sakura', 'sakura', 'shrine'))
                rx = R(6, max(7, w - 18))
                p.props.append((kind, rx, random.choice(NEON)))
                if kind == 'sakura':
                    s.sakuras.append((p, rx + 6))
            if y > GY - 70:                       # low rooftops are real buildings with lit windows
                for wy in range(10, int(GY - y) - 6, 9):
                    for wx in range(5, int(w) - 8, 9):
                        if random.random() < .35:
                            p.win.append((wx, wy, random.choice([(255, 200, 130), (130, 220, 255), (255, 120, 190)])))
            s.plats.append(p)
            return p

        def tower_body(x, w, top, col):
            wins = [(wx, wy, random.choice([(120, 90, 60), (60, 100, 120), (120, 55, 90)]))
                    for wy in range(8, int(GY - top) - 6, 8) for wx in range(5, int(w) - 6, 7) if random.random() < .3]
            s.towers.append((x, w, top, wins, col))

        x = 280
        kinds = ('stairs', 'tower', 'mover', 'elevator', 'crumble', 'pad', 'skyscraper', 'bridge', 'scaffold')
        weights = (2, 1.6, 1.3, 1, 1.1, 1, 1.7, 1.3, 1.1)
        while x < LW - 320:
            kind = random.choices(kinds, weights)[0]
            if kind == 'skyscraper':                    # tall zig-zag tower, billboard on the roof
                w = R(110, 130)
                st(x, GY - R(50, 56), w)
                py, left = s.plats[-1].y, True
                for _ in range(random.randint(3, 5)):
                    py -= R(50, 56)
                    fw = w * R(.56, .62)
                    st(x if left else x + w - fw, py, fw)
                    left = not left
                roof = st(x - 8, py - R(52, 56), w + 16)
                roof.props = [('board', w / 2 - 13, random.choice(NEON))]
                tower_body(x + 6, w - 12, roof.y + 8, random.choice(NEON))
                end = x + w + 30
            elif kind == 'bridge':                      # two stacks joined by a high walkway with lanterns
                aw, tiers = R(60, 74), random.randint(2, 3)
                py = GY
                for _ in range(tiers):
                    py -= R(50, 56)
                    st(x + R(-6, 6), py, aw)
                bl = R(140, 200)
                br = st(x + aw - 4, py, bl)
                br.props = [('sakura', R(10, bl - 30), WHITE)] if random.random() < .6 else []
                if br.props:
                    s.sakuras.append((br, br.props[0][1] + 6))
                s.strings.append((br.x + 4, py - 34, br.x + bl - 4, py - 34, 10, random.randint(4, 6)))
                bx = br.x + bl - 4
                for i in range(tiers):
                    st(bx + R(-6, 6), py + i * R(50, 56), aw)
                end = bx + aw + 20
            elif kind == 'scaffold':                    # grid of small platforms on poles
                cols, rows = random.randint(2, 3), random.randint(3, 5)
                top = GY
                for c in range(cols):
                    for r in range(rows):
                        if r == 0 or random.random() < .85:
                            y = GY - 54 * (r + 1) - (c % 2) * 22
                            st(x + c * 58, y, R(38, 46))
                            top = min(top, y)
                s.scaffolds.append((x + 4, x + (cols - 1) * 58 + 33, top))
                end = x + cols * 58 + 30
            elif kind == 'stairs':
                px, py = x, GY
                for _ in range(random.randint(2, 4)):
                    py -= R(50, 56)
                    w = R(64, 96)
                    st(px, py, w)
                    px += w * .6 + R(30, 55)
                end = px + 40
            elif kind == 'tower':
                w = R(80, 110)
                p = st(x, GY - R(50, 56), w)
                px, py = x, p.y
                for _ in range(random.randint(1, 3)):
                    px, py = px + R(-30, 40), py - R(52, 56)
                    st(px, py, R(60, 90))
                end = x + w + 30
            elif kind == 'mover':
                a = st(x, GY - R(50, 56), R(60, 80))
                m = Plat(a.x + a.w + 40, a.y - R(44, 50), 50, 'move')
                m.axis, m.amp, m.spd = 'x', R(35, 50), R(1.0, 1.5)
                s.plats.append(m)
                b = st(m.x0 + m.amp + 90, m.y - R(30, 45), R(70, 95))
                end = b.x + b.w
            elif kind == 'elevator':
                e = Plat(x, GY - 110, 46, 'move')
                e.axis, e.amp, e.spd = 'y', 70, R(.8, 1.1)
                s.plats.append(e)
                top = st(x + 80, GY - R(185, 198), R(80, 110))
                end = top.x + top.w
            elif kind == 'crumble':
                px, py = x, GY - R(48, 56)
                for _ in range(random.randint(3, 4)):
                    s.plats.append(Plat(px, py, R(36, 44), 'crumble'))
                    px += R(62, 74)
                    py = max(GY - 130, min(GY - 50, py + R(-24, 20)))
                end = px
            else:
                s.pads.append([x + 10, G, 0.0])
                hi = st(x + R(40, 70), GY - R(165, 180), R(80, 110))
                if random.random() < .5:
                    st(hi.x + R(40, 80), hi.y - R(50, 56), R(60, 80))
                end = hi.x + hi.w
            x = end + R(50, 100)
        sp = sorted((p for p in s.plats if p.kind == 'static' and not p.ground and p.y < GY - 90), key=lambda p: p.x)
        for a, b in zip(sp, sp[1:]):                     # random lantern strings between nearby high rooftops
            gap = b.x - (a.x + a.w)
            if 20 < gap < 150 and abs(a.y - b.y) < 60 and random.random() < .45:
                s.strings.append((a.x + a.w - 6, a.y - 26, b.x + 6, b.y - 26, 8 + gap * .08, random.randint(2, 4)))
        s.camtop = min(p.y0 - (p.amp if p.axis == 'y' else 0) for p in s.plats) - 70
        s.lamps = list(range(330, LW, 380))
        s.pl = Player()
        s.pl.hp, s.pl.maxhp = s.hp_keep, s.maxhp
        s.en, s.parts, s.fx, s.coins, s.proj, s.gibs, s.ghosts, s.loot, s.trail = [], [], [], [], [], [], [], [], []
        s.cam = s.camy = s.shake = s.hitstop = s.flash = s.deadT = s.coinpop = s.pflash = s.slowmo = 0.0
        s.spawnT, s.coinT, s.enterT, s.superT, s.intensity = 4.5, 3.5, 0.0, -1.0, 0.0
        s.max_en = 9 + s.lvl                      # later districts are busier
        s.door = {'x': EXIT_X, 'k': 0.0, 'closing': False, 'kind': 'red' if s.lvl == 1 else 'gate'}
        s.kiosk = {'x': 205, 'used': False, 'cards': None} if s.lvl >= 2 else None
        s.keydoor = None
        s.noise = []                              # [x, y, time left]: fights the enemies can hear
        for i in range(32):
            s.add_coin(i >= 28)                  # rarer coins: 28 gold + 4 mythic, slowly respawning
        for _ in range(8 + s.lvl * 2):
            s.spawn_enemy(False)

    def finish_level(s):
        """Walked through the torii at the end of the district."""
        s.hp_keep, s.maxhp = s.pl.hp, s.pl.maxhp
        s.runst['levels'] += 1
        if s.lvl >= LEVELS:
            s.end_kind = 'victory'
            s.end_run('victory')
            s.go('victory', 1.0)
        else:
            s.phrase = random.choice(PHRASES)
            s.go('trans', 1.0)

    def static_plats(s):
        return [p for p in s.plats if p.kind == 'static']

    def add_coin(s, mythic):
        sp = s.static_plats()
        high = [p for p in sp if p.y < GY - 120]
        while True:
            if mythic and high:
                p = random.choice(high)          # mythic coins sit on the high rooftops
            else:
                p = s.plats[0] if random.random() < .25 else random.choice(sp)
            x = R(max(p.x, 0) + 6, min(p.x + p.w, LW) - 6)
            if x > 150:
                break
        s.coins.append([x, p.y - R(10, 36), mythic, R(0, 6)])

    def spawn_enemy(s, offscreen):
        r = random.random()
        oni = .12 + .04 * s.lvl                     # more oni in later districts
        kind = 'ronin' if r < .55 - oni / 2 else ('ninja' if r < 1 - oni else 'oni')
        taken = {id(e.home) for e in s.en if not e.home.ground}
        sp = s.static_plats()
        for _ in range(60):
            p = random.choice(sp)
            if p.w < 50 or (not p.ground and id(p) in taken):          # max 1 enemy per rooftop
                continue
            x = R(max(p.x, 0) + 5, min(p.x + p.w, LW) - 22)
            if p.ground and any(e.home.ground and abs(e.x - x) < 80 for e in s.en):
                continue
            if (not offscreen and x < 330) or abs(x - s.pl.x) < 160:
                continue
            if offscreen and s.cam - 20 < x < s.cam + W + 20:
                continue
            e = Enemy(x, p, kind)
            s.en.append(e)
            if p.ground and kind != 'oni' and random.random() < .35 and len(s.en) < s.max_en:   # two of them chatting
                mate = Enemy(x + 30, p, 'ronin')
                e.act = mate.act = 'talk'
                e.face, mate.face = 1, -1
                s.en.append(mate)
            return

    # ---------- particles
    def burst(s, x, y, n, col, spd=120, life=(.3, .7), size=(1, 2.5), grav=500, glowing=False, dirx=0):
        for _ in range(n):
            l = R(*life)
            s.parts.append([x, y, dirx * R(30, 160) + R(-spd, spd) * (.4 if dirx else 1), R(-spd, spd * .2),
                            l, l, col, R(*size), grav, glowing])

    def puff(s, x, y, n=4, dirx=0, col=(150, 130, 175)):
        """Soft smoke puffs (run start, stops, turns, jumps, landings)."""
        for _ in range(n):
            l = R(.3, .55)
            s.parts.append([x + R(-3, 3), y - R(0, 3), dirx * R(20, 60) + R(-25, 25), R(-30, -5), l, l, col, R(2.5, 4.5), -20, 2])

    def drop_loot(s, x, y, n):
        for _ in range(n):
            s.loot.append([x, y, R(-90, 90), R(-240, -140), random.random() < .1, 0.0])

    def collect(s, mythic, x, y):
        s.score += 5 if mythic else (2 if s.buff('greed') else 1)
        s.coinpop = .25
        if mythic:
            s.runst['mythic'] += 1
            sfx('myth')
            for i in range(16):
                s.burst(x, y, 1, hue(i * 22), spd=90, glowing=True, grav=100)
        else:
            sfx('coin')
            s.burst(x, y, 6, (255, 210, 60), spd=60, glowing=True, grav=100)

    # ---------- combat
    def hurt_enemy(s, e, f, dmg=1):
        if e.st == 'calm':                                         # caught unaware: one silent cut
            dmg = max(dmg, e.hp)
        if e.st == 'stun':                                         # parried enemies take a deathblow
            dmg *= 2
            s.burst(e.x + e.w / 2, e.y + e.h / 2, 12, (255, 240, 200), spd=160, glowing=True, grav=300)
        e.hp -= dmg
        e.hurt, e.kb, e.st, e.cd, e.vy = .22, f * 170, 'chase', .5, -90
        s.hitstop, s.shake = .05, 3
        s.burst(e.x + e.w / 2, e.y + e.h / 2, 10, (255, 30, 70), dirx=f)
        s.fx.append(['spark', e.x + e.w / 2 - f * 3, e.y + e.h * .45, f, .14, .14, R(0, 1)])
        sfx('hit')
        if e.hp <= 0:
            s.kill_enemy(e, f)

    def kill_enemy(s, e, f):
        if e.dead:
            return
        e.dead = True
        s.kills += 1
        s.noise.append([e.x + e.w / 2, e.y + e.h, .4])              # the others may hear it
        need = s.super_need()
        if s.superk < need:                                       # every kill charges the super
            s.superk += 1
            if s.superk >= need:
                sfx('charge')
        s.vampk += 1
        if s.buff('vamp') and s.vampk % 8 == 0 and s.pl.hp < s.pl.maxhp:
            s.pl.hp += 1
            s.burst(s.pl.x + s.pl.w / 2, s.pl.y, 10, (255, 60, 90), spd=60, glowing=True, grav=-40)
        s.hitstop, s.shake = .1, 5
        cx, cy = e.x + e.w / 2, e.y + e.h / 2
        sfx('kill')
        s.rumble(.5, .3, 120)
        if e.kind == 'ninja':                    # shinobi vanish in a smoke-bomb explosion
            s.runst['shinobi'] += 1
            s.fx.append(['boom', cx, cy, 1, .45, .45, 0])
            s.puff(cx, cy + 6, 14, col=(110, 90, 140))
            s.burst(cx, cy, 16, (255, 200, 90), spd=170, glowing=True, grav=200)
            sfx('boom')
            s.drop_loot(cx, cy, 3)
            return
        if e.kind == 'oni':
            s.runst['oni'] += 1
        s.burst(cx, cy, 34, (255, 30, 70), spd=170, dirx=f)
        s.fx.append(['cut', cx, cy, f, .18, .18, 0])
        S = PAL_E[e.kind]
        for half in (0, 1):                      # sliced in two
            s.gibs.append([cx, e.y + e.h * (.3 if half == 0 else .75), f * R(60, 150), R(-220, -100) if half == 0 else R(-60, 0),
                           0.0, R(-14, 14) if half == 0 else R(-4, 4), half, 5.0, e.w, e.h / 2, e.kind, S])
        s.drop_loot(cx, cy, 3 if e.kind == 'oni' else (1 if random.random() < .5 else 0))

    def parry_fx(s, x, y):
        """Steel on steel: white flash, a spray of sparks, a ringing Sekiro-style clang."""
        s.fx.append(['clang', x, y, 1, .22, .22, R(0, 1)])
        for _ in range(26):
            a, sp = R(0, math.tau), R(80, 320)
            l = R(.15, .45)
            s.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp - 60, l, l,
                            random.choice(((255, 250, 220), (255, 210, 110), (255, 160, 60))), R(1, 2), 700, True])
        sfx('parry')
        s.pflash, s.shake = .12, max(s.shake, 4)
        s.rumble(.4, 1.0, 140)

    def parried(s, e):
        """A blow landed inside the parry window: no damage, the enemy reels and is open to a deathblow."""
        p = s.pl
        p.parry, p.pcd = 0, .12
        e.st, e.t, e.hit, e.vx, e.cd = 'stun', 1.1, True, 0, 1.0
        e.kb = 0
        e.x -= e.face * 6
        s.parry_fx((p.x + p.w / 2 + e.x + e.w / 2) / 2, p.y + 10)
        s.hitstop, s.slowmo = .14, .35
        s.runst['parries'] += 1

    def start_super(s):
        p = s.pl
        s.superT, s.superk, s.super_hit = 0.0, 0, False
        p.atk, p.slide, p.dash, p.vx = 0, 0, 0, 0
        s.runst['supers'] += 1
        sfx('charge')
        s.rumble(.3, .3, 500)

    def super_k(s):
        """Progress of the swing part of the super (after the manga cut-in), 0..1."""
        return max(0.0, (s.superT - SUPER_CUT) / (SUPER_T - SUPER_CUT))

    def update_super(s, dt):
        """Manga cut-in close-up, then: raise the lit blade from the back, one huge cut with double reach."""
        p = s.pl
        s.superT += dt
        if s.superT < SUPER_CUT:                                   # the world is frozen during the cut-in
            if s.superT - dt < .25 <= s.superT:
                sfx('glint')
            return
        k = s.super_k()
        if k >= .12 and not s.super_hit:
            s.super_hit = True
            f, cx = p.face, p.x + p.w / 2
            hb = (cx if f > 0 else cx - 108, p.y - 34, 108, p.h + 60)       # 2x the normal reach
            for e in s.en:
                if not e.dead and not e.trav and ov(hb, e.rect()):
                    s.hurt_enemy(e, f, 4 + s.buff('edge'))
            for pr in s.proj:
                if ov(hb, (pr[0] - 3, pr[1] - 3, 6, 6)):
                    pr[5] = 0
            s.fx.append(['super', cx, p.y + p.h / 2, f, .45, .45, 0])
            s.burst(cx + f * 50, p.y + 10, 40, s.pal()['rim'], spd=220, glowing=True, grav=200, dirx=f)
            s.shake, s.hitstop = 11, 0
            sfx('super')
            s.rumble(1, 1, 400)
        if s.superT >= SUPER_T:
            s.superT = -1.0
        for f_ in s.fx:
            f_[4] -= dt
        s.fx = [f_ for f_ in s.fx if f_[4] > 0]
        for q in s.parts:
            q[4] -= dt
            q[3] += q[8] * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
        s.parts = [q for q in s.parts if q[4] > 0]
        s.en = [e for e in s.en if not e.dead]

    def hurt_player(s, f, dmg):
        p = s.pl
        if p.inv > 0 or p.dead or p.dash > 0 or p.slam or s.superT >= 0:   # dash, slam and super are invulnerable
            return
        p.hp -= dmg
        p.inv, p.vx, p.vy, p.slide, p.atk = 1.0, f * 170, -170, 0, 0
        s.shake, s.hitstop, s.flash = 6, .08, .25
        s.burst(p.x + p.w / 2, p.y + p.h / 2, 14, (0, 230, 255), glowing=True, dirx=f)
        sfx('hurt')
        s.rumble(.8, .9, 260)
        if p.hp <= 0:
            p.dead, s.deadT = True, 1.6
            s.burst(p.x + p.w / 2, p.y + p.h / 2, 50, (0, 230, 255), spd=180, life=(.6, 1.4), glowing=True)
            s.puff(p.x + p.w / 2, p.y + p.h / 2, 12, col=(60, 50, 90))

    def slam_impact(s):
        p = s.pl
        p.slam, p.landT = False, .28
        s.shake, s.hitstop = 9, .07
        s.runst['slams'] += 1
        x, y = p.x + p.w / 2, p.y + p.h
        s.fx.append(['wave', x, y, 1, .4, .4, 0])
        for sg in (-1, 1):
            s.puff(x + sg * 8, y, 6, sg)
        s.burst(x, y, 14, (110, 220, 255), spd=150, glowing=True, grav=300)
        s.punch, s.tilt = 1.0, random.choice((-4, 4))          # camera: short zoom + tilt on the landing
        sfx('slam')
        s.rumble(1.0, .6, 320)
        for e in s.en:
            ex = e.x + e.w / 2
            if not e.dead and not e.trav and abs(ex - x) < 70 and abs(e.y + e.h - y) < 28:
                s.hurt_enemy(e, 1 if ex > x else -1, 2)
                e.vy = -220

    def player_hits(s):
        p = s.pl
        f, cx = p.face, p.x + p.w / 2
        if p.atkdir == 'up':
            hb = (p.x - 18, p.y - 42, p.w + 36, 46)
        elif p.atkdir == 'down':
            hb = (p.x - 18, p.y + p.h - 6, p.w + 36, 44)
        else:
            reach = 66 if p.step == 3 else 54
            hb = (cx if f > 0 else cx - reach, p.y - 14, reach, p.h + 26)
        if p.atk < p.atkT * .65:
            return
        dmg = (2 if p.step == 3 and p.atkdir == 'side' else 1) + s.buff('edge')
        for e in s.en:
            if not e.dead and not e.trav and id(e) not in p.swing and ov(hb, e.rect()):
                p.swing.add(id(e))
                s.hurt_enemy(e, f if p.atkdir == 'side' else (1 if e.x > p.x else -1), dmg)
                if dmg == 2:
                    s.shake, s.hitstop = 3, .06
                    if p.step == 3:                            # combo finisher: a light camera push-in
                        s.punch, s.tilt = .45, -1.2 * f
                if p.atkdir == 'down':                     # pogo off enemies
                    p.vy, p.airdash = -300, True
        for pr in s.proj:                                  # deflect shuriken
            if not pr[4] and ov(hb, (pr[0] - 3, pr[1] - 3, 6, 6)):
                if p.atkdir == 'side':
                    pr[2], pr[3] = f * 380, 0
                else:
                    pr[2], pr[3] = -pr[2] * 1.8, -pr[3] * 1.8
                pr[4] = True
                s.hitstop = .06
                s.burst(pr[0], pr[1], 8, (255, 255, 200), spd=80, glowing=True, grav=0)
                sfx('ping')

    # ---------- player
    def upd_player(s, dt):
        p, h, A = s.pl, s.held(), s.act | s.pending
        s.pending = set()
        left, right, down, up, jump_held = h['left'], h['right'], h['down'], h['up'], h['jump']
        d = (1 if right else 0) - (1 if left else 0)
        for a in ('inv', 'acd', 'atk', 'dcd', 'landT', 'cwin', 'skidT', 'turnT', 'startT', 'parry', 'pcd'):
            setattr(p, a, getattr(p, a) - dt)
        if p.g:
            p.airdash = True
            p.runph += abs(p.vx) * dt * .105
            stepn = int(p.runph / math.pi)
            if stepn != p.stepn and abs(p.vx) > 60 and p.slide <= 0 and p.dash <= 0:   # footsteps per surface
                kind = 'water' if p.plat.ground else {'move': 'metal', 'crumble': 'wood'}.get(p.plat.kind, 'stone')
                sfx('step_' + kind)
                if kind == 'water':
                    s.burst(p.x + p.w / 2, p.y + p.h - 1, 3, (150, 160, 220), spd=40, life=(.15, .3), size=(1, 1.5), grav=500)
                s.puff(p.x + p.w / 2 - p.face * 3, p.y + p.h, 1, -p.face, (120, 105, 150))
            p.stepn = stepn
        if 'super' in A and s.superk >= s.super_need() and not p.slam:  # SUPER: 20 kills (10 with Storm Heart)
            s.start_super()
            return
        if 'parry' in A and p.pcd <= 0 and not p.slam and p.dash <= 0:   # PARRY window
            p.parry, p.pcd, p.atk = .2 * (1.6 if s.buff('iron') else 1), .5, 0
            sfx('throw')
        if p.slam:                                                   # ground slam: hover, then plunge
            p.slamT += dt
            p.vx, p.vy = 0, (-30 if p.slamT < .12 else 820)
            for e in s.en:
                if not e.dead and not e.trav and id(e) not in p.swing and ov(p.rect(), e.rect()):
                    p.swing.add(id(e))
                    s.hurt_enemy(e, 1 if e.x > p.x else -1, 2)
        else:
            if 'dash' in A and p.dcd <= 0 and (p.g or p.airdash) and p.landT <= 0:
                if d:
                    p.face = d
                p.dash, p.dcd, p.slide, p.crouch, p.atk = .18, .5 * (.6 if s.buff('ghost') else 1), 0, False, 0
                if not p.g:
                    p.airdash = False
                s.shake = max(s.shake, 2)
                s.puff(p.x + p.w / 2, p.y + p.h, 5, -p.face)
                sfx('dash')
            if p.dash > 0:                                             # long dash, passes through enemies
                p.dash -= dt
                p.vx, p.vy = p.face * 470, 0
            elif p.landT > 0:
                p.vx = 0
            elif p.atk > 0 and p.step == 3 and p.atkdir == 'side':      # finisher lunge
                p.vx = p.face * 160 * (p.atk / p.atkT) if p.atk < p.atkT * .65 else 0
            elif p.slide > 0:
                p.slide -= dt
                p.vx *= .12 ** dt
                if abs(p.vx) < 60 or not p.g:
                    p.slide = 0
                if random.random() < .4:
                    s.puff(p.x + p.w / 2 - p.face * 4, p.y + p.h, 1, -p.face)
            else:
                p.crouch = h['crouch'] and p.g
                if 'crouch' in A and p.g and abs(p.vx) > 90:           # crouch while running = slide
                    p.slide, p.vx, p.crouch = .5, p.face * 290, False
                    sfx('dash')
                else:
                    # sharp movement: full speed at once, stop on the spot (a quick plant pose + dust sells it)
                    top = 185 * (1.15 if s.buff('swift') else 1)
                    tgt = 0 if p.crouch else d * top
                    if p.g and d and d != p.face and abs(p.vx) > 100:    # instant turn
                        p.turnT = .06
                        s.puff(p.x + p.w / 2, p.y + p.h, 2, p.face)
                    elif p.g and not d and abs(p.vx) > 120 and p.skidT <= 0:   # hard stop
                        p.skidT = .08
                        s.puff(p.x + p.w / 2 + p.face * 4, p.y + p.h, 2, p.face)
                    elif p.g and d and abs(p.vx) < 20:                   # explosive start
                        p.startT = .06
                        s.puff(p.x + p.w / 2 - d * 4, p.y + p.h, 2, -d)
                    p.vx = tgt if p.g else p.vx + (tgt - p.vx) * min(1, dt * 22)
                    if d:
                        p.face = d
            if 'jump' in A and p.dash <= 0 and p.landT <= 0:
                if p.g:
                    if down and not p.plat.ground:
                        p.y += 3                                       # down + jump on a rooftop: drop through
                    else:
                        p.vy, p.crouch, p.slide = -JUMP_V, False, 0
                        sfx('jump')
                        s.puff(p.x + p.w / 2, p.y + p.h, 4)
                elif down:                                             # down + jump in the air: slam
                    p.slam, p.slamT, p.swing, p.atk = True, 0.0, set(), 0
                    sfx('dash')
            if not jump_held and p.vy < -120 and not p.launched:
                p.vy = -120                                            # short hop when released early
            if 'atk' in A and p.acd <= 0 and not p.slam and p.dash <= 0:
                dirn = 'up' if up else ('down' if down and not p.g else 'side')
                if dirn == 'side' and p.atkdir == 'side' and p.cwin > 0:
                    p.step = p.step % (3 if p.g else 2) + 1           # 3-hit combo on the ground, 2 in the air
                else:
                    p.step = 1
                p.atkdir = dirn
                p.atkT = .26 if (p.step == 3 and dirn == 'side') else .18
                p.atk, p.slide, p.swing = p.atkT, 0, set()
                p.acd = p.atkT + (.12 if p.step == 3 else .02)
                p.cwin = p.atkT + .3
                if not p.g and p.vy > 0 and dirn == 'side':
                    p.vy = -70
                if p.step == 3 and dirn == 'side':
                    s.fx.append(['thrust', 0, 0, p.face, p.atkT, p.atkT, 0])
                s.trail = []
                sfx('slash')
            if p.atk > 0:
                s.player_hits()
        nh = 16 if (p.crouch or p.slide > 0) else 28
        if nh != p.h:
            p.y += p.h - nh
            p.h = nh
        p.phys(dt, s.plats, 900 if p.slam else 600)
        if p.vy >= 0:
            p.launched = False
        if p.slam and p.g:
            s.slam_impact()
        elif p.g and not p.was_g:
            s.puff(p.x + p.w / 2, p.y + p.h, 4)
            sfx('land')
        p.was_g = p.g
        busy = d or A or not p.g or abs(p.vx) > 5 or p.atk > 0 or p.slide > 0 or p.crouch or p.parry > 0
        if busy:                                                       # any input cancels the idle animation
            p.idleT, p.idle_anim = 0.0, None
        else:
            p.idleT += dt
            if p.idle_anim:
                was = p.idle_animT
                p.idle_animT += dt
                if p.idle_anim == 'look' and any(was < m_ <= p.idle_animT for m_ in (.8, 1.9)):
                    p.face = -p.face                                   # glances back over his shoulder
                if p.idle_animT >= IDLE_ANIMS[p.idle_anim]:
                    p.idle_anim, p.idleT = None, 5.0                   # the next one comes a bit sooner
            elif p.idleT >= 10:
                p.idle_anim, p.idle_animT = random.choice(list(IDLE_ANIMS)), 0.0
                if p.idle_anim in ('inspect', 'wipe'):
                    sfx('unsheathe')
        if p.g and p.plat.kind == 'crumble' and p.plat.crumbleT < 0:   # crumbling rooftop starts to give way
            p.plat.crumbleT = .5
            sfx('crack')
        for pad in s.pads:                                             # jump pads
            if p.g and p.plat is pad[1] and abs(p.x + p.w / 2 - pad[0]) < 10 and not p.slam:
                p.vy, p.g, p.launched, p.airdash = -PAD_V, False, True, True
                pad[2] = .3
                s.burst(pad[0], pad[1].y - 3, 14, (0, 230, 255), spd=90, glowing=True, grav=200)
                sfx('pad')
        if p.x + p.w / 2 > END_X:                                      # through the torii: district cleared
            s.finish_level()
            return
        if s.kiosk and not s.kiosk['used'] and abs(p.x + p.w / 2 - s.kiosk['x']) < 28 and p.g and 'use' in A:
            if not s.kiosk['cards']:                                   # 3 random buffs, 1/3 chance of an exit key
                cards = random.sample(list(BUFFS), 3)
                if random.random() < 1 / 3:
                    cards[random.randrange(3)] = 'key'
                s.kiosk['cards'] = cards
            sfx('kiosk')
            s.go('kiosk', 0)
        if s.keydoor and s.keydoor['k'] >= 1 and abs(p.x + p.w / 2 - s.keydoor['x']) < 18 and 'use' in A:
            s.end_kind = 'escape'
            s.hp_keep = p.hp
            s.end_run('escape')
            sfx('door')
            s.wipe_to(lambda: s.go('exit', 0))

    # ---------- enemies: ronin (sword), oni (heavy club), shinobi (shuriken)
    def enemy_calm(s, e, dt, dx, dist, dy):
        """Off-duty routine, and noticing the player: sight cone in front (shorter while distracted, crouching helps),
        hearing up close, and the noise of nearby fights."""
        p = s.pl
        e.actT += dt
        e.vx = 0
        if e.act == 'walk':
            e.vx = e.face * 28 * e.spd
            e.t -= dt
            if e.t < 0:
                e.face, e.t = -e.face, R(2, 4)
        elif e.act == 'guard':                                       # looks around now and then
            e.t -= dt
            if e.t < 0:
                e.face, e.t = -e.face, R(3, 6)
        talking_near = any(o is not e and o.say and abs(o.x - e.x) < 70 for o in s.en)   # take turns
        if e.act in ('talk', 'phone') and e.say is None and not talking_near and random.random() < dt * .35:
            e.say = [random.choice(TALK_LINES if e.act == 'talk' else PHONE_LINES), 2.4]
        if e.say:
            e.say[1] -= dt
            if e.say[1] <= 0:
                e.say = None
        if p.dead or s.enterT > 0:
            return
        sight = {'sleep': 0, 'meditate': 90, 'talk': 110, 'phone': 105, 'tea': 120, 'smoke': 130}.get(e.act, 180)
        if p.crouch or p.slide > 0:
            sight *= .6
        hear = 34 if e.act == 'sleep' else 64
        ex, ey = e.x + e.w / 2, e.y + e.h
        heard = any(abs(n[0] - ex) < 150 and abs(n[1] - ey) < 80 for n in s.noise)
        if (dist < sight and dy < 50 and (dx > 0) == (e.face > 0)) or (dist < hear and dy < 30) or heard:
            e.st, e.t, e.say, e.alert = 'notice', .45, None, 0
            e.face = 1 if dx > 0 else -1
            if e.act in ('tea', 'phone', 'smoke'):                   # drops what was in his hand
                s.burst(ex + e.face * 6, e.y + 12, 5, (200, 196, 186), spd=50, life=(.3, .6))

    def climb_target(s, e):
        """A rooftop just above this enemy that it can climb onto, and where along it to climb."""
        p, ef = s.pl, e.y + e.h
        lo0, hi0 = (e.plat.x, e.plat.x + e.plat.w) if e.plat else (0, LW)
        best, bscore = None, 1e9
        for q in s.plats:
            if q.kind != 'static' or q.ground or not (ef - 82 < q.y < ef - 20):
                continue
            lo, hi = max(lo0, q.x) + 4, min(hi0, q.x + q.w) - e.w - 4
            if hi - lo < 2:
                continue
            cx = max(lo, min(hi, p.x - e.w / 2))
            score = abs(cx - p.x) + abs(cx - e.x) * .5 + abs(q.y - p.y) * .3
            if score < bscore:
                best, bscore = (q, cx), score
        return best

    def enemy_traverse(s, e, dt):
        """Climb up the back of a rooftop, hang on the edge, pull up - or hop down - then return to the front."""
        q = e.navp
        e.vx = 0
        if e.trav == 'climb':
            e.y -= 62 * e.spd * dt
            e.anim += dt * 9
            if e.y + e.h <= q.y + e.h * .8:
                e.trav, e.travT = 'grab', .25
        elif e.trav == 'grab':                                         # hanging from the edge
            e.travT -= dt
            if e.travT <= 0:
                e.trav, e.travT = 'pull', .18
        elif e.trav == 'pull':                                         # pull up over the edge
            e.travT -= dt
            k = 1 - max(0, e.travT) / .18
            e.y = q.y + e.h * .8 * (1 - k) - e.h
            if e.travT <= 0:
                e.y, e.vy, e.g, e.plat, e.home = q.y - e.h, 0, True, q, q
                e.trav, e.navx, e.navcd = None, None, .7
                s.puff(e.x + e.w / 2, q.y, 3)
        elif e.trav == 'drop':                                         # hop down behind the rooftop
            pb = e.y + e.h
            e.vy = min(e.vy + GRAV * dt, 600)
            e.y += e.vy * dt
            e.x = max(0, min(LW - e.w, e.x + e.face * 30 * dt))
            if e.vy > 0:
                for p in s.plats:
                    if p.solid and p.y >= e.dropy and e.x + e.w > p.x and e.x < p.x + p.w and pb <= p.y + 1 and e.y + e.h >= p.y:
                        e.y, e.vy, e.g, e.plat, e.home = p.y - e.h, 0, True, p, p
                        e.trav, e.navcd = None, .7
                        s.puff(e.x + e.w / 2, p.y, 4)
                        sfx('land')
                        break

    def upd_enemy(s, e, dt):
        p = s.pl
        for a in ('hurt', 'cd', 'alert', 'throwT', 'navcd'):
            setattr(e, a, getattr(e, a) - dt)
        if e.trav:
            s.enemy_traverse(e, dt)
            return
        dx = (p.x + p.w / 2) - (e.x + e.w / 2)
        dist, dy = abs(dx), abs((p.y + p.h) - (e.y + e.h))
        pdy = (p.y + p.h) - (e.y + e.h)                               # < 0: player is above
        if e.st == 'chase' and e.hurt <= 0 and e.g and not p.dead:
            if e.navx is None and e.navcd <= 0 and pdy < -30:          # player is higher: find a roof to climb
                t = s.climb_target(e)
                e.navcd = .6
                if t:
                    e.navp, e.navx = t
            elif e.navx is None and e.navcd <= 0 and pdy > 34 and not e.plat.ground and dist < 220:
                e.trav, e.vy, e.dropy, e.navcd = 'drop', -150, e.y + e.h + 4, 1.0   # player is lower: drop down
                return
            if e.navx is not None:
                if pdy > -20 or not e.navp.solid:
                    e.navx = None
                else:
                    ddx = e.navx - e.x
                    if abs(ddx) < 3:
                        e.trav, e.x, e.vy, e.g = 'climb', e.navx, 0, False
                        sfx('step_stone')
                        return
                    e.face = 1 if ddx > 0 else -1
                    e.vx = e.face * 92 * e.spd
                    e.phys(dt, s.plats)
                    e.anim += abs(e.vx) * dt * .12
                    return
        if e.hurt > 0:
            e.vx = e.kb
            e.kb *= .8
        elif e.st == 'calm':
            s.enemy_calm(e, dt, dx, dist, dy)
        elif e.st == 'notice':                                     # "?!" - a beat of surprise, then they draw
            e.vx = 0
            e.t -= dt
            if e.t <= 0:
                e.st, e.alert = 'chase', .6
                sfx('unsheathe')
        elif e.st == 'patrol':
            e.vx = e.face * 35 * e.spd
            e.t -= dt
            if e.t < 0:
                e.face, e.t = -e.face, R(1.5, 3.5)
            if not p.dead and (dist < 190 and dy < 55 and (dx > 0) == (e.face > 0) or dist < 60 and dy < 30):
                e.st, e.alert = 'chase', .6
        elif e.st == 'chase':
            e.face = 1 if dx > 0 else -1
            if e.kind == 'ninja':
                e.vx = (-e.face * 90 if dist < 80 else (e.face * 95 if dist > 160 else 0)) * e.spd
                if e.cd <= 0 and dy < 70 and dist < 240:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
            else:
                e.vx = e.face * 88 * e.spd
                if dist < e.reach and dy < 28 and e.cd <= 0:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
            if dist > 340 or dy > 280 or p.dead:
                e.st, e.navx = 'patrol', None
        elif e.st == 'stun':                                           # reeling after being parried
            e.vx *= .8
            e.t -= dt
            if e.t <= 0:
                e.st, e.cd = 'chase', .5
        elif e.st == 'wind':
            e.vx = 0
            e.t -= dt
            if e.t <= 0:
                if e.kind == 'ninja':
                    tx, ty = p.x + p.w / 2, p.y + p.h / 2
                    sx, sy = e.x + e.w / 2, e.y + 8
                    dd = max(1, math.hypot(tx - sx, ty - sy))
                    s.proj.append([sx, sy, (tx - sx) / dd * 210, (ty - sy) / dd * 210, False, 3.0])
                    e.st, e.cd, e.throwT = 'chase', R(1.3, 2.1), .25
                    sfx('throw')
                else:
                    e.st, e.t, e.vx, e.hit = 'slash', .18, e.face * (120 if e.kind == 'oni' else 160), False
                    sfx('eslash')
        elif e.st == 'slash':
            e.t -= dt
            e.vx *= .85
            if not e.hit:
                e.hit = True
                hb = (e.x + e.w if e.face > 0 else e.x - e.reach, e.y - 6, e.reach, e.h + 6)
                if ov(hb, p.rect()) and p.parry > 0:
                    s.parried(e)
                elif ov(hb, p.rect()):
                    s.hurt_player(e.face, e.dmg)
                    if e.kind == 'oni' and p.inv > .9:
                        p.vx, p.vy = e.face * 260, -220
            if e.t <= 0:
                e.st, e.cd = 'chase', (1.3 if e.kind == 'oni' else .9)
        if e.g and e.plat and not e.plat.ground:                       # don't walk off rooftop edges
            nx = e.x + e.vx * dt
            if nx < e.plat.x or nx + e.w > e.plat.x + e.plat.w:
                e.vx = 0
                if e.st == 'patrol':
                    e.face = -e.face
        e.phys(dt, s.plats)
        e.anim += abs(e.vx) * dt * .12
        if not p.dead and e.hurt <= 0 and e.st != 'stun' and ov(e.rect(), p.rect()):   # touching an enemy hurts
            if p.parry > 0:
                s.parried(e)
            else:
                s.hurt_player(1 if dx > 0 else -1, 1)

    def separate_enemies(s):
        """Enemies have bodies: they never overlap each other (except while climbing in the background)."""
        front = [e for e in s.en if not e.trav]
        for i, a in enumerate(front):
            for b in front[i + 1:]:
                if abs((a.y + a.h) - (b.y + b.h)) > 8:
                    continue
                d = (b.x + b.w / 2) - (a.x + a.w / 2)
                need = (a.w + b.w) / 2 + 3
                if abs(d) < need:
                    push = (need - abs(d)) / 2 * (1 if d >= 0 else -1)
                    a.x -= push
                    b.x += push
                    for e in (a, b):
                        if e.plat and not e.plat.ground:
                            e.x = max(e.plat.x, min(e.plat.x + e.plat.w - e.w, e.x))

    def update_plats(s, dt):
        for p in s.plats:
            ox, oy = p.x, p.y
            if p.kind == 'move':
                p.ph += dt * p.spd
                if p.axis == 'x':
                    p.x = p.x0 + math.sin(p.ph) * p.amp
                else:
                    p.y = p.y0 + math.sin(p.ph) * p.amp
            elif p.kind == 'crumble':
                p.appear = max(0, p.appear - dt)
                if p.crumbleT > 0:
                    p.crumbleT -= dt
                    if random.random() < .3:
                        s.burst(R(p.x, p.x + p.w), p.y + 4, 1, (90, 60, 50), spd=20, life=(.3, .5))
                    if p.crumbleT <= 0:
                        p.solid, p.fallT, p.vy = False, 4.0, 0
                        s.burst(p.x + p.w / 2, p.y, 10, (100, 70, 60), spd=60, size=(1.5, 3))
                elif not p.solid:
                    p.vy += GRAV * dt
                    p.y += p.vy * dt
                    p.fallT -= dt
                    if p.fallT <= 0:
                        p.y, p.solid, p.crumbleT, p.appear = p.y0, True, -1.0, .6
            p.dx, p.dy = p.x - ox, p.y - oy

    # ---------- world update
    def update_door(s, dt):
        d, p = s.door, s.pl
        if d['closing'] and d['k'] < 1:
            if d['k'] == 0:
                sfx('door' if d['kind'] == 'red' else 'gate')
            d['k'] = min(1, d['k'] + dt / .6)
            if d['k'] >= 1:
                s.shake = max(s.shake, 5)
                s.puff(d['x'], GY, 8)
                s.rumble(.6, .3, 200)
        if d['closing'] and p.x < d['x'] + 16:                  # no way back
            p.x, p.vx = d['x'] + 16, max(0, p.vx)
        if s.keydoor:
            s.keydoor['k'] = min(1, s.keydoor['k'] + dt / .8)

    def update(s, dt):
        s.flash = max(0, s.flash - dt)
        s.pflash = max(0, s.pflash - dt)
        s.shake = max(0, s.shake - dt * 20)
        s.coinpop = max(0, s.coinpop - dt)
        for pad in s.pads:
            pad[2] = max(0, pad[2] - dt)
        for n in s.noise:
            n[2] -= dt
        s.noise = [n for n in s.noise if n[2] > 0]
        for tr in s.trail:
            tr[4] -= dt
        s.trail = [tr for tr in s.trail if tr[4] > 0]
        s.punch = max(0.0, s.punch - dt * 2.5)
        s.tilt *= max(0.0, 1 - dt * 5)
        if s.superT >= 0:                                      # the super freezes the world around you
            s.update_super(dt)
            return
        if s.hitstop > 0:
            s.hitstop -= dt
            s.pending |= s.act & {'atk', 'jump', 'dash', 'parry', 'super', 'crouch', 'use'}   # input buffer
            return
        if s.slowmo > 0:                                       # brief slow motion after a parry
            s.slowmo -= dt
            dt *= .35
        p = s.pl
        if p.dead:
            s.deadT -= dt
            if s.deadT <= 0 and s.state == 'play':
                s.end_run('death')
                s.go('dead', 1.0)
            dt *= .35                                          # slow-mo on death
        s.update_plats(dt)
        s.update_door(dt)
        if not p.dead:
            s.gtime += dt
            s.enter_cam = max(0.0, s.enter_cam - dt)
            if s.enterT > 0:                                   # walking in at the start of a district
                s.enterT -= dt
                p.vx, p.face = 115, 1
                p.runph += p.vx * dt * .105
                p.phys(dt, s.plats)
                if s.enterT <= 0:
                    s.door['closing'] = True
            else:
                s.upd_player(dt)
        for e in s.en:
            s.upd_enemy(e, dt)
        s.separate_enemies()
        near = any(e.st in ('chase', 'wind', 'slash') and not e.trav and abs(e.x - p.x) < 300 for e in s.en)
        s.intensity += ((1.0 if near else 0.0) - s.intensity) * min(1, dt * (2.5 if near else .6))
        s.music_volume()
        for pr in s.proj:
            pr[0] += pr[2] * dt
            pr[1] += pr[3] * dt
            pr[5] -= dt
            r = (pr[0] - 3, pr[1] - 3, 6, 6)
            if pr[4]:
                for e in s.en:
                    if not e.dead and not e.trav and ov(r, e.rect()):
                        s.kill_enemy(e, 1 if pr[2] > 0 else -1)
                        pr[5] = 0
            elif ov(r, p.rect()) and not p.dead and p.parry > 0:  # parried shuriken fly back
                pr[2], pr[3], pr[4] = p.face * 380, 0, True
                s.parry_fx(pr[0], pr[1])
            elif ov(r, p.rect()) and not p.dead and p.inv <= 0 and p.dash <= 0:
                s.hurt_player(1 if pr[2] > 0 else -1, 1)
                pr[5] = 0
            if pr[1] > GY:
                pr[5] = 0
        s.proj = [pr for pr in s.proj if pr[5] > 0]
        s.en = [e for e in s.en if not e.dead and e.y < GY + 40]
        s.spawnT -= dt
        if s.spawnT <= 0 and len(s.en) < s.max_en:
            s.spawnT = 4.5
            s.spawn_enemy(True)
        s.coinT -= dt
        if s.coinT <= 0:
            s.coinT = 3.5
            if len(s.coins) < 32:
                s.add_coin(random.random() < .1)
        for pl, rx in s.sakuras:                               # drifting sakura petals
            if random.random() < dt * 1.5 and abs(pl.x + rx - s.cam - W / 2) < W:
                s.parts.append([pl.x + rx + R(-8, 8), pl.y - 22, R(-30, -10), R(5, 15), 3.0, 3.0,
                                random.choice(((250, 160, 200), (230, 120, 170))), 1.5, 8, False])
        for vx in s.vents:                                     # steam vents in the street
            if random.random() < dt * 5:
                s.parts.append([vx + R(-3, 3), GY - 2, R(-8, 8), R(-60, -30), 1.2, 1.2, (150, 130, 170), R(3, 6), -15, 2])
        cx, cy = p.x + p.w / 2, p.y + p.h / 2
        for c in s.coins[:]:
            if s.buff('magnet') and not p.dead:                # COIN MAGNET buff pulls coins in
                ddx, ddy = cx - c[0], cy - c[1]
                dd = math.hypot(ddx, ddy) or 1
                if dd < 95:
                    c[0] += ddx / dd * 160 * dt
                    c[1] += ddy / dd * 160 * dt
            if not p.dead and abs(c[0] - cx) < 10 and abs(c[1] - cy) < 16:
                s.coins.remove(c)
                s.collect(c[2], c[0], c[1])
        for l in s.loot:                                       # dropped coins: pop out, then fly to you
            l[5] += dt
            if l[5] < .55 or p.dead:
                l[3] += GRAV * dt
                l[0] += l[2] * dt
                l[1] += l[3] * dt
                if l[1] > GY - 4:
                    l[1], l[3], l[2] = GY - 4, l[3] * -.45, l[2] * .7
            else:
                ddx, ddy = cx - l[0], cy - l[1]
                dd = math.hypot(ddx, ddy) or 1
                sp = 150 + (l[5] - .55) * 700
                l[0] += ddx / dd * min(dd, sp * dt)
                l[1] += ddy / dd * min(dd, sp * dt)
                if dd < 8:
                    l[5] = -99
                    s.collect(l[4], l[0], l[1])
        s.loot = [l for l in s.loot if l[5] > -50]
        for q in s.parts:
            q[4] -= dt
            q[3] += q[8] * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            if q[9] == 2:
                q[2] *= .96
            if q[1] > GY:
                q[1], q[3], q[2] = GY, 0, q[2] * .5
        s.parts = [q for q in s.parts if q[4] > 0]
        for gb in s.gibs:
            gb[3] += GRAV * dt
            gb[0] += gb[2] * dt
            gb[1] += gb[3] * dt
            gb[4] += gb[5] * dt
            gb[7] -= dt
            if gb[1] + gb[9] / 2 > GY:
                gb[1], gb[3], gb[2], gb[5] = GY - gb[9] / 2, -abs(gb[3]) * .25, gb[2] * .6, gb[5] * .5
            elif random.random() < .3:
                s.burst(gb[0], gb[1], 1, (220, 20, 60), spd=10, life=(.3, .6))
        s.gibs = [gb for gb in s.gibs if gb[7] > 0]
        for f in s.fx:
            f[4] -= dt
        s.fx = [f for f in s.fx if f[4] > 0]
        for gh in s.ghosts:
            gh[3] -= dt
        s.ghosts = [gh for gh in s.ghosts if gh[3] > 0]
        tgt = p.x - W * .4 + p.face * 30
        s.cam += (tgt - s.cam) * min(1, dt * 5)
        s.cam = max(0, min(LW - W, s.cam))
        ty = max(s.camtop, min(0, p.y + p.h / 2 - H * .55))   # camera follows you up the rooftops
        s.camy += (ty - s.camy) * min(1, dt * 4)

    def end_run(s, kind):
        if s.run_done:
            return
        s.run_done = True
        st = s.stats
        st['kills'] += s.kills
        st['time'] += s.gtime
        for k in ('oni', 'shinobi', 'slams', 'parries', 'supers', 'levels'):
            st[k] += s.runst[k]
        if kind in ('victory', 'escape'):        # coins are only banked when you survive the run
            st['coins'] += s.score
            st['wallet'] += s.score              # the wallet is what you spend on skins
            st['mythic'] += s.runst['mythic']
            st['runs'] += 1
            st['best'] = max(st['best'], s.score)
        elif kind == 'death':
            st['deaths'] += 1
        save_stats(st)

    # ---------- rendering: characters
    def compose(s, m, D, sx, sy, S, flash=False, target=None):
        """Outline + back-light rim around a painted sprite (gives the clean pixel-art look)."""
        T = target or scr
        ol = m.to_surface(setcolor=S['line'] + (255,), unsetcolor=(0, 0, 0, 0))
        for ddx, ddy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            T.blit(ol, (sx + ddx, sy + ddy))
        if flash:
            T.blit(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (sx, sy))
            return
        T.blit(D, (sx, sy))
        side = m.copy()
        side.erase(m, (1, 0))
        side2 = m.copy()
        side2.erase(m, (-1, 0))
        side.draw(side2, (0, 0))
        T.blit(side.to_surface(setcolor=S['rim2'] + (255,), unsetcolor=(0, 0, 0, 0)), (sx, sy))
        top = m.copy()
        top.erase(m, (0, 1))
        T.blit(top.to_surface(setcolor=S['rim'] + (255,), unsetcolor=(0, 0, 0, 0)), (sx, sy))

    def draw_char(s, wx, wy, f, P, S, chains, cx, oy, flash=False, ghost=None):
        D = s.spr
        D.fill((0, 0, 0, 0))
        org = (wx - 48, wy - 84)
        info = paint(D, 48, 84, f, P, S, s.t, chains, org)
        m = pg.mask.from_surface(D)
        sx, sy = org[0] - cx, org[1] + oy
        s.compose(m, D, sx, sy, S, flash)
        if not flash:
            glow(scr, sx + info['eye'][0], sy + info['eye'][1], 7, S['eyeglow'])
            if info['blade'] and P.get('hot', 0) > 0:
                glow(scr, sx + info['blade'][0], sy + info['blade'][1], 12, qcol((40, 80, 110), P['hot']))
        if ghost and s.state == 'play':
            s.ghosts.append([m, org[0], org[1], ghost[0], ghost[1], ghost[0]])
        return info, sx, sy

    def player_pose(s):
        p = s.pl
        if s.superT >= 0:                               # raise during the camera dive, swing right after it
            if s.superT < SUPER_CUT:
                return pose_super(.4 * ease(s.superT / SUPER_CUT))
            return pose_super(.4 + .6 * min(1, s.super_k() * 2.5))
        if s.state == 'cine':                           # intro: look at the blade, then pull the hood up
            if s.cine_phase == 'inspect':
                return POSE_INSPECT
            if s.cine_phase == 'hood' and s.cine_t < 2.4:
                return dict(POSE_HOODUP, hood=0.0 if s.cine_t < 2.05 else 1.0)
            return pose_idle(s.t)
        if p.parry > 0:
            return POSE_PARRY
        if p.slam:
            P = POSE_SLAM
        elif p.landT > 0:
            P = POSE_CROUCH
        elif p.inv > .75:
            P = POSE_HURT
        elif p.dash > 0:
            P = POSE_DASH
        elif p.slide > 0:
            P = POSE_SLIDE
        elif p.crouch:
            P = POSE_CROUCH
        elif not p.g:
            P = pose_jump(p.vy)
        elif p.turnT > 0:
            P = POSE_TURN
        elif p.skidT > 0:
            P = POSE_SKID
        elif p.startT > 0:
            P = POSE_START
        elif abs(p.vx) > 20:
            P = pose_run(p.runph, min(1.15, abs(p.vx) / 150))     # leans deeper as the sprint builds up
        elif p.idle_anim:                               # left alone for a while: a little idle animation
            P = pose_idle_anim(p.idle_anim, p.idle_animT / IDLE_ANIMS[p.idle_anim], s.t)
        else:
            P = pose_idle(s.t)
        if p.atk > 0 and not p.slam:
            P = with_attack(P, p.atkdir, 1 - p.atk / p.atkT, p.step)
        return P

    def draw_player(s, cx, oy):
        p = s.pl
        if p.dead:
            return
        tgt = s.player_pose()
        snap = p.atk > 0 or s.superT >= 0 or p.parry > 0
        k = 1 if snap else min(1, s.dt * 28)                   # snappy pose changes to match the sharp movement
        if s.state in ('play', 'cine') and s.hitstop <= 0:
            p.pose = blend(p.pose, tgt, k)
            p.pose['hot'] = tgt.get('hot', 0)
        if p.inv > 0 and int(s.t * 20) % 2:
            return
        ghost = None
        if p.dash > 0:
            ghost = (.3, (0, 200, 255) if int(s.t * 30) % 2 else (255, 40, 150))
        elif p.slam and p.slamT > .12 and int(s.t * 60) % 2 == 0:
            ghost = (.25, (0, 160, 255))
        elif p.slide > 0 and int(s.t * 60) % 3 == 0:
            ghost = (.2, (120, 40, 200))
        S = s.pal()
        info, sx, sy = s.draw_char(p.x + p.w / 2, p.y + p.h, p.face, p.pose, S, p.chains, cx, oy, ghost=ghost)
        s.hand_scr = (info['hand'][0] + sx, info['hand'][1] + sy)
        s.tip_scr = (info['tip'][0] + sx, info['tip'][1] + sy) if info['tip'] else None
        if info['tip'] and s.state == 'play' and (p.atk > 0 or 0 < s.super_k() < .4):   # record the blade's path
            hx, hy = info['hand'][0] + sx + cx, info['hand'][1] + sy - oy
            tx, ty = info['tip'][0] + sx + cx, info['tip'][1] + sy - oy
            if s.superT >= 0:                                 # the super blade is longer and brighter
                tx, ty = hx + (tx - hx) * 2.2, hy + (ty - hy) * 2.2
            s.trail.append([hx, hy, tx, ty, .13 if s.superT < 0 else .3])
        if s.superT >= 0 and info['blade']:                    # the lit blade during the super
            for kk in (.3, .6, .9):
                bx = sx + lerp(info['hand'][0], info['tip'][0] if info['tip'] else info['blade'][0], kk)
                by = sy + lerp(info['hand'][1], info['tip'][1] if info['tip'] else info['blade'][1], kk)
                glow(scr, bx, by, 14, qcol(S['rim'], .5))

    def draw_trail(s, cx, oy):
        """Sword trail: a ribbon swept by the blade, white-hot at the edge and fading into the skin's colour."""
        tr = s.trail
        if len(tr) < 2:
            return
        layer = s.trail_layer
        layer.fill((0, 0, 0))
        acc = s.pal()['rim']
        for a, b in zip(tr, tr[1:]):
            k = max(0, min(1, b[4] / (.3 if s.superT >= 0 else .13)))
            ia = (lerp(a[0], a[2], .45) - cx, lerp(a[1], a[3], .45) + oy)
            ib = (lerp(b[0], b[2], .45) - cx, lerp(b[1], b[3], .45) + oy)
            ta, tb = (a[2] - cx, a[3] + oy), (b[2] - cx, b[3] + oy)
            pg.draw.polygon(layer, qcol(acc, k * .55), [ia, ta, tb, ib])
            pg.draw.line(layer, qcol((255, 255, 255), k), ta, tb, 2)
        scr.blit(layer, (0, 0), special_flags=pg.BLEND_RGB_ADD)

    def draw_ghosts(s, cx, oy):
        for m, wx, wy, life, col, ml in s.ghosts:
            img = m.to_surface(setcolor=qcol(col, life / ml * .8) + (255,), unsetcolor=(0, 0, 0, 0))
            scr.blit(img, (wx - cx, wy + oy), special_flags=pg.BLEND_RGB_ADD)

    def draw_enemy(s, e, cx, oy):
        bx, by = e.x + e.w / 2 - cx, e.y + e.h + oy
        if bx < -50 or bx > W + 50:
            return
        if s.state == 'play' and s.hitstop <= 0:
            e.pose = blend(e.pose, pose_enemy(e, s.t), min(1, s.dt * 16))
        S = PAL_BACK[e.kind] if e.trav else PAL_E[e.kind]
        info, sx, sy = s.draw_char(e.x + e.w / 2, e.y + e.h, e.face, e.pose, S, e.chains, cx, oy, e.hurt > .1)
        if e.trav:
            return
        hx, hy = sx + info['hc'][0], sy + info['hc'][1]
        wind = e.st == 'wind' and e.hurt <= 0
        if e.kind == 'ninja' and wind:
            glow(scr, sx + info['hand'][0], sy + info['hand'][1], 9, (90, 90, 50))
            star(sx + info['hand'][0], sy + info['hand'][1], 3, s.t * 20, (230, 230, 240))
        elif wind and int(s.t * 16) % 2 and info['blade']:
            glow(scr, sx + info['blade'][0], sy + info['blade'][1], 14, (160, 30, 30))
        if e.st == 'calm':
            s.draw_activity(e, sx + info['hand'][0], sy + info['hand'][1], hx, hy, cx, oy)
        if e.st == 'notice':
            outlined('?', F_PM, (255, 220, 60), hx, hy - 30 - (.45 - e.t) * 12, center=True, r=1)
        if wind or e.alert > 0:
            col = (255, 50, 50) if wind else (255, 220, 60)
            outlined('!', F_PM, col, hx, hy - 34 + (0 if wind else -e.alert * 6), center=True, r=1)
        if e.maxhp > 2 and e.hp < e.maxhp:
            pg.draw.rect(scr, (40, 0, 10), (bx - 10, hy - 16, 20, 3))
            pg.draw.rect(scr, (255, 40, 60), (bx - 10, hy - 16, 20 * e.hp / e.maxhp, 3))

    def draw_activity(s, e, hx_, hy_, hx, hy, cx, oy):
        """Props and speech for the off-duty routines (drawn at the hand / above the head)."""
        live = s.state == 'play'
        if e.act == 'tea':
            pg.draw.rect(scr, (226, 222, 210), (hx_ - 1, hy_ - 3, 4, 4))
            if live and random.random() < .08:
                s.parts.append([hx_ + cx, hy_ - 4 - oy, R(-4, 4), R(-14, -8), .9, .9, (190, 186, 200), R(1.5, 2.5), -6, 2])
        elif e.act == 'phone':
            pg.draw.rect(scr, (20, 20, 26), (hx_ - 1, hy_ - 2, 2, 5))
            scr.fill((150, 210, 255), (hx_ - 1, hy_ - 1, 1, 2))
            glow(scr, hx_, hy_, 7, (20, 40, 60))
        elif e.act == 'smoke':
            scr.fill((255, 150, 60), (hx_, hy_ - 1, 1, 1))
            glow(scr, hx_, hy_ - 1, 5, (90, 40, 10))
            if live and random.random() < .06:
                s.parts.append([hx_ + cx, hy_ - 2 - oy, R(-3, 6), R(-12, -6), 1.4, 1.4, (150, 146, 156), R(2, 3), -4, 2])
        elif e.act == 'sleep':
            for i in range(3):                                         # z z z drifting up
                k = (s.t * .5 + i / 3 + e.anim) % 1
                img = F_S.render("z", False, (200, 200, 230))
                img.set_alpha(int(255 * (1 - k)))
                scr.blit(img, (hx + 4 + k * 8 + i * 2, hy - 8 - k * 14))
        if e.say:                                                      # speech bubble
            txt = e.say[0]
            w = F_S.size(txt)[0] + 8
            bx, by = max(2, min(W - w - 2, hx - w // 2)), hy - 30
            pg.draw.rect(scr, (240, 238, 232), (bx, by, w, 13), border_radius=4)
            pg.draw.polygon(scr, (240, 238, 232), [(hx - 2, by + 12), (hx + 3, by + 12), (hx, by + 16)])
            scr.blit(F_S.render(txt, False, INK), (bx + 4, by + 1))

    def draw_gib(s, gb, cx, oy):
        x, y, a, half, w, h, S = gb[0] - cx, gb[1] + oy, gb[4], gb[6], gb[8], gb[9], gb[11]
        pts = rot([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], x, y, a)
        sil_poly(scr, pts, S['coat'] if half == 0 else S['pants'], S['rim'])
        if half == 0:
            hx, hy = rot([(0, -h / 2 - 4)], x, y, a)[0]
            pg.draw.circle(scr, S['rim'], (hx, hy - 1), 4)
            pg.draw.circle(scr, S.get('skin', S['coat']), (hx, hy), 4)
            if gb[10] == 'ronin':
                sil_poly(scr, rot([(-10, -h / 2 - 5), (0, -h / 2 - 11), (10, -h / 2 - 5)], x, y, a), S['straw'], S['rim'])
        cut = rot([(-w / 2, h / 2 if half == 0 else -h / 2), (w / 2, h / 2 if half == 0 else -h / 2)], x, y, a)
        pg.draw.line(scr, (255, 30, 70), cut[0], cut[1], 2)

    # ---------- rendering: world
    def draw_bg(s, cam, oy):
        L, dt = s.L, s.dt
        scr.blit(L['sky'], (0, 0))
        s.lightT -= dt                                         # occasional lightning
        if s.lightT <= 0:
            s.lightT, s.lightning, s.boltx = R(14, 28), .5, R(40, W - 40)
        if s.lightning > 0:
            s.lightning -= dt
            k = s.lightning / .5
            fl = max(0, math.sin(k * math.pi * 3)) * k
            scr.fill(qcol((130, 110, 170), fl), special_flags=pg.BLEND_RGB_ADD)
            if k > .6:
                x, y = s.boltx, 0
                pts = [(x, y)]
                rnd = random.Random(int(s.boltx))
                while y < 150:
                    x, y = x + rnd.uniform(-14, 14), y + rnd.uniform(10, 22)
                    pts.append((x, y))
                pg.draw.lines(scr, (230, 220, 255), False, pts, 2)
        for i, bx in enumerate((60, 230, 400)):                 # sweeping searchlights
            a = math.radians(90 + math.sin(s.t * .4 + i * 2.1) * 35)
            img = pg.transform.rotate(L['beam'], math.degrees(a))
            ox, oyy = (bx - cam * .15) % (W + 120) - 60, GY - 40 + oy * .15
            scr.blit(img, img.get_rect(center=(ox + math.cos(a) * 120, oyy - math.sin(a) * 120)), special_flags=pg.BLEND_RGB_ADD)
        s.blimp += dt * 8                                       # advertising blimp
        bx = (s.blimp - cam * .08) % (W + 240) - 120
        by = 34 + oy * .08 + math.sin(s.t * .5) * 3
        pg.draw.ellipse(scr, (40, 30, 62), (bx, by, 96, 26))
        pg.draw.arc(scr, (110, 90, 160), (bx, by, 96, 26), .4, 2.7, 1)
        pg.draw.polygon(scr, (40, 30, 62), [(bx + 2, by + 13), (bx - 8, by + 4), (bx - 8, by + 22)])
        scr.fill((6, 4, 12), (bx + 20, by + 7, 56, 12))
        msg = F_JP.render("ネオン浪人 ◆ NEO TOKYO ◆ 新宿 ◆ ", False, hue(s.t * 40))
        off = int(s.t * 20) % msg.get_width()
        scr.blit(msg, (bx + 21, by + 7), (off, 0, 54, 12))
        scr.blit(msg, (bx + 21 + msg.get_width() - off, by + 7), (0, 0, max(0, 54 - (msg.get_width() - off)), 12))
        if int(s.t * 2) % 2:
            glow(scr, bx - 6, by + 13, 6, (90, 0, 0))
        scr.blit(L['far'], (-int(cam * .15), int(oy * .15)))
        for i in range(4):                                      # drones
            dxp = (i * 137 + s.t * (18 + i * 7)) % (W + 40) - 20
            dyp = 70 + i * 16 + math.sin(s.t * 1.3 + i) * 8 + oy * .3
            scr.fill((20, 14, 30), (dxp - 2, dyp, 5, 2))
            if int(s.t * 3 + i) % 2:
                glow(scr, dxp, dyp, 5, (90, 10, 10) if i % 2 else (10, 90, 30))
        scr.blit(L['mid'], (-int(cam * .4), int(oy * .4)))
        ty = GY - 128 + oy * .55                               # elevated train line
        pg.draw.rect(scr, (18, 8, 30), (0, ty, W, 5))
        pg.draw.line(scr, (255, 60, 160), (0, ty), (W, ty))
        for px in range(-(int(cam * .55) % 70), W, 70):
            pg.draw.rect(scr, (14, 6, 24), (px, ty + 5, 6, H))
        s.trainT -= dt
        if s.train is None and s.trainT <= 0:
            s.train = [cam * .55 + W + 40, -230.0]
        if s.train:
            s.train[0] += s.train[1] * dt
            tx = s.train[0] - cam * .55
            glow(scr, tx + 150, ty - 6, 150, (70, 50, 25), .12)
            for car in range(4):
                cxp = tx + car * 76
                pg.draw.rect(scr, (36, 32, 56), (cxp, ty - 17, 72, 16))
                pg.draw.line(scr, (110, 100, 150), (cxp, ty - 17), (cxp + 72, ty - 17))
                for wx in range(int(cxp) + 5, int(cxp) + 68, 9):
                    scr.fill((255, 222, 150), (wx, ty - 13, 6, 6))
            glow(scr, tx - 2, ty - 9, 18, (120, 120, 100))
            if tx < -320:
                s.train, s.trainT = None, R(10, 18)
        scr.blit(L['haze'], (0, int(oy * .5)))
        scr.blit(L['near'], (-int(cam * .7), int(oy * .7)))

    def draw_rain(s, gys):
        for r in s.rain:
            r[1] += r[3] * s.dt
            r[0] -= r[3] * s.dt * .25
            if gys < H and r[1] > gys + random.random() * (H - gys):
                s.splash.append([r[0], r[1], .15])
                r[0], r[1] = R(0, W + 60), R(-20, 0)
            elif r[1] > H or r[0] < -10:
                r[0], r[1] = R(0, W + 60), R(-20, 0)
            pg.draw.line(scr, (120, 130, 200), (r[0], r[1]), (r[0] - r[2] * .25, r[1] + r[2]))
        for sp in s.splash:
            sp[2] -= s.dt
            scr.fill((160, 170, 230), (sp[0] - 1, sp[1] - 1, 1, 1))
            scr.fill((160, 170, 230), (sp[0] + 1, sp[1] - 1, 1, 1))
        s.splash = [sp for sp in s.splash if sp[2] > 0]

    def draw_torii(s, x, oy):
        red, rim = (150, 20, 30), (255, 120, 120)
        for px in (x - 22, x + 18):
            sil_poly(scr, [(px, GY + oy), (px + 4, GY + oy), (px + 4, GY - 70 + oy), (px, GY - 70 + oy)], red, rim)
        sil_poly(scr, [(x - 32, GY - 74 + oy), (x + 32, GY - 74 + oy), (x + 36, GY - 80 + oy), (x - 36, GY - 80 + oy)], (25, 5, 10), rim)
        sil_poly(scr, [(x - 28, GY - 62 + oy), (x + 28, GY - 62 + oy), (x + 28, GY - 59 + oy), (x - 28, GY - 59 + oy)], red, rim)

    @staticmethod
    def shinobi_mask(x, y, sc, glow_k):
        """The shinobi clan's neon mask emblem."""
        pts = [(x - 9 * sc, y - 5 * sc), (x + 9 * sc, y - 5 * sc), (x + 7 * sc, y + 5 * sc), (x, y + 8 * sc), (x - 7 * sc, y + 5 * sc)]
        glow(scr, x, y, int(26 * sc), qcol((90, 40, 160), glow_k))
        pg.draw.polygon(scr, (24, 28, 60), pts)
        pg.draw.polygon(scr, (190, 110, 255), pts, 1)
        for sg in (-1, 1):
            pg.draw.line(scr, (255, 230, 90), (x + sg * 2 * sc, y - 1 * sc), (x + sg * 6 * sc, y - 2 * sc), max(1, int(sc)))
        pg.draw.line(scr, (210, 30, 60), (x - 9 * sc, y - 5 * sc), (x - 13 * sc, y - 1 * sc), 1)

    def draw_door(s, d, cx, oy):
        """Start-of-district door: a red sliding door (district 1) or a neon shinobi gate. k: 0 open .. 1 shut."""
        x, gys, k = d['x'] - cx, GY + oy, d['k']
        if x < -60 or x > W + 60:
            return
        pg.draw.rect(scr, (8, 4, 10), (x - 16, gys - 62, 32, 62))                  # dark doorway
        if d['kind'] == 'red':
            for sg in (-1, 1):                                                    # two sliding panels
                px = x + sg * (8 + 16 * (1 - ease(k))) - 8
                pg.draw.rect(scr, (170, 24, 34), (px, gys - 60, 16, 60))
                for ly in range(gys - 54, gys - 4, 10):
                    pg.draw.line(scr, (60, 8, 12), (px + 1, ly), (px + 14, ly))
                pg.draw.line(scr, (60, 8, 12), (px + 8, gys - 60), (px + 8, gys))
                scr.fill((230, 190, 90), (px + (12 if sg < 0 else 2), gys - 32, 2, 4))
            for px in (x - 22, x + 16):                                           # posts + roof
                sil_poly(scr, [(px, gys), (px + 6, gys), (px + 6, gys - 66), (px, gys - 66)], (34, 10, 14), (255, 110, 110))
            sil_poly(scr, [(x - 30, gys - 66), (x + 30, gys - 66), (x + 34, gys - 74), (x - 34, gys - 74)], (24, 6, 10), (255, 110, 110))
            if 0 < k < 1:
                glow(scr, x, gys - 30, 30, (90, 20, 20))
        else:
            for px in (x - 22, x + 16):
                pg.draw.rect(scr, (40, 36, 62), (px, gys - 66, 6, 66))
                pg.draw.line(scr, (190, 110, 255), (px + 3, gys - 66), (px + 3, gys))
            pg.draw.rect(scr, (40, 36, 62), (x - 24, gys - 72, 48, 7))
            drop = 62 * ease(k)                                                   # neon bars slam down
            for i in range(5):
                bx = x - 13 + i * 6.5
                pg.draw.line(scr, (190, 110, 255), (bx, gys - 64), (bx, gys - 64 + drop), 2)
            if k > 0:
                glow(scr, x, gys - 64 + drop / 2, 34, qcol((70, 30, 120), min(1, k * 2)))
            if k >= 1:
                s.shinobi_mask(x, gys - 36, 1.1, .6 + math.sin(s.t * 3) * .3)

    def prompt(s, label, x, y):
        key = s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'use')
        txt = f"[{key}] {label}"
        w = F_S.size(txt)[0] + 10
        pg.draw.polygon(scr, INK, [(x - w / 2, y), (x + w / 2, y - 2), (x + w / 2 - 3, y + 12), (x - w / 2 - 3, y + 14)])
        text(txt, F_S, WHITE, x, y + 1, True)

    def draw_kiosk(s, x, gys):
        """The Shinobi Kiosk: a little neon booth that sells one buff per district."""
        if x < -60 or x > W + 60:
            return
        used = s.kiosk['used']
        pg.draw.rect(scr, (18, 10, 30), (x - 38, gys - 62, 76, 62))
        pg.draw.rect(scr, (28, 40, 72), (x - 33, gys - 56, 66, 28))                   # glass
        pg.draw.circle(scr, (24, 28, 60), (x, gys - 38), 8)                           # the vendor behind the glass
        pg.draw.rect(scr, (24, 28, 60), (x - 9, gys - 33, 18, 6))
        if not used:
            for sg in (-1, 1):
                scr.fill((255, 230, 90), (x + sg * 3 - 1, gys - 40, 2, 1))
            glow(scr, x, gys - 40, 8, (60, 50, 0))
        for i in range(5):                                                            # reflections on the glass
            gx = x - 30 + i * 15
            pg.draw.line(scr, (70, 90, 140), (gx, gys - 30), (gx + 10, gys - 54))
        pg.draw.rect(scr, (90, 50, 30), (x - 37, gys - 28, 74, 5))                     # counter
        for i in range(3):                                                            # posters (like the cards)
            px = x - 27 + i * 19
            pg.draw.rect(scr, (230, 226, 236), (px, gys - 20, 13, 16))
            pg.draw.rect(scr, RED if i == 1 else INK, (px + 3, gys - 18, 7, 5))
            for ly in (gys - 11, gys - 8):
                pg.draw.line(scr, INK, (px + 2, ly), (px + 10, ly))
        pg.draw.polygon(scr, (150, 20, 30), [(x - 44, gys - 64), (x + 44, gys - 68), (x + 40, gys - 58), (x - 40, gys - 56)])
        for sx in range(int(x) - 40, int(x) + 40, 10):
            pg.draw.line(scr, (230, 220, 230), (sx, gys - 64), (sx + 4, gys - 57), 2)
        col = (70, 80, 100) if used else (0, 230, 255)
        pg.draw.rect(scr, INK, (x - 36, gys - 86, 72, 15))
        pg.draw.rect(scr, col, (x - 36, gys - 86, 72, 15), 1)
        if not used:
            glow(scr, x, gys - 79, 40, (0, 50, 70), .4)
        text("SHINOBI KIOSK" if not used else "SOLD OUT", F_S, col, x, gys - 84, True)
        if not used and abs(s.pl.x + s.pl.w / 2 - s.kiosk['x']) < 28:
            s.prompt("OPEN KIOSK", x, gys - 104)

    def buff_icon(s, b, x, y, col):
        if b == 'vital':
            for sg in (-1, 1):
                pg.draw.circle(scr, col, (x + sg * 4, y - 2), 5)
            pg.draw.polygon(scr, col, [(x - 9, y), (x + 9, y), (x, y + 9)])
        elif b == 'edge':
            pg.draw.line(scr, col, (x - 9, y + 9), (x + 9, y - 9), 3)
            pg.draw.line(scr, RED, (x - 9, y + 9), (x - 5, y + 5), 3)
        elif b in ('swift', 'ghost'):
            for i in range(3):
                pg.draw.lines(scr, col, False, [(x - 9 + i * 6, y - 7), (x - 3 + i * 6, y), (x - 9 + i * 6, y + 7)], 2)
        elif b == 'magnet':
            pg.draw.arc(scr, col, (x - 8, y - 8, 16, 16), math.pi, math.tau, 4)
            pg.draw.line(scr, col, (x - 7, y), (x - 7, y - 8), 4)
            pg.draw.line(scr, col, (x + 6, y), (x + 6, y - 8), 4)
        elif b == 'vamp':
            pg.draw.circle(scr, col, (x, y + 3), 6)
            pg.draw.polygon(scr, col, [(x - 6, y + 2), (x + 6, y + 2), (x, y - 9)])
        elif b == 'storm':
            pg.draw.polygon(scr, col, [(x + 2, y - 10), (x - 6, y + 1), (x, y + 1), (x - 2, y + 10), (x + 6, y - 1), (x, y - 1)])
        elif b == 'iron':
            pg.draw.polygon(scr, col, [(x - 8, y - 8), (x + 8, y - 8), (x + 7, y + 2), (x, y + 9), (x - 7, y + 2)])
        elif b == 'greed':
            pg.draw.circle(scr, col, (x, y), 8)
            pg.draw.circle(scr, (255, 240, 160), (x - 2, y - 2), 3)
        else:                                                         # exit key
            pg.draw.circle(scr, col, (x - 4, y), 5, 2)
            pg.draw.line(scr, col, (x + 1, y), (x + 10, y), 2)
            pg.draw.line(scr, col, (x + 7, y), (x + 7, y + 4), 2)

    def draw_prop(s, kind, x, y, col):
        if kind == 'ac':
            pg.draw.rect(scr, (40, 32, 58), (x, y - 8, 12, 8))
            pg.draw.line(scr, (90, 80, 120), (x, y - 8), (x + 12, y - 8))
            pg.draw.circle(scr, (20, 16, 30), (x + 6, y - 4), 3)
            a = s.t * 12
            pg.draw.line(scr, (90, 80, 120), (x + 6 - math.cos(a) * 2, y - 4 - math.sin(a) * 2), (x + 6 + math.cos(a) * 2, y - 4 + math.sin(a) * 2))
        elif kind == 'tank':
            for lx in (x + 2, x + 11):
                pg.draw.line(scr, (30, 24, 44), (lx, y), (lx, y - 6))
            pg.draw.rect(scr, (46, 36, 64), (x, y - 20, 14, 14))
            pg.draw.ellipse(scr, (70, 58, 96), (x, y - 23, 14, 6))
            pg.draw.line(scr, (30, 24, 44), (x, y - 14), (x + 14, y - 14))
        elif kind == 'ant':
            pg.draw.line(scr, (40, 32, 58), (x + 3, y), (x + 3, y - 22))
            pg.draw.line(scr, (40, 32, 58), (x, y - 16), (x + 6, y - 16))
            if int(s.t * 1.5 + x) % 2:
                scr.fill((255, 40, 40), (x + 3, y - 23, 1, 2))
                glow(scr, x + 3, y - 22, 6, (90, 0, 0))
        elif kind == 'sakura':                                  # cherry tree swaying in the wind
            sw = math.sin(s.t * 1.3 + x * .1) * 1.5
            pg.draw.line(scr, (50, 26, 34), (x + 6, y), (x + 6 + sw * .4, y - 14), 3)
            pg.draw.line(scr, (50, 26, 34), (x + 6, y - 9), (x + 12 + sw * .6, y - 16), 2)
            glow(scr, x + 7 + sw, y - 20, 22, (60, 20, 40))
            for ox_, oy_, r in ((-5, -18, 6), (5, -21, 7), (0, -26, 6), (11, -17, 5), (-1, -14, 4)):
                pg.draw.circle(scr, (200, 90, 140), (x + 6 + ox_ + sw, y + oy_), r)
                pg.draw.circle(scr, (250, 160, 200), (x + 5 + ox_ + sw, y + oy_ - 2), max(1, r - 3))
        elif kind == 'shrine':                                  # tiny rooftop torii
            for px in (x + 1, x + 11):
                pg.draw.line(scr, (190, 30, 40), (px, y), (px, y - 12), 2)
            pg.draw.line(scr, (30, 8, 12), (x - 3, y - 13), (x + 15, y - 13), 2)
            pg.draw.line(scr, (190, 30, 40), (x - 1, y - 9), (x + 13, y - 9))
            glow(scr, x + 6, y - 4, 8, (70, 30, 10))
            scr.fill((255, 200, 120), (x + 5, y - 3, 2, 3))
        elif kind == 'board':                                   # big rooftop billboard with scrolling text
            for px in (x + 6, x + 34):
                pg.draw.line(scr, (30, 24, 44), (px, y), (px, y - 10), 2)
            pg.draw.rect(scr, (8, 4, 14), (x, y - 32, 42, 22))
            glow(scr, x + 21, y - 21, 30, tuple(c // 4 for c in col))
            pg.draw.rect(scr, col, (x, y - 32, 42, 22), 1)
            msg = F_JP.render("ネオン浪人 新宿 未来 ", False, col)
            off = int(s.t * 25 + x) % msg.get_width()
            scr.blit(msg, (x + 2, y - 28), (off, 0, 38, 14))
            if msg.get_width() - off < 38:
                scr.blit(msg, (x + 2 + msg.get_width() - off, y - 28), (0, 0, 38 - (msg.get_width() - off), 14))
        else:
            pg.draw.line(scr, (30, 24, 44), (x + 2, y), (x + 2, y - 8))
            pg.draw.line(scr, (30, 24, 44), (x + 16, y), (x + 16, y - 8))
            pg.draw.rect(scr, (10, 4, 16), (x, y - 20, 19, 12))
            if not (int(s.t * 7 + x) % 23 == 0):                # neon flicker
                pg.draw.rect(scr, col, (x, y - 20, 19, 12), 1)
                glow(scr, x + 9, y - 14, 14, tuple(c // 4 for c in col))
                scr.fill(col, (x + 4, y - 16, 11, 2))

    def draw_plat(s, p, cx, oy):
        x, y, w = p.x - cx, p.y + oy, p.w
        if x > W + 20 or x + w < -20 or y > H + 30 or y < -40:
            return
        if p.kind == 'static':
            for kind, rx, col in p.props:
                s.draw_prop(kind, x + rx, y, col)
            for sx in range(int(x) + 4, int(x + w) - 2, 18):
                pg.draw.line(scr, (24, 10, 34), (sx, y + 8), (sx, y + 16))
            pg.draw.rect(scr, (20, 8, 34), (x, y, w, 8))
            pg.draw.line(scr, (40, 20, 62), (x, y + 3), (x + w, y + 3))
            pg.draw.line(scr, (255, 40, 140), (x, y + 8), (x + w, y + 8))
            glow(scr, x + w / 2, y + 9, int(w / 2), (40, 6, 26), .2)
            pg.draw.line(scr, (0, 60, 80), (x, y - 1), (x + w, y - 1))
            pg.draw.line(scr, (0, 230, 255), (x, y), (x + w, y))
            if p.deco:
                ch, col = p.deco
                sx = x + w * .7
                pg.draw.line(scr, (24, 10, 34), (sx + 6, y + 8), (sx + 6, y + 12))
                pg.draw.rect(scr, (10, 3, 15), (sx, y + 12, 13, 15))
                pg.draw.rect(scr, col, (sx, y + 12, 13, 15), 1)
                scr.blit(F_JP.render(ch, False, col), (sx + 1, y + 13))
                glow(scr, sx + 6, y + 19, 14, tuple(c // 4 for c in col))
        elif p.kind == 'move':
            if p.axis == 'y':
                pg.draw.line(scr, (30, 22, 46), (x + w / 2, p.y0 - p.amp - 30 + oy), (x + w / 2, y))
            pg.draw.rect(scr, (40, 36, 62), (x, y, w, 6))
            pg.draw.line(scr, (120, 230, 255), (x, y), (x + w, y))
            for ex in (x + 6, x + w - 6):
                glow(scr, ex, y + 8, 9, (0, 80, 110), .6)
                if s.state == 'play' and random.random() < .3:
                    s.parts.append([ex + cx, y + 7 - oy, R(-10, 10), R(30, 60), .25, .25, (90, 220, 255), 1, 0, True])
            scr.fill((255, 60, 160) if int(s.t * 4) % 2 else (0, 230, 255), (x + w / 2 - 1, y + 2, 3, 2))
        else:                                                   # crumbling tiles
            if p.appear > 0 and int(s.t * 20) % 2:
                return
            jx = R(-1, 1) if p.crumbleT > 0 else 0
            pg.draw.rect(scr, (74, 48, 44), (x + jx, y, w, 6))
            pg.draw.line(scr, (140, 100, 80), (x + jx, y), (x + jx + w, y))
            for tx in range(int(x + jx) + 7, int(x + jx + w), 8):
                pg.draw.line(scr, (40, 24, 24), (tx, y + 1), (tx, y + 6))
            if p.crumbleT > 0 or not p.solid:
                pg.draw.lines(scr, (20, 10, 10), False, [(x + w * .3, y), (x + w * .4, y + 3), (x + w * .55, y + 2), (x + w * .6, y + 6)])

    def reflect(s, gys):
        """Wet-street reflection: mirror everything just above the ground, with ripples."""
        fh = H - gys
        if fh <= 0:
            return
        top = max(0, gys - fh)
        src = pg.transform.flip(scr.subsurface((0, top, W, gys - top)).copy(), False, True)
        src.fill((150, 130, 175), special_flags=pg.BLEND_RGB_MULT)
        scr.fill((6, 3, 12), (0, gys, W, fh))
        for y in range(min(fh, gys - top)):
            off = math.sin(y * .9 + s.t * 5) * (.5 + y * .04)
            scr.blit(src, (off, gys + y), (0, y, W, 1))
        scr.blit(s.L['floor'], (0, gys))

    def draw_coin(s, x, y, mythic, ph):
        sw = abs(math.cos(s.t * 4 + ph))
        if mythic:
            h = s.t * 220 + ph * 60
            glow(scr, x, y, 12, hue(int(h // 30) * 30, .45))
            pg.draw.ellipse(scr, hue(h), (x - max(1, sw * 4), y - 4, max(2, sw * 8), 8))
            pg.draw.ellipse(scr, (255, 255, 255), (x - max(1, sw * 1.5), y - 2, max(2, sw * 3), 3))
        else:
            glow(scr, x, y, 7, (50, 35, 5))
            pg.draw.ellipse(scr, (150, 95, 15), (x - max(1, sw * 3), y - 3, max(2, sw * 6), 6))
            pg.draw.ellipse(scr, (255, 205, 50), (x - max(1, sw * 2), y - 2, max(2, sw * 4), 4))

    def draw_world(s, overlay=True):
        sh = s.shake if s.settings['shake'] else 0
        ox = int(R(-sh, sh)) if sh > 0 else 0
        oy = (int(R(-sh, sh)) if sh > 0 else 0) - int(s.camy)
        cx = int(s.cam) - ox
        gys = GY + oy
        s.draw_bg(cx, oy)
        for lx in s.lamps:                              # tall street lamps (pole silhouettes)
            x = lx - cx
            if -60 < x < W + 60:
                sil_poly(scr, [(x - 1, gys), (x + 2, gys), (x + 2, gys - 100), (x - 1, gys - 100)], (10, 4, 16), (90, 50, 60))
                pg.draw.line(scr, (10, 4, 16), (x, gys - 100), (x + 12, gys - 102), 2)
                pg.draw.rect(scr, (255, 210, 140), (x + 8, gys - 101, 8, 10))
                pg.draw.rect(scr, (90, 30, 20), (x + 8, gys - 101, 8, 10), 1)
        for tx, tw, ttop, wins, col in s.towers:        # skyscraper bodies behind their zig-zag floors
            x, y = tx - cx, ttop + oy
            if -tw < x < W:
                pg.draw.rect(scr, (15, 7, 28), (x, y, tw, gys - y))
                pg.draw.line(scr, (80, 40, 110), (x, y), (x, gys))
                pg.draw.line(scr, (80, 40, 110), (x + tw - 1, y), (x + tw - 1, gys))
                pg.draw.line(scr, col, (x, y), (x + tw, y))
                for wx, wy, wc in wins:
                    scr.fill(wc, (x + wx, y + wy, 3, 4))
        for sx0, sx1, stop in s.scaffolds:              # scaffolding poles and cross braces
            for px in range(int(sx0), int(sx1) + 1, 29):
                x = px - cx
                if -10 < x < W + 10:
                    pg.draw.line(scr, (52, 40, 70), (x, stop + oy), (x, gys), 2)
                    for py in range(int(stop), GY, 27):
                        pg.draw.line(scr, (34, 26, 48), (x, py + oy), (x + 29, py + 27 + oy))
        for p in s.plats[1:]:                           # building facades below the low rooftops
            if p.win:
                x, y = p.x - cx, p.y + oy
                if -p.w < x < W:
                    pg.draw.rect(scr, (17, 8, 30), (x + 3, y + 8, p.w - 6, gys - y - 8))
                    pg.draw.line(scr, (70, 36, 100), (x + 3, y + 8), (x + 3, gys))
                    pg.draw.line(scr, (70, 36, 100), (x + p.w - 4, y + 8), (x + p.w - 4, gys))
                    for wx, wy, col in p.win:
                        scr.fill(tuple(c // 2 for c in col), (x + wx, y + wy, 4, 4))
        s.draw_door(s.door, cx, oy)
        s.draw_torii(END_X - cx, oy)
        if END_X - cx < W + 40:                         # exit sign above the torii
            a = .6 + math.sin(s.t * 4) * .4
            outlined("出口  EXIT >>", F_JP, qcol((255, 140, 160), a), END_X - cx, gys - 98, center=True, r=1)
        if s.kiosk:
            s.draw_kiosk(s.kiosk['x'] - cx, gys)
        if s.keydoor:
            s.draw_door({'x': s.keydoor['x'], 'k': 1 - s.keydoor['k'], 'kind': 'red', 'closing': True}, cx, oy)
            if s.keydoor['k'] >= 1 and abs(s.pl.x - s.keydoor['x']) < 40:
                s.prompt("LEAVE", s.keydoor['x'] - cx, gys - 84)
        for vx in s.vents:
            x = vx - cx
            if -10 < x < W + 10:
                pg.draw.rect(scr, (30, 24, 40), (x - 6, gys - 2, 12, 2))
        for pad in s.pads:                              # neon jump pads
            x, y = pad[0] - cx, pad[1].y + oy
            if -20 < x < W + 20:
                sq = pad[2] / .3
                pg.draw.rect(scr, (40, 36, 62), (x - 9, y - 3 + sq * 2, 18, 3))
                glow(scr, x, y - 6, 16, (0, 70, 90))
                for i in range(2):
                    yy = y - 6 - i * 5 - (s.t * 14) % 5
                    pg.draw.lines(scr, (0, 230, 255), False, [(x - 5, yy + 3), (x, yy), (x + 5, yy + 3)])
        for e in s.en:                                  # enemies climbing/dropping behind the rooftops
            if e.trav:
                s.draw_enemy(e, cx, oy)
        for p in s.plats[1:]:
            s.draw_plat(p, cx, oy)
        for x1, y1, x2, y2, sag, n in s.strings:        # paper lantern strings between rooftops
            if x2 - cx < -20 or x1 - cx > W + 20:
                continue
            pts = [(lerp(x1, x2, k / 12) - cx, lerp(y1, y2, k / 12) + math.sin(k / 12 * math.pi) * sag + oy) for k in range(13)]
            pg.draw.lines(scr, (30, 20, 40), False, pts, 1)
            for i in range(1, n + 1):
                lx, ly = pts[int(i * 12 / (n + 1))]
                sway = math.sin(s.t * 2 + i) * 1
                pg.draw.ellipse(scr, (230, 50, 50), (lx - 3 + sway, ly + 2, 6, 7))
                scr.fill((255, 200, 120), (lx - 1 + sway, ly + 4, 2, 3))
                glow(scr, lx + sway, ly + 5, 10, (70, 14, 10))
        for c in s.coins:
            x = c[0] - cx
            if -12 < x < W + 12:
                y = c[1] + math.sin(s.t * 3 + c[3]) * 2 + oy
                s.draw_coin(x, y, c[2], c[3])
                if c[2] and random.random() < .08:
                    s.burst(c[0] + R(-4, 4), c[1] + R(-4, 4), 1, hue(s.t * 220), spd=10, life=(.3, .6), grav=-20, glowing=True)
        for l in s.loot:
            x, y = l[0] - cx, l[1] + oy
            if l[5] > .55:
                glow(scr, x, y, 10, (60, 45, 10))
            s.draw_coin(x, y, l[4], l[5] * 3)
        for gb in s.gibs:
            s.draw_gib(gb, cx, oy)
        for e in s.en:
            if not e.trav:
                s.draw_enemy(e, cx, oy)
        s.draw_ghosts(cx, oy)
        if s.superT < 0:
            s.draw_player(cx, oy)
            s.draw_trail(cx, oy)
        for pr in s.proj:                               # shuriken
            x, y = pr[0] - cx, pr[1] + oy
            glow(scr, x, y, 7, (40, 60, 70) if pr[4] else (50, 40, 40))
            star(x, y, 4, s.t * 25, (120, 255, 255) if pr[4] else (230, 230, 240))
        p = s.pl
        for f in s.fx:
            kind, x, y, d, life, ml, extra = f
            k = life / ml
            if kind == 'thrust':                        # combo finisher: a long piercing streak
                if k < .65:
                    x, y = p.x + p.w / 2 - cx, p.y + p.h * .45 + oy
                    pg.draw.line(scr, (255, 255, 255), (x, y), (x + d * 52 * (1 - k * .3), y), max(1, int(k * 3)))
                    pg.draw.line(scr, s.pal()['rim'], (x, y + 2), (x + d * 44, y + 2), 1)
                    glow(scr, x + d * 34, y, 16, qcol((30, 44, 66), k))
                continue
            x, y = x - cx, y + oy
            if kind == 'clang':                         # parry flash: white star burst
                r = 6 + (1 - k) * 22
                for i in range(8):
                    a = extra + i * math.pi / 4
                    rr = r * (1 if i % 2 else .55)
                    pg.draw.line(scr, (255, 255, 240), (x, y), (x + math.cos(a) * rr, y + math.sin(a) * rr), 2 if k > .4 else 1)
                glow(scr, x, y, 30, qcol((200, 180, 120), k))
                pg.draw.circle(scr, WHITE, (x, y), max(1, 6 * k))
                continue
            if kind == 'super':                         # the super's giant crescent cut
                acc = s.pal()['rim']
                r = 50 + (1 - k) * 30
                c = 0 if d > 0 else math.pi
                glow(scr, x + d * 50, y, 60, qcol(tuple(v // 2 for v in acc), k))
                for i, (col, w_) in enumerate(((acc, 9), (WHITE, 4))):
                    arc(col, x, y, r - i * 4, c, 1.25, max(1, int(w_ * k)))
                pg.draw.line(scr, WHITE, (x, y), (x + d * 112 * min(1, (1 - k) * 4), y), max(1, int(5 * k)))
                continue
            if kind == 'cut':
                pg.draw.line(scr, (255, 255, 255), (x - 16, y + 7 * d), (x + 16, y - 7 * d), max(1, int(k * 3)))
                glow(scr, x, y, 20, qcol((80, 60, 70), k))
            elif kind == 'spark':                       # hit spark
                r = 4 + (1 - k) * 8
                for i in range(4):
                    a = extra + i * math.pi / 2
                    pg.draw.line(scr, (255, 250, 220), (x, y), (x + math.cos(a) * r, y + math.sin(a) * r), 2 if k > .5 else 1)
                glow(scr, x, y, 14, qcol((120, 100, 60), k))
            elif kind == 'boom':
                r = 4 + (1 - k) * 26
                glow(scr, x, y, 34, qcol((150, 100, 50), k))
                pg.draw.circle(scr, (255, 230, 170), (x, y), r, max(1, int(k * 4)))
                if k > .7:
                    pg.draw.circle(scr, (255, 255, 255), (x, y), 8 * (k - .5))
            elif kind == 'wave':
                rx = 6 + (1 - k) * 76
                pg.draw.ellipse(scr, (150, 220, 255), (x - rx, y - rx * .2, rx * 2, rx * .4), max(1, int(k * 3)))
                glow(scr, x, y - 4, 40, qcol((40, 70, 100), k), .5)
        for q in s.parts:
            x, y = q[0] - cx, q[1] + oy
            if q[9] == 2:                               # smoke puff
                k = q[4] / q[5]
                r = max(1, int(q[7] * (1.6 - k)))
                img = smoke_img(r, int(k * 6) * 25 + 20, q[6])
                scr.blit(img, (x - r - 1, y - r - 1))
                continue
            if q[9]:
                glow(scr, x, y, 4, tuple(c // 3 for c in q[6]))
            scr.fill(q[6], (x, y, q[7], q[7]))
        for lx in s.lamps:                              # lamp light falls on everything in front
            x = lx - cx
            if -60 < x < W + 60:
                scr.blit(s.L['cone'], (x + 12 - 45, gys - 92), special_flags=pg.BLEND_RGB_ADD)
                glow(scr, x + 12, gys - 96, 46, (80, 50, 25))
        s.reflect(gys)
        if gys < H:
            for lx in s.lamps:                          # light pools on the wet street
                x = lx - cx
                if -60 < x < W + 60:
                    glow(scr, x + 12, gys + 6, 50, (60, 40, 20), .22)
            for gx in range(-60, W + 60, 30):          # 2.5D perspective grid on the street
                wx = gx - (cx % 30)
                pg.draw.line(scr, (22, 10, 34), (wx, gys + 1), (W / 2 + (wx - W / 2) * 1.8, gys + FLOOR))
            for yy in (6, 14, 26, 42):
                pg.draw.line(scr, (18, 8, 28), (0, gys + yy), (W, gys + yy))
            pg.draw.line(scr, (255, 60, 160), (0, gys), (W, gys))
            glow(scr, W / 2, gys + 1, 240, (30, 8, 26), .03)
        s.draw_rain(gys)
        scr.blit(s.L['fg'], (-int(cx * 1.25), int(oy * 1.25)))
        if s.superT >= 0:                               # super: the world goes dark, only you and the blade glow
            k = s.super_k()
            fade = min(1, s.superT * 8) if s.superT < SUPER_CUT else (1 if k < .7 else max(0, (1 - k) / .3))
            s.dark.set_alpha(int(190 * fade))
            scr.blit(s.dark, (0, 0))
            s.draw_player(cx, oy)
            s.draw_trail(cx, oy)
            if s.superT < SUPER_CUT and s.tip_scr:     # the glint running up to the tip of the raised blade
                gk = min(1, s.superT / SUPER_CUT * 1.4)
                hx, hy = s.hand_scr
                gx, gy = lerp(hx, s.tip_scr[0], gk), lerp(hy, s.tip_scr[1], gk)
                glow(scr, gx, gy, 12, (110, 90, 20))
                four_star(scr, gx, gy, 5, (255, 214, 70))
                four_star(scr, gx, gy, 2, WHITE)
            for f in s.fx:
                if f[0] == 'super':
                    kk = f[4] / f[5]
                    x, y, d = f[1] - cx, f[2] + oy, f[3]
                    acc = s.pal()['rim']
                    glow(scr, x + d * 50, y, 60, qcol(tuple(v // 2 for v in acc), kk))
                    for i, (col, w_) in enumerate(((acc, 9), (WHITE, 4))):
                        arc(col, x, y, 50 + (1 - kk) * 30 - i * 4, 0 if d > 0 else math.pi, 1.25, max(1, int(w_ * kk)))
        if s.flash > 0:
            s.red.set_alpha(int(s.flash * 600))
            scr.blit(s.red, (0, 0))
        if s.pflash > 0:                                # parry: brief white flash
            s.black.fill(WHITE)
            s.black.set_alpha(int(s.pflash / .12 * 70))
            scr.blit(s.black, (0, 0))
            s.black.fill((0, 0, 0))
        if overlay and s.settings['crt']:
            scr.blit(s.L['over'], (0, 0))

    # ---------- anime camera
    def camera(s):
        """Where the camera looks and how close/tilted it is: (zoom, focus x, focus y, tilt in degrees)."""
        p = s.pl
        fx, fy = p.x + p.w / 2 - s.cam, p.y + p.h / 2 - s.camy
        z, tilt = 1 + .16 * ease(s.punch), s.tilt
        if 0 <= s.superT < SUPER_CUT:                  # super: dive in close and tilt onto the raised blade
            k = ease(s.superT / (SUPER_CUT * .55))
            z, tilt, fy = lerp(1, 2.7, k), lerp(0, -9, k), fy - 8 * k
        elif s.superT >= 0:                            # ...then snap back out for the cut
            k = ease(min(1, s.super_k() / .3))
            z, tilt = max(z, lerp(1.5, 1, k)), lerp(-9, 0, k)
        if s.state == 'play' and s.enter_cam > 0:      # district start: begin close, pull back as you walk in
            k = ease(s.enter_cam / 1.6)
            z, fy = max(z, 1 + 1.2 * k), fy - 6 * k
        return z, fx, fy, tilt

    def hud(s):
        for i in range(s.pl.maxhp):
            x, y = 14 + i * 13, 13
            pts = [(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]
            pg.draw.polygon(scr, INK, [(a + 1, b + 1) for a, b in pts])
            pg.draw.polygon(scr, RED if i < s.pl.hp else (60, 24, 40), pts)
            if i < s.pl.hp:
                scr.fill(WHITE, (x - 1, y - 3, 2, 2))
        dc = max(0, s.pl.dcd) / .5
        pg.draw.rect(scr, INK, (8, 22, 62, 4))
        pg.draw.rect(scr, (0, 230, 255), (9, 23, 60 * (1 - dc), 2))
        need = s.super_need()                              # super meter: fills with kills
        full = s.superk >= need
        acc = s.pal()['rim']
        pg.draw.polygon(scr, INK, [(8, 29), (88, 29), (85, 37), (5, 37)])
        pg.draw.rect(scr, acc if full and int(s.t * 6) % 2 else (150, 90, 230), (9, 31, 76 * min(1, s.superk / need), 4))
        if full:
            glow(scr, 48, 33, 30, qcol(tuple(c // 3 for c in acc), .8), .4)
            outlined(f"SUPER [{s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'super')}]", F_S, WHITE, 92, 28, r=1)
        for i, (b, n) in enumerate(sorted(s.buffs.items())):    # active buffs
            col = BUFFS[b][2] if b in BUFFS else RED
            pg.draw.rect(scr, INK, (8 + i * 22, 42, 20, 20))
            pg.draw.rect(scr, col, (8 + i * 22, 42, 20, 20), 1)
            s.buff_icon(b, 18 + i * 22, 52, col)
            if n > 1:
                text(str(n), F_S, WHITE, 22 + i * 22, 52)
        outlined(f"DISTRICT {s.lvl}/{LEVELS}", F_PS, WHITE, W // 2, 4, center=True, r=1)
        pop = s.coinpop / .25                              # Persona-style coin tag
        pg.draw.polygon(scr, INK, [(W - 118, 4), (W - 6, 2), (W - 12, 26), (W - 124, 28)])
        pg.draw.polygon(scr, RED, [(W - 118, 4), (W - 108, 4), (W - 114, 28), (W - 124, 28)])
        glow(scr, W - 96, 15, 10 + int(pop * 6), (60, 45, 10))
        pg.draw.ellipse(scr, (255, 205, 50), (W - 100, 11, 8, 8))
        img = F_PM.render(str(s.score), False, (255, 230, 120) if pop > 0 else WHITE)
        if pop > 0:
            img = pg.transform.scale_by(img, 1 + pop * .3)
        scr.blit(img, (W - 86, 15 - img.get_height() // 2))
        text(f"KILLS {s.kills}", F_S, (255, 120, 140), W - 112, 31)
        text(fmt_time(s.gtime), F_S, (200, 190, 230), W - 52, 31)
        if s.gtime < 10 and s.lvl == 1 and not TOUCH:
            pg.draw.polygon(scr, INK, [(10, H - 20), (W - 6, H - 22), (W - 12, H - 6), (4, H - 4)])
            text(s.hint(), F_S, WHITE, W // 2, H - 17, True)

    def hint(s):
        """Short control reminder built from the current bindings."""
        kind = 'pad' if s.last_input == 'pad' else 'kb'
        n = lambda a: s.bind_name(kind, a)
        if kind == 'pad':
            return f"{n('jump')} jump  DOWN+{n('jump')} slam  {n('atk')} slash  {n('parry')} parry  {n('dash')} dash  {n('crouch')} slide"
        return (f"{n('jump')} jump  {n('down')}+{n('jump')} slam  {n('atk')} slash  {n('parry')} parry  "
                f"{n('dash')} dash  {n('crouch')} slide")

    # ---------- Persona-style UI
    def nav(s, n):
        if 'up' in s.act:
            s.sel, s.selT = (s.sel - 1) % n, s.t
            sfx('sel')
        if 'down' in s.act:
            s.sel, s.selT = (s.sel + 1) % n, s.t
            sfx('sel')

    def p_items(s, items, x0, y0, dx=18, dy=36, font=None, wipe=True):
        font = font or F_P
        n = len(items)
        s.sel %= n
        s.nav(n)
        mx, my = pg.mouse.get_pos()
        el = s.t - s.state_t
        fire = -1
        for i, (lab, _) in enumerate(items):
            slide = (1 - ease((el - .05 - i * .07) * 4)) * -260          # items fly in from the left
            x, y = x0 + i * dx + slide, y0 + i * dy
            on = i == s.sel
            w, h = font.size(lab)
            r = pg.Rect(x - 8, y - 2, w + 16, h + 2)
            if r.collidepoint(mx, my):
                if s.moved and not on:
                    s.sel, s.selT = i, s.t
                    sfx('sel')
                if s.click:
                    fire = i
            if on:
                pop = 1 + .35 * (1 - ease((s.t - s.selT) * 7))
                j = math.sin(s.t * 9) * 1.5
                jag = [(r.left - 8, r.bottom + 3 + j), (r.left + 6, r.top - 5), (r.right + 16, r.top - 2 - j), (r.right + 6, r.bottom + 6)]
                pg.draw.polygon(scr, RED, [(a + 7, b + 5) for a, b in jag])
                pg.draw.polygon(scr, WHITE, jag)
                pg.draw.polygon(scr, WHITE, [(r.right + 12, r.centery - 2), (r.right + 34, r.centery - 10 + j), (r.right + 16, r.centery + 5)])
                pg.draw.polygon(scr, INK, [(r.left - 18, r.centery + 2), (r.left - 6, r.centery - 6), (r.left - 4, r.centery + 6)])
                img = pg.transform.rotate(pg.transform.scale_by(font.render(lab, False, INK), pop), -4)
                scr.blit(img, (r.centerx - img.get_width() // 2, r.centery - img.get_height() // 2))
            else:
                outlined(lab, font, WHITE, x, y - 1)
        if 'ok' in s.act:
            fire = s.sel
        if fire >= 0:
            sfx('sel')
            fn = items[fire][1]
            if wipe:
                s.wipe_to(fn)
            else:
                fn()

    def portrait(s, P, scale, skin=None, chains=None, crop=(20, 30, 58, 58), want_info=False):
        """Big outlined portrait of the hero's sprite in a skin (menu / stats / shop)."""
        S = s.pal(skin)
        D = s.spr
        D.fill((0, 0, 0, 0))
        info = paint(D, 48, 84, 1, P, S, s.t, chains or s.port_chains, (0, 0))
        m = pg.mask.from_surface(D)
        out = pg.Surface((96, 96), pg.SRCALPHA)
        wht = m.to_surface(setcolor=WHITE + (255,), unsetcolor=(0, 0, 0, 0))
        for ddx in (-2, -1, 0, 1, 2):
            for ddy in (-2, -1, 0, 1, 2):
                if abs(ddx) + abs(ddy) >= 2:
                    out.blit(wht, (ddx, ddy))
        s.compose(m, D, 0, 0, S, target=out)
        img = pg.transform.scale_by(out.subsurface(crop), scale)
        return (img, info) if want_info else img

    def side_card(s, scale, flip=True):
        """The samurai as in the skin cards (side view, hood down), idling with the odd slash. flip: face left."""
        P = pose_idle(s.t)
        if int(s.t / 3) % 2 and (s.t % 3) < .5:
            P = with_attack(P, 'side', (s.t % 3) / .3)
        P['hood'] = 0.0
        img = s.portrait(P, scale)
        return pg.transform.flip(img, True, False) if flip else img

    def hero_card(s, crop, scale, flip=False):
        """The samurai turned a little toward us, idling with the blade held up beside his face (menu / stats)."""
        b = math.sin(s.t * 2.2)                                    # idle breathing
        P = dict(POSE_PORTRAIT, lean=b * .02, sword=-1.5 + b * .025,
                 arms=[(.35, .9 + b * .05), (2.05 + b * .03, 2.85 + b * .03)])
        img, info = s.portrait(P, scale, crop=crop, want_info=True)
        card = pg.Surface(img.get_size(), pg.SRCALPHA)
        card.blit(img, (0, 0))
        s.reflect_blade(info, crop, scale, 0, 0, card)
        return pg.transform.flip(card, True, False) if flip else card

    def reflect_blade(s, info, crop, scale, ix, iy, T=None):
        """Repaint the katana in a portrait: a wide steel blade with the neon city sliding across it, smoothly."""
        T = T or scr
        if not info['tip']:
            return
        mp = lambda p: (ix + (p[0] - crop[0]) * scale, iy + (p[1] - crop[1]) * scale)
        (hx, hy), (tx, ty) = mp(info['hand']), mp(info['tip'])
        L = math.hypot(tx - hx, ty - hy) or 1
        ux, uy = (tx - hx) / L, (ty - hy) / L
        nx, ny = -uy, ux
        w = scale * 1.5
        mid, sky = s.L['mid'], s.L['sky']
        col0 = int(s.t * 14) % (mid.get_width() - 4)
        cur = None
        for i in range(int(L)):
            sy = int(GY - 165 + i / L * 160)
            c = mid.get_at((col0 + i % 3, max(0, min(H - 1, sy))))
            if c.a < 128:
                c = sky.get_at((col0 % W, max(0, min(H - 1, sy - 40))))
            new = (min(255, c.r * 1.4 + 40), min(255, c.g * 1.4 + 40), min(255, c.b * 1.4 + 55))
            cur = new if cur is None else tuple(cur[j] * .82 + new[j] * .18 for j in range(3))   # smooth it out
            x, y = hx + ux * i, hy + uy * i
            pg.draw.line(T, cur, (x - nx * w / 2, y - ny * w / 2), (x + nx * w / 2, y + ny * w / 2), 2)
        pg.draw.line(T, (250, 252, 255), (hx + nx * w / 2, hy + ny * w / 2), (tx + nx * w / 2, ty + ny * w / 2), 1)
        pg.draw.line(T, (50, 50, 70), (hx - nx * w / 2, hy - ny * w / 2), (tx - nx * w / 2, ty - ny * w / 2), 1)
        pg.draw.polygon(T, (250, 252, 255), [(tx - nx * w / 2, ty - ny * w / 2), (tx + nx * w / 2, ty + ny * w / 2),
                                                (tx + ux * w * 1.4, ty + uy * w * 1.4)])

    def p_bar(s, x, y, w, label, val, accent):
        pg.draw.polygon(scr, INK, [(x, y), (x + w, y - 2), (x + w - 6, y + 15), (x - 6, y + 17)])
        pg.draw.polygon(scr, accent, [(x, y), (x + 5, y), (x - 1, y + 17), (x - 6, y + 17)])
        text(label, F_S, WHITE, x + 8, y + 3)
        img = F_PS.render(val, False, INK)
        tw = img.get_width() + 12
        pg.draw.polygon(scr, WHITE, [(x + w - tw - 4, y - 1), (x + w + 2, y - 3), (x + w - 3, y + 16), (x + w - tw - 9, y + 18)])
        scr.blit(img, (x + w - tw + 1, y))

    def persona_bg(s, tint=True):
        s.cam = (s.t * 15) % (LW - W)
        s.draw_bg(s.cam, 0)
        s.reflect(GY)
        s.draw_rain(GY)
        scr.blit(s.menu_dim, (0, 0))
        if tint:
            sl = int(math.sin(s.t * .8) * 6)
            scr.blit(s.L['p_red'], (sl, 0))
            star(30 + sl, 240, 10, s.t, INK)
            star(268, 22, 7, -s.t * 1.3, WHITE)
        if s.settings['crt']:
            scr.blit(s.L['over'], (0, 0))

    def quit(s):
        if s.state in ('play', 'pause'):
            s.end_run('abandon')
        pg.quit()
        sys.exit()

    def to_menu(s):
        if s.state == 'pause':
            s.end_run('abandon')
        s.go('menu', 0)

    def restart(s):
        if s.state == 'pause':
            s.end_run('abandon')
        s.new_run()
        s.fade = 0

    # ---------- states
    def st_menu(s, dt):
        s.persona_bg()
        el = s.t - s.state_t
        cut = ease(el * 3)                                   # hero portrait slides in from the right
        sx_ = (1 - cut) * 220                                 # the hero's sprite, big, on the right
        img = s.side_card(3.6)                                   # the samurai like in the skin cards, mirrored
        pg.draw.polygon(scr, INK, [(W - 190 + sx_, 40), (W, 22), (W, H), (W - 230 + sx_, H)])
        pg.draw.polygon(scr, RED, [(W - 200 + sx_, 40), (W - 190 + sx_, 40), (W - 230 + sx_, H), (W - 240 + sx_, H)])
        scr.blit(img, (W - 236 + sx_, H - img.get_height() + 6))
        ransom("NEON", 22, 34, [F_PB, F_P], 7, s.t, tilt=-7)
        ransom("RONIN", 70, 76, [F_PB, F_P], 19, s.t, tilt=-7)
        pg.draw.polygon(scr, INK, [(150, 96), (236, 92), (232, 110), (146, 113)])
        scr.blit(F_JPB.render("ネオン浪人", False, WHITE), (156, 93))
        s.p_items([("START", s.new_run), ("STATS", lambda: s.go('stats', 0)),
                   ("SETTINGS", lambda: s.go('settings', 0)), ("QUIT", s.quit)], 36, 124, dx=14, dy=31)
        pg.draw.polygon(scr, INK, [(0, H - 14), (W, H - 18), (W, H), (0, H)])
        text(MENU_HINT[s.last_input == 'pad'], F_S, (220, 210, 240), W // 2, H - 13, True)

    SETTING_ROWS = [('SOUND', 'MASTER VOLUME', 'master', 'slider'), ('', 'MUSIC', 'music', 'slider'),
                    ('', 'EFFECTS', 'sfx', 'slider'), ('VIDEO', 'FULLSCREEN', 'fullscreen', 'toggle'),
                    ('', 'SCREEN SHAKE', 'shake', 'toggle'), ('', 'RAIN', 'rain', 'rain'),
                    ('', 'CRT FILTER', 'crt', 'toggle'), ('INPUT', 'GAMEPAD VIBRATION', 'rumble', 'toggle'),
                    ('', 'CONTROLS', None, 'open')] + ([('', 'TOUCH LAYOUT', None, 'touch')] if TOUCH else []) + \
                   [('', 'BACK', None, 'back')]

    def row_text(s, txt, selected, x, y):
        if selected:                                    # black on the white highlight
            scr.blit(F_S.render(txt, False, INK), (x, y))
        else:
            text(txt, F_S, WHITE, x, y)

    def change_setting(s, row, delta, mx=None):
        _, _, key, kind = row
        st = s.settings
        if kind == 'slider':
            st[key] = round(max(0, min(1, (mx if mx is not None else st[key] + delta * .1))), 2)
        elif kind == 'toggle':
            st[key] = not st[key]
        elif kind == 'rain':
            st[key] = (st[key] + (delta or 1)) % len(RAIN_LEVELS)
        elif kind == 'open':
            s.wipe_to(lambda: s.go('controls', 0))
            return
        elif kind == 'touch':                                   # move / resize the on-screen buttons
            s.tedit_sel = None
            s.wipe_to(lambda: s.go('touchedit', 0))
            return
        else:
            s.wipe_to(lambda: s.go('menu', 0))
            return
        s.apply_settings()
        s.save_settings()
        sfx('sel')
        if key == 'rumble' and st[key]:
            s.rumble(.6, .6, 200)

    def st_settings(s, dt):
        s.persona_bg()
        el = s.t - s.state_t
        ransom("SETTINGS", 20, 26, [F_PB, F_P], 29, s.t, tilt=-6)
        rows = s.SETTING_ROWS
        s.nav(len(rows))
        row = rows[s.sel]
        if 'left' in s.act or 'right' in s.act:
            if row[3] in ('slider', 'toggle', 'rain'):
                s.change_setting(row, 1 if 'right' in s.act else -1)
        if 'ok' in s.act:
            s.change_setting(row, 1)
        if 'back' in s.act:
            s.wipe_to(lambda: s.go('menu', 0))
        mx, my = pg.mouse.get_pos()
        for i, (sec, lab, key, kind) in enumerate(rows):
            a = ease((el - .05 - i * .04) * 4)
            x, y, w = 120 + int((1 - a) * 380) - i * 2, 54 + i * 19, 330
            on = i == s.sel
            r = pg.Rect(x - 6, y - 1, w, 17)
            vx = x + 170                                        # value area
            if r.collidepoint(mx, my):
                if s.moved and not on:
                    s.sel, s.selT = i, s.t
                    sfx('sel')
                if s.click:
                    s.sel = i
                    if kind == 'slider' and mx >= vx:
                        s.change_setting(rows[i], 0, (mx - vx) / 120)
                    else:
                        s.change_setting(rows[i], 1)
            if sec:
                tag = [(14, y - 1), (96, y - 3), (92, y + 15), (10, y + 17)]
                pg.draw.polygon(scr, RED, tag)
                outlined(sec, F_PS, WHITE, 20, y - 1, r=1)
            bar = [(x, y), (x + w, y - 2), (x + w - 6, y + 15), (x - 6, y + 17)]
            pg.draw.polygon(scr, INK, bar)
            if on:
                j = math.sin(s.t * 9)
                pg.draw.polygon(scr, RED, [(x + 4, y + 4), (x + w + 4, y + 1 + j), (x + w - 2, y + 19), (x - 2, y + 21)])
                pg.draw.polygon(scr, WHITE, bar)
            label = s.row_text
            label(lab, on, x + 8, y + 3)
            if kind == 'slider':
                v = s.settings[key]
                for b in range(10):
                    filled = b < round(v * 10)
                    scr.fill((RED if on else (0, 200, 230)) if filled else ((60, 50, 70) if not on else (190, 180, 200)),
                             (vx + b * 12, y + 4, 10, 9))
                label(f"{int(v * 100)}%", on, vx + 124, y + 3)
            elif kind in ('toggle', 'rain'):
                val = RAIN_LEVELS[s.settings[key]][0] if kind == 'rain' else ("ON" if s.settings[key] else "OFF")
                img = F_PS.render(val, False, WHITE)
                tw = img.get_width() + 14
                tx = vx + 60 - tw // 2
                pg.draw.polygon(scr, RED if (kind == 'rain' or s.settings[key]) else (70, 60, 80),
                                [(tx, y), (tx + tw, y - 1), (tx + tw - 4, y + 16), (tx - 4, y + 17)])
                scr.blit(img, (tx + 7, y - 1))
                if on:
                    scr.blit(F_PS.render("<", False, INK), (tx - 16, y - 1))
                    scr.blit(F_PS.render(">", False, INK), (tx + tw + 4, y - 1))
            elif kind in ('open', 'touch'):
                scr.blit(F_PS.render(">>", False, INK if on else WHITE), (vx + 100, y - 1))
        pg.draw.polygon(scr, INK, [(0, H - 14), (W, H - 18), (W, H), (0, H)])
        text("UP/DOWN select   LEFT/RIGHT change   ENTER / A confirm   ESC / B back", F_S, (220, 210, 240), W // 2, H - 13, True)

    def st_controls(s, dt):
        """Rebind every action, for keyboard and for the Xbox pad."""
        s.persona_bg()
        el = s.t - s.state_t
        ransom("CONTROLS", 16, 22, [F_PB, F_P], 31, s.t, tilt=-6)
        names = [j.get_name() for j in s.joys.values()]
        status = ("PAD: " + names[0][:22]) if names else "NO CONTROLLER CONNECTED"
        pg.draw.polygon(scr, (0, 200, 230) if names else (70, 60, 80), [(250, 10), (W - 8, 6), (W - 14, 22), (244, 26)])
        text(status, F_S, INK if names else WHITE, 258, 11)
        rows = BIND_ACTIONS + [('reset', "RESET TO DEFAULTS"), ('back', "BACK")]
        n = len(rows)
        if not s.capture:
            s.nav(n)
            if s.act & {'left', 'right'}:
                s.col = 1 - s.col
                sfx('sel')
        for c, (title, x) in enumerate((("KEYBOARD / MOUSE", 186), ("XBOX CONTROLLER", 330))):
            pg.draw.polygon(scr, RED if c == s.col else INK, [(x - 4, 32), (x + 132, 30), (x + 128, 44), (x - 8, 46)])
            outlined(title, F_PS, WHITE, x + 2, 30, r=1)
        mx, my = pg.mouse.get_pos()
        fire = None
        for i, (a, label) in enumerate(rows):
            sl = ease((el - .05 - i * .03) * 4)
            x, y = 14 + int((1 - sl) * 470), 50 + i * 14.5
            on = i == s.sel
            pg.draw.polygon(scr, WHITE if on and a in ('reset', 'back') else INK,
                            [(x, y), (x + 456, y - 2), (x + 452, y + 12), (x - 4, y + 14)])
            scr.fill(RED if i % 2 else (0, 200, 230), (x, y + 1, 3, 12))
            s.row_text(label, on and a in ('reset', 'back'), x + 8, y + 1)
            if a in ('reset', 'back'):
                if s.moved and pg.Rect(x, y, 456, 13).collidepoint(mx, my):
                    s.sel = i
                if s.click and pg.Rect(x, y, 456, 13).collidepoint(mx, my):
                    fire = (i, s.col)
                continue
            kbt = s.bind_name('kb', a) + {'atk': " / LMB", 'parry': " / RMB"}.get(a, "")
            padt = s.bind_name('pad', a) if a in DEFAULT_PAD else ("STICK / D-PAD" if a in ('left', 'right', 'up', 'down') else "-")
            for c, (txt, cx_) in enumerate(((kbt, 186), (padt, 330))):
                cell = pg.Rect(cx_ - 6, y - 1, 136, 14)
                if s.moved and cell.collidepoint(mx, my):
                    s.sel, s.col = i, c
                if s.click and cell.collidepoint(mx, my):
                    fire = (i, c)
                if on and c == s.col:
                    pg.draw.rect(scr, WHITE, cell)
                    if s.capture and int(s.t * 4) % 2:
                        txt = "PRESS..."
                    scr.blit(F_S.render(txt, False, INK), (cx_, y + 1))
                else:
                    text(txt, F_S, (255, 230, 150) if c == 0 else (150, 240, 255), cx_, y + 1)
        text("MOVE ON PAD: LEFT STICK / D-PAD      ENTER / A: rebind      ESC: cancel / back", F_S, (200, 190, 230), W // 2, H - 12, True)
        if not s.capture and 'ok' in s.act:
            fire = (s.sel, s.col)
        if fire and not s.capture:
            i, c = fire
            s.sel, s.col = i, c
            a = rows[i][0]
            if a == 'back':
                s.wipe_to(lambda: s.go('settings', 0))
            elif a == 'reset':
                s.settings['kb'], s.settings['pad'] = dict(DEFAULT_KB), dict(DEFAULT_PAD)
                s.save_settings()
                sfx('buy')
            elif c == 1 and a not in DEFAULT_PAD:
                sfx('deny')
            else:
                s.capture = ('kb' if c == 0 else 'pad', a)
                sfx('sel')
        elif not s.capture and 'back' in s.act:
            s.wipe_to(lambda: s.go('settings', 0))
        if s.capture:
            pg.draw.polygon(scr, INK, [(60, 112), (W - 60, 106), (W - 66, 150), (54, 156)])
            pg.draw.polygon(scr, RED, [(60, 112), (W - 60, 106), (W - 66, 150), (54, 156)], 2)
            label = dict(BIND_ACTIONS)[s.capture[1]]
            outlined(("PRESS A KEY FOR " if s.capture[0] == 'kb' else "PRESS A PAD BUTTON FOR ") + label,
                     F_PS, WHITE, W // 2, 116, center=True, r=1)
            text("ESC to cancel", F_S, (200, 190, 230), W // 2, 138, True)

    # ---------- stats (avatar + name plate) and the skin shop
    def start_name(s):
        s.typing = True
        s.name_buf = '' if s.stats['name'] == "NAMELESS" else s.stats['name']
        pg.key.start_text_input()
        sfx('sel')

    def finish_name(s, save):
        if save and s.name_buf.strip():
            s.stats['name'] = s.name_buf.strip()[:12]
            save_stats(s.stats)
            sfx('buy')
        s.typing = False
        pg.key.stop_text_input()

    def row_small(s, x, y, w, label, val, accent):
        pg.draw.polygon(scr, INK, [(x, y), (x + w, y - 1), (x + w - 4, y + 12), (x - 4, y + 13)])
        scr.fill(accent, (x, y + 1, 3, 11))
        text(label, F_S, WHITE, x + 7, y + 1)
        img = F_S.render(val, False, INK)
        tw = img.get_width() + 10
        pg.draw.polygon(scr, WHITE, [(x + w - tw, y), (x + w + 1, y - 1), (x + w - 3, y + 12), (x + w - tw - 4, y + 13)])
        scr.blit(img, (x + w - tw + 3, y + 1))

    def wallet_tag(s, x, y):
        txt = f"{s.stats['wallet']}"
        w = F_PS.size(txt)[0] + 34
        pg.draw.polygon(scr, INK, [(x, y), (x + w, y - 2), (x + w - 4, y + 18), (x - 4, y + 20)])
        pg.draw.ellipse(scr, (255, 205, 50), (x + 6, y + 5, 9, 9))
        glow(scr, x + 10, y + 9, 10, (60, 45, 10))
        scr.blit(F_PS.render(txt, False, WHITE), (x + 20, y))

    def st_stats(s, dt):
        s.persona_bg()
        el = s.t - s.state_t
        st = s.stats
        ransom("STATS", 220, 18, [F_P, F_PM], 3, s.t, tilt=-6)
        s.wallet_tag(362, 8)
        cut = (1 - ease(el * 3)) * -240
        frame = pg.Rect(18 + cut, 36, 160, 160)                   # close-up: sword held up across half his face
        pg.draw.rect(scr, RED, frame.move(6, 5))
        scr.set_clip(frame)
        vgrad_rect(scr, frame, (40, 22, 60), (10, 6, 18))
        city = s.L['mid'].subsurface((int(s.t * 6) % 600, GY - 170, 160, 170))   # the city behind him, out of focus
        bg = pg.transform.smoothscale(pg.transform.smoothscale(city, (32, 34)), frame.size)
        bg.set_alpha(140)
        scr.blit(bg, frame)
        img = s.side_card(2.6, flip=False)                         # mirror of the main menu: facing right
        scr.blit(img, (frame.centerx - img.get_width() // 2, frame.bottom - img.get_height() + 2))
        scr.set_clip(None)
        pg.draw.rect(scr, WHITE, frame, 3)
        plate = [(16 + cut, 204), (182 + cut, 200), (178 + cut, 228), (12 + cut, 232)]   # name plate
        mx, my = pg.mouse.get_pos()
        if s.typing or s.sel == 0:
            pg.draw.polygon(scr, RED, [(a + 4, b_ + 3) for a, b_ in plate])
        pg.draw.polygon(scr, INK, plate)
        pg.draw.polygon(scr, WHITE if not s.typing else (255, 230, 120), plate, 2)
        name = (s.name_buf + ("_" if int(s.t * 3) % 2 else " ")) if s.typing else st['name']
        img = F_PM.render(name, False, WHITE)
        scr.blit(img, (97 + cut - img.get_width() // 2, 204))
        pg.draw.line(scr, WHITE, (206, 40), (198, 250), 3)        # divider
        for i, (lab, key) in enumerate(STAT_ROWS):
            a = ease((el - .15 - i * .04) * 4)
            if a <= 0:
                continue
            v = st[key] * ease((el - .3 - i * .04) * 1.2)
            s.row_small(216 + int((1 - a) * 280), 40 + i * 14.6, 252, lab, fmt_time(v) if key == 'time' else str(int(v)),
                        RED if i % 2 else (0, 200, 230))
        btns = [("SKINS >", pg.Rect(384, 241, 88, 22)), ("< BACK", pg.Rect(14, 6, 76, 22))]
        for i, (lab, r) in enumerate(btns, 1):
            on = s.sel == i
            pg.draw.polygon(scr, WHITE if on else INK, [(r.x, r.y), (r.right, r.y - 2), (r.right - 4, r.bottom), (r.x - 4, r.bottom + 2)])
            img = F_PS.render(lab, False, INK if on else WHITE)
            scr.blit(img, (r.centerx - img.get_width() // 2, r.y + 1))
            if s.moved and r.collidepoint(mx, my) and not s.typing:
                s.sel = i
        if s.typing:                                              # keyboard types; on a pad: up/down letter, right add, left delete
            if s.last_input == 'pad':
                abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"
                if s.act & {'up', 'down'}:
                    ch = s.name_buf[-1:] or 'A'
                    i = (abc.find(ch) + (1 if 'down' in s.act else -1)) % len(abc)
                    s.name_buf = s.name_buf[:-1] + abc[i]
                if 'right' in s.act and len(s.name_buf) < 12:
                    s.name_buf += 'A'
                if 'left' in s.act:
                    s.name_buf = s.name_buf[:-1]
                if 'use' in s.act:
                    s.name_buf = random.choice(NAMES)
                if 'ok' in s.act:
                    s.finish_name(True)
                elif 'back' in s.act:
                    s.finish_name(False)
            text("type your name  -  ENTER save  -  ESC cancel" if s.last_input == 'kb' else
                 "UP/DOWN letter  RIGHT add  LEFT delete  Y random  A save", F_S, (255, 230, 120), 98, 248, True)
            return
        s.nav(3)
        click_plate = s.click and pg.Rect(12 + cut, 200, 170, 32).collidepoint(mx, my)
        if s.moved and pg.Rect(12 + cut, 200, 170, 32).collidepoint(mx, my):
            s.sel = 0
        if click_plate or ('ok' in s.act and s.sel == 0):
            s.start_name()
        elif (s.click and btns[0][1].collidepoint(mx, my)) or ('ok' in s.act and s.sel == 1) or 'right' in s.act:
            s.wipe_to(lambda: s.go('skins', 0))
        elif (s.click and btns[1][1].collidepoint(mx, my)) or ('ok' in s.act and s.sel == 2) or 'back' in s.act:
            s.wipe_to(s.to_menu)
        if s.sel == 0:
            text("ENTER / A: change name", F_S, (220, 210, 240), 98, 248, True)

    def st_skins(s, dt):
        s.persona_bg()
        el = s.t - s.state_t
        st = s.stats
        ransom("SKINS", 16, 22, [F_PB, F_P], 17, s.t, tilt=-6)
        s.wallet_tag(W - 110, 14)
        ids = list(SKINS)
        n = len(ids)
        s.sel %= n
        if 'left' in s.act:
            s.sel, s.selT = (s.sel - 1) % n, s.t
            sfx('sel')
        if 'right' in s.act:
            s.sel, s.selT = (s.sel + 1) % n, s.t
            sfx('sel')
        cw, gap = 130, 16
        scroll = max(0, min(s.sel * (cw + gap) - (cw + gap), n * (cw + gap) - gap - (W - 40)))
        x0 = max(20, W // 2 - (n * (cw + gap) - gap) // 2) - scroll
        mx, my = pg.mouse.get_pos()
        fire = 'ok' in s.act
        for i, sid in enumerate(ids):
            name, price, _ = SKINS[sid]
            on = i == s.sel
            a = ease((el - .05 - i * .08) * 4)
            x, y = x0 + i * (cw + gap) + int((1 - a) * 400), 56 - (8 if on else 0)
            shake = math.sin(s.t * 60) * 3 if on and s.t - s.denyT < .25 else 0
            x += shake
            card = [(x, y + 4), (x + cw, y), (x + cw + 4, y + 172), (x - 4, y + 176)]
            if on:
                pg.draw.polygon(scr, RED, [(px + 7, py + 6) for px, py in card])
            pg.draw.polygon(scr, WHITE if on else INK, card)
            pg.draw.polygon(scr, INK if on else WHITE, card, 2)
            pg.draw.rect(scr, (20, 12, 30), (x + 8, y + 10, cw - 16, 112))
            k = (s.t * .9 + i * .3) % 1
            P = with_attack(pose_idle(s.t), 'side', min(1, k / .35), 1) if on and k < .45 else pose_idle(s.t + i)
            P['hood'] = 0.0                                        # shop shows the samurai with the hood down
            if sid not in s.skin_chains:
                s.skin_chains[sid] = {'scarf': [[48, 60] for _ in range(5)], 'hair': [[48, 55] for _ in range(5)]}
            img = s.portrait(P, 1.85, sid, s.skin_chains[sid])
            scr.blit(img, (x + cw // 2 - img.get_width() // 2, y + 120 - img.get_height()))
            img = F_PS.render(name, False, INK if on else WHITE)
            scr.blit(img, (x + cw // 2 - img.get_width() // 2, y + 126))
            if st['skin'] == sid:
                tag, col, tcol = "EQUIPPED", RED, WHITE
            elif sid in st['skins']:
                tag, col, tcol = "OWNED - EQUIP", (0, 200, 230), INK
            else:
                tag, col, tcol = f"{price} COINS", (255, 205, 50) if st['wallet'] >= price else (90, 80, 100), INK
            tw = F_S.size(tag)[0] + 14
            pg.draw.polygon(scr, col, [(x + cw // 2 - tw // 2, y + 150), (x + cw // 2 + tw // 2, y + 148),
                                       (x + cw // 2 + tw // 2 - 3, y + 164), (x + cw // 2 - tw // 2 - 3, y + 166)])
            s.row_text(tag, tcol == INK, x + cw // 2 - F_S.size(tag)[0] // 2, y + 152)
            r = pg.Rect(x, y, cw, 176)
            if s.moved and r.collidepoint(mx, my) and not on:
                s.sel, s.selT = i, s.t
                sfx('sel')
            if s.click and r.collidepoint(mx, my):
                s.sel, fire = i, True
        if fire:
            sid = ids[s.sel]
            price = SKINS[sid][1]
            if sid in st['skins']:
                st['skin'] = sid
                sfx('sel')
            elif st['wallet'] >= price:                           # buy it and wear it
                st['wallet'] -= price
                st['skins'].append(sid)
                st['skin'] = sid
                sfx('buy')
            else:
                s.denyT = s.t
                sfx('deny')
            save_stats(st)
        pg.draw.polygon(scr, INK, [(0, H - 14), (W, H - 18), (W, H), (0, H)])
        text("LEFT/RIGHT choose     ENTER / A buy or equip     ESC / B back      more skins soon", F_S,
             (220, 210, 240), W // 2, H - 13, True)
        if 'back' in s.act:
            s.wipe_to(lambda: s.go('stats', 0))

    # ---------- opening cinematic, dialog, kiosk
    def dialog_box(s, dt):
        """Persona-style dialog box. Returns True when all lines are done."""
        if s.dl >= len(DIALOG):
            return True
        name, txt = DIALOG[s.dl]
        name = name.replace("{NAME}", s.stats['name'])
        lines = wrap(txt, F_S, 400)
        total = sum(len(l) for l in lines)
        s.dc += dt * 45
        box = [(16, H - 74), (W - 12, H - 82), (W - 20, H - 8), (24, H - 4)]
        pg.draw.polygon(scr, RED, [(a + 5, b + 4) for a, b in box])
        pg.draw.polygon(scr, INK, box)
        pg.draw.polygon(scr, WHITE, box, 2)
        hero = DIALOG[s.dl][0] == "{NAME}"
        tag = pg.Surface((F_PM.size(name)[0] + 18, 24), pg.SRCALPHA)
        tag.fill((0, 230, 255) if hero else RED)
        tag.blit(F_PM.render(name, False, INK if hero else WHITE), (9, 0))
        scr.blit(pg.transform.rotate(tag, 6), (22, H - 100))
        n = int(s.dc)
        for i, l in enumerate(lines):
            text(l[:max(0, n)], F_S, WHITE, 40, H - 60 + i * 13)
            n -= len(l)
        if s.dc >= total:
            star(W - 40, H - 22 + math.sin(s.t * 8) * 2, 5, s.t * 3, RED)
        if s.tapped():
            if s.dc < total:
                s.dc = total
            else:
                s.dl, s.dc = s.dl + 1, 0
                sfx('sel')
        return s.dl >= len(DIALOG)

    def zoom_view(s, z, fx, fy, tilt=0.0):
        """Cinematic camera: blow up the area around (fx, fy) by z, optionally tilted (Dutch angle)."""
        if z <= 1.01 and abs(tilt) < .3:
            return
        z = max(z, 1 + abs(tilt) * .025)                             # zoom a little more so a tilt never shows edges
        cw, ch = W / z, H / z
        rx, ry = max(0, min(W - cw, fx - cw / 2)), max(0, min(H - ch, fy - ch * .55))
        img = pg.transform.scale(scr.subsurface((rx, ry, cw, ch)).copy(), (W, H))
        if abs(tilt) >= .3:
            img = pg.transform.rotate(img, tilt)
        scr.blit(img, img.get_rect(center=(W // 2, H // 2)))

    def st_cine(s, dt):
        """District 1 intro, filmed with the in-game camera: close on the samurai looking at his blade, he sheathes it
        and pulls up his hood, a few lines of dialog, then the camera pulls back and the red door shuts behind him."""
        p = s.pl
        s.cine_t += dt
        t = s.cine_t
        p.vx = 0
        p.phys(dt, s.plats)
        if s.cine_phase == 'inspect' and t >= 1.6:
            s.cine_phase = 'hood'
            sfx('unsheathe')
        elif s.cine_phase == 'hood' and t >= 2.9:
            s.cine_phase = 'dialog'
        elif s.cine_phase == 'out':
            s.cine_out += dt
            if s.cine_out >= .9:
                s.go('play', 0)
                s.door['closing'] = True                            # the red door shuts behind you
        if s.cine_t - dt < .5 <= s.cine_t:
            sfx('glint')
        if s.cine_t - dt < 2.05 <= s.cine_t:
            sfx('hood')
        for q in s.parts:
            q[4] -= dt
            q[3] += q[8] * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
        s.parts = [q for q in s.parts if q[4] > 0]
        s.cam = max(0, min(LW - W, p.x - W * .4))
        s.camy = 0
        s.draw_world(overlay=False)
        if s.cine_phase == 'inspect' and s.tip_scr and .5 < t < 1.5:   # a glint runs along the blade
            gx, gy = (lerp(s.hand_scr[i], s.tip_scr[i], min(1, (t - .5) / .9)) for i in (0, 1))
            glow(scr, gx, gy, 8, (110, 90, 20))
            four_star(scr, gx, gy, 3, (255, 214, 70))
        # camera: push in on the hands and blade, tilt up to the face as the hood goes on, then pull back
        fx, by = p.x + p.w / 2 - s.cam, p.y - s.camy
        k_out = 0.0
        if s.cine_phase == 'inspect':
            k = ease(t / 1.6)
            z, fy, tilt = lerp(2.6, 3.1, k), by + 16 - 2 * k, lerp(4, 2, k)
        elif s.cine_phase == 'hood':
            k = ease((t - 1.6) / 1.3)
            z, fy, tilt = lerp(3.1, 2.4, k), by + lerp(14, 6, k), lerp(2, 0, k)
        elif s.cine_phase == 'dialog':
            z, fy, tilt = 2.4, by + 6, 0
        else:
            k_out = ease(s.cine_out / .9)
            z, fy, tilt = lerp(2.4, 1, k_out), by + 6 + (p.h / 2 - 6) * k_out, 0
        s.zoom_view(z, fx, fy, tilt)
        if s.settings['crt']:
            scr.blit(s.L['over'], (0, 0))
        bh = int(34 * min(1, t / .4) * (1 - k_out))                 # letterbox bars
        scr.fill((0, 0, 0), (0, 0, W, bh))
        scr.fill((0, 0, 0), (0, H - bh, W, bh))
        if s.cine_phase == 'dialog' and s.dialog_box(dt):
            s.cine_phase, s.cine_out = 'out', 0.0
        if s.cine_phase != 'out':
            outlined("ESC skip", F_S, WHITE, W - 64, 8 + bh, r=1)
            if s.act & {'back', 'pause'}:
                s.cine_phase, s.cine_out = 'out', 0.0

    def apply_buff(s, b):
        p = s.pl
        if b == 'key':                                              # an exit door opens next to the kiosk
            s.keydoor = {'x': s.kiosk['x'] + 72, 'k': 0.0}
            sfx('door')
        else:
            s.buffs[b] = s.buffs.get(b, 0) + 1
            if b == 'vital':
                p.maxhp += 1
                p.hp = p.maxhp
        s.kiosk['used'] = True
        sfx('buy')
        s.burst(p.x + p.w / 2, p.y, 20, (BUFFS[b][2] if b in BUFFS else KEY_BUFF[3]), spd=120, glowing=True, grav=100)
        s.go('play', 0)

    def st_kiosk(s, dt):
        """The Shinobi Kiosk: pick one of three buffs (sometimes an exit key)."""
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        el = ease((s.t - s.state_t) * 4)
        cards = s.kiosk['cards']
        if 'left' in s.act:
            s.sel, s.selT = (s.sel - 1) % 3, s.t
            sfx('sel')
        if 'right' in s.act:
            s.sel, s.selT = (s.sel + 1) % 3, s.t
            sfx('sel')
        oy = int((1 - el) * -200)
        sign = [(70, 8 + oy), (410, 4 + oy), (406, 34 + oy), (74, 38 + oy)]          # the sign
        pg.draw.polygon(scr, INK, sign)
        pg.draw.polygon(scr, (0, 230, 255), sign, 2)
        glow(scr, 240, 20 + oy, 120, (0, 40, 60), .25)
        outlined("SHINOBI  KIOSK", F_PM, (0, 230, 255), 240, 8 + oy, center=True, r=1)
        for mxp in (100, 380):
            s.shinobi_mask(mxp, 21 + oy, .9, .5)
        win = [(40, 46 + oy), (440, 42 + oy), (446, 146 + oy), (34, 150 + oy)]         # glass window with reflections
        pg.draw.polygon(scr, (20, 26, 52), win)
        for i in range(12):
            gx = 50 + i * 34
            pg.draw.line(scr, (52, 66, 110), (gx, 140 + oy), (gx + 40, 52 + oy), 2)
        s.shinobi_mask(240, 92 + oy, 3, .7 + math.sin(s.t * 3) * .2)                   # the vendor
        pg.draw.polygon(scr, WHITE, win, 2)
        for px in (30, 442):                                                            # wooden posts
            pg.draw.rect(scr, (78, 44, 24), (px, 146 + oy, 9, H - 146 - oy))
            pg.draw.line(scr, (120, 74, 42), (px + 1, 146 + oy), (px + 1, H))
        counter = pg.Rect(30, 146 + oy, 421, 46)                                        # big wooden counter
        pg.draw.rect(scr, (122, 74, 40), counter)
        pg.draw.rect(scr, (168, 110, 62), (counter.x, counter.y, counter.w, 4))
        for i, ly in enumerate(range(counter.y + 14, counter.bottom, 11)):              # planks
            pg.draw.line(scr, (86, 50, 26), (counter.x, ly), (counter.right, ly))
            for jx in range(counter.x + 40 + (i % 2) * 55, counter.right, 110):
                pg.draw.line(scr, (86, 50, 26), (jx, ly - 10), (jx, ly))
        pg.draw.rect(scr, (60, 34, 18), counter, 2)
        mx, my = pg.mouse.get_pos()
        fire = 'ok' in s.act
        for i, b in enumerate(cards):
            title, desc, col = (BUFFS[b] if b in BUFFS else KEY_BUFF[1:])
            on = i == s.sel
            cx_ = 120 + i * 120
            y = 168 - (8 if on else 0) + int((1 - el) * 120)                       # cards stand in front of the counter
            card = [(cx_ - 50, y + 2), (cx_ + 50, y), (cx_ + 52, y + 92), (cx_ - 52, y + 94)]
            if on:
                pg.draw.polygon(scr, RED, [(a + 6, b_ + 5) for a, b_ in card])
            pg.draw.polygon(scr, WHITE if b != 'key' else (255, 225, 225), card)
            pg.draw.polygon(scr, col if on else INK, card, 3 if on else 1)
            pg.draw.rect(scr, INK, (cx_ - 16, y + 6, 32, 28))
            glow(scr, cx_, y + 20, 18, tuple(c // 3 for c in col))
            s.buff_icon(b, cx_, y + 20, col)
            img = F_PS.render(title, False, INK)
            scr.blit(img, (cx_ - img.get_width() // 2, y + 36))
            for j, line in enumerate(wrap(desc, F_S, 94)):
                img = F_S.render(line, False, (40, 30, 50))
                scr.blit(img, (cx_ - img.get_width() // 2, y + 56 + j * 11))
            r = pg.Rect(cx_ - 52, y, 104, 94)
            if s.moved and r.collidepoint(mx, my) and not on:
                s.sel, s.selT = i, s.t
                sfx('sel')
            if s.click and r.collidepoint(mx, my):
                s.sel, fire = i, True
        kind = 'pad' if s.last_input == 'pad' else 'kb'
        text("LEFT/RIGHT choose   " + ("A take   B leave" if kind == 'pad' else "ENTER / CLICK take   ESC leave"),
             F_S, (220, 210, 240), W // 2, H - 11, True)
        if fire:
            s.apply_buff(cards[s.sel])
        elif 'back' in s.act:
            s.go('play', 0)

    def st_play(s, dt):
        if 'pause' in s.act:
            s.go('pause', 0)
            s.music_volume()
        s.update(dt)
        s.draw_world(overlay=False)
        s.zoom_view(*s.camera())                                  # anime camera moves (zoom / tilt)
        if 0 <= s.superT < SUPER_CUT:                             # cinematic bars during the super's camera dive
            bh = int(30 * ease(s.superT / (SUPER_CUT * .4)))
            scr.fill((0, 0, 0), (0, 0, W, bh))
            scr.fill((0, 0, 0), (0, H - bh, W, bh))
        if s.settings['crt']:
            scr.blit(s.L['over'], (0, 0))
        if s.superT < 0:
            s.hud()
            if TOUCH and s.state == 'play':
                s.draw_touch()

    def st_pause(s, dt):
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        el = ease((s.t - s.state_t) * 5)
        off = (1 - el) * -300
        pg.draw.polygon(scr, RED, [(off, 0), (230 + off, 0), (150 + off, H), (off, H)])
        pg.draw.polygon(scr, INK, [(236 + off, 0), (262 + off, 0), (182 + off, H), (156 + off, H)])
        ransom("PAUSE", 24, 44, [F_PB, F_P], 5, s.t, tilt=-7)
        if s.act & {'pause', 'back'}:
            s.go('play', 0)
            return
        s.p_items([("RESUME", lambda: s.go('play', 0)), ("RESTART", s.restart), ("MAIN MENU", s.to_menu)], 28, 108, wipe=False)

    def result_rows(s, rows, y0):
        el = s.t - s.state_t
        for i, (lab, v, fmt) in enumerate(rows):
            a = ease((el - .3 - i * .12) * 4)
            if a <= 0:
                continue
            s.p_bar(W // 2 - 110 + int((1 - a) * 300) + i * 3, y0 + i * 19, 230, lab, fmt(v * ease((el - .4 - i * .12) * 1.5)),
                    RED if i % 2 == 0 else (0, 200, 230))

    def st_dead(s, dt):
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        scr.blit(s.red, (0, 0))
        pg.draw.polygon(scr, INK, [(0, 18), (W, 4), (W, 92), (0, 104)])
        ransom("YOU DIED", W // 2, 50, [F_PB, F_P], 13, s.t, center=True, tilt=-4)
        outlined("Your coins scatter in the rain...", F_PS, (255, 140, 160), W // 2, 78, center=True, r=1)
        s.result_rows([("DISTRICT", s.lvl, lambda v: f"{int(v)} / {LEVELS}"), ("TIME", s.gtime, fmt_time),
                       ("KILLS", s.kills, lambda v: str(int(v))), ("COINS LOST", s.score, lambda v: str(int(v)))], 112)
        s.p_items([("RETRY", s.new_run), ("MAIN MENU", s.to_menu)], 150, 194, font=F_PM, dy=28)

    def st_exit(s, dt):
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        pg.draw.polygon(scr, RED, [(0, 10), (W, 0), (W, 80), (0, 94)])
        won = s.end_kind == 'victory'
        ransom("RUN COMPLETE" if won else "ESCAPED", W // 2, 42, [F_PB, F_P], 23, s.t, center=True, tilt=-4)
        outlined("All five districts are behind you." if won else "The exit key turns. You live to cut another night.",
                 F_S, WHITE, W // 2, 70, center=True, r=1)
        num = lambda v: str(int(v))
        s.result_rows([("DISTRICTS", s.runst['levels'], lambda v: f"{int(v)} / {LEVELS}"), ("TIME", s.gtime, fmt_time),
                       ("KILLS", s.kills, num), ("COINS EARNED", s.score, num), ("WALLET", s.stats['wallet'], num)], 98)
        s.p_items([("NEW RUN", s.new_run), ("MAIN MENU", s.to_menu)], 150, 206, font=F_PM, dy=26)

    def st_trans(s, dt):
        """Between districts: darkness, a random line, then the next district fades in."""
        scr.fill((4, 2, 8))
        el = s.t - s.state_t
        for i in range(30):                                      # slow falling rain in the dark
            x = (i * 53 + el * 40) % W
            y = (i * 97 + el * 260) % H
            pg.draw.line(scr, (40, 36, 70), (x, y), (x - 2, y + 7))
        n = int(max(0, el - .5) * 30)
        outlined(f"DISTRICT {s.lvl + 1} / {LEVELS}", F_PS, RED, W // 2, 96, center=True, r=1)
        img = F_PM.render(s.phrase[:n], False, WHITE)
        scr.blit(img, (W // 2 - F_PM.size(s.phrase)[0] // 2, 120))
        if el > 3.2 or (el > 1 and s.tapped()):
            s.lvl += 1
            s.build_level()
            s.start_level()

    def st_victory(s, dt):
        scr.fill((4, 2, 8))
        el = s.t - s.state_t
        glow(scr, W // 2, 110, 140, qcol((80, 20, 40), min(1, el / 2)))
        if el > .4:
            ransom(VICTORY_LINES[0].upper(), W // 2, 70, [F_PB, F_P], 41, s.t, center=True, tilt=-4)
        for i, line in enumerate(VICTORY_LINES[1:]):
            a = el - 1.4 - i * 1.1
            if a > 0:
                img = F_PM.render(line[:int(a * 35)], False, WHITE)
                scr.blit(img, (W // 2 - F_PM.size(line)[0] // 2, 118 + i * 26))
        if el > 5.5:
            outlined("press to continue", F_S, (200, 190, 230), W // 2, 236, center=True, r=1)
        if (el > 5.5 and s.tapped()) or el > 12:
            s.wipe_to(lambda: s.go('exit', 0))

    # ---------- loop
    def run(s):
        while True:
            dt = min(clock.tick(60) / 1000, 1 / 30)
            s.t += dt
            s.dt = dt
            s.act, s.click, s.moved = set(), False, False
            for ev in pg.event.get():
                if ev.type == pg.QUIT:
                    s.quit()
                s.handle_event(ev)
            s.frame(dt)
            pg.display.flip()

    def frame(s, dt):
        if s.wipe_fn is not None:                # block input while the wipe covers the screen
            s.act, s.click = set(), False
        getattr(s, 'st_' + s.state)(dt)
        if s.fade > 0:                           # fade-in on screen changes
            s.black.set_alpha(int(min(1, s.fade) * 255))
            scr.blit(s.black, (0, 0))
            s.fade -= dt * 3
        if s.wipe_fn is not None:                # Persona-style red slash wipe
            s.wipe += dt * 2.6
            k = s.wipe
            if k < .5:
                X = lerp(-120, W + 140, ease(k * 2))
                pg.draw.polygon(scr, RED, [(0, 0), (X, 0), (X - 110, H), (0, H)])
                pg.draw.polygon(scr, INK, [(X, 0), (X + 26, 0), (X - 84, H), (X - 110, H)])
                pg.draw.line(scr, WHITE, (X + 30, 0), (X - 80, H), 3)
            else:
                if s.wipe_fn != 'done':
                    fn, s.wipe_fn = s.wipe_fn, 'done'
                    fn()
                    s.fade = 0
                Lx = lerp(-120, W + 140, ease((k - .5) * 2))
                pg.draw.polygon(scr, RED, [(Lx, 0), (W, 0), (W, H), (Lx - 110, H)])
                pg.draw.line(scr, WHITE, (Lx - 4, 0), (Lx - 114, H), 3)
                if k >= 1:
                    s.wipe_fn = None


if __name__ == '__main__':
    Game().run()
