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
                    'rain': 1, 'crt': True, 'rumble': True, 'lang': 'ru', 'god': False,
                    'admin': False, 'a_dmg': 0, 'a_fly': False, 'a_noclip': False, 'a_speed': 0, 'a_jump': 0,
                    'a_kills': False, 'a_money': False, 'diff': 2,
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
            "SUPER": "СУПЕР", "USE": "ИСП."}                 # short Russian names that fit on a round button
# difficulty: name, enemy HP, boss HP, how fast enemies and bosses attack (1 = normal), parry window for you
DIFFS = (("NOVICE", .7, .6, .8, 1.3), ("NORMAL", 1.0, .8, 1.0, 1.0), ("BASED SAMURAI", 1.0, 1.0, 1.0, 1.0),
         ("TRUE SAMURAI", 1.2, 1.2, 1.0, 1.0))
# admin options (for testing): multipliers you step through, switches, and buttons that change the save
ADMIN_CYCLE = {'a_dmg': (1, 2, 5, 10, 100), 'a_speed': (1, 1.5, 2, 3), 'a_jump': (1, 1.3, 1.6, 2)}
ADMIN_ROWS = [('', 'TELEPORT', 'teleport', 'action'), ('', 'DAMAGE', 'a_dmg', 'cycle'), ('', 'FLY', 'a_fly', 'toggle'), ('', 'NOCLIP', 'a_noclip', 'toggle'),
              ('', 'SPEED', 'a_speed', 'cycle'), ('', 'JUMP', 'a_jump', 'cycle'), ('', 'INFINITE KILLS', 'a_kills', 'toggle'),
              ('', 'INFINITE MONEY', 'a_money', 'toggle'), ('', 'UNLOCK ALL SKINS', 'skins_all', 'action'),
              ('', 'REMOVE SKINS', 'skins_clear', 'action'), ('', 'MAX UPGRADES', 'upg_all', 'action'),
              ('', 'REMOVE UPGRADES', 'upg_clear', 'action'), ('', 'OPEN ALL MAPS', 'maps_all', 'action'),
              ('', 'REMOVE ALL MAPS', 'maps_clear', 'action')]
LANG = 'ru'                                # 'en' or 'ru', set from the settings (SETTINGS -> LANGUAGE)
RAIN_LEVELS = (("LIGHT", 35), ("MEDIUM", 70), ("HEAVY", 120))

if ANDROID:                                          # phones report the accelerometer as a joystick: tilting
    os.environ['SDL_ACCELEROMETER_AS_JOYSTICK'] = '0'  # the phone would press buttons. Turn that off.
pg.mixer.pre_init(44100, -16, 2, 512)
pg.init()


def make_icon():
    """The window and taskbar icon: a katana across the neon Shinjuku night."""
    n = 64
    ic = pg.Surface((n, n))
    for y in range(n):                                        # night sky, magenta at the horizon
        f = y / n
        ic.fill((int(20 + 120 * f * f), int(8 + 14 * f), int(48 + 60 * f)), (0, y, n, 1))
    pg.draw.circle(ic, (255, 90, 170), (44, 22), 9)
    pg.draw.circle(ic, (255, 160, 210), (44, 22), 6)
    rnd = random.Random(7)
    x = 0
    while x < n:                                              # skyline with lit windows and neon signs
        w, h = rnd.randint(6, 11), rnd.randint(14, 34)
        pg.draw.rect(ic, (14, 8, 26), (x, n - h, w, h))
        for wy in range(n - h + 3, n - 2, 4):
            for wx in range(x + 1, x + w - 1, 3):
                if rnd.random() < .35:
                    ic.set_at((wx, wy), rnd.choice([(255, 210, 120), (120, 230, 255), (255, 80, 160)]))
        if rnd.random() < .5:
            pg.draw.rect(ic, rnd.choice([(255, 40, 120), (60, 220, 255)]), (x + 1, n - h + 2, 2, 7))
        x += w + rnd.randint(0, 2)
    # the katana, corner to corner: a white curved blade, a gold guard, a red-wrapped hilt
    pts = [(19 + i * 2.6, 45 - i * 2.6 - 2.2 * math.sin(i / 14 * math.pi)) for i in range(15)]
    pg.draw.lines(ic, (40, 30, 60), False, [(px + 1, py + 1) for px, py in pts], 5)
    pg.draw.lines(ic, (235, 240, 255), False, pts, 4)
    pg.draw.lines(ic, (150, 220, 255), False, [(px, py + 1) for px, py in pts[1:]], 1)
    gx, gy = pts[0]
    pg.draw.line(ic, (40, 20, 30), (gx - 2, gy + 2), (gx - 12, gy + 12), 7)
    pg.draw.line(ic, (210, 30, 50), (gx - 2, gy + 2), (gx - 12, gy + 12), 5)
    for k in range(3):
        pg.draw.line(ic, (60, 10, 20), (gx - 5 - k * 3, gy + 1 + k * 3), (gx - 2 - k * 3, gy + 5 + k * 3), 1)
    pg.draw.circle(ic, (255, 210, 80), (int(gx - 13), int(gy + 13)), 2)
    pg.draw.line(ic, (255, 210, 80), (gx - 4, gy - 4), (gx + 4, gy + 4), 4)
    return ic


ICON = make_icon()
pg.display.set_icon(ICON)
if not hasattr(pg.transform, 'scale_by'):           # Android's pygame is older than pygame-ce: no scale_by
    pg.transform.scale_by = lambda s_, k: pg.transform.scale(s_, (max(1, int(s_.get_width() * k)), max(1, int(s_.get_height() * k))))
scr = pg.display.set_mode((W, H), pg.SCALED | (pg.FULLSCREEN if ANDROID else pg.RESIZABLE))
pg.display.set_caption("Neon Ronin")
clock = pg.time.Clock()
def pick_font(names, size, bold=True):
    """First installed font from a comma list that has Cyrillic glyphs too (the Russian text needs them)."""
    if ANDROID or '--phonefonts' in sys.argv:            # phones: the bundled fonts
        disp = 'impact' in names
        path = os.path.join(ASSETS, 'fonts', 'Oswald.ttf' if disp else 'DotGothic16-Regular.ttf')
        if os.path.exists(path):
            f = pg.font.Font(path, max(9, round(size * (.92 if disp else .9))))
            if disp:
                f.set_bold(True)
            return f
    for name in names.split(","):
        path = pg.font.match_font(name.strip(), bold=bold)
        if path:
            f = pg.font.Font(path, size)
            if f.metrics("Ж")[0] is not None:
                return f
    return pg.font.Font(None, size)            # pygame's built-in font covers Cyrillic too


F_S = pick_font("consolas,couriernew,dejavusansmono", 10, bold=True)
F_M = pick_font("consolas,couriernew,dejavusansmono", 14, bold=True)
F_JP = pick_font("yugothic,msgothic,meiryo", 11) if ANDROID or '--phonefonts' in sys.argv else pg.font.SysFont("yugothic,msgothic,meiryo", 11, bold=True)
F_JPB = pick_font("yugothic,msgothic,meiryo", 16) if ANDROID or '--phonefonts' in sys.argv else pg.font.SysFont("yugothic,msgothic,meiryo", 16, bold=True)
F_P = pick_font("impact,arialblack,arial", 28)      # Persona-style display fonts
F_PB = pick_font("impact,arialblack,arial", 40)
F_PM = pick_font("impact,arialblack,arial", 20)
F_PS = pick_font("impact,arialblack,arial", 15)
SUPER_CUT, SUPER_T = .35, 1.0                                        # super: camera-dive length, total length

# ---- rebindable controls. Keyboard: action -> key. Xbox pad: action -> button index or trigger ('LT'/'RT').
BIND_ACTIONS = [('left', "MOVE LEFT"), ('right', "MOVE RIGHT"), ('up', "AIM UP"), ('down', "AIM DOWN / SLAM"),
                ('jump', "JUMP"), ('atk', "SLASH"), ('dash', "DASH"),
                ('parry', "PARRY"), ('super', "SUPER"), ('skill', "SKILL"), ('use', "USE"), ('pause', "PAUSE")]
DEFAULT_KB = {'left': pg.K_a, 'right': pg.K_d, 'up': pg.K_w, 'down': pg.K_s, 'jump': pg.K_SPACE, 'atk': pg.K_j,
              'dash': pg.K_LSHIFT, 'crouch': pg.K_LCTRL, 'parry': pg.K_k, 'super': pg.K_q, 'skill': pg.K_r, 'use': pg.K_e, 'pause': pg.K_ESCAPE}
DEFAULT_PAD = {'jump': 0, 'atk': 2, 'crouch': 1, 'use': 3, 'super': 4, 'parry': 5, 'dash': 'RT', 'skill': 6, 'pause': 7}
PAD_NAMES = {0: 'A', 1: 'B', 2: 'X', 3: 'Y', 4: 'LB', 5: 'RB', 6: 'VIEW', 7: 'MENU', 8: 'LS', 9: 'RS', 'LT': 'LT', 'RT': 'RT'}
# keys that always work in menus, whatever the bindings
MENU_KEYS = {pg.K_AC_BACK: ('back', 'pause'), pg.K_RETURN: ('ok',), pg.K_KP_ENTER: ('ok',), pg.K_SPACE: ('ok',), pg.K_ESCAPE: ('back', 'pause'),
             pg.K_BACKSPACE: ('back',), pg.K_UP: ('up',), pg.K_DOWN: ('down',), pg.K_LEFT: ('left',), pg.K_RIGHT: ('right',)}
MENU_HINT = ("W/S select   ENTER confirm   F11 fullscreen", "D-PAD select   A confirm   B back")
RED, WHITE, INK = (215, 20, 40), (255, 255, 255), (10, 8, 12)
VERSION = "v3: 10 districts, bosses, Russian"

# "{NAME}" is replaced with the player's chosen name
DIALOG = [
    ("{NAME}", "...Where am I?"),
    ("VOICE", "Neo-Tokyo. Shinjuku, Sector 9. The rain never stops here."),
    ("VOICE", "Fifteen districts stand between you and the way out. The doors close behind you."),
    ("VOICE", "Coins of light lie scattered across the rooftops. Gold... and the rare mythic ones."),
    ("{NAME}", "And the ones with swords?"),
    ("VOICE", "The Shogun's ronin, his oni and his shinobi. Cut them down."),
]
LEVELS = 15                                 # districts per run; every fifth one ends in a boss
PHRASES = ["The rain remembers every blade.", "Neon bleeds. You don't.", "Deeper into Shinjuku...",
           "The Shogun is watching.", "Steel sings in the dark.", "No way back. Only forward.",
           "Every door closes behind you.", "The city hums a funeral song.", "Your blade is still thirsty.",
           "Masks in the alleys. Eyes on the roofs.", "Breathe. Draw. Cut.", "The night is long. Longer still.",
           "Somewhere a bell rings for the fallen.", "Even the neon is afraid of you now."]
VICTORY_LINES = ["You've done it."]
GLASS = (150, 205, 220)                          # glass HP: cyan-gray, never heals back
BUFFS = {   # id: (title, description, colour) - the normal kiosk cards
    'edge': ("RAZOR EDGE", "+1 damage on every slash", (230, 230, 255)),
    'quake': ("EARTHSHAKER", "+1 damage on ground slams", (110, 220, 255)),
    'shadow': ("SHADOW STEP", "Dashing through enemies cuts each for 1", (150, 120, 255)),
    'swift': ("WIND STEP", "Run 15% faster", (80, 255, 170)),
    'ghost': ("GHOST DASH", "Dash recharges 40% faster", (0, 230, 255)),
    'storm': ("STORM HEART", "Super charges twice as fast", (170, 90, 255)),
    'iron': ("STILL MIND", "Parry window +60%", (190, 200, 220)),
    'reach': ("LONG BLADE", "Slashes reach 25% further", (150, 200, 255)),
    'quick': ("QUICK DRAW", "Attack 20% faster", (255, 240, 120)),
    'thorns': ("RIPOSTE", "A parry also cuts for 2 damage", (255, 150, 90)),
    'execute': ("EXECUTIONER", "Enemies below 50% HP die in one cut", (230, 50, 50)),
    'rage': ("RAGE", "+50% damage while you are at 1 HP", (255, 70, 30)),
    'magnet': ("COIN MAGNET", "Coins fly to you from afar", (255, 205, 50)),
    'greed': ("GOLD RUSH", "Gold coins worth 3 for 3 min. Again: +3 min", (255, 170, 40)),
    'bounty': ("BOUNTY HUNTER", "+2 coins per kill for 3 min. Again: +3 min", (255, 215, 90)),
    'vital': ("VITAL SPIRIT", "+1 max HP and heal 1 HP", (255, 70, 100)),
    'vamp': ("BLOOD OATH", "Heal 1 HP every 8 kills", (220, 30, 60)),
    'onigiri': ("ONIGIRI", "Heal 2 HP. At full HP: +1 glass HP", (240, 240, 230)),
    'medic': ("FIELD MEDIC", "5% of enemies drop a heart, for 5 districts", (255, 110, 140)),
    'armor': ("IRON HAORI", "Every 3rd hit you take is blocked", (170, 180, 200)),
    'ward': ("SPIRIT WARD", "A ward blocks 1 hit, back every 4 minutes", (200, 160, 255)),
    'glass': ("GLASS SKIN", "+20% of max HP as glass HP (can't heal)", GLASS),
    'second': ("SECOND WIND", "Survive one deadly hit with 1 HP", (120, 255, 200)),
    'sky': ("SKY DANCER", "One more dash in the air", (130, 220, 255)),
}
CARD_CATS = {   # a kiosk holds at most one normal card of each category; the numbers are how often each one comes up
    'attack': {'edge': 3, 'quake': 1, 'shadow': 1},
    'ability': {'swift': 1, 'ghost': 1, 'storm': 1, 'iron': 1, 'reach': 1, 'quick': 1, 'thorns': 1, 'execute': 1, 'rage': 1,
                'sky': 1},
    'coins': {'magnet': 1, 'greed': 1, 'bounty': 1},
    'health': {'vital': 1, 'vamp': 1, 'onigiri': 1, 'medic': 1},
    'defense': {'armor': 1, 'ward': 1, 'glass': 1, 'second': 1},
}
ONCE_CARDS = {'shadow', 'swift', 'ghost', 'storm', 'iron', 'reach', 'quick', 'thorns', 'execute', 'rage', 'sky', 'magnet',
              'vamp', 'medic', 'armor', 'ward', 'second'}   # not offered while you have them (FIELD MEDIC: until it runs out)
TIMED_CARDS = {'greed': 180.0, 'bounty': 180.0}           # seconds of run time; taking it again adds the time
SPECIALS = {    # dark cards with a mythic glow: each one once per run
    'four': ("EXTRA CARD", "4 cards in every kiosk from now on", (120, 255, 230)),
    'gamble': ("ALL IN", "3x coin drops, coins worth 5x. One hit kills", (255, 200, 40)),
    'invis': ("SHADOW CLOAK", "Unseen. Mythic coins only. Gate: kill 3 spirit-touched", (150, 160, 255)),
    'jackpot': ("JACKPOT", "+1 HP, +1 glass HP, +1 slash and slam damage", (255, 230, 90)),
    'untouch': ("UNTOUCHABLE", "Blade x3, longer dash. Touching enemies hurts", (255, 80, 200)),
    'slammaster': ("SLAM MASTER", "Slam range x3, damage +200%. Blade -70%", (90, 200, 255)),
    'joker': ("JOKER", "No kiosk. Free card every district, 2 every 3rd", (230, 50, 80)),
    'scars': ("BLOOD TRADE", "Each HP you lose: 1 card next district (max 5)", (255, 90, 120)),
}
RANDOM_CARD = ('random', "RANDOM CARD", "50% normal card, 50% special card", (200, 140, 255))
CARD_KANJI = {'attack': '斬', 'ability': '技', 'coins': '金', 'health': '命', 'defense': '守', 'special': '秘', 'key': '出'}
ONE_SHOT_BUFFS = {'onigiri'}                     # used up the moment you take them (not kept in the buff row)
KEY_BUFF = ('key', "EXIT KEY", "Leave the run now and keep your coins", (255, 60, 60))


def card_cat(b):
    """The card's category (for the corner kanji)."""
    if b in SPECIALS:
        return 'special'
    if b == 'key':
        return 'key'
    return next((c for c, d in CARD_CATS.items() if b in d), 'ability')


def card_info(b):
    """(title, description, colour) of any card id: normal, special, the exit key or the random card."""
    if b in BUFFS:
        return BUFFS[b]
    if b in SPECIALS:
        return SPECIALS[b]
    if b == 'random':
        return RANDOM_CARD[1:]
    if b == 'key':
        return KEY_BUFF[1:]
    return (b.upper(), "", RED)


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
    'white': ("WHITE SAMURAI", 1000, samurai((226, 222, 232), (172, 166, 184), (255, 255, 255), (196, 190, 204), (140, 134, 150),
                                            (210, 30, 44), (255, 210, 220), (170, 120, 140),
                                            hair=(222, 40, 58), hood=(214, 212, 224), mask=(40, 36, 46),
                                            hair_down=(235, 235, 240))),
    'crimson': ("CRIMSON SAMURAI", 1500, samurai((34, 22, 28), (22, 14, 18), (150, 34, 46), (26, 18, 22), (16, 10, 14),
                                                (225, 30, 44), (255, 130, 140), (140, 50, 60),
                                                hair=(160, 22, 36), hood=(30, 18, 24), mask=(20, 12, 16))),
    'azure': ("AZURE SAMURAI", 2500, samurai((40, 110, 170), (24, 66, 110), (96, 176, 226), (30, 40, 84), (18, 24, 54),
                                            (84, 226, 255), (150, 236, 255), (60, 140, 196),
                                            hair=(230, 240, 255), hood=(40, 60, 100), mask=(20, 28, 50),
                                            hair_down=(230, 240, 255))),
    'jade': ("JADE SAMURAI", 2500, samurai((34, 92, 70), (20, 58, 44), (90, 170, 130), (26, 50, 42), (16, 32, 26),
                                          (120, 255, 170), (170, 255, 210), (60, 170, 120),
                                          hair=(20, 30, 26), hood=(30, 70, 56), mask=(18, 36, 30), hair_down=(20, 30, 26))),
    'gold': ("GOLDEN SAMURAI", 4000, samurai((150, 112, 30), (100, 72, 18), (240, 200, 90), (60, 44, 20), (38, 28, 12),
                                            (255, 220, 80), (255, 240, 170), (190, 150, 60),
                                            hair=(250, 250, 240), hood=(120, 90, 30), mask=(40, 30, 12), hair_down=(250, 250, 240))),
    'void': ("VOID SAMURAI", 5000, samurai((14, 12, 22), (8, 6, 14), (60, 50, 90), (12, 10, 18), (6, 5, 10),
                                          (120, 60, 255), (200, 160, 255), (80, 50, 170),
                                          hair=(90, 60, 200), hood=(18, 14, 30), mask=(10, 8, 18), hair_down=(90, 60, 200))),
}
PAL_P = SKINS['shadow'][2]
SKIN_PERKS = {   # id: (perk name, what it does, colour) - the starting skin has no perk
    'shadow': ("STANDARD ISSUE", "The original blade. No perks.", (170, 160, 200)),
    'white': ("SILVER EDGE", "+1 damage. SKILL: spirit shield, 1.5s (8s cooldown)", (230, 230, 255)),
    'crimson': ("BLOOD RUSH", "Run 15% faster. SKILL: blood wave (2 dmg, 3s cooldown)", (255, 60, 90)),
    'azure': ("WIND STEP", "Double jump. Run 30% faster.", (120, 230, 255)),
    'jade': ("JADE BREATH", "Heal 1 HP every 12 kills. SKILL: meditation", (120, 255, 170)),
    'gold': ("GILDED", "Coins are worth more. SKILL: thunder step", (255, 220, 80)),
    'void': ("VOID WALKER", "Dash recharges faster. SKILL: time stop", (170, 120, 255)),
}
SKIN_DIFF = {'shadow': 1, 'white': 2, 'crimson': 1.5, 'azure': 1.5,   # enemies per district: the stronger the skin, the busier the streets
             'jade': 1.5, 'gold': 1.5, 'void': 2}
SKIN_SKILLS = {  # skin id: (skill name, kind, cooldown seconds) - bound to the SKILL key
    'white': ("SPIRIT SHIELD", 'shield', 8.0),
    'crimson': ("BLOOD WAVE", 'wave', 3.0),
    'jade': ("MEDITATION", 'heal', 20.0),
    'gold': ("THUNDER STEP", 'tstep', 4.0),
    'void': ("TIME STOP", 'freeze', 16.0),
}
SKIN_DESC = {   # what the skin gives, written out for the player (SKILL key name is filled in at runtime)
    'shadow': ["No perk, no skill: the original blade."],
    'white': ["PERK SILVER EDGE: +1 damage on every slash and super.",
              "SKILL SPIRIT SHIELD [{K}]: 1.5s invulnerable. Cooldown 8s."],
    'azure': ["PERK WIND STEP: double jump in the air and run 30% faster.",
              "No skill on this skin."],
    'crimson': ["PERK BLOOD RUSH: run 15% faster.",
                "SKILL BLOOD WAVE [{K}]: a wave flies forward, 2 damage. Cooldown 3s."],
    'jade': ["PERK JADE BREATH: heal 1 HP every 12 kills.",
             "SKILL MEDITATION [{K}]: heal 1 HP. Cooldown 20s."],
    'gold': ["PERK GILDED: gold coins +1, mythic coins +3.",
             "SKILL THUNDER STEP [{K}]: dash through enemies, 2 damage. Cooldown 4s."],
    'void': ["PERK VOID WALKER: dash recharges 30% faster.",
             "SKILL TIME STOP [{K}]: enemies freeze for 2.5s. Cooldown 16s."],
}
PAL_E = {
    # grounded looks: muted cloth, real skin tones, soft city back-light, no glowing eyes
    'ronin': dict(sc=1, head='hat', weapon='katana', blade=14, skirt=True, skin=(156, 116, 94), straw=(158, 128, 84), straw_d=(112, 88, 56),
                  coat=(60, 56, 78), coat_d=(42, 38, 56), coat_l=(96, 90, 116), pants=(48, 46, 52), pants_d=(32, 30, 36),
                  boot=(30, 26, 26), boot_d=(20, 17, 17), glove=(156, 116, 94), glove_d=(112, 82, 66), belt=(118, 34, 40),
                  eye=(30, 20, 20), eyeglow=(0, 0, 0), line=(12, 8, 12), rim=(196, 186, 214), rim2=(104, 96, 124), hilt=(40, 40, 46)),
    'oni': dict(sc=1.3, head='oni', weapon='club', blade=22, skirt=False, skin=(150, 112, 92), mask=(160, 32, 34),
                coat=(48, 40, 48), coat_d=(30, 26, 32), coat_l=(96, 84, 96), arm=(40, 36, 44), arm_d=(28, 24, 30),
                pants=(36, 34, 40), pants_d=(24, 22, 28), boot=(26, 22, 22), boot_d=(18, 15, 15), glove=(60, 50, 46), glove_d=(40, 34, 30),
                belt=(128, 36, 36), eye=(255, 196, 70), eyeglow=(0, 0, 0), line=(10, 8, 10), rim=(200, 180, 180), rim2=(110, 96, 96),
                armor=True, lace=(150, 40, 44), gilt=(176, 146, 72)),
    'ninja': dict(sc=.9, head='mask', weapon=None, blade=0, skirt=False, coat=(40, 42, 50), coat_d=(28, 30, 36), coat_l=(72, 76, 88),
                  pants=(34, 36, 44), pants_d=(24, 26, 32), boot=(18, 18, 22), boot_d=(12, 12, 16), glove=(34, 36, 44), glove_d=(24, 26, 32),
                  belt=(140, 34, 44), scarf=(140, 34, 44), eye=(190, 186, 170), eyeglow=(0, 0, 0), line=(8, 8, 12),
                  rim=(180, 186, 210), rim2=(96, 100, 120)),
}
def shade_pal(S, k=.55):
    """Darker copy of a palette, for characters moving in the background plane."""
    return {key: (tuple(int(c * k) for c in v) if isinstance(v, tuple) and len(v) == 3 else v) for key, v in S.items()}


PAL_E.update({   # the bosses: the same figures drawn 2x bigger ('zoom') in bright colours that stand out from the night
    'boss_destroyer': dict(samurai((92, 104, 126), (56, 62, 80), (150, 166, 194), (60, 64, 82), (36, 38, 52), (70, 240, 255),
                                   (130, 245, 255), (60, 170, 210), hair=(30, 34, 44), hood=(70, 76, 94), mask=(44, 48, 62),
                                   skin=(170, 180, 192), hair_down=(30, 34, 44)), sc=1.2, zoom=2.4, line=(10, 12, 18)),
    'boss_chaos': dict(PAL_E['ninja'], sc=1.1, zoom=2.4, coat=(34, 22, 56), coat_d=(18, 12, 34), coat_l=(120, 60, 170),
                       pants=(24, 18, 40), pants_d=(14, 10, 26), boot=(14, 10, 20), boot_d=(8, 6, 12),
                       glove=(40, 26, 60), glove_d=(24, 16, 38), belt=(255, 60, 200), scarf=(60, 240, 255),
                       eye=(255, 255, 120), eyeglow=(255, 90, 230), line=(8, 4, 14), rim=(255, 80, 220), rim2=(60, 240, 255)),
    'boss_mutant': dict(PAL_E['oni'], armor=False, sc=1.3, zoom=2.4, skin=(120, 190, 90), mask=(70, 160, 80),
                        coat=(64, 74, 52), coat_d=(38, 44, 30), coat_l=(120, 136, 96), arm=(64, 74, 52), arm_d=(38, 44, 30),
                        pants=(56, 52, 40), pants_d=(34, 30, 24), boot=(34, 28, 22), boot_d=(20, 16, 12),
                        glove=(120, 190, 90), glove_d=(80, 130, 60), belt=(200, 170, 60), eye=(255, 240, 60),
                        eyeglow=(180, 255, 80), line=(8, 12, 6), rim=(170, 255, 120), rim2=(90, 200, 80)),
})
PAL_E.update({   # more street enemies: the yari spearman and the kunoichi
    'yari': dict(PAL_E['ronin'], weapon='spear', blade=26, straw=(46, 40, 52), straw_d=(28, 24, 32),
                 coat=(70, 50, 44), coat_d=(48, 34, 30), coat_l=(112, 84, 72), belt=(170, 140, 70),
                 pants=(40, 38, 46), pants_d=(26, 24, 30)),
    'kunoichi': dict(PAL_E['ninja'], weapon='katana', blade=8, hilt=(60, 20, 30), coat=(58, 26, 44), coat_d=(38, 16, 30),
                     coat_l=(110, 52, 84), pants=(40, 20, 34), pants_d=(26, 12, 22), glove=(58, 26, 44), glove_d=(38, 16, 30),
                     belt=(220, 40, 90), scarf=(220, 40, 90), hair=(20, 16, 24), rim=(255, 150, 200), rim2=(140, 70, 110)),
})
PAL_E.update({   # the radical update: dock riflemen and shield wall, temple warrior monks and the vengeful dead
    'teppo': dict(PAL_E['ronin'], weapon='rifle', blade=18, straw=(40, 44, 60), straw_d=(26, 28, 40),
                  coat=(36, 44, 70), coat_d=(24, 30, 50), coat_l=(70, 84, 120), belt=(200, 170, 80),
                  pants=(30, 34, 48), pants_d=(20, 22, 32), rim=(170, 200, 240)),
    'tate': dict(PAL_E['oni'], armor=False, sc=1.12, weapon='shield', blade=0, mask=(70, 72, 84), coat=(54, 58, 66), coat_d=(36, 38, 46),
                 coat_l=(110, 116, 130), arm=(54, 58, 66), arm_d=(36, 38, 46), belt=(170, 40, 40), rim=(210, 214, 230)),
    'sohei': dict(PAL_E['ronin'], head='hood', weapon='naginata', blade=24, hood=(214, 208, 196), hood_l=(255, 252, 244),
                  coat=(70, 58, 54), coat_d=(46, 38, 36), coat_l=(120, 100, 92), belt=(160, 120, 60), eye=(220, 210, 190),
                  pants=(214, 208, 196), pants_d=(160, 154, 144), rim=(255, 220, 190)),
    'onryo': dict(PAL_E['ninja'], head='ghost', weapon=None, skirt=True, coat=(214, 218, 228), coat_d=(160, 166, 182),
                  coat_l=(255, 255, 255), pants=(200, 204, 214), pants_d=(150, 154, 170), boot=(210, 214, 224),
                  boot_d=(160, 164, 176), glove=(214, 220, 226), glove_d=(170, 176, 186), hair=(10, 8, 14),
                  skin=(226, 232, 238), belt=(150, 160, 180), eye=(255, 60, 60), rim=(150, 220, 255), rim2=(90, 140, 200)),
    'boss_shogun': dict(samurai((34, 28, 32), (18, 14, 18), (210, 168, 70), (90, 16, 24), (56, 10, 16), (255, 204, 70),
                                (255, 226, 150), (190, 130, 40), hair=(20, 18, 24), hood=(40, 30, 30), mask=(170, 24, 34)),
                        head='oni', mask=(176, 26, 36), sc=1.2, zoom=2.4, blade=22, scarf=(170, 20, 34), line=(8, 6, 8)),
})
PAL_E.update({   # the new locations' people: each one fights like an older enemy (LOOKS) but is its own figure
    # Aokigahara: the lost who wander the sea of trees, forest bandits, old hunters with matchlocks
    'wanderer': dict(PAL_E['onryo'], head='hood', hood=(44, 58, 46), hood_l=(96, 130, 96), coat=(52, 66, 50), coat_d=(32, 42, 32),
                     coat_l=(92, 116, 86), pants=(40, 52, 40), pants_d=(26, 34, 26), boot=(40, 52, 40), boot_d=(26, 34, 26),
                     glove=(140, 150, 130), glove_d=(100, 110, 94), belt=(110, 90, 50), eye=(170, 255, 140),
                     eyeglow=(40, 110, 40), rim=(150, 230, 150), rim2=(70, 130, 80)),
    'bandit': dict(PAL_E['ronin'], straw=(96, 82, 52), straw_d=(66, 54, 34), coat=(72, 58, 40), coat_d=(50, 40, 28),
                   coat_l=(110, 92, 64), belt=(70, 120, 60), pants=(44, 52, 40), pants_d=(30, 36, 28), rim=(200, 220, 170)),
    'hunter': dict(PAL_E['teppo'], straw=(60, 66, 40), straw_d=(40, 44, 26), coat=(46, 60, 38), coat_d=(30, 40, 24),
                   coat_l=(84, 104, 66), belt=(150, 110, 60), pants=(40, 44, 32), pants_d=(26, 30, 22), rim=(190, 230, 160)),
    # Kirigamine: tengu of the mountain wind, yamabushi hermits, the snow woman
    'tengu': dict(PAL_E['sohei'], head='tengu', skin=(196, 46, 40), hair=(236, 232, 226), coat=(214, 208, 196),
                  coat_d=(160, 154, 144), coat_l=(255, 252, 244), pants=(60, 60, 70), pants_d=(40, 40, 50),
                  belt=(200, 60, 50), eye=(255, 230, 120), rim=(255, 200, 190), rim2=(150, 120, 120)),
    'yamabushi': dict(PAL_E['yari'], straw=(26, 26, 30), straw_d=(14, 14, 18), coat=(206, 200, 186), coat_d=(150, 144, 132),
                      coat_l=(250, 246, 236), belt=(210, 120, 40), pants=(70, 74, 90), pants_d=(48, 50, 64), rim=(220, 230, 255)),
    'yukionna': dict(PAL_E['onryo'], coat=(206, 230, 250), coat_d=(150, 186, 220), coat_l=(250, 254, 255),
                     pants=(196, 222, 246), pants_d=(150, 180, 214), hair=(214, 232, 250), skin=(236, 244, 255),
                     eye=(120, 220, 255), belt=(90, 150, 210), rim=(170, 230, 255), rim2=(110, 170, 230)),
    # Tenshin Dojo: the training dummies that fight back, students with bokken, the senior pupils
    'mokujin': dict(PAL_E['tate'], head='wood', skin=(156, 108, 62), coat=(140, 96, 56), coat_d=(100, 66, 36),
                    coat_l=(196, 146, 90), arm=(150, 104, 60), arm_d=(108, 72, 40), pants=(124, 86, 50), pants_d=(90, 60, 34),
                    boot=(96, 64, 36), boot_d=(70, 46, 26), glove=(156, 108, 62), glove_d=(110, 74, 40), belt=(60, 40, 24),
                    mask=(150, 104, 60), eye=(255, 190, 110), eyeglow=(90, 40, 10), rim=(255, 210, 150), rim2=(170, 120, 70)),
    'deshi': dict(PAL_E['ronin'], head='samurai', hair=(22, 18, 22), skin=(196, 150, 128), coat=(224, 220, 210),
                  coat_d=(176, 170, 160), coat_l=(255, 252, 244), pants=(34, 40, 70), pants_d=(22, 26, 48),
                  belt=(30, 30, 34), glove=(196, 150, 128), glove_d=(150, 110, 92), steel=(150, 104, 60),
                  steel_l=(206, 156, 100), hilt=(90, 60, 34), rim=(255, 230, 200)),
    'senpai': dict(PAL_E['kunoichi'], coat=(30, 30, 40), coat_d=(18, 18, 26), coat_l=(70, 70, 90), pants=(24, 24, 32),
                   pants_d=(14, 14, 20), glove=(30, 30, 40), glove_d=(18, 18, 26), belt=(200, 40, 40), scarf=(200, 40, 40),
                   rim=(255, 190, 150), rim2=(150, 90, 70)),
})
LOOKS = {'wanderer': 'onryo', 'bandit': 'ronin', 'hunter': 'teppo', 'tengu': 'sohei', 'yamabushi': 'yari',
         'yukionna': 'onryo', 'mokujin': 'tate', 'deshi': 'ronin', 'senpai': 'kunoichi'}
LOOK_HP = {'mokujin': 1.4, 'tengu': 1.25, 'wanderer': 1.2, 'yamabushi': 1.15}
PAL_E.update({   # every location has its own three bosses
    'boss_nio': dict(PAL_E['oni'], armor=False, sc=1.3, zoom=2.4, head='nio', hair=(30, 22, 22), weapon='club', skin=(200, 70, 50), mask=(210, 60, 40),
                     coat=(176, 134, 50), coat_d=(124, 90, 30), coat_l=(236, 196, 96), arm=(200, 70, 50), arm_d=(150, 50, 36),
                     pants=(150, 40, 30), pants_d=(104, 26, 20), glove=(200, 70, 50), glove_d=(150, 50, 36),
                     belt=(240, 200, 90), eye=(255, 230, 120), eyeglow=(255, 120, 40), rim=(255, 200, 120), rim2=(200, 90, 40)),
    'boss_abbot': dict(PAL_E['sohei'], sc=1.2, zoom=2.4, blade=30, hood=(44, 30, 40), hood_l=(110, 70, 90),
                       coat=(120, 30, 40), coat_d=(80, 18, 26), coat_l=(176, 60, 70), belt=(230, 190, 80),
                       pants=(44, 30, 40), pants_d=(28, 18, 26), eye=(255, 90, 60), eyeglow=(160, 20, 20),
                       rim=(255, 180, 120), rim2=(180, 60, 50)),
    'boss_wanderer': dict(PAL_E['wanderer'], sc=1.15, zoom=2.4, eyeglow=(80, 220, 80)),
    'boss_kitsune': dict(PAL_E['kunoichi'], sc=1.1, zoom=2.3, coat=(236, 232, 224), coat_d=(190, 184, 176), coat_l=(255, 255, 250),
                         pants=(200, 194, 186), pants_d=(150, 144, 136), glove=(236, 232, 224), glove_d=(190, 184, 176),
                         belt=(255, 120, 30), scarf=(255, 120, 30), hair=(255, 140, 40), hilt=(255, 120, 30),
                         eye=(255, 220, 80), eyeglow=(255, 140, 40), rim=(255, 180, 90), rim2=(255, 120, 40)),
    'boss_mossoni': dict(PAL_E['oni'], sc=1.3, zoom=2.4, head='moss', coat=(40, 62, 40), coat_d=(26, 40, 26), coat_l=(84, 124, 72),
                         arm=(40, 62, 40), arm_d=(26, 40, 26), mask=(60, 110, 50), lace=(100, 160, 70), gilt=(160, 176, 90),
                         eye=(200, 255, 120), eyeglow=(100, 200, 60), rim=(170, 240, 140), rim2=(80, 150, 70)),
    'boss_tengu': dict(PAL_E['tengu'], sc=1.2, zoom=2.4, blade=12, weapon='fan', eyeglow=(255, 120, 60)),
    'boss_yukionna': dict(PAL_E['yukionna'], sc=1.1, zoom=2.4, eyeglow=(90, 200, 255), weapon='daggers', blade=8),
    'boss_sensei': dict(PAL_E['ronin'], head='sage', weapon='staff', blade=26, sc=1.0, zoom=1.35, skin=(204, 164, 134),
                        hair=(238, 238, 242), straw=(180, 150, 96), straw_d=(124, 98, 60), coat=(56, 60, 84),
                        coat_d=(36, 40, 58), coat_l=(98, 104, 140), pants=(40, 36, 46), pants_d=(26, 24, 30),
                        glove=(204, 164, 134), glove_d=(156, 120, 98), belt=(210, 176, 96), scarf=(210, 176, 96), gilt=(220, 190, 100),
                        eye=(40, 30, 30), eyeglow=(0, 0, 0), rim=(220, 224, 255), rim2=(120, 126, 170)),
    'boss_mokujin': dict(PAL_E['mokujin'], sc=1.3, zoom=2.4, weapon='club', blade=20, armor=False, headband=(220, 30, 40),
                         belt=(220, 30, 40)),
    'boss_tomoe': dict(samurai((226, 222, 232), (170, 164, 182), (255, 255, 255), (120, 20, 34), (80, 12, 22), (230, 40, 60),
                               (255, 200, 210), (170, 90, 110), hair=(20, 16, 24), hood=(60, 20, 30), mask=(40, 20, 26)),
                       weapon='naginata', blade=30, sc=1.1, zoom=2.2, line=(10, 6, 10)),
    'boss_brother': dict(samurai((40, 22, 28), (24, 12, 16), (112, 40, 52), (26, 20, 24), (16, 12, 14), (230, 40, 60),
                                 (255, 140, 150), (150, 50, 60), hair=(232, 232, 238), hood=(40, 22, 28), mask=(24, 12, 16),
                                 hair_down=(232, 232, 238)), zoom=1.2),
})
PAL_E['boss_shogun3'] = dict(PAL_E['boss_shogun'], coat=(34, 22, 56), coat_d=(18, 12, 34), coat_l=(140, 70, 200),
                             arm=(34, 22, 56), arm_d=(18, 12, 34), mask=(120, 40, 200), belt=(255, 60, 200),
                             scarf=(60, 240, 255), eye=(255, 255, 120), rim=(255, 80, 220), rim2=(60, 240, 255))
PAL_BACK = {k: shade_pal(v) for k, v in PAL_E.items()}
_TIER_PAL = {}


def tier_pal(kind, tier, back=False):
    """Stronger districts dress their enemies up: gold trim after district 5, a red war-paint glow after district 10."""
    key = (kind, tier, back)
    if key not in _TIER_PAL:
        S = dict(PAL_BACK[kind] if back else PAL_E[kind])
        if tier >= 1 and not back:
            S.update(belt=(230, 190, 70), rim=(255, 226, 150), scarf=(230, 190, 70) if 'scarf' in S else None)
            if S['scarf'] is None:
                del S['scarf']
        if tier >= 2 and not back:
            S.update(eye=(255, 60, 60), eyeglow=(150, 10, 20), rim=(255, 120, 110), belt=(220, 30, 40))
        _TIER_PAL[key] = S
    return _TIER_PAL[key]
STAT_ROWS = [("TOTAL KILLS", 'kills'), ("COINS EARNED", 'coins'), ("TIME PLAYED", 'time'), ("RUNS SURVIVED", 'runs'),
             ("DISTRICTS CLEARED", 'levels'), ("DEATHS", 'deaths'), ("MOST COINS IN A RUN", 'best'), ("PARRIES", 'parries'),
             ("NEON SHINJUKU RUNS", 'won0'), ("TEMPLE HEIGHTS RUNS", 'won1'), ("AOKIGAHARA RUNS", 'won2'),
             ("KIRIGAMINE RUNS", 'won3'), ("TENSHIN DOJO RUNS", 'won4')]
STAT_HIDDEN = ('mythic', 'supers', 'oni', 'shinobi', 'slams')    # still counted, no longer shown
PROFILE_DEFAULTS = {'name': "NAMELESS", 'wallet': 0, 'skins': ['shadow'], 'skin': 'shadow', 'upg': {}, 'cleared': []}
# permanent upgrades, bought for each skin on its own (save: upg = {skin: {id: level}}): id, name, what one level gives, prices per level (no jump or speed upgrades on purpose)
UPGRADES = [('blade', "SHARPENED BLADE", "+1 sword damage", "刃", (700, 1000, 1500, 2200, 3000)),
            ('slam', "HEAVY SLAM", "+1 slam damage, wider shockwave", "撃", (500, 900, 1300, 1900, 2600)),
            ('skin', "SKIN MASTERY", "Skin skill recharges 15% faster", "技", (1000, 1500, 2000)),
            ('vital', "IRON BODY", "+1 max HP at the start of a run", "体", (800, 1200, 1500, 2200, 3000)),
            ('focus', "FOCUS", "Super charges 10% faster", "気", (500, 700, 1000, 1500, 2100)),
            ('guard', "STEADY GUARD", "Parry window 15% longer", "守", (500, 1000, 1200, 1800, 2500))]
# the Shadow Samurai has no skill to master: his own upgrade instead
ROLL_UPG = ('roll', "ROLL CARDS", "Re-roll the kiosk cards once per district", "札", (5000,))
UPG_CAPS = (0, 3, 4, 5)        # upgrade levels open: none before Neon Shinjuku is cleared, then 3 / 4 (Temple Heights) / 5
UPG_GATES = {'skin': (0, 1, 3)}  # Skin Mastery: level 1 always, level 2 after the 1st location, level 3 after the 3rd


def upgrade_list(sid):
    """The upgrades a skin can buy (the Shadow Samurai swaps SKIN MASTERY for ROLL CARDS)."""
    return [ROLL_UPG if (u[0] == 'skin' and sid == 'shadow') else u for u in UPGRADES]
NAMES = ["KAGE", "RYU", "HAYATE", "KENSHIN", "AKAME", "SHIRO", "TSUKI", "RAIDEN", "YORU", "KAZE", "JIN", "MUSASHI"]


def R(a, b):
    return random.uniform(a, b)


def lerp(a, b, k):
    return a + (b - a) * k


def ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


def out_back(k, o=1.4):
    """Ease out with a small overshoot: the 'pop' of a card landing."""
    k = max(0.0, min(1.0, k)) - 1
    return 1 + k * k * ((o + 1) * k + o)


def in_cubic(k):
    k = max(0.0, min(1.0, k))
    return k * k * k


def silhouette(img, col, a=255):
    """A one-colour copy of a transparent surface (a card's shadow)."""
    sil = img.copy()
    sil.fill((0, 0, 0), special_flags=pg.BLEND_RGB_MULT)
    sil.fill(col, special_flags=pg.BLEND_RGB_ADD)
    if a < 255:
        sil.set_alpha(a)
    return sil


def ov(a, b):
    return a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]


def sk_col(sk):
    return {'wave': (255, 60, 90), 'heal': (120, 255, 170), 'tstep': (255, 220, 80),
            'freeze': (170, 120, 255)}.get(sk[1], (200, 200, 255))


def fmt_time(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec // 60 % 60, sec % 60
    hu, mu, su = ("ч", "м", "с") if LANG == 'ru' else ("h", "m", "s")
    return f"{h}{hu} {m:02d}{mu}" if h else f"{m}{mu} {s:02d}{su}"


# ---------------------------------------------------------------- persistent stats
def load_stats():
    """Stats + profile (name, coin wallet, owned/equipped skins) live in one save file."""
    st = {k: 0 for k in [k for _, k in STAT_ROWS] + list(STAT_HIDDEN)}
    st.update({k: (list(v) if isinstance(v, list) else v) for k, v in PROFILE_DEFAULTS.items()})
    try:
        with open(SAVE, encoding='utf-8') as fh:
            data = json.load(fh)
        if isinstance(data, dict):                       # (a broken or hand-edited file must never stop the game)
            st.update(data)
    except (OSError, ValueError, TypeError):
        pass
    for k, v in list(st.items()):                        # repair wrong types with the defaults
        if k in PROFILE_DEFAULTS:
            d = PROFILE_DEFAULTS[k]
            if not isinstance(v, type(d)) or (isinstance(d, int) and isinstance(v, bool)):
                st[k] = list(d) if isinstance(d, list) else (dict(d) if isinstance(d, dict) else d)
        elif not isinstance(v, (int, float)) or isinstance(v, bool):
            st[k] = 0
    st['skins'] = [x for x in st['skins'] if x in SKINS] or ['shadow']
    if 'shadow' not in st['skins']:
        st['skins'].insert(0, 'shadow')
    if st['skin'] not in st['skins']:
        st['skin'] = 'shadow'
    ids = {x[0] for x in UPGRADES} | {ROLL_UPG[0]}

    def clean(d):
        return {u: max(0, min(5, int(l))) for u, l in d.items()
                if u in ids and isinstance(l, (int, float)) and not isinstance(l, bool)}
    raw = st['upg']
    if raw and all(k in ids for k in raw):                    # old save: one shared set -> the skin worn back then
        raw = {st['skin']: raw}
    st['upg'] = {sid: clean(d) for sid, d in raw.items() if sid in SKINS and isinstance(d, dict)}
    st['wallet'] = max(0, st['wallet'])
    st['cleared'] = sorted({c for c in st['cleared'] if isinstance(c, int) and not isinstance(c, bool) and 0 <= c < 5})
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
            data = json.load(fh)
        if isinstance(data, dict):                       # (a broken or hand-edited file must never stop the game)
            st.update(data)
    except (OSError, ValueError, TypeError):
        pass
    for k, d in DEFAULT_SETTINGS.items():                # wrong types / out-of-range values fall back to the defaults
        v = st.get(k)
        if isinstance(d, bool):
            if not isinstance(v, bool):
                st[k] = d
        elif isinstance(d, float):
            st[k] = max(0.0, min(1.0, float(v))) if isinstance(v, (int, float)) and not isinstance(v, bool) else d
        elif isinstance(d, int):
            ok = isinstance(v, int) and not isinstance(v, bool)
            size = len(RAIN_LEVELS) if k == 'rain' else (4 if k == 'diff' else len(ADMIN_CYCLE.get(k, ())) or 10 ** 6)
            st[k] = v if ok and 0 <= v < size else d
        elif isinstance(d, str) and not isinstance(v, str):
            st[k] = d
    if st['lang'] not in ('en', 'ru'):
        st['lang'] = 'ru'

    def as_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    kb, pad = dict(DEFAULT_KB), dict(DEFAULT_PAD)       # bindings saved as {action: key/button}
    raw_kb, raw_pad = st.get('kb'), st.get('pad')
    if isinstance(raw_kb, dict):
        kb.update({k: as_int(v) for k, v in raw_kb.items() if k in kb and as_int(v) is not None})
    if isinstance(raw_pad, dict):
        pad.update({k: (v if v in ('LT', 'RT') else as_int(v)) for k, v in raw_pad.items()
                    if k in DEFAULT_PAD and (v in ('LT', 'RT') or as_int(v) is not None)})
    st['kb'], st['pad'] = kb, pad
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
        'snap': synth(.18, .5, L_('noise', 1, gain=1.4, decay=140, lpf=.95), L_('sin', 2300, 1700, .5, 70),
                      L_('noise', 1, gain=.3, decay=30, lpf=.25, start=.01)),
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
        'bwave': synth(.3, .35, L_('saw', 420, 160, .4, 10, .25), L_('noise', 1, gain=.5, decay=20, lpf=.3)),
        'sel': synth(.06, .15, L_('sq', 880, gain=.5, decay=40, lpf=.4), L_('sin', 1760, gain=.3, decay=50)),
    }
except Exception:
    SFX = {}


def sfx(n):
    if n in SFX:
        SFX[n].play()


# ---------------------------------------------------------------- drawing helpers
_glow, _smoke, _touch = {}, {}, {}


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


# ---------------------------------------------------------------- Russian text (English string -> Russian)
RU = {
    # main menu, general
    "W/S select   ENTER confirm   F11 fullscreen": "W/S выбор   ENTER подтвердить   F11 полный экран",
    "D-PAD select   A confirm   B back": "D-PAD выбор   A подтвердить   B назад",
    "START": "СТАРТ", "QUIT": "ВЫХОД", "NEW RUN": "НОВАЯ ИГРА", "RESUME": "ПРОДОЛЖИТЬ",
    "RESTART": "ЗАНОВО", "MAIN MENU": "ГЛАВНОЕ МЕНЮ", "RETRY": "ЕЩЁ РАЗ", "BACK": "НАЗАД",
    "< BACK": "< НАЗАД", "SKINS >": "СКИНЫ >", "STATS": "СТАТИСТИКА", "SKINS": "СКИНЫ",
    "SETTINGS": "НАСТРОЙКИ", "CONTROLS": "КЛАВИШИ", "PRESS...": "НАЖМИТЕ...",
    "v3: 10 districts, bosses, Russian": "v3: 10 районов, боссы, русский язык",
    "DESTROYER": "РАЗРУШИТЕЛЬ", "CHAOSMAKER": "ТВОРЕЦ ХАОСА", "MUTANT": "МУТАНТ",
    "KILL HALF THE ENEMIES": "УБЕЙТЕ ХОТЯ БЫ ПОЛОВИНУ ВРАГОВ", "ENEMIES": "ВРАГИ", "MORE ENEMIES": "ВРАГОВ БОЛЬШЕ",
    "BOSS DEFEATED": "БОСС ПОВЕРЖЕН", "ENRAGED": "ЯРОСТЬ!", "DEFEAT THE BOSS": "ПОБЕДИТЕ БОССА",
    "  - level.mp3 NOT FOUND in ": "  - level.mp3 НЕ НАЙДЕН в ",
    "LEFT/RIGHT choose     ENTER / A buy or equip     ESC / B back      more skins soon":
        "ВЛЕВО/ВПРАВО выбор   ENTER / A купить или надеть   ESC / B назад",
    "LEFT/RIGHT choose   ": "ВЛЕВО/ВПРАВО выбор   ",
    "ENTER / CLICK take   ESC leave": "ENTER / КЛИК взять   ESC выйти",
    "A take   B leave": "A взять   B выйти",
    "press to continue": "нажмите, чтобы продолжить",
    "ESC skip": "ESC пропуск",
    "ESC to cancel": "ESC — отмена",
    # settings
    "SOUND": "ЗВУК", "MASTER VOLUME": "ОБЩАЯ ГРОМКОСТЬ", "MUSIC": "МУЗЫКА", "EFFECTS": "ЭФФЕКТЫ",
    "VIDEO": "ВИДЕО", "FULLSCREEN": "ПОЛНЫЙ ЭКРАН", "SCREEN SHAKE": "ТРЯСКА ЭКРАНА", "RAIN": "ДОЖДЬ",
    "CRT FILTER": "ФИЛЬТР CRT", "INPUT": "ВВОД", "GAMEPAD VIBRATION": "ВИБРАЦИЯ ГЕЙМПАДА",
    "GAME": "ИГРА", "LANGUAGE": "ЯЗЫК", "ADMIN": "АДМИН", "DAMAGE": "УРОН", "FLY": "ПОЛЁТ", "NOCLIP": "СКВОЗЬ СТЕНЫ",
    "SPEED": "СКОРОСТЬ", "JUMP": "ПРЫЖОК", "INFINITE KILLS": "БЕСКОНЕЧНЫЕ УБИЙСТВА", "INFINITE MONEY": "БЕСКОНЕЧНЫЕ ДЕНЬГИ",
    "UNLOCK ALL SKINS": "ОТКРЫТЬ ВСЕ СКИНЫ", "REMOVE SKINS": "УДАЛИТЬ СКИНЫ", "MAX UPGRADES": "МАКС. УЛУЧШЕНИЯ",
    "REMOVE UPGRADES": "УДАЛИТЬ УЛУЧШЕНИЯ", "DO IT": "ВЫПОЛНИТЬ", "DONE": "ГОТОВО", "UPGRADES": "УЛУЧШЕНИЯ", "UPGRADES >": "УЛУЧШЕНИЯ >", "MAX": "МАКС",
    "SHARPENED BLADE": "ЗАТОЧЕННЫЙ КЛИНОК", "+1 sword damage": "+1 урон мечом", "HEAVY SLAM": "ТЯЖЁЛЫЙ УДАР",
    "+1 slam damage, wider shockwave": "+1 урон удара о землю, шире волна", "SKIN MASTERY": "МАСТЕРСТВО СКИНА",
    "Skin skill recharges 15% faster": "Навык скина на 15% быстрее", "IRON BODY": "ЖЕЛЕЗНОЕ ТЕЛО",
    "+1 max HP at the start of a run": "+1 макс. HP в начале забега", "FOCUS": "КОНЦЕНТРАЦИЯ",
    "Super charges 10% faster": "Супер заряжается на 10% быстрее", "STEADY GUARD": "ТВЁРДЫЙ БЛОК",
    "Parry window 15% longer": "Окно парирования на 15% дольше", "THE RED DOOR IS OPEN": "КРАСНАЯ ДВЕРЬ ОТКРЫТА", "COMING SOON": "СКОРО", "STANDARD RUN": "ОБЫЧНЫЙ ЗАБЕГ", "INFINITE RUN": "БЕСКОНЕЧНЫЙ",
    "15 districts": "15 районов", "No limit, random bosses": "Без конца, случайные боссы", "START": "СТАРТ",
    "Rain waits for you": "Дождь ждёт тебя", "Snow on the thousand steps": "Снег на тысяче ступеней",
    "The trees remember": "Деревья помнят", "Above the clouds, the wind": "Над облаками ветер",
    "Where blades are born": "Где рождаются клинки", "AOKIGAHARA FOREST": "ЛЕС АОКИГАХАРА",
    "KIRIGAMINE PEAKS": "ПИКИ КИРИГАМИНЭ", "TENSHIN DOJO": "ДОДЗЁ ТЭНСИН", "Music and blade volume": "Громкость музыки и клинков",
    "Screen, rain, CRT glow": "Экран, дождь, CRT", "Gamepad and keys": "Геймпад и клавиши", "Language and tests": "Язык и тесты",
    "UP/DOWN select   LEFT/RIGHT change   ENTER / A confirm   ESC / B back":
        "ВВЕРХ/ВНИЗ выбор  ВЛЕВО/ВПРАВО  ENTER/A ок  ESC/B назад",
    "LIGHT": "СЛАБЫЙ", "MEDIUM": "СРЕДНИЙ", "HEAVY": "СИЛЬНЫЙ", "ON": "ВКЛ", "OFF": "ВЫКЛ",
    # controls
    "MOVE LEFT": "ВЛЕВО", "MOVE RIGHT": "ВПРАВО", "AIM UP": "ПРИЦЕЛ ВВЕРХ",
    "AIM DOWN / SLAM": "ПРИЦЕЛ ВНИЗ / УДАР", "JUMP": "ПРЫЖОК", "SLASH": "УДАР", "DASH": "РЫВОК",
    "CROUCH / SLIDE": "ПРИСЕСТЬ / СКОЛЬЖЕНИЕ", "PARRY": "ПАРИРОВАНИЕ", "SUPER": "СУПЕР",
    "SKILL": "НАВЫК", "USE": "ИСПОЛЬЗОВАТЬ", "PAUSE": "ПАУЗА", "RESET TO DEFAULTS": "СБРОС НАСТРОЕК",
    "KEYBOARD / MOUSE": "КЛАВИАТУРА", "XBOX CONTROLLER": "ГЕЙМПАД XBOX",
    "STICK / D-PAD": "СТИК / D-PAD", "NO CONTROLLER CONNECTED": "ГЕЙМПАД НЕ ПОДКЛЮЧЁН",
    "PAD:": "ГЕЙМПАД:", "SKILL: NONE": "НАВЫК: НЕТ",
    "MOVE ON PAD: LEFT STICK / D-PAD      ENTER / A: rebind      ESC: cancel / back":
        "ДВИЖЕНИЕ: ЛЕВЫЙ СТИК / D-PAD   ENTER/A: назначить   ESC: назад",
    "PRESS A KEY FOR ": "НАЖМИТЕ КЛАВИШУ ДЛЯ ", "PRESS A PAD BUTTON FOR ": "НАЖМИТЕ КНОПКУ ДЛЯ ",
    "DASH ": "РЫВОК ", "DOWN+": "ВНИЗ+", "jump": "прыжок", "slam": "удар вниз", "slash": "удар",
    "parry": "парир.", "dash": "рывок", "slide": "скольж.",
    # stats and results
    "TOTAL KILLS": "ВСЕГО УБИЙСТВ", "COINS EARNED": "МОНЕТ ЗАРАБОТАНО", "MYTHIC COINS": "МИФИЧЕСКИХ МОНЕТ",
    "TIME PLAYED": "ВРЕМЯ В ИГРЕ", "RUNS SURVIVED": "ЗАБЕГОВ ПРОЙДЕНО", "DISTRICTS CLEARED": "РАЙОНОВ ПРОЙДЕНО",
    "DEATHS": "СМЕРТЕЙ", "BEST RUN": "ЛУЧШИЙ ЗАБЕГ", "PARRIES": "ПАРИРОВАНИЙ", "SUPERS": "СУПЕРУДАРОВ",
    "ONI SLAIN": "ОНИ УБИТО", "SHINOBI SLAIN": "СИНОБИ УБИТО", "GROUND SLAMS": "УДАРОВ ОБ ЗЕМЛЮ",
    "TIME": "ВРЕМЯ", "KILLS": "УБИЙСТВ", "DISTRICT": "РАЙОН", "DISTRICTS": "РАЙОНЫ", "COINS": "МОНЕТ",
    "COINS LOST": "МОНЕТ ПОТЕРЯНО", "WALLET": "КОШЕЛЁК", "RUN COMPLETE": "ЗАБЕГ ЗАВЕРШЁН",
    "ESCAPED": "СБЕЖАЛ", "YOU DIED": "ВЫ ПОГИБЛИ", "Your coins scatter in the rain...": "Ваши монеты рассыпались под дождём...",
    "All districts are behind you.": "Все районы остались позади.",
    "The exit key turns. You live to cut another night.": "Ключ выхода поворачивается. Вы живы и готовы к следующей ночи.",
    "EQUIPPED": "НАДЕТ", "OWNED": "КУПЛЕН", "OWNED - EQUIP": "КУПЛЕН - НАДЕТЬ", "OFF ": "ВЫКЛ ",
    # shop and kiosk
    "SHINOBI  KIOSK": "КИОСК СИНОБИ", "SHINOBI KIOSK": "КИОСК СИНОБИ", "OPEN KIOSK": "ОТКРЫТЬ КИОСК",
    "SOLD OUT": "ПРОДАНО", "EXIT KEY": "КЛЮЧ ВЫХОДА", "Leave the run now and keep your coins": "Уйти сейчас и сохранить монеты",
    "LEAVE": "УЙТИ", "YOU DIED ": "ВЫ ПОГИБЛИ ",
    "ENTER / A: change name": "ENTER / A: сменить имя",
    "type your name  -  ENTER save  -  ESC cancel": "введите имя  -  ENTER сохранить  -  ESC отмена",
    "UP/DOWN letter  RIGHT add  LEFT delete  Y random  A save": "ВВЕРХ/ВНИЗ буква  ВПРАВО добавить  ВЛЕВО стереть  Y случайная  A сохранить",
    "PERK:": "ПЕРК:", "SUPER": "СУПЕР", "SKILL:": "НАВЫК:",
    "NAMELESS": "БЕЗЫМЯННЫЙ",
    # skins
    "SHADOW SAMURAI": "ТЕНЕВОЙ САМУРАЙ", "CRIMSON SAMURAI": "АЛЫЙ САМУРАЙ", "WHITE SAMURAI": "БЕЛЫЙ САМУРАЙ",
    "AZURE SAMURAI": "ЛАЗУРНЫЙ САМУРАЙ", "STANDARD ISSUE": "СТАНДАРТНЫЙ ОБРАЗЕЦ",
    "The original blade. No perks.": "Оригинальный клинок. Без перков.",
    "SILVER EDGE": "СЕРЕБРЯНАЯ КРОМКА",
    "+1 damage. SKILL: spirit shield, 1.5s (8s cooldown)": "+1 урон. НАВЫК: духовный щит, 1.5 с (откат 8 с)",
    "BLOOD RUSH": "КРОВАВЫЙ РЫВОК",
    "Run 15% faster. SKILL: blood wave (2 dmg, 3s cooldown)": "Бег на 15% быстрее. НАВЫК: кровавая волна (2 урона, откат 3 с)",
    "Double jump. Run 30% faster.": "Двойной прыжок. Бег на 30% быстрее.",
    "WIND STEP": "ПОРЫВ ВЕТРА", "SPIRIT SHIELD": "ДУХОВНЫЙ ЩИТ", "BLOOD WAVE": "КРОВАВАЯ ВОЛНА",
    "No perk, no skill: the original blade.": "Без перков и навыков: оригинальный клинок.",
    "PERK SILVER EDGE: +1 damage on every slash and super.": "ПЕРК СЕРЕБРЯНАЯ КРОМКА: +1 урон удара и супера.",
    "SKILL SPIRIT SHIELD [{K}]: 1.5s invulnerable. Cooldown 8s.": "НАВЫК ДУХОВНЫЙ ЩИТ [{K}]: 1.5 с неуязвимости, откат 8 с",
    "PERK WIND STEP: double jump in the air and run 30% faster.": "ПЕРК ПОРЫВ ВЕТРА: двойной прыжок, бег на 30% быстрее.",
    "No skill on this skin.": "На этом скине навыка нет.",
    "PERK BLOOD RUSH: run 15% faster.": "ПЕРК КРОВАВЫЙ РЫВОК: бег на 15% быстрее.",
    "SKILL BLOOD WAVE [{K}]: a wave flies forward, 2 damage. Cooldown 3s.": "НАВЫК КРОВАВАЯ ВОЛНА [{K}]: 2 урона, откат 3 с",
    # buffs (kiosk)
    "VITAL SPIRIT": "ЖИЗНЕННАЯ СИЛА", "+1 max HP and heal fully": "+1 макс. HP и полное исцеление",
    "RAZOR EDGE": "БРИТВЕННОЕ ЛЕЗВИЕ", "+1 damage on every slash": "+1 урон каждого удара",
    "Run 15% faster": "Бег на 15% быстрее", "GHOST DASH": "РЫВОК ПРИЗРАКА",
    "Dash recharges 40% faster": "Рывок перезаряжается на 40% быстрее", "COIN MAGNET": "МАГНИТ ДЛЯ МОНЕТ",
    "Coins fly to you from afar": "Монеты летят к вам издалека", "BLOOD OATH": "КРОВАВАЯ КЛЯТВА",
    "Heal 1 HP every 8 kills": "Лечение 1 HP за каждые 8 убийств", "STORM HEART": "СЕРДЦЕ БУРИ",
    "Super charges twice as fast": "Супер заряжается вдвое быстрее", "IRON WILL": "ЖЕЛЕЗНАЯ ВОЛЯ",
    "Parry window +60%": "Окно парирования +60%", "GOLD RUSH": "ЗОЛОТАЯ ЛИХОРАДКА",
    "Gold coins are worth 2": "Золотые монеты стоят 2",
    "+1 max HP and heal 1 HP": "+1 макс. HP и лечение 1 HP",
    "+1 damage on ground slams": "+1 урон удара о землю",
    "SHADOW STEP": "ТЕНЕВОЙ ШАГ", "Dashing through enemies cuts each for 1": "Рывок сквозь врагов режет каждого на 1",
    "RAGE": "ЯРОСТЬ", "+50% damage while you are at 1 HP": "+50% урона, когда у тебя 1 HP",
    "Gold coins worth 2x for 3 minutes": "Золотые монеты x2 на 3 минуты",
    "Enemies drop 2x coins for 3 minutes": "Враги роняют x2 монет 3 минуты",
    "FIELD MEDIC": "ПОЛЕВОЙ ЛЕКАРЬ", "10% of enemies drop a heart: +1 HP": "10% врагов роняют сердце: +1 HP",
    "SPIRIT WARD": "ДУХОВНЫЙ ОБЕРЕГ", "A ward blocks 1 hit, back every 4 minutes": "Оберег блокирует 1 удар, снова каждые 4 мин",
    "GLASS SKIN": "СТЕКЛЯННАЯ КОЖА", "+20% of max HP as glass HP (can't heal)": "+20% макс. HP стеклянным HP (не лечится)",
    "EXTRA CARD": "ЛИШНЯЯ КАРТА", "4 cards in every kiosk from now on": "Теперь 4 карты в каждом киоске",
    "GAMBLE": "АЗАРТ", "3x coin drops, coins worth 5x. One hit kills": "x3 монет с врагов, монеты x5. Один удар убивает",
    "INVISIBILITY": "НЕВИДИМОСТЬ", "Unseen. Mythic coins only. Gate: kill 3 spirit-touched": "Тебя не видят. Только мифич. монеты. Врата: убей 3 одержимых",
    "TOUCH LAYOUT": "РАСКЛАДКА КНОПОК", "CALIBRATE TOUCH": "КАЛИБРОВКА ЭКРАНА", "FLOATING STICK": "ПЛАВАЮЩИЙ СТИК",
    "BUTTON OPACITY": "ПРОЗРАЧНОСТЬ КНОПОК", "TOUCH CALIBRATION": "КАЛИБРОВКА ЭКРАНА", "MOVE": "ХОД",
    "tap the exact center of the target": "нажми точно в центр мишени",
    "so every button reacts right where you press it": "чтобы кнопки срабатывали ровно там, где жмёшь",
    "drag to move  -  tap, then - / + to resize": "тяни - сдвинуть,  нажми и -/+ - размер",
    "RESET": "СБРОС",
    "SPIRITS": "ОДЕРЖИМЫЕ", "KILL 3 SPIRIT-TOUCHED": "УБЕЙ 3 ОДЕРЖИМЫХ", "SHADOW STRIKE": "УДАР ИЗ ТЕНИ",
    "JACKPOT": "ДЖЕКПОТ", "+1 HP, +1 glass HP, +1 slash and slam damage": "+1 HP, +1 стекл. HP, +1 урон удара и удара о землю",
    "UNTOUCHABLE": "НЕПРИКАСАЕМЫЙ", "Blade cuts 3x harder, touching enemies hurts": "Клинок режет x3, касание врагов ранит",
    "SLAM MASTER": "МАСТЕР УДАРА", "Slam range x2, damage +300%. Blade -70%": "Удар о землю: радиус x2, урон +300%. Клинок -70%",
    "JOKER": "ДЖОКЕР", "No kiosk. Free card every district, 2 every 3rd": "Без киоска. Карта каждый район, 2 каждый 3-й",
    "BLOOD TRADE": "КРОВАВЫЙ ОБМЕН", "Each HP you lose: 1 card next district (max 5)": "Каждое потерянное HP: 1 карта в след. районе (макс. 5)",
    "STILL MIND": "ЯСНЫЙ РАЗУМ", "RIPOSTE": "РИПОСТ", "ALL IN": "ВА-БАНК", "SHADOW CLOAK": "ПЛАЩ ТЕНИ",
    "Enemies below 50% HP die in one cut": "Враги с HP ниже 50% гибнут от одного удара",
    "Gold coins worth 3 for 3 min. Again: +3 min": "Золотые монеты стоят 3, 3 мин. Ещё раз: +3 мин",
    "+2 coins per kill for 3 min. Again: +3 min": "+2 монеты за убийство, 3 мин. Ещё раз: +3 мин",
    "Heal 2 HP. At full HP: +1 glass HP": "Лечит 2 HP. При полном HP: +1 стекл. HP",
    "5% of enemies drop a heart, for 5 districts": "5% врагов роняют сердце, 5 районов",
    "Blade x3, longer dash. Touching enemies hurts": "Клинок x3, рывок длиннее. Касание врагов ранит",
    "Slam range x3, damage +200%. Blade -70%": "Удар о землю: радиус x3, урон +200%. Клинок -70%",
    "districts left": "районов осталось",
    "RANDOM CARD": "СЛУЧАЙНАЯ КАРТА", "50% normal card, 50% special card": "50% обычная карта, 50% особая",
    "FREE CARDS": "КАРТЫ В ПОДАРОК", "TAKE THE CARD": "ВОЗЬМИ КАРТУ", "TAKE THE CARDS": "ВОЗЬМИ КАРТЫ",
    "CONTINUE": "ДАЛЕЕ", "CLOSED": "ЗАКРЫТО",
    # dialog, phrases, chatter
    "...Where am I?": "...Где я?", "VOICE": "ГОЛОС",
    "Neo-Tokyo. Shinjuku, Sector 9. The rain never stops here.": "Нео-Токио. Синдзюку, сектор 9. Здесь дождь не прекращается никогда.",
    "Fifteen districts stand between you and the way out. The doors close behind you.": "Между вами и выходом пятнадцать районов. Двери закрываются за спиной.",
    "Coins of light lie scattered across the rooftops. Gold... and the rare mythic ones.": "Монеты света разбросаны по крышам. Золотые... и редкие мифические.",
    "And the ones with swords?": "А те, с мечами?",
    "The Shogun's ronin, his oni and his shinobi. Cut them down.": "Ронины Сёгуна, его они и синоби. Режьте их.",
    "The rain remembers every blade.": "Дождь помнит каждый клинок.",
    "Neon bleeds. You don't.": "Неон истекает кровью. Вы — нет.",
    "Deeper into Shinjuku...": "Глубже в Синдзюку...",
    "The Shogun is watching.": "Сёгун наблюдает.",
    "Steel sings in the dark.": "Сталь поёт в темноте.",
    "No way back. Only forward.": "Пути назад нет. Только вперёд.",
    "Every door closes behind you.": "Каждая дверь закрывается за вами.",
    "The city hums a funeral song.": "Город напевает похоронную песню.",
    "Your blade is still thirsty.": "Ваш клинок всё ещё жаждет.",
    "Masks in the alleys. Eyes on the roofs.": "Маски в переулках. Глаза на крышах.",
    "Breathe. Draw. Cut.": "Дышите. Выхватите. Режьте.",
    "The night is long. Longer still.": "Ночь длинна. Ещё длиннее.",
    "Somewhere a bell rings for the fallen.": "Где-то звонит колокол по павшим.",
    "Even the neon is afraid of you now.": "Даже неон теперь боится вас.",
    "You've done it.": "Вы справились.",
    "Fifteen districts. Fifteen doors. All of them behind you now.": "Пятнадцать районов. Пятнадцать дверей. Все они теперь позади.",
    "The rain stops - just for a moment.": "Дождь стихает — всего на миг.",
    "The Shogun will remember this name.": "Сёгун запомнит это имя.",
    "Rain again...": "Опять дождь...", "The Shogun pays well.": "Сёгун платит щедро.",
    "Did you hear that?": "Вы слышали?", "My feet are killing me.": "Ноги гудят.",
    "Ramen after the shift?": "Рамен после смены?", "...heh.": "...хе.", "Quiet night.": "Тихая ночь.",
    "Who's up on the roofs?": "Кто там, на крышах?", "I hate this district.": "Ненавижу этот район.",
    "Yes, boss.": "Да, босс.", "No sign of him.": "Его нигде нет.", "...uh-huh.": "...угу.",
    "I'll call you back.": "Перезвоню.", "Tell her I'm working late.": "Скажи ей, что задерживаюсь на работе.",
    "The rain? Still raining.": "Дождь? Всё ещё льёт.",
    "...": "...",
    # v4: no slide, the boss arena, new cards, new skins
    "CROUCH": "ПРИСЕСТЬ", "crouch": "присесть",
    "THE GATE IS SEALED": "ВРАТА ЗАПЕЧАТАНЫ", "THE WAY DOWN IS OPEN": "ПУТЬ ВНИЗ ОТКРЫТ",
    "THE CAVE OPENS": "ПЕЩЕРА ОТКРЫВАЕТСЯ", "ENTER": "ВОЙТИ",
    "THE GROUND BREAKS OPEN": "ЗЕМЛЯ РАСКАЛЫВАЕТСЯ",
    "AMBUSH!": "ЗАСАДА!", "TREASURE!": "СОКРОВИЩЕ!", "NEON SHINJUKU": "НЕОНОВЫЙ СИНДЗЮКУ",
    "RYUGU DOCKS": "ДОКИ РЮГУ", "TEMPLE HEIGHTS": "ХРАМОВЫЕ ВЫСОТЫ",
    "Iron fist of the Shogun": "Железный кулак Сёгуна", "The one who breaks the night": "Тот, кто ломает ночь",
    "What the sewers made": "Порождение канализации",
    "LONG BLADE": "ДЛИННЫЙ КЛИНОК", "Slashes reach 25% further": "Удары достают на 25% дальше",
    "QUICK DRAW": "БЫСТРЫЙ ВЗМАХ", "Attack 20% faster": "Атака на 20% быстрее",
    "COUNTER EDGE": "ОТВЕТНЫЙ КЛИНОК", "A parry also cuts for 2 damage": "Парирование наносит 2 урона",
    "SECOND WIND": "ВТОРОЕ ДЫХАНИЕ", "Survive one deadly hit with 1 HP": "Пережить смертельный удар с 1 HP",
    "IRON HAORI": "ЖЕЛЕЗНОЕ ХАОРИ", "Every 3rd hit you take is blocked": "Каждый 3-й удар по вам блокируется",
    "SKY DANCER": "НЕБЕСНЫЙ ТАНЕЦ", "One more dash in the air": "Ещё один рывок в воздухе",
    "EXECUTIONER": "ПАЛАЧ", "Enemies below 30% HP die in one cut": "Враги с HP ниже 30% гибнут от одного удара",
    "ONIGIRI": "ОНИГИРИ", "Heal 2 HP right now": "Сразу лечит 2 HP",
    "BOUNTY HUNTER": "ОХОТНИК ЗА ГОЛОВАМИ", "Every kill drops 2 more coins": "Каждое убийство даёт ещё 2 монеты",
    "EARTHSHAKER": "СОТРЯСАТЕЛЬ", "Ground slam: wider and +1 damage": "Удар об землю: шире и +1 урон",
    "JADE SAMURAI": "НЕФРИТОВЫЙ САМУРАЙ", "GOLDEN SAMURAI": "ЗОЛОТОЙ САМУРАЙ", "VOID SAMURAI": "САМУРАЙ ПУСТОТЫ",
    "JADE BREATH": "НЕФРИТОВОЕ ДЫХАНИЕ", "GILDED": "ПОЗОЛОТА", "VOID WALKER": "СТРАННИК ПУСТОТЫ",
    "Heal 1 HP every 12 kills. SKILL: meditation": "Лечение 1 HP за 12 убийств. НАВЫК: медитация",
    "Coins are worth more. SKILL: thunder step": "Монеты ценнее. НАВЫК: громовой шаг",
    "Dash recharges faster. SKILL: time stop": "Рывок быстрее. НАВЫК: остановка времени",
    "MEDITATION": "МЕДИТАЦИЯ", "THUNDER STEP": "ГРОМОВОЙ ШАГ", "TIME STOP": "ОСТАНОВКА ВРЕМЕНИ",
    "PERK JADE BREATH: heal 1 HP every 12 kills.": "ПЕРК НЕФРИТОВОЕ ДЫХАНИЕ: +1 HP за каждые 12 убийств.",
    "SKILL MEDITATION [{K}]: heal 1 HP. Cooldown 20s.": "НАВЫК МЕДИТАЦИЯ [{K}]: лечит 1 HP, откат 20 с",
    "PERK GILDED: gold coins +1, mythic coins +3.": "ПЕРК ПОЗОЛОТА: золотые монеты +1, мифические +3.",
    "SKILL THUNDER STEP [{K}]: dash through enemies, 2 damage. Cooldown 4s.":
        "НАВЫК ГРОМОВОЙ ШАГ [{K}]: рывок сквозь врагов, 2 урона, откат 4 с",
    "PERK VOID WALKER: dash recharges 30% faster.": "ПЕРК СТРАННИК ПУСТОТЫ: рывок на 30% быстрее.",
    "SKILL TIME STOP [{K}]: enemies freeze for 2.5s. Cooldown 16s.":
        "НАВЫК ОСТАНОВКА ВРЕМЕНИ [{K}]: враги замирают на 2.5 с, откат 16 с",
    "ACT": "АКТ", "THE SHOGUN": "СЁГУН", "CHAOS SHOGUN": "СЁГУН ХАОСА", "Lord of the burning tower": "Владыка горящей башни",
    "THE CHAOS AWAKENS": "ХАОС ПРОБУЖДАЕТСЯ", "SHOGUN'S FOUNDRY": "ЛИТЕЙНАЯ СЁГУНА", "FLOODED DRYDOCK": "ЗАТОПЛЕННЫЙ ДОК",
    "TENSHU THRONE": "ТРОННЫЙ ЗАЛ ТЭНСЮ", "THE BOSS'S HEART: +1 MAX HP": "СЕРДЦЕ БОССА: +1 К МАКС. HP",
    "THUNDER SUBSTATION": "ГРОЗОВАЯ ПОДСТАНЦИЯ", "TOXIC CISTERN": "ЯДОВИТАЯ ЦИСТЕРНА", "THE FLOOR IS LIVE": "ПОЛ ПОД ТОКОМ",
    "THE DRAINS OVERFLOW": "СТОКИ ПЕРЕЛИВАЮТСЯ",
    "THE TIDE IS RISING": "ПРИЛИВ ПОДНИМАЕТСЯ", "GET TO HIGH GROUND": "ЗАБЕРИТЕСЬ ПОВЫШЕ", "THE FURNACE ROARS": "ПЕЧЬ РЕВЁТ",
    "THE HALL IS BURNING": "ЗАЛ ГОРИТ", "SHIELD BROKEN": "ЩИТ СЛОМАН", "COUNTER!": "КОНТРУДАР!",
    "The streets where it began": "Улицы, где всё началось", "Salt, rust and gunpowder": "Соль, ржавчина и порох",
    "Where the Shogun waits": "Где ждёт Сёгун", "IMMORTALITY": "БЕССМЕРТИЕ",
}


RU.update({
    "AOKIGAHARA FOREST": "ЛЕС АОКИГАХАРА", "KIRIGAMINE PEAKS": "ПИКИ КИРИГАМИНЕ", "TENSHIN DOJO": "ДОДЗЁ ТЭНСИН",
    "The sea of trees": "Море деревьев", "The monastery above the clouds": "Монастырь над облаками",
    "Where blades are born": "Где рождаются клинки", "The trees remember": "Деревья помнят",
    "Above the clouds, the wind": "Над облаками - ветер",
    "NIO GUARDIAN": "СТРАЖ НИО", "THE FALLEN ABBOT": "ПАДШИЙ НАСТОЯТЕЛЬ", "JUKAI WANDERER": "СКИТАЛЕЦ ДЗЮКАЙ",
    "KITSUNE": "КИЦУНЭ", "MOSS ONI": "МШИСТЫЙ ОНИ", "DAITENGU": "ДАЙТЭНГУ", "YUKI-ONNA": "ЮКИ-ОННА",
    "THE SENSEI": "СЕНСЕЙ", "MOKUJIN": "МОКУДЗИН", "LADY TOMOE": "ГОСПОЖА ТОМОЭ", "BROTHER": "БРАТ",
    "The gate does not open": "Врата не откроются", "His prayers turned to ash": "Его молитвы стали пеплом",
    "Lost, and looking for company": "Потерян и ищет компанию", "Nine tails, nine lies": "Девять хвостов, девять обманов",
    "The forest's old jailer": "Старый тюремщик леса", "King of the mountain wind": "Король горного ветра",
    "Her breath is winter": "Её дыхание - зима", "He taught you to hold the blade": "Он научил тебя держать клинок",
    "A thousand strikes, a thousand years": "Тысяча ударов, тысяча лет", "The blade of the dojo": "Клинок додзё",
    "Same blood, other path": "Одна кровь, другой путь", "NO MORE HOLDING BACK": "БОЛЬШЕ НИКАКОЙ ПОЩАДЫ",
    "WANDERER": "СКИТАЛЕЦ", "BANDIT": "РАЗБОЙНИК", "HUNTER": "ОХОТНИК", "TENGU": "ТЭНГУ", "YAMABUSHI": "ЯМАБУСИ",
    "DESHI": "ДЕСИ", "SENPAI": "СЭМПАЙ",
    "ROLL CARDS": "ПЕРЕБРОСИТЬ КАРТЫ", "Re-roll the kiosk cards once per district": "Раз за район перебросить карты киоска",
    "LOCKED": "ЗАКРЫТО", "CLEAR NEON SHINJUKU TO UNLOCK UPGRADES": "ПРОЙДИ НЕОНОВЫЙ СИНДЗЮКУ, ЧТОБЫ ОТКРЫТЬ УЛУЧШЕНИЯ",
    "CLEAR ANOTHER LOCATION FOR LEVEL 4": "ПРОЙДИ ЕЩЁ ЛОКАЦИЮ ДЛЯ УРОВНЯ 4",
    "CLEAR ANOTHER LOCATION FOR LEVEL 5": "ПРОЙДИ ЕЩЁ ЛОКАЦИЮ ДЛЯ УРОВНЯ 5",
    "DIFFICULTY": "СЛОЖНОСТЬ", "NOVICE": "НОВИЧОК", "NORMAL": "НОРМАЛЬНАЯ", "BASED SAMURAI": "БАЗОВЫЙ САМУРАЙ",
    "TRUE SAMURAI": "ИСТИННЫЙ САМУРАЙ",
    "MOST COINS IN A RUN": "БОЛЬШЕ ВСЕГО МОНЕТ ЗА ЗАБЕГ", "NEON SHINJUKU RUNS": "ЗАБЕГИ: НЕОНОВЫЙ СИНДЗЮКУ",
    "TEMPLE HEIGHTS RUNS": "ЗАБЕГИ: ХРАМОВЫЕ ВЫСОТЫ", "AOKIGAHARA RUNS": "ЗАБЕГИ: АОКИГАХАРА",
    "KIRIGAMINE RUNS": "ЗАБЕГИ: КИРИГАМИНЕ", "TENSHIN DOJO RUNS": "ЗАБЕГИ: ДОДЗЁ ТЭНСИН", "CLEAR": "ПРОЙДИ",
    "OPEN ALL MAPS": "ОТКРЫТЬ ВСЕ КАРТЫ", "REMOVE ALL MAPS": "ЗАКРЫТЬ ВСЕ КАРТЫ",
    "HE IS WAITING FOR YOU": "ОН ЖДЁТ ТЕБЯ",
    "YOUR CARDS": "ТВОИ КАРТЫ", "NO CARDS YET": "ПОКА НЕТ КАРТ", "Find a shinobi kiosk": "Найди киоск шиноби",
    "Point at a card": "Наведи на карту", "Press right to look at them": "Нажми вправо, чтобы посмотреть",
    "TELEPORT": "ТЕЛЕПОРТ", "WAVE": "ВОЛНА", "PARRIED!": "ПАРИРОВАНО!", "THE SHOGUN RAGES": "СЁГУН В ЯРОСТИ",
    "SUNKEN BOG": "ГНИЛАЯ ТОПЬ", "LOCATION": "ЛОКАЦИЯ", "BOSSES": "БОССЫ", "GO": "ВПЕРЁД",
})


def tr(s):
    """Russian text for an English UI string (unchanged when the language is English or the string is unknown)."""
    return RU.get(s, s) if LANG == 'ru' and isinstance(s, str) else s


def text(s, f, col, x, y, center=False, surf=None):
    s = tr(s)
    surf = surf or scr
    img = f.render(s, False, col)
    if center:
        x -= img.get_width() // 2
    surf.blit(f.render(s, False, (0, 0, 0)), (x + 1, y + 1))
    surf.blit(img, (x, y))


def outlined(s, f, col, x, y, line=INK, center=False, r=2):
    s = tr(s)
    img = f.render(s, False, col)
    sh = f.render(s, False, line)
    if center:
        x -= img.get_width() // 2
    for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r), (r, r)):
        scr.blit(sh, (x + dx, y + dy))
    scr.blit(img, (x, y))


def ransom(txt, x, y, fonts, seed, t, center=False, tilt=-5.0, surf=None, rise=0.0):
    """Persona-style ransom-note lettering: every letter on its own tilted card."""
    txt = tr(txt)
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
        img, jy = p  # (rise: each letter a step higher than the one before)
        (surf or scr).blit(img, (cx, y + jy - img.get_height() // 2 - (cx - (x - total // 2 if center else x)) * rise))
        cx += img.get_width() - 4
    return total


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
        return P_(.05 + b * .02, stand, [(.3, .8), (1.3, 3.2) if sip else (.9, 1.9)], .9, nowep=1.0)   # (hand to the mouth, under the brim)
    if a == 'phone':                                        # hand at the ear, shifting weight
        return P_(.04 + b * .03, stand, [(.25 + b * .1, .6), (1.35, 3.5)], .9, nowep=1.0)   # (phone at the ear, not over the hat)
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
    if e.kind == 'onryo':                                   # floats: arms hanging forward, flat out when she lunges
        if e.st == 'slash':
            return P_(.95, [(-.6, -.4), (-.3, -.6)], [(1.45, 1.5), (1.55, 1.6)], .9, nowep=1.0, coat=6)
        sw = math.sin(t * 2 + e.anim) * .1
        k = 1 - max(0.0, e.t) / e.wind if e.st == 'wind' else 0.0
        return P_(.15 + sw * .3 - .3 * k, [(.25 + sw, .5), (.05 - sw, .6)], [(1.2 + sw - k, 1.5 - k), (1.35 - k, 1.65 - k)], .9,
                  nowep=1.0, coat=3 + sw * 10)
    if e.hurt > 0:
        return P_(-.5, [(.4, .2), (-.3, -.5)], [(-1.5, -1.0), (-2.2, -1.8)], -1.0)
    if e.st == 'stun':                                      # staggered, guard broken
        sw = math.sin(t * 7) * .12
        return P_(-.45 + sw, [(.5, .3), (-.5, -.4)], [(-1.9, -1.4), (-1.2 + sw, -.4)], 2.3)
    if e.st == 'notice':                                    # startled: "?!" and a step back, weapon not out yet
        return P_(-.3, [(.45, .1), (-.45, -.5)], [(-1.0, -.6), (-1.3, -.9)], .6, nowep=1.0)
    if e.st == 'calm':                                      # off duty: what they do before they see you
        return pose_activity(e, t)
    if e.st == 'back':                                      # hop back out of reach after a swing
        return P_(-.35, [(.7, .2), (-.6, -.7)], [(-.8, -.3), (.6, 1.3)], .4)
    if e.st == 'smash':                                     # oni: kanabo hoisted with both hands, then into the ground
        k = 1 - max(0.0, e.t) / .6
        if k < .7:
            w = ease(k / .7)
            sh = math.sin(t * 50) * .05 * w
            return P_(-.35 * w, [(.7, .1 - .2 * w), (-.5, -.5)], [(-2.4 - .5 * w, -2.9), (-2.6 - .5 * w + sh, -3.0 - .2 * w)],
                      -2.9 - .4 * w + sh)
        w = ease(min(1, (k - .7) / .12))
        return P_(lerp(-.35, .75, w), [(-.9, -1.2), (1.1, .6)], [(lerp(-2.9, 1.3, w), lerp(-3.1, 1.4, w)), (lerp(-3.1, 1.5, w), lerp(-3.2, 1.45, w))],
                  lerp(-3.3, 1.55, w))
    if e.st == 'wind':
        k = 1 - max(0.0, e.t) / e.wind
        if e.kind == 'ninja':
            return P_(-.1, [(.5, 0), (-.4, -.3)], [(.3, .6), (-2.2 - .4 * k, -1.8)], 0)
        if e.kind in ('yari', 'sohei'):                     # spear drawn back at hip height, weight on the back leg
            return P_(-.25 * k, [(.7, .1), (-.5, -.5)], [(-.6, -.2), (-.9 - .5 * k, .3)], .05 * math.sin(t * 50) * k)
        if e.kind == 'teppo':                               # rifle shouldered, aimed down the red line
            return P_(-.05, [(.45, .05), (-.35, -.3)], [(1.3, 1.55), (1.45, 1.57)], 0.0)
        if e.kind == 'tate':                                # shield pulled back for the bash
            return P_(-.2 * k, [(.6, .1), (-.4, -.5)], [(-.3, .2), (.4 - .4 * k, 1.0)], .5)
        if e.kind == 'kunoichi':                            # low crouch, blade reversed behind her
            return P_(.55 * k, [(1.2 * k, -.9 * k), (.4, -1.2 * k)], [(-1.4, -1.0), (-2.0, -1.4)], 2.8)
        shake = math.sin(t * 60) * .05 * k
        if e.kind == 'oni':                                 # kanabo dragged up over the shoulder
            w = ease(k)
            return P_(-.3 * w, [(.7, .1), (-.5, -.6)], [(lerp(.3, -2.5, w), lerp(.6, -2.9, w)), (lerp(.6, -2.7, w) + shake, lerp(1.0, -3.1, w))],
                      lerp(.9, -3.0, w) + shake)
        if e.combo:                                         # ronin's second cut: blade pulled low for a rising slash
            return P_(.2, [(.6, .1), (-.4, -.5)], [(-.4, 0), (1.6, 1.8)], 1.3)
        w = ease(k)                                         # ronin: hand on the hilt, then raised high, weight sinking
        return P_(-.2 * w, [(.5 + .2 * w, .1 - .3 * w), (-.35, -.4 - .3 * w)], [(-.5, -.2), (lerp(.6, -2.8, w) + shake, lerp(1.0, -3.0, w))],
                  lerp(.9, -2.7, w) + shake)
    if e.st == 'slash':
        dur = {'kunoichi': .3, 'sohei': .5, 'yari': .22, 'tate': .22}.get(e.kind, .18)
        k = min(1.0, max(0.0, 1 - e.t / dur))
        if e.kind == 'yari':                                # thrust: the spear shoots out, holds, comes back a little
            w = ease(min(1, k * 2.2))
            back = max(0, k - .7) / .3
            return P_(lerp(-.1, .55, w) - .15 * back, [(lerp(.6, -.9, w), lerp(.1, -1.1, w)), (lerp(-.4, 1.05, w), lerp(-.5, .4, w))],
                      [(lerp(-.9, .3, w), lerp(.3, .9, w)), (lerp(-1.1, 1.45, w) - .25 * back, lerp(.3, 1.57, w))], 0.0, coat=3 * w)
        if e.kind == 'oni':                                 # overhead chop: the kanabo comes down in one arc
            w = ease(min(1, k * 1.6))
            return P_(lerp(-.3, .7, w), [(lerp(.7, -.9, w), lerp(.1, -1.2, w)), (lerp(-.5, 1.1, w), lerp(-.6, .6, w))],
                      [(lerp(-2.5, 1.2, w), lerp(-2.9, 1.3, w)), (lerp(-2.7, 1.45, w), lerp(-3.1, 1.4, w))], lerp(-3.0, 1.6, w))
        if e.kind == 'ronin':                               # a real cut through the whole arc (rising on the second one)
            base = P_(.25, [(-.7, -.9), (.9, .4)], [(-.4, 0), (0, 0)], 0)
            return with_attack(base, 'side', k, 2 if e.combo else 1)
        if e.kind == 'sohei':                               # the whirlwind: naginata spun all the way round
            a = t * 26
            return P_(.1, [(.6, .1), (-.5, -.4)], [(1.2 + .5 * math.sin(a), 1.5), (1.5, 1.6 + .4 * math.cos(a))], a)
        if e.kind == 'tate':                                # shield bash: shoulder behind it, the shield shoved out
            w = ease(min(1, k * 2.5))
            return P_(lerp(-.2, .7, w), [(lerp(.6, -.9, w), lerp(.1, -1.1, w)), (lerp(-.4, 1.1, w), lerp(-.5, .5, w))],
                      [(-.4, 0), (lerp(.0, 1.6, w), lerp(.9, 1.6, w))], .5)
        if e.kind == 'kunoichi':                            # dash-cut: body flat, blade sweeping from behind to the front
            w = ease(k)
            return P_(1.0, [(-1.0, -1.7), (.55, -.4)], [(-1.7, -1.4), (lerp(-1.6, 1.5, w), lerp(-1.2, 1.6, w))], lerp(2.9, -.5, w), coat=7)
        return P_(.45, [(-.7, -.9), (.9, .4)], [(-.4, 0), (1.4, 1.5)], .6)
    if e.throwT > 0 and e.kind == 'teppo':                 # recoil: the rifle kicks up
        return P_(-.25, [(.6, .1), (-.4, -.5)], [(1.0, 1.2), (1.1, 1.0)], -.45)
    if e.throwT > 0:
        return P_(.3, [(.4, 0), (-.3, -.4)], [(-.6, -.2), (1.6, 1.6)], 0)
    if abs(e.vx) > 5 and e.g:
        P = pose_jog(e.anim, min(1, abs(e.vx) / 90))
        P['sword'] = .9
        return P
    P = pose_idle(t + e.anim)
    P['sword'] = .6
    return P


def pose_boss(e, t):
    """Boss animation: every state and attack has its own pose (blended smoothly by the drawer)."""
    st, k_, bt = e.bs, e.batk, e.bt
    br = math.sin(t * (4.5 if e.bphase >= 2 else 3))
    stand = [(.32, .06), (-.3, -.08)]
    if st in ('enter', 'descend'):                         # falling into the arena / stepping down from the chair
        return pose_jump(e.bvy)
    if st == 'chair':                                      # seated, the rod across his knees; raises a hand and snaps
        up = 0 < t - getattr(e, 'handT', -9) < 1.3
        snap = 0 < t - getattr(e, 'clapT', -9) < .15
        arm = (2.05, 3.1) if snap else (1.8, 2.6)               # the front hand up by his face (the flick of the fingers)
        return P_(.05, [(1.5, .15), (1.4, .05)], [(.4, 1.2), arm] if up else [(.4, 1.2), (.6, 1.4)], 1.5, coat=0)
    if st in ('intro', 'roar'):                            # roar: lean back, arms flung out
        sh = math.sin(t * 40) * .06
        return P_(-.35 + sh, [(.5, .2), (-.5, -.5)], [(-2.0 + sh, -2.5), (2.0 - sh, 2.6)], -1.2, coat=-3, hot=.6)
    if st == 'dying':                                      # sinks to one knee, blade dropping
        k = min(1, bt / .8)
        return P_(lerp(.1, .7, k), [(lerp(.3, 1.55, k), lerp(.06, -.3, k)), (lerp(-.3, .2, k), lerp(-.1, -1.5, k))],
                  [(.2, .3), (lerp(.3, .6, k), lerp(.6, .8, k))], lerp(1.0, 1.55, k))
    if st == 'rec':                                        # out of breath: the window to punish it
        if k_ == 'charge':                                 # dazed after hitting the wall
            sw = math.sin(t * 7) * .14
            return P_(-.45 + sw, [(.5, .3), (-.5, -.4)], [(-1.9, -1.4), (-1.2 + sw, -.4)], 2.3)
        return P_(.42 + br * .05, [(.45, .1), (-.35, -.3)], [(.2 + br * .05, .3), (.35, .6 + br * .08)], 1.35)
    if st in ('idle', 'pick') or k_ is None:
        return P_(.06 + br * .03, stand, [(.14 + br * .06, .45), (.3, 1.0 + br * .06)], 1.0 + br * .05, coat=br * .6)
    if st == 'walk':
        if e.kind in BOSS_KITE:                            # glides: barely touches the ground
            return P_(.25, [(.5, -.2), (-.1, -.6)], [(-1.2, -1.0), (-1.4, -1.1)], 2.9, coat=4 + br)
        return pose_jog(e.anim, .85)
    tele = st == 'tele'
    k = min(1.0, bt / max(.01, BOSS_TIMING[k_][0])) if tele else min(1.0, bt / .18)
    shake = math.sin(t * 60) * .05 * (k if tele else 0)
    if k_ == 'counter' and not tele:                       # iai stance: blade low behind him, waiting for your swing
        return P_(.28 + br * .02, [(.95, -.25), (-.55, -.95)], [(-.7, .1), (.3, 1.1)], 2.95, coat=-2, hot=.9)
    if k_ == 'combo' and not tele:                         # three cuts, like the samurai's own
        i = min(2, int(bt / .33))
        P = with_attack(P_(.1, [(.6, .1), (-.5, -.6)], [(-.4, 0), (0, 0)], 0), 'side', min(1, (bt % .33) / .2), i + 1)
        P['hot'] = 1.0
        return P
    if k_ == 'whirl':                                      # the polearm drawn back, then spinning round and round
        if tele:
            return P_(.2 * k, [(.7, .1), (-.5, -.6)], [(-1.6, -1.0), (-1.9 + shake, -1.4)], 3.0 + shake, coat=2 * k)
        a = bt * 22
        return P_(.15, [(.6 + .3 * math.sin(a), .1), (-.5, -.6 + .3 * math.cos(a))],
                  [(math.sin(a) * 1.5, math.cos(a)), (a % math.tau - math.pi, 1.2)], a, coat=4 * math.sin(a), hot=1.0)
    if k_ == 'sweep':                                      # low: crouched, the staff swung along the floor
        if tele:
            return P_(.3 * k, [(1.0 * k, -.5 * k), (-.3, -1.0 * k)], [(-1.4, -1.0), (-2.0 - .3 * k, -1.6)], -2.4, coat=2 * k)
        w = ease(min(1, bt / .2))
        return P_(.55, [(1.3, -.9), (.5, -1.6)], [(-.4, 0), (lerp(-2.2, 1.6, w), lerp(-1.8, 1.4, w))], lerp(-2.2, 1.5, w),
                  hot=1.0, coat=4)
    if k_ in ('hop', 'pounce', 'vault', 'ricochet') and not tele:
        return dict(pose_jump(e.bvy), hot=1.0 if k_ != 'hop' else 0.0)
    if k_ == 'risecut' and not tele:
        return with_attack(pose_jump(e.bvy), 'up', min(1, bt / .2))
    if k_ == 'airdash' and not tele:
        return dict(POSE_DASH, hot=1.0) if e.bidx else pose_jump(e.bvy)
    if k_ == 'slide' and not tele:
        return dict(POSE_SLIDE, hot=1.0)
    if k_ == 'thrust':
        if tele:
            return P_(-.1 * k, [(.6, .1), (-.5, -.6)], [(-.6, -.2), (-.9 - .3 * k + shake, -.6)], .0 + shake, coat=2 * k)
        return P_(.35, [(-.7, -1.0), (.9, .3)], [(-.4, 0), (1.5, 1.5)], .05, hot=1.0, coat=4)
    if k_ == 'twin' and not tele:
        if bt < .38:
            return with_attack(P_(.1, [(.6, .1), (-.5, -.6)], [(-.4, 0), (0, 0)], 0), 'side', min(1, bt / .2), 1)
        w = ease(min(1, (bt - .38) / .15))
        return P_(.55, [(1.3, -.9), (.5, -1.6)], [(-.4, 0), (lerp(-2.2, 1.6, w), lerp(-1.8, 1.4, w))], lerp(-2.2, 1.5, w), hot=1.0)
    if k_ == 'dashcut':
        if tele:
            return P_(.5 * k, [(.9 * k, -.6 * k), (-.4, -.9 * k)], [(-1.3, -1.0), (-1.6, -1.2)], 2.9 + shake, coat=3 * k)
        return dict(POSE_DASH, hot=1.0)
    if k_ == 'stomp' and e.h < 60 and not tele and e.bvy != 0:   # the brother's ground slam, blade down
        return dict(POSE_SLAM, hot=1.0)
    k_ = {'iai': 'crossdash', 'waves': 'cleave', 'riposte': 'cleave', 'summon': 'blades', 'counter': 'cleave',
          'roots': 'quake', 'gust': 'barrage', 'warp': 'rift', 'gale': 'rift', 'rush': 'charge', 'twin': 'cleave',
          'hop': 'stomp', 'pounce': 'charge', 'vault': 'stomp', 'ricochet': 'charge', 'risecut': 'cleave', 'airdash': 'stomp',
          'slide': 'charge'}.get(k_, k_)
    if k_ in ('cleave', 'blink'):
        if tele:
            return P_(-.25 * k, [(.6, .1), (-.5, -.6)], [(-.6, -.2), (-2.6 - .3 * k + shake, -3.0)], -2.4 - .3 * k + shake, hot=k)
        P = with_attack(P_(.1, [(-.6, -.9), (.8, .3)], [(-.4, 0), (0, 0)], 0), 'side', min(1, bt / .22), 1)
        P['hot'] = 1.0
        return P
    if k_ in ('charge', 'crossdash'):
        if tele:
            return P_(.55 * k, [(.9 * k, -.6 * k), (-.4, -.9 * k)], [(-1.3, -1.0), (-1.6, -1.2)], 2.9 + shake, coat=3 * k)
        return P_(1.0, [(-1.0, -1.7), (.55, -.4)], [(-1.7, -1.4), (1.3, 1.45)], .1, coat=7, hot=1.0)
    if k_ in ('stomp', 'leap', 'quake') and (tele or e.bvy == 0):
        if k_ == 'quake' and not tele:                     # both fists into the ground
            return P_(.8, [(-.6, -.9), (.8, .3)], [(1.2, 1.4), (1.4, 1.5)], 1.5)
        if k_ == 'quake':
            return P_(-.2 * k, [(.6, .1), (-.5, -.6)], [(-2.6 + shake, -3.0), (-2.8 - shake, -3.1)], -2.6)
        return P_(.4 * k, [(1.3 * k, -.9 * k), (.5 * k, -1.5 * k)], [(.7 * k, 1.4 * k), (1.0 * k, 1.7 * k)], .3)
    if k_ in ('stomp', 'leap'):                            # airborne: knees tucked, then stretched down
        return P_(.15, [(1.3, -.5), (.9, -1.3)], [(-1.2, -.6), (-1.5, -.9)], 2.6, coat=-3)
    if k_ == 'barrage':                                    # arm thrust out like a cannon
        return P_(-.1, [(.6, .1), (-.5, -.5)], [(-.6, -.2), (1.5 - .3 * (1 - k), 1.6)], .1 + shake)
    if k_ == 'rift':                                       # both hands pushing magic forward
        return P_(-.1, stand, [(1.4 + .3 * br, 2.1), (1.7, 2.4 + .2 * br)], .9, coat=-1)
    if k_ == 'blades':                                     # arms straight up: blades rain from the ceiling
        return P_(-.15 + shake, stand, [(-2.9, -3.05), (-2.8 - shake, -3.0)], -1.6)
    if k_ == 'acid':                                       # rears back, then hurls
        if tele:
            return P_(-.4 * k, [(.6, .1), (-.4, -.5)], [(-1.5, -1.0), (-2.4 - .3 * k, -2.0)], 1.0)
        return P_(.5, [(-.6, -.9), (.8, .3)], [(-.4, 0), (1.6, 1.7)], 1.0)
    if k_ == 'claw':                                       # feral rakes: crouch with the talons drawn back, then three lunging swipes
        if tele:
            return P_(.5 * k, [(.4 + .9 * k, -.7 * k), (-.3, -1.1 * k)], [(-2.0 - .3 * k, -1.5), (-2.5 - .3 * k + shake, -2.0)], 1.0,
                      nowep=1.0, claws=1.0, coat=2 * k)
        i, u = int(bt / .2), (bt % .2) / .2
        w = ease(min(1, u * 1.7))
        if i % 2 == 0:                                     # overhead rake, down through you
            fa = (lerp(-2.7, 1.5, w), lerp(-2.4, 1.0, w))
            ba = (lerp(.6, -1.6, w), lerp(.4, -1.2, w))
        else:                                              # rising rake with the other hand
            fa = (lerp(.8, -.6, w), lerp(1.6, -1.2, w))
            ba = (lerp(-1.6, 1.4, w), lerp(-1.2, .9, w))
        return P_(.55 + .1 * math.sin(u * math.pi), [(-.7, -1.0), (.9, .3)], [ba, fa], 1.0, nowep=1.0, claws=1.0, coat=5)
    return pose_idle(t)


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
    lw = max(2, int(3 * sc)) + (1 if S.get('armor') else 0)
    legs, arms = P['legs'], P['arms']
    hip = (ax, ay - max(th * math.cos(a) + sh * math.cos(b) for a, b in legs))
    dx, dy = f * math.sin(P['lean']), -math.cos(P['lean'])
    nx, ny = -dy, dx
    neck = (hip[0] + dx * to, hip[1] + dy * to)
    sho = (hip[0] + dx * to * .82, hip[1] + dy * to * .82)
    hr = {'hood': 5.5, 'hat': 4.2, 'oni': 4.8, 'mask': 4.4, 'samurai': 4.6, 'ghost': 4.6, 'tengu': 4.6, 'wood': 4.8,
          'sage': 4.4, 'nio': 4.8, 'moss': 5.0}[S['head']] * sc
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
    armor = S.get('armor')
    if armor:                                                       # the oni: a broad armoured brute
        wh, ws = 3.3 * sc, 4.6 * sc
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
    if armor:                                                       # lacquered do: laced plates, kusazuri skirt
        for kk in (.3, .55, .8):
            a_ = (lerp(hip[0], neck[0], kk), lerp(hip[1], neck[1], kk))
            w_ = lerp(wh, ws, kk) - .5
            pg.draw.line(D, S['lace'], (a_[0] + nx * w_, a_[1] + ny * w_), (a_[0] - nx * w_, a_[1] - ny * w_))
        for sg in (-1, 1):
            b_ = (hip[0] + nx * wh * .55 * sg, hip[1] + ny * wh * .55 * sg)
            pg.draw.polygon(D, S['coat_d'], [(b_[0] - 2.2 * sc, b_[1]), (b_[0] + 2.2 * sc, b_[1]),
                                             (b_[0] + 2.8 * sc - f * sg * .5, b_[1] + 5.5 * sc), (b_[0] - 2.8 * sc - f * sg * .5, b_[1] + 5.5 * sc)])
            pg.draw.line(D, S['lace'], (b_[0] - 2.4 * sc, b_[1] + 2.6 * sc), (b_[0] + 2.4 * sc, b_[1] + 2.6 * sc))
            pg.draw.line(D, S['gilt'], (b_[0] - 2.8 * sc, b_[1] + 5.5 * sc), (b_[0] + 2.8 * sc, b_[1] + 5.5 * sc))
        pg.draw.line(D, S['gilt'], (neck[0] + nx * ws, neck[1] + ny * ws), (neck[0] - nx * ws, neck[1] - ny * ws))
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
    elif head == 'tengu':                                           # tengu: red face, long nose, black tokin cap, white mane
        mane = S.get('hair', (236, 232, 226))
        pg.draw.circle(D, mane, (hc[0] - f * 1.5, hc[1] + .5), hr)
        pg.draw.circle(D, S['skin'], (hc[0] + f * .6, hc[1] + .4), hr - 1)
        pg.draw.polygon(D, S['skin'], [(hc[0] + f * (hr - 1.5), hc[1] - .6), (hc[0] + f * (hr + 4.5 * sc), hc[1] + .6),
                                       (hc[0] + f * (hr - 1.5), hc[1] + 1.8)])
        pg.draw.line(D, tuple(min(255, c + 60) for c in S['skin']), (hc[0] + f * (hr - 1), hc[1] - .4),
                     (hc[0] + f * (hr + 3.5 * sc), hc[1] + .4))
        pg.draw.rect(D, (16, 14, 18), (hc[0] - 2 * sc, hc[1] - hr - 2.5 * sc, 4 * sc, 3.5 * sc))
        pg.draw.line(D, (255, 255, 255), (hc[0] + f * .4, hc[1] - 2), (hc[0] + f * 2.8, hc[1] - 1.3))
        D.fill(S['eye'], (hc[0] + f * 2 - .5, hc[1] - .6, 1, 1))
        for k_ in range(3):                                         # a white beard blown by the wind
            pg.draw.line(D, mane, (hc[0] + f * (1 + k_), hc[1] + hr - 1.5),
                         (hc[0] + f * (k_ - .5) - f * math.sin(t * 5 + k_) * .6, hc[1] + hr + 2.5 + k_ * .5))
        eye = (hc[0] + f * 2, hc[1] - .6)
    elif head == 'wood':                                            # mokujin: a carved wooden ball, a peg for a nose, no face
        pg.draw.circle(D, S['skin'], hc, hr)
        pg.draw.circle(D, S['coat_d'], hc, hr, 1)
        pg.draw.arc(D, S['coat_l'], (hc[0] - hr + 1, hc[1] - hr + 1, hr * 2 - 2, hr * 2 - 2), .4, 1.6, 1)
        pg.draw.line(D, S['coat_d'], (hc[0] - hr + 2, hc[1] - 1.5), (hc[0] + hr - 2, hc[1] - 1))
        pg.draw.line(D, S['coat_l'], (hc[0] + f * (hr - .5), hc[1] + .5), (hc[0] + f * (hr + 1.5), hc[1] + .5), 2)
        D.fill(S['eye'], (hc[0] + f * 2 - .5, hc[1] - .5, 1, 1))
        eye = (hc[0] + f * 2, hc[1] - .5)
        if S.get('headband'):                                       # the mokujin boss: a red headband, its tails flying
            pg.draw.line(D, S['headband'], (hc[0] - hr + .5, hc[1] - 2), (hc[0] + hr - .5, hc[1] - 2.4), 2)
            for k_ in (0, 1):
                pg.draw.line(D, S['headband'], (hc[0] - f * hr, hc[1] - 2),
                             (hc[0] - f * (hr + 4 + k_ * 2), hc[1] - 1 + k_ * 2 + math.sin(t * 9 + k_) * 1.2), 1)
    elif head == 'nio':                                             # the temple guardian: bald, a hair knot, glaring, mouth open
        pg.draw.circle(D, S['skin'], hc, hr)
        pg.draw.circle(D, S['hair'], (hc[0] - f * 1.5, hc[1] - hr + .5), 2 * sc)
        pg.draw.line(D, S['line'], (hc[0] + f * .6, hc[1] - 2.2), (hc[0] + f * 3.4, hc[1] - 1), 2)
        D.fill((255, 240, 200), (hc[0] + f * 2.2 - .5, hc[1] - .6, 1, 1))
        pg.draw.line(D, (90, 10, 10), (hc[0] + f * 1.2, hc[1] + 2.4), (hc[0] + f * 3.2, hc[1] + 2), 2)
        eye = (hc[0] + f * 2.2, hc[1] - .6)
    elif head == 'moss':                                            # the bog oni: a mossy boulder of a head, two green eyes
        pg.draw.circle(D, S['mask'], hc, hr)
        for k_ in range(5):
            a_ = math.pi + k_ * math.pi / 4
            pg.draw.circle(D, S['lace'], (hc[0] + math.cos(a_) * hr * .8, hc[1] + math.sin(a_) * hr * .8), 1.6)
        pg.draw.line(D, S['coat_d'], (hc[0] - hr + 1, hc[1] + 1), (hc[0] + hr - 1, hc[1] + 1.4))
        D.fill(S['eye'], (hc[0] + f * 1 - .5, hc[1] - .5, 1, 1))
        D.fill(S['eye'], (hc[0] + f * 3 - .5, hc[1] - .5, 1, 1))
        eye = (hc[0] + f * 2, hc[1] - .5)
    elif head == 'sage':                                            # the sensei: old face, white brows, a long beard, wide straw hat
        pg.draw.circle(D, S['skin'], hc, hr)
        beard, sway = S.get('hair', (236, 236, 240)), math.sin(t * 3) * .7
        pg.draw.polygon(D, beard, [(hc[0] - f * .8, hc[1] + 1.4), (hc[0] + f * (hr - .3), hc[1] + 1.1),
                                   (hc[0] + f * 2.2 + sway, hc[1] + hr + 5 * sc), (hc[0] + f * .2 + sway, hc[1] + hr + 3 * sc)])
        pg.draw.line(D, beard, (hc[0] + f * .8, hc[1] - 1.2), (hc[0] + f * 3.2, hc[1] - .8), 2)
        D.fill((30, 20, 24), (hc[0] + f * 2.3 - .5, hc[1] + .1, 1, 1))
        brim = hc[1] - 1.8 * sc
        pts = [(hc[0] - 14 * sc, brim + 2.2), (hc[0] - 3 * sc, brim - 4.5 * sc), (hc[0] + 3 * sc, brim - 4.5 * sc),
               (hc[0] + 14 * sc, brim + 2.2)]
        pg.draw.polygon(D, S['straw'], pts)
        for kx in (-9, -5, -1.5, 2, 5.5, 9):
            pg.draw.line(D, S['straw_d'], (hc[0] + kx * .3 * sc, brim - 4 * sc), (hc[0] + kx * sc, brim + 2))
        pg.draw.line(D, S['straw_d'], pts[0], pts[3])
        pg.draw.circle(D, S['straw_d'], (hc[0], brim - 4.8 * sc), 1.3 * sc)
        eye = (hc[0] + f * 2.3, hc[1] + .1)
    elif head == 'oni' and armor:                                   # the oni: kabuto, golden crescent, snarling menpo
        pg.draw.circle(D, (20, 14, 16), (hc[0] + f * .5, hc[1] + .5), hr - .4)
        neckg = [(hc[0] - f * (hr * .2), hc[1] - 1), (hc[0] - f * (hr + 3.2 * sc), hc[1] + 3.5 * sc),   # shikoro neck guard
                 (hc[0] - f * (hr + 1.5 * sc), hc[1] + 5.2 * sc), (hc[0] + f * .5, hc[1] + 3)]
        pg.draw.polygon(D, S['coat_d'], neckg)
        for kk in (1.6, 3.2):
            pg.draw.line(D, S['lace'], (hc[0] - f * hr * .6, hc[1] + kk * sc * .7), (hc[0] - f * (hr + 2.4 * sc), hc[1] + kk * sc + 1))
        bowl = [(hc[0] - hr - 1.2, hc[1] + .5), (hc[0] - hr + .5, hc[1] - hr + .2), (hc[0] - 1, hc[1] - hr - 1.8),
                (hc[0] + 1, hc[1] - hr - 1.8), (hc[0] + hr - .5, hc[1] - hr + .2), (hc[0] + hr + 1.2, hc[1] - .5)]
        pg.draw.polygon(D, S['coat'], bowl)
        pg.draw.line(D, S['coat_l'], (hc[0] - hr + 1, hc[1] - hr + .6), (hc[0] + hr - 1, hc[1] - hr + .6))
        pg.draw.line(D, S['gilt'], (hc[0] - hr - 1.5, hc[1] + .3), (hc[0] + hr + 1.5, hc[1] - .3), 1)          # brim
        bx_, by_ = hc[0] + f * .8, hc[1] - hr - .5                                                          # kuwagata
        for sg in (-1, 1):
            pg.draw.lines(D, S['gilt'], False, [(bx_, by_ + 1), (bx_ + sg * 2.4 * sc, by_ - 2.2 * sc),
                                                (bx_ + sg * 3.4 * sc, by_ - 5.6 * sc), (bx_ + sg * 2.8 * sc, by_ - 7.2 * sc)], 2)
        pg.draw.circle(D, S['mask'], (bx_, by_ + .5), 1.4)
        mx_ = hc[0] + f * 1.2
        pg.draw.polygon(D, S['mask'], [(mx_ - f * 1.5, hc[1] + .4), (mx_ + f * (hr + .4), hc[1] - .2),
                                       (mx_ + f * (hr + .8), hc[1] + 2.4), (mx_ + f * (hr - .6), hc[1] + 5.0), (mx_ - f * .4, hc[1] + 5.4)])
        pg.draw.line(D, (90, 16, 20), (mx_ + f * 1, hc[1] - .4), (mx_ + f * (hr - .2), hc[1] - 1.4))           # scowl
        D.fill((236, 230, 214), (mx_ + f * 1.3 - .5, hc[1] + 2.8, 1, 2))                                     # tusks
        D.fill((236, 230, 214), (mx_ + f * (hr - 1.2) - .5, hc[1] + 2.6, 1, 2))
        pg.draw.line(D, (40, 8, 10), (mx_ + f * 1, hc[1] + 3.2), (mx_ + f * (hr - .8), hc[1] + 3.0))
        D.fill(S['eye'], (mx_ + f * 2.2 - .5, hc[1] + .6, 2, 1))
        eye = (mx_ + f * 2.2, hc[1] + .6)
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
    elif head == 'ghost':                                           # onryo: long black hair over a pale face, one red eye
        pg.draw.circle(D, S['hair'], (hc[0] - f * .6, hc[1] - .4), hr)
        pg.draw.circle(D, S['skin'], (hc[0] + f * 1.8, hc[1] + .8), hr - 2.2)
        for i in range(5):                                          # strands hanging down past the shoulders
            sx_ = hc[0] + f * (1.6 - i * 1.3)
            pg.draw.line(D, S['hair'], (sx_, hc[1] - 1), (sx_ - f * .5, hc[1] + hr + 5 + (i % 2) * 3), 2)
        D.fill(S['eye'], (hc[0] + f * 2.4 - .5, hc[1] + .2, 1, 1))
        eye = (hc[0] + f * 2.4, hc[1] + .2)
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
    if P.get('claws', 0) > .5:                                      # bare talons (the mutant's rakes)
        fx_, fy_ = e[0] - k[0], e[1] - k[1]
        n_ = math.hypot(fx_, fy_) or 1
        fx_, fy_ = fx_ / n_, fy_ / n_
        for sg in (-1, 0, 1):
            a_ = (e[0] - fy_ * sg * 1.3, e[1] + fx_ * sg * 1.3)
            pg.draw.line(D, (230, 240, 200), a_, (a_[0] + fx_ * 4 * sc - fy_ * sg * 1.2, a_[1] + fy_ * 4 * sc + fx_ * sg * 1.2))
    if armor:                                                       # sode: big shoulder plates over both arms
        for i_, col_ in ((0, S['coat_d']), (1, S['coat'])):
            a1 = arms[i_][0]
            ux, uy = f * math.sin(a1), math.cos(a1)
            qx, qy = -uy, ux
            o = (sho[0] - ux * 1.2, sho[1] - uy * 1.2)
            pts = [(o[0] + qx * 2.6 * sc, o[1] + qy * 2.6 * sc), (o[0] - qx * 2.6 * sc, o[1] - qy * 2.6 * sc),
                   (o[0] - qx * 3.0 * sc + ux * 6.5 * sc, o[1] - qy * 3.0 * sc + uy * 6.5 * sc),
                   (o[0] + qx * 3.0 * sc + ux * 6.5 * sc, o[1] + qy * 3.0 * sc + uy * 6.5 * sc)]
            pg.draw.polygon(D, col_, pts)
            for kk in (.4, .75):
                pg.draw.line(D, S['lace'], (lerp(pts[0][0], pts[3][0], kk), lerp(pts[0][1], pts[3][1], kk)),
                             (lerp(pts[1][0], pts[2][0], kk), lerp(pts[1][1], pts[2][1], kk)))
            pg.draw.line(D, S['gilt'], pts[2], pts[3])
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
        pg.draw.line(D, S.get('steel', (168, 178, 198)), e, tip, 2)          # (a wooden bokken for the dojo's pupils)
        pg.draw.line(D, S.get('steel_l', (246, 250, 255)), (e[0] + px * .6, e[1] + py * .6), (tip[0] + px * .6, tip[1] + py * .6))
        blade = ((e[0] + tip[0]) / 2, (e[1] + tip[1]) / 2)
    elif S['weapon'] == 'club' and not nowep and armor:             # kanabo: iron club, flaring, studded
        L = S['blade']
        mid, end = (e[0] + vx * 5, e[1] + vy * 5), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (60, 30, 30), (e[0] - vx * 4, e[1] - vy * 4), mid, 3)
        pg.draw.circle(D, S['gilt'], (e[0] - vx * 4, e[1] - vy * 4), 1.5)
        body = [(mid[0] + px * 1.6, mid[1] + py * 1.6), (end[0] + px * 3.4, end[1] + py * 3.4),
                (end[0] + vx * 2.5, end[1] + vy * 2.5), (end[0] - px * 3.4, end[1] - py * 3.4), (mid[0] - px * 1.6, mid[1] - py * 1.6)]
        pg.draw.polygon(D, (50, 50, 58), body)
        pg.draw.line(D, (110, 112, 126), body[0], body[1])
        pg.draw.line(D, S['gilt'], (mid[0] + px * 1.8, mid[1] + py * 1.8), (mid[0] - px * 1.8, mid[1] - py * 1.8))
        for kk in range(9, int(L) + 1, 3):
            w_ = lerp(1.6, 3.4, (kk - 5) / max(1, L - 5)) + .6
            for sg in (-1, 1):
                D.fill((214, 214, 226), (e[0] + vx * kk + px * w_ * sg, e[1] + vy * kk + py * w_ * sg, 1, 1))
        blade = ((e[0] + end[0]) / 2, (e[1] + end[1]) / 2)
    elif S['weapon'] == 'club' and not nowep:
        L = S['blade']
        mid, end = (e[0] + vx * 5, e[1] + vy * 5), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (52, 36, 30), (e[0] - vx * 3, e[1] - vy * 3), mid, 2)
        pg.draw.line(D, (74, 54, 46), mid, end, 5)
        for kk in range(8, int(L), 4):
            for sg in (-1, 1):
                D.fill((200, 200, 212), (e[0] + vx * kk + px * 2 * sg, e[1] + vy * kk + py * 2 * sg, 1, 1))
        blade = ((e[0] + end[0]) / 2, (e[1] + end[1]) / 2)
    elif S['weapon'] == 'spear' and not nowep:                      # yari: long shaft, steel head, red tassel
        L = S['blade']
        butt, end = (e[0] - vx * 9, e[1] - vy * 9), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (86, 60, 40), butt, end, 2)
        head = (end[0] + vx * 6, end[1] + vy * 6)
        pg.draw.polygon(D, (200, 206, 220), [(end[0] + px * 1.6, end[1] + py * 1.6), head, (end[0] - px * 1.6, end[1] - py * 1.6)])
        pg.draw.line(D, (190, 30, 40), end, (end[0] - vx * 2 + py * 2, end[1] - vy * 2 + 2), 2)
        blade = (end[0], end[1])
    elif S['weapon'] == 'naginata' and not nowep:                   # sohei: long shaft, curved blade
        L = S['blade']
        butt, end = (e[0] - vx * 10, e[1] - vy * 10), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (60, 40, 30), butt, end, 2)
        tip = (end[0] + vx * 9 - px * 2.5, end[1] + vy * 9 - py * 2.5)
        pg.draw.polygon(D, (214, 220, 232), [(end[0] + px * 1.4, end[1] + py * 1.4), (end[0] + vx * 5 + px * .8, end[1] + vy * 5 + py * .8),
                                             tip, (end[0] - px * 1.2, end[1] - py * 1.2)])
        blade, tip = (end[0], end[1]), None
    elif S['weapon'] == 'fan' and not nowep:                        # the tengu's feather fan
        L = S['blade']
        end = (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (90, 60, 40), e, end, 1)
        pts = [(end[0] + px * 4 * sc + vx * k_ * 1.5, end[1] + py * 4 * sc + vy * k_ * 1.5) for k_ in range(0, 7)]
        pts += [(end[0] - px * 4 * sc + vx * k_ * 1.5, end[1] - py * 4 * sc + vy * k_ * 1.5) for k_ in range(6, -1, -1)]
        tipf = (end[0] + vx * 12 * sc, end[1] + vy * 12 * sc)
        pg.draw.polygon(D, (60, 120, 70), [(end[0] + px * 2, end[1] + py * 2), (end[0] + px * 5 * sc + vx * 6 * sc, end[1] + py * 5 * sc + vy * 6 * sc),
                                           tipf, (end[0] - px * 5 * sc + vx * 6 * sc, end[1] - py * 5 * sc + vy * 6 * sc), (end[0] - px * 2, end[1] - py * 2)])
        for k_ in (-3, 0, 3):
            pg.draw.line(D, (150, 200, 140), end, (tipf[0] + px * k_, tipf[1] + py * k_))
        blade = tipf
    elif S['weapon'] == 'daggers' and not nowep:                    # two short knives: one forward, one in a reverse grip
        L = S['blade']
        tip = (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (200, 230, 250), e, tip, 2)
        pg.draw.line(D, (255, 255, 255), (e[0] + px * .5, e[1] + py * .5), tip)
        pg.draw.line(D, (200, 230, 250), (e[0] - px * 2, e[1] - py * 2), (e[0] - vx * L * .7 - px * 3, e[1] - vy * L * .7 - py * 3), 2)
        blade, tip = tip, None
    elif S['weapon'] == 'staff' and not nowep:                      # the sensei's rod: a long dark staff with bound ends
        L = S['blade']
        butt, end = (e[0] - vx * L * .55, e[1] - vy * L * .55), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (70, 46, 30), butt, end, 2)
        pg.draw.line(D, (126, 90, 58), (butt[0] + px * .5, butt[1] + py * .5), (end[0] + px * .5, end[1] + py * .5))
        for q_ in (butt, end):
            pg.draw.circle(D, S.get('gilt', (210, 176, 90)), q_, 1.3)
        blade = end
    elif S['weapon'] == 'rifle' and not nowep:                      # teppo: matchlock rifle, stock under the arm
        L = S['blade']
        stock, muzzle = (e[0] - vx * 6 + px * 1.5, e[1] - vy * 6 + py * 1.5), (e[0] + vx * L, e[1] + vy * L)
        pg.draw.line(D, (90, 56, 36), stock, (e[0] + vx * 4, e[1] + vy * 4), 3)
        pg.draw.line(D, (70, 72, 84), e, muzzle, 2)
        pg.draw.line(D, (150, 154, 170), (e[0] + vx * 5, e[1] + vy * 5), muzzle)
        D.fill((255, 140, 60), (e[0] + vx * 3, e[1] + vy * 3, 1, 1))   # the lit match cord
        blade = muzzle
    elif S['weapon'] == 'shield':                                   # tate: a tall iron shield carried in front
        c = (e[0] + f * 2 * sc, e[1] - 3 * sc)
        hh, hw2 = 11 * sc, 2.4 * sc
        pts = [(c[0] - hw2, c[1] - hh), (c[0] + hw2, c[1] - hh), (c[0] + hw2, c[1] + hh), (c[0] - hw2, c[1] + hh)]
        pg.draw.polygon(D, (66, 70, 82), pts)
        pg.draw.polygon(D, (140, 146, 164), pts, 1)
        pg.draw.line(D, (170, 40, 40), (c[0], c[1] - hh + 3), (c[0], c[1] + hh - 3))
        blade = c
    return {'eye': eye, 'blade': blade, 'hand': e, 'hc': hc,
            'tip': tip if S['weapon'] == 'katana' and not sheathed and not nowep else None}


# ---------------------------------------------------------------- small shapes
def chain(surf, a, b, col=(150, 146, 160)):
    """A row of iron links from a to b."""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 6))
    for i in range(n + 1):
        px, py = lerp(a[0], b[0], i / n), lerp(a[1], b[1], i / n)
        if i % 2:
            pg.draw.ellipse(surf, (40, 36, 46), (px - 3, py - 2, 7, 5), 2)
            pg.draw.ellipse(surf, col, (px - 3, py - 2, 6, 4), 1)
        else:
            pg.draw.ellipse(surf, (40, 36, 46), (px - 2, py - 3, 5, 7), 2)
            pg.draw.ellipse(surf, col, (px - 2, py - 3, 4, 6), 1)


def padlock(surf, x, y):
    pg.draw.arc(surf, (190, 180, 120), (x - 5, y - 11, 10, 12), 0, math.pi, 2)
    pg.draw.rect(surf, (40, 30, 20), (x - 7, y - 5, 14, 11))
    pg.draw.rect(surf, (220, 190, 90), (x - 6, y - 4, 12, 9))
    pg.draw.rect(surf, (40, 30, 20), (x - 1, y - 2, 2, 4))


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


def bake_env(env):
    """Background layers of the other two acts: the RYUGU DOCKS (sea, ships, cranes, fog) and the TEMPLE HEIGHTS
    (a red moon over the mountains, pagodas and pines, temple walls). Same layer sizes / parallax as the city."""
    rnd = random.Random({'docks': 31, 'temple': 47, 'forest': 53, 'peaks': 59, 'dojo': 61}[env])
    L = {}
    sky = pg.Surface((W, H))
    far = pg.Surface((layer_w(.15), H), pg.SRCALPHA)
    mid = pg.Surface((layer_w(.4), H), pg.SRCALPHA)
    near = pg.Surface((layer_w(.7), H), pg.SRCALPHA)
    haze = pg.Surface((W, H), pg.SRCALPHA)
    if env == 'docks':
        vgrad(sky, [(0, (4, 10, 18)), (110, (14, 40, 56)), (GY - 40, (60, 110, 116)), (H, (60, 110, 116))])
        for _ in range(40):
            sky.set_at((rnd.randint(0, W - 1), rnd.randint(0, 80)), (90, 130, 140))
        glow(sky, int(W * .22), 70, 70, (30, 60, 60))
        pg.draw.circle(sky, (220, 240, 230), (int(W * .22), 70), 16)
        sea = GY - 64                                             # the sea: the horizon, swell lines, ships far out
        far.fill((10, 30, 40, 255), (0, sea, far.get_width(), H - sea))
        for y in range(sea + 3, GY, 4):
            for _ in range(far.get_width() // 30):
                x = rnd.randint(0, far.get_width())
                far.fill((40, 80, 90, 255), (x, y, rnd.randint(4, 14), 1))
        x = 60
        while x < far.get_width():
            hw = rnd.randint(40, 80)                              # a cargo ship: hull, bridge, stacked boxes, lights
            pg.draw.polygon(far, (8, 20, 28), [(x, sea - 4), (x + hw, sea - 4), (x + hw - 6, sea + 3), (x + 4, sea + 3)])
            pg.draw.rect(far, (8, 20, 28), (x + hw - 18, sea - 16, 10, 12))
            for bx in range(x + 6, x + hw - 22, 7):
                pg.draw.rect(far, (12, 28, 36), (bx, sea - 4 - rnd.randint(4, 9), 6, 9))
            far.fill((255, 220, 140), (x + hw - 15, sea - 13, 2, 1))
            far.fill((255, 60, 60), (x + 2, sea - 6, 1, 1))
            x += hw + rnd.randint(70, 160)
        lx = 30                                                   # the lighthouse on the breakwater
        pg.draw.polygon(far, (16, 34, 40), [(lx - 6, sea + 2), (lx + 6, sea + 2), (lx + 3, sea - 50), (lx - 3, sea - 50)])
        for yy in range(sea - 44, sea, 12):
            far.fill((150, 40, 40), (lx - 4, yy, 8, 4))
        far.fill((255, 250, 210), (lx - 3, sea - 56, 6, 5))
        L['light'] = (lx, sea - 54)
        x = -10                                                   # warehouses with sawtooth roofs, gantry cranes over them
        while x < mid.get_width():
            w, h = rnd.randint(80, 140), rnd.randint(46, 90)
            top = GY - h
            pg.draw.rect(mid, (10, 26, 32), (x, top, w, H - top))
            for tx in range(x, x + w - 10, 14):
                pg.draw.polygon(mid, (10, 26, 32), [(tx, top), (tx + 14, top), (tx + 14, top - 7)])
            pg.draw.line(mid, (30, 60, 66), (x, top), (x + w, top))
            num = F_JP.render(rnd.choice(("倉庫", "七番", "竜宮", "港")), False, (40, 80, 80))
            mid.blit(num, (x + 8, top + 10))
            windows(mid, x, top + 24, w, GY, 6, .12, [(255, 200, 120), (140, 230, 220)], 2)
            if rnd.random() < .45:
                cx_ = x + w // 2
                for lg in (-26, 26):
                    pg.draw.line(mid, (18, 40, 44), (cx_ + lg, GY), (cx_ + lg // 3, top - 70), 3)
                pg.draw.line(mid, (18, 40, 44), (cx_ - 60, top - 70), (cx_ + 90, top - 70), 4)
                pg.draw.line(mid, (18, 40, 44), (cx_, top - 96), (cx_ + 90, top - 70), 1)
                pg.draw.line(mid, (18, 40, 44), (cx_, top - 96), (cx_ - 60, top - 70), 1)
                mid.fill((255, 50, 50), (cx_ + 88, top - 72, 2, 2))
            x += w + rnd.randint(6, 30)
        x = -10                                                   # container stacks along the quay
        while x < near.get_width():
            w = rnd.choice((40, 56, 56, 72))
            hgt = rnd.choice((1, 1, 2, 2, 3))
            col = rnd.choice(((60, 28, 20), (20, 40, 60), (50, 20, 24), (24, 46, 34), (60, 50, 20)))
            for i in range(hgt):
                y0 = GY - 26 * (i + 1)
                pg.draw.rect(near, col, (x, y0, w, 26))
                for rx in range(x + 4, x + w - 2, 4):
                    pg.draw.line(near, tuple(c * 3 // 4 for c in col), (rx, y0 + 2), (rx, y0 + 24))
                pg.draw.line(near, tuple(min(255, c * 2) for c in col), (x, y0), (x + w, y0))
            x += w + rnd.randint(4, 40)
        for y in range(GY - 110, GY):
            haze.fill((90, 170, 170, int(70 * ((y - GY + 110) / 110) ** 2)), (0, y, W, 1))
        fog = pg.Surface((W + 240, 70), pg.SRCALPHA)              # drifting fog banks
        for _ in range(60):
            fx, fy, fr = rnd.randint(0, W + 240), rnd.randint(10, 60), rnd.randint(18, 40)
            pg.draw.ellipse(fog, (150, 200, 200, 14), (fx - fr, fy - fr * .4, fr * 2, fr * .8))
        L['fog'] = fog
    elif env == 'forest':
        bake_forest(rnd, sky, far, mid, near, haze)
    elif env == 'peaks':
        bake_peaks(rnd, sky, far, mid, near, haze)
    elif env == 'dojo':
        bake_dojo(rnd, sky, far, mid, near, haze)
    else:
        vgrad(sky, [(0, (10, 4, 18)), (90, (58, 14, 40)), (GY - 40, (190, 70, 60)), (H, (190, 86, 70))])
        for _ in range(60):
            sky.set_at((rnd.randint(0, W - 1), rnd.randint(0, 80)), (170, 120, 150))
        mx, my = int(W * .68), 78                                 # a huge red moon
        glow(sky, mx, my, 110, (90, 30, 30))
        pg.draw.circle(sky, (255, 186, 150), (mx, my), 34)
        for _ in range(6):
            pg.draw.circle(sky, (240, 160, 130), (mx + rnd.randint(-20, 20), my + rnd.randint(-20, 20)), rnd.randint(3, 7))
        fw = far.get_width()                                      # mountain ranges: one tall snow-capped peak
        for col, base, amp in (((58, 20, 40), GY - 60, 60), ((40, 12, 30), GY - 30, 40)):
            pts, x = [(0, H)], 0
            while x <= fw:
                pts.append((x, base - rnd.randint(0, amp)))
                x += rnd.randint(30, 60)
            pts += [(fw, H)]
            pg.draw.polygon(far, col, pts)
        px_ = int(fw * .55)
        pg.draw.polygon(far, (66, 24, 46), [(px_ - 120, GY), (px_ - 14, GY - 150), (px_ + 14, GY - 150), (px_ + 120, GY)])
        pg.draw.polygon(far, (230, 210, 220), [(px_ - 40, GY - 100), (px_ - 14, GY - 150), (px_ + 14, GY - 150), (px_ + 40, GY - 100),
                                               (px_ + 20, GY - 108), (px_ + 4, GY - 98), (px_ - 12, GY - 110), (px_ - 26, GY - 98)])
        x = -10                                                   # pagodas, pines and a torii on the hills
        while x < mid.get_width():
            r = rnd.random()
            if r < .4:
                tiers, w = rnd.randint(3, 5), rnd.randint(40, 56)
                y = GY
                for i in range(tiers):
                    tw = w - i * 7
                    y -= 22
                    pg.draw.rect(mid, (24, 6, 18), (x + (w - tw) // 2 + 6, y, tw - 12, 22))
                    pg.draw.polygon(mid, (24, 6, 18), [(x + (w - tw) // 2 - 4, y + 2), (x + (w + tw) // 2 + 4, y + 2),
                                                       (x + (w + tw) // 2 - 6, y - 6), (x + (w - tw) // 2 + 6, y - 6)])
                    if rnd.random() < .5:
                        mid.fill((255, 170, 80), (x + w // 2 - 2, y + 8, 4, 6))
                pg.draw.line(mid, (24, 6, 18), (x + w // 2, y - 6), (x + w // 2, y - 22), 2)
                x += w + rnd.randint(10, 40)
            elif r < .8:
                tx, h = x + 20, rnd.randint(50, 90)               # a pine: crooked trunk, cloud-like needle clumps
                pg.draw.line(mid, (20, 6, 14), (tx, GY), (tx + rnd.randint(-8, 8), GY - h), 3)
                for _ in range(4):
                    cx_, cy_ = tx + rnd.randint(-22, 22), GY - h + rnd.randint(-6, 30)
                    pg.draw.ellipse(mid, (20, 6, 14), (cx_ - 16, cy_ - 5, 32, 11))
                x += rnd.randint(40, 70)
            else:
                pg.draw.rect(mid, (40, 8, 14), (x + 4, GY - 54, 4, 54))
                pg.draw.rect(mid, (40, 8, 14), (x + 36, GY - 54, 4, 54))
                pg.draw.polygon(mid, (40, 8, 14), [(x - 4, GY - 58), (x + 48, GY - 58), (x + 50, GY - 63), (x - 6, GY - 63)])
                pg.draw.rect(mid, (40, 8, 14), (x, GY - 48, 44, 3))
                x += rnd.randint(60, 100)
        x = -10                                                   # temple walls with tiled caps and stone lanterns
        while x < near.get_width():
            w, h = rnd.randint(70, 130), rnd.randint(26, 44)
            top = GY - h
            pg.draw.rect(near, (16, 4, 10), (x, top, w, H - top))
            pg.draw.polygon(near, (30, 8, 14), [(x - 4, top + 2), (x + w + 4, top + 2), (x + w - 2, top - 5), (x + 2, top - 5)])
            for bx in range(x + 8, x + w - 8, 18):
                pg.draw.line(near, (30, 10, 16), (bx, top + 6), (bx, GY))
            if rnd.random() < .6:
                lx = x + w + 8
                pg.draw.rect(near, (40, 30, 36), (lx - 2, GY - 20, 4, 20))
                pg.draw.rect(near, (50, 40, 46), (lx - 6, GY - 30, 12, 9))
                pg.draw.polygon(near, (40, 30, 36), [(lx - 9, GY - 30), (lx + 9, GY - 30), (lx, GY - 37)])
                near.fill((255, 190, 100), (lx - 3, GY - 28, 6, 5))
                glow(near, lx, GY - 26, 18, (80, 40, 14))
            x += w + rnd.randint(24, 60)
        for y in range(GY - 100, GY):
            haze.fill((255, 110, 80, int(55 * ((y - GY + 100) / 100) ** 2)), (0, y, W, 1))
    L.update(sky=sky, far=far, mid=mid, near=near, haze=haze)
    return L


def bake_forest(rnd, sky, far, mid, near, haze):
    """AOKIGAHARA: Fuji's snowy cone far away, a sea of cedar trunks, twisted roots, moss, old stones and a sacred rope."""
    vgrad(sky, [(0, (4, 10, 10)), (100, (12, 32, 28)), (GY - 40, (44, 80, 60)), (H, (44, 80, 60))])
    for _ in range(40):
        sky.set_at((rnd.randint(0, W - 1), rnd.randint(0, 90)), (150, 190, 170))
    glow(sky, int(W * .3), 64, 60, (30, 60, 50))
    pg.draw.circle(sky, (220, 240, 220), (int(W * .3), 64), 12)
    fw = far.get_width()
    fx = int(fw * .5)                                              # Mount Fuji over the trees
    pg.draw.polygon(far, (30, 50, 52), [(fx - 260, GY - 20), (fx - 34, GY - 156), (fx + 34, GY - 156), (fx + 260, GY - 20)])
    pg.draw.polygon(far, (210, 226, 226), [(fx - 34, GY - 156), (fx + 34, GY - 156), (fx + 62, GY - 124), (fx + 40, GY - 128),
                                           (fx + 22, GY - 116), (fx + 4, GY - 128), (fx - 16, GY - 118), (fx - 40, GY - 130),
                                           (fx - 62, GY - 124)])
    for row, (col, base) in enumerate((((16, 40, 30), GY - 70), ((10, 28, 20), GY - 40))):   # the canopy: rows of cedar tops
        x = -10
        while x < fw:
            h = rnd.randint(30, 60)
            pg.draw.polygon(far, col, [(x - 12, base + 30), (x, base - h), (x + 12, base + 30)])
            x += rnd.randint(8, 16)
        far.fill(col, (0, base + 20, fw, H - base))
    x = -10
    while x < mid.get_width():                                     # big cedar trunks with roots spreading on the ground
        w = rnd.randint(8, 18)
        col = rnd.choice(((14, 30, 22), (18, 36, 26), (12, 24, 18)))
        pg.draw.rect(mid, col, (x, 0, w, GY))
        pg.draw.line(mid, tuple(c + 14 for c in col), (x + 2, 0), (x + 2, GY))
        for _ in range(3):                                         # roots
            d = rnd.choice((-1, 1))
            pts = [(x + w // 2, GY - rnd.randint(10, 26))]
            for k in range(4):
                pts.append((pts[-1][0] + d * rnd.randint(6, 12), pts[-1][1] + rnd.randint(3, 8)))
            pg.draw.lines(mid, col, False, pts, 3)
        for _ in range(4):                                         # moss patches
            mid.fill((40, 80, 44), (x + rnd.randint(0, w - 2), rnd.randint(30, GY - 10), 2, rnd.randint(4, 10)))
        if rnd.random() < .12:                                     # a sacred tree: shimenawa rope with paper streamers
            ry = GY - rnd.randint(70, 110)
            pg.draw.line(mid, (200, 180, 120), (x - 2, ry), (x + w + 2, ry + 2), 3)
            for k in range(3):
                zx = x + 2 + k * w // 3
                pg.draw.lines(mid, (236, 236, 226), False, [(zx, ry + 2), (zx + 2, ry + 6), (zx - 1, ry + 9), (zx + 1, ry + 13)], 1)
        x += w + rnd.randint(14, 46)
    x = -10
    while x < near.get_width():                                    # ferns, mossy stones, a jizo statue now and then
        r = rnd.random()
        if r < .5:
            for k in range(6):
                a = -math.pi / 2 + (k - 2.5) * .3
                pg.draw.line(near, (20, 50, 30), (x, GY), (x + math.cos(a) * 18, GY + math.sin(a) * 16), 2)
            x += rnd.randint(20, 40)
        elif r < .8:
            w = rnd.randint(16, 30)
            pg.draw.ellipse(near, (30, 40, 34), (x, GY - 12, w, 16))
            pg.draw.ellipse(near, (44, 90, 50), (x + 2, GY - 13, w - 4, 6))
            x += w + rnd.randint(10, 30)
        else:
            pg.draw.rect(near, (60, 66, 62), (x, GY - 16, 9, 16))
            pg.draw.circle(near, (66, 72, 68), (x + 4, GY - 19), 5)
            pg.draw.rect(near, (170, 30, 40), (x - 1, GY - 14, 11, 4))   # a red bib
            x += rnd.randint(30, 60)
    for y in range(GY - 120, GY):
        haze.fill((110, 190, 140, int(70 * ((y - GY + 120) / 120) ** 2)), (0, y, W, 1))


def bake_peaks(rnd, sky, far, mid, near, haze):
    """KIRIGAMINE: a cold moon over jagged snow peaks, a sea of clouds, a monastery on the cliffs, prayer flags in the wind."""
    vgrad(sky, [(0, (4, 6, 18)), (100, (20, 30, 64)), (GY - 40, (110, 130, 176)), (H, (120, 140, 186))])
    for _ in range(90):
        sky.set_at((rnd.randint(0, W - 1), rnd.randint(0, 110)), rnd.choice(((200, 210, 255), (140, 150, 200))))
    mx, my = int(W * .72), 56
    glow(sky, mx, my, 90, (40, 50, 90))
    pg.draw.circle(sky, (226, 236, 255), (mx, my), 20)
    pg.draw.circle(sky, (196, 210, 240), (mx - 6, my - 4), 5)
    fw = far.get_width()
    for row, (col, base, amp) in enumerate((((56, 66, 104), GY - 90, 80), ((38, 46, 80), GY - 50, 60))):
        pts, x = [(0, H)], 0
        while x <= fw:
            pts.append((x, base - rnd.randint(0, amp)))
            x += rnd.randint(26, 60)
        pts += [(fw, H)]
        pg.draw.polygon(far, col, pts)
        for a_, b_ in zip(pts[1:-2], pts[2:-1]):                    # snow on the ridges
            top_, low_ = (a_, b_) if a_[1] < b_[1] else (b_, a_)
            pg.draw.polygon(far, (220, 230, 250) if row == 0 else (170, 186, 220),
                            [top_, (lerp(top_[0], low_[0], .4), lerp(top_[1], low_[1], .4)),
                             (top_[0] + (6 if low_[0] > top_[0] else -6), top_[1] + 9)])
    for i in range(70):                                            # the sea of clouds below the peaks
        cx_, cy_ = rnd.randint(0, fw), GY - 30 + rnd.randint(-8, 14)
        pg.draw.ellipse(far, (150, 166, 206), (cx_ - 30, cy_ - 7, 60, 16))
    x = -10
    while x < mid.get_width():                                     # cliffs with a monastery and pines, prayer flags between
        w, h = rnd.randint(70, 130), rnd.randint(40, 100)
        top = GY - h
        pg.draw.polygon(mid, (26, 30, 52), [(x, GY), (x + 8, top + 10), (x + w // 2, top), (x + w - 6, top + 14), (x + w, GY)])
        pg.draw.line(mid, (190, 206, 236), (x + 8, top + 10), (x + w // 2, top), 2)
        pg.draw.line(mid, (190, 206, 236), (x + w // 2, top), (x + w - 6, top + 14), 2)
        if rnd.random() < .55:                                     # a hall on the cliff top: curved roof, a warm window
            hx, hw = x + w // 2 - 18, 36
            pg.draw.rect(mid, (20, 22, 40), (hx + 4, top - 16, hw - 8, 16))
            pg.draw.polygon(mid, (20, 22, 40), [(hx - 6, top - 14), (hx + hw + 6, top - 14), (hx + hw - 4, top - 24), (hx + 4, top - 24)])
            pg.draw.line(mid, (200, 214, 240), (hx - 6, top - 14), (hx + 4, top - 24))
            pg.draw.line(mid, (200, 214, 240), (hx + 4, top - 24), (hx + hw - 4, top - 24))
            mid.fill((255, 190, 110), (hx + hw // 2 - 3, top - 11, 6, 5))
        if rnd.random() < .6:                                      # a line of prayer flags down to the next cliff
            x0, y0 = x + w - 6, top + 14
            x1, y1 = x + w + 40, GY - rnd.randint(40, 80)
            pg.draw.line(mid, (60, 60, 80), (x0, y0), (x1, y1))
            for k in range(1, 8):
                fx_, fy_ = lerp(x0, x1, k / 8), lerp(y0, y1, k / 8) + 1
                mid.fill(((210, 60, 60), (240, 220, 80), (80, 170, 90), (70, 120, 220), (236, 236, 236))[k % 5], (fx_, fy_, 3, 4))
        x += w + rnd.randint(30, 80)
    x = -10
    while x < near.get_width():                                    # snowy rocks and wind-bent pines
        if rnd.random() < .6:
            w, h = rnd.randint(20, 46), rnd.randint(10, 26)
            pg.draw.polygon(near, (30, 34, 54), [(x, GY), (x + 4, GY - h), (x + w // 2, GY - h - 6), (x + w, GY)])
            pg.draw.polygon(near, (220, 230, 250), [(x + 4, GY - h), (x + w // 2, GY - h - 6), (x + w // 2 + 8, GY - h - 1), (x + 6, GY - h + 3)])
            x += w + rnd.randint(10, 40)
        else:
            tx, h = x + 10, rnd.randint(40, 70)
            pg.draw.line(near, (22, 20, 30), (tx, GY), (tx - 6, GY - h), 3)
            for k in range(3):
                pg.draw.ellipse(near, (22, 30, 34), (tx - 28 + k * 4, GY - h + k * 12, 34, 9))
                pg.draw.line(near, (220, 230, 250), (tx - 26 + k * 4, GY - h + k * 12 + 1), (tx + 2 + k * 4, GY - h + k * 12 + 1))
            x += rnd.randint(40, 70)
    for y in range(GY - 110, GY):
        haze.fill((190, 210, 250, int(60 * ((y - GY + 110) / 110) ** 2)), (0, y, W, 1))


def bake_dojo(rnd, sky, far, mid, near, haze):
    """TENSHIN DOJO: a red evening sun, far mountains and a castle, the dojo's wooden halls, sakura over the walls."""
    vgrad(sky, [(0, (20, 8, 16)), (100, (92, 30, 34)), (GY - 40, (236, 130, 66)), (H, (240, 140, 70))])
    sx, sy = int(W * .4), 92
    glow(sky, sx, sy, 120, (100, 40, 20))
    pg.draw.circle(sky, (255, 120, 70), (sx, sy), 30)
    for k in range(4):                                             # bands of evening cloud across the sun
        sky.fill((236, 110, 70), (sx - 50 + k * 8, sy - 6 + k * 9, 100 - k * 16, 2))
    fw = far.get_width()
    for col, base, amp in (((110, 44, 50), GY - 60, 50), ((80, 30, 40), GY - 34, 30)):
        pts, x = [(0, H)], 0
        while x <= fw:
            pts.append((x, base - rnd.randint(0, amp)))
            x += rnd.randint(40, 80)
        pts += [(fw, H)]
        pg.draw.polygon(far, col, pts)
    cx_ = int(fw * .7)                                             # a castle keep on a far hill
    for i, (w, h) in enumerate(((50, 16), (40, 14), (30, 12), (20, 12))):
        y = GY - 70 - i * 14
        pg.draw.rect(far, (60, 22, 30), (cx_ - w // 2, y, w, h))
        pg.draw.polygon(far, (50, 18, 26), [(cx_ - w // 2 - 6, y + 2), (cx_ + w // 2 + 6, y + 2), (cx_ + w // 2 - 2, y - 4), (cx_ - w // 2 + 2, y - 4)])
    x = -10
    while x < mid.get_width():                                     # dojo halls: white plaster, dark beams, heavy curved roofs
        if rnd.random() < .7:
            w, h = rnd.randint(90, 150), rnd.randint(40, 64)
            top = GY - h
            pg.draw.rect(mid, (70, 50, 46), (x, top, w, h))
            for bx in range(x, x + w, 18):
                pg.draw.line(mid, (36, 22, 20), (bx, top), (bx, GY), 2)
            pg.draw.line(mid, (36, 22, 20), (x, top + h // 2), (x + w, top + h // 2), 2)
            pg.draw.polygon(mid, (32, 18, 20), [(x - 14, top + 4), (x + w + 14, top + 4), (x + w - 6, top - 18), (x + 6, top - 18)])
            pg.draw.polygon(mid, (32, 18, 20), [(x + w // 2 - 20, top - 18), (x + w // 2 + 20, top - 18), (x + w // 2, top - 30)])
            pg.draw.line(mid, (255, 170, 100), (x - 14, top + 4), (x + 6, top - 18))
            if rnd.random() < .6:                                  # the name board over the door
                pg.draw.rect(mid, (24, 12, 10), (x + w // 2 - 16, top + 6, 32, 10))
                img = F_JP.render(rnd.choice(("道場", "天真", "一心")), False, (230, 190, 110))
                mid.blit(img, (x + w // 2 - img.get_width() // 2, top + 4))
            x += w + rnd.randint(16, 40)
        else:                                                      # a sakura tree
            tx, h = x + 24, rnd.randint(60, 90)
            pg.draw.line(mid, (40, 20, 24), (tx, GY), (tx + rnd.randint(-6, 6), GY - h), 4)
            for _ in range(6):
                cx2, cy2 = tx + rnd.randint(-26, 26), GY - h + rnd.randint(-10, 24)
                pg.draw.circle(mid, rnd.choice(((240, 150, 180), (220, 120, 160), (255, 180, 200))), (cx2, cy2), rnd.randint(8, 14))
            x += rnd.randint(50, 80)
    x = -10
    while x < near.get_width():                                    # the compound wall with a tiled cap, training posts by it
        w = rnd.randint(80, 140)
        top = GY - 30
        pg.draw.rect(near, (60, 40, 36), (x, top, w, 30))
        pg.draw.polygon(near, (30, 18, 18), [(x - 4, top + 2), (x + w + 4, top + 2), (x + w - 2, top - 6), (x + 2, top - 6)])
        for bx in range(x + 6, x + w - 6, 22):
            pg.draw.line(near, (40, 24, 22), (bx, top + 4), (bx, GY))
        if rnd.random() < .6:                                      # a makiwara post wrapped in straw
            mx_ = x + w + 10
            pg.draw.rect(near, (90, 60, 36), (mx_ - 2, GY - 34, 5, 34))
            pg.draw.rect(near, (190, 160, 100), (mx_ - 3, GY - 32, 7, 10))
        x += w + rnd.randint(20, 50)
    for y in range(GY - 100, GY):
        haze.fill((255, 150, 90, int(60 * ((y - GY + 100) / 100) ** 2)), (0, y, W, 1))


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
                  'atkT', 'parry', 'pcd', 'runk', 'idleT', 'idle_animT', 'skcd', 'shield'):
            setattr(s, a, 0.0)
        s.crouch = s.dead = s.slam = s.launched = False
        s.stepn, s.idle_anim = 0, None
        s.airdash, s.was_g, s.swing, s.atkdir, s.step = True, True, set(), 'side', 1
        s.air_jump = s.tdash = False
        s.chains = {'scarf': [[s.x, s.y] for _ in range(7)], 'hair': [[s.x, s.y] for _ in range(6)]}
        s.pose = pose_idle(0)


KINDS = {  # w, h, hp, speed, windup, reach, damage
    'ronin': (12, 28, 2, 1.0, .45, 30, 1),
    'oni': (18, 37, 5, .65, .75, 44, 2),
    'ninja': (11, 25, 1, 1.15, .35, 0, 1),
    'yari': (12, 28, 3, .9, .55, 58, 1),        # spearman: long thrust, keeps you at the end of his spear
    'kunoichi': (11, 26, 2, 1.04, .3, 130, 1),  # kunoichi: dashes through you with a short blade (80% of the old 1.3)
    'teppo': (12, 28, 2, .85, .95, 320, 1),     # dock rifleman: a red aiming line, then one fast shot (parry it back)
    'tate': (15, 30, 4, .7, .6, 30, 1),         # shield wall: blocks cuts from the front - slam, go round, or wait for the bash
    'sohei': (13, 29, 4, .85, .6, 46, 1),       # warrior monk: the naginata whirlwind hits both sides
    'onryo': (12, 26, 2, 1.0, .6, 0, 1),        # vengeful ghost: floats through roofs, shrieks, then lunges
    'boss_destroyer': (42, 118, 65, .8, .6, 100, 2),
    'boss_chaos': (28, 96, 67, 1.3, .3, 60, 2),
    'boss_mutant': (42, 116, 80, 1.0, .6, 90, 2),
    'boss_shogun': (40, 112, 120, 1.1, .45, 90, 2),
    # the other locations' bosses (their HP grows with the location: LOC_HP)
    'boss_nio': (42, 118, 60, .8, .6, 100, 2), 'boss_abbot': (40, 116, 96, 1.0, .5, 90, 2),
    'boss_wanderer': (36, 110, 56, 1.0, .5, 80, 2), 'boss_kitsune': (30, 100, 62, 1.3, .35, 70, 2),
    'boss_mossoni': (44, 120, 125, .8, .6, 100, 2), 'boss_tengu': (38, 112, 70, 1.1, .5, 90, 2),
    'boss_yukionna': (30, 104, 59, 1.2, .4, 70, 2), 'boss_sensei': (16, 38, 63, 1.2, .4, 40, 2),
    'boss_mokujin': (44, 120, 50, .8, .6, 100, 2), 'boss_tomoe': (32, 108, 56, 1.2, .45, 90, 2),
    'boss_brother': (14, 34, 79, 1.4, .35, 36, 2),
}
ACTIVITIES = {'ronin': ('walk', 'guard', 'tea', 'phone', 'smoke', 'sleep'), 'oni': ('walk', 'guard', 'tea', 'sleep'),
              'ninja': ('walk', 'guard', 'meditate', 'phone'), 'yari': ('walk', 'guard', 'tea', 'smoke'),
              'kunoichi': ('walk', 'meditate', 'phone', 'guard'), 'teppo': ('walk', 'guard', 'smoke', 'phone'),
              'tate': ('guard', 'walk', 'tea'), 'sohei': ('meditate', 'walk', 'guard'), 'onryo': ('float',),
              'boss_destroyer': ('guard',), 'boss_chaos': ('meditate',), 'boss_mutant': ('guard',), 'boss_shogun': ('guard',)}
ACTIVITIES.update({k: ('guard',) for k in KINDS if k.startswith('boss_') and k not in ACTIVITIES})
ACT_BOSS = ('boss_destroyer', 'boss_mutant', 'boss_shogun')    # the boss under the end of each act (districts 5, 10, 15)
LOC_BOSSES = (ACT_BOSS,                                          # every location: its own boss after districts 5, 10 and 15
              ('boss_nio', 'boss_chaos', 'boss_abbot'),
              ('boss_wanderer', 'boss_kitsune', 'boss_mossoni'),
              ('boss_tengu', 'boss_yukionna', 'boss_sensei'),
              ('boss_mokujin', 'boss_tomoe', 'boss_brother'))
BOSS_KINDS = tuple(k for loc in LOC_BOSSES for k in loc)
BOSS_TITLES = {'boss_destroyer': "DESTROYER", 'boss_chaos': "CHAOSMAKER", 'boss_mutant': "MUTANT", 'boss_shogun': "THE SHOGUN",
               'boss_nio': "NIO GUARDIAN", 'boss_abbot': "THE FALLEN ABBOT", 'boss_wanderer': "JUKAI WANDERER",
               'boss_kitsune': "KITSUNE", 'boss_mossoni': "MOSS ONI", 'boss_tengu': "DAITENGU", 'boss_yukionna': "YUKI-ONNA",
               'boss_sensei': "THE SENSEI", 'boss_mokujin': "MOKUJIN", 'boss_tomoe': "LADY TOMOE", 'boss_brother': "BROTHER"}
BOSS_SUBS = {'boss_destroyer': "Iron fist of the Shogun", 'boss_chaos': "The one who breaks the night",
             'boss_mutant': "What the sewers made", 'boss_shogun': "Lord of the burning tower",
             'boss_nio': "The gate does not open", 'boss_abbot': "His prayers turned to ash",
             'boss_wanderer': "Lost, and looking for company", 'boss_kitsune': "Nine tails, nine lies",
             'boss_mossoni': "The forest's old jailer", 'boss_tengu': "King of the mountain wind",
             'boss_yukionna': "Her breath is winter", 'boss_sensei': "He taught you to hold the blade",
             'boss_mokujin': "A thousand strikes, a thousand years", 'boss_tomoe': "The blade of the dojo",
             'boss_brother': "Same blood, other path"}
BOSS_KITE = ('boss_chaos', 'boss_wanderer')     # keep their distance and glide instead of walking
BOSS_MINION = {'boss_abbot': 'sohei', 'boss_kitsune': 'ninja', 'boss_mokujin': 'mokujin', 'boss_tomoe': 'deshi'}
BOSS_BLADE = {'boss_tengu': 'feather', 'boss_yukionna': 'ice', 'boss_wanderer': 'branch', 'boss_sensei': 'blade',
              'boss_mossoni': 'rock'}
BOSS_ORB = {'boss_wanderer': ((60, 200, 80), (200, 255, 180)), 'boss_kitsune': ((60, 150, 255), (190, 230, 255)),
            'boss_yukionna': ((80, 190, 255), (220, 245, 255)), 'boss_abbot': ((255, 160, 50), (255, 230, 170))}
BOSS_CHAINS = {'boss_chaos': {'scarf': 6, 'band': 4}, 'boss_shogun': {'scarf': 7}, 'boss_kitsune': {'hair': 7, 'band': 4},
               'boss_yukionna': {'hair': 7}, 'boss_tomoe': {'hair': 6, 'scarf': 5}, 'boss_brother': {'scarf': 7, 'hair': 6},
               'boss_sensei': {'scarf': 5}}
# Dead Cells style move sets: (attack, weight, phase it unlocks in)
BOSS_ATTACKS = {'boss_destroyer': (('cleave', 3, 1), ('charge', 2, 1), ('stomp', 2, 1), ('barrage', 2, 2)),
                'boss_chaos': (('blink', 3, 1), ('warp', 3, 1), ('rift', 2, 1), ('blades', 2, 1), ('crossdash', 2, 2)),
                # the Mutant: wild - pounces, wall bounces, fast rakes
                'boss_mutant': (('claw', 3, 1), ('pounce', 3, 1), ('acid', 2, 1), ('leap', 1, 1), ('ricochet', 3, 2),
                                ('quake', 1, 2)),
                # the Shogun: a swordsman only - no parries, no chaos; at 1/3 HP the rage rush
                'boss_shogun': (('iai', 3, 1), ('combo', 2, 1), ('cleave', 2, 1), ('waves', 2, 1), ('summon', 1, 1),
                                ('rush', 3, 2)),
                # Temple Heights: the temple-gate statue (low sweeps, stomps, statue rush), the Wasp-like abbot
                'boss_nio': (('sweep', 3, 1), ('cleave', 2, 1), ('stomp', 2, 1), ('charge', 2, 1), ('quake', 2, 2),
                             ('waves', 1, 2)),
                'boss_abbot': (('combo', 3, 1), ('sweep', 2, 1), ('pounce', 2, 1), ('barrage', 2, 1), ('blink', 2, 1),
                               ('hop', 1, 1), ('whirl', 1, 2)),
                # Aokigahara: the witch, the fox, the bog oni
                'boss_wanderer': (('roots', 3, 1), ('rift', 3, 1), ('warp', 3, 1), ('blades', 2, 1), ('barrage', 2, 2)),
                'boss_kitsune': (('pounce', 3, 1), ('rift', 2, 1), ('sweep', 2, 1), ('warp', 2, 1), ('iai', 2, 1), ('hop', 2, 1),
                                 ('ricochet', 2, 2), ('summon', 1, 2)),
                'boss_mossoni': (('cleave', 2, 1), ('sweep', 2, 1), ('roots', 2, 1), ('charge', 2, 1), ('leap', 2, 1),
                                 ('pounce', 1, 1), ('blades', 2, 2),
                                 ('quake', 2, 2)),
                # Kirigamine: the tengu (gusts, dives, twin cuts, the gale pull), the snow woman with two knives, the Sensei
                'boss_tengu': (('gust', 3, 1), ('pounce', 2, 1), ('twin', 2, 1), ('hop', 2, 1), ('gale', 2, 1), ('blades', 2, 2)),
                'boss_yukionna': (('combo', 3, 1), ('dashcut', 3, 1), ('blink', 2, 1), ('barrage', 2, 1), ('hop', 2, 1),
                                  ('pounce', 2, 2)),
                'boss_sensei': (('combo', 3, 1), ('risecut', 2, 1), ('airdash', 2, 1), ('dashcut', 2, 1), ('sweep', 2, 1),
                                ('hop', 2, 1), ('barrage', 1, 2), ('waves', 2, 2)),
                # Tenshin Dojo: the wooden dummy, the naginata duellist, the brother who fights like you
                'boss_mokujin': (('combo', 3, 1), ('charge', 2, 1), ('barrage', 2, 1), ('stomp', 2, 1), ('blink', 2, 2)),
                'boss_tomoe': (('sweep', 3, 1), ('thrust', 3, 1), ('vault', 2, 1), ('combo', 2, 1), ('counter', 1, 2),
                               ('whirl', 1, 2)),
                'boss_brother': (('combo', 3, 1), ('dashcut', 3, 1), ('slide', 2, 1), ('hop', 2, 1), ('airdash', 2, 1),
                                 ('stomp', 2, 1), ('counter', 1, 1), ('barrage', 2, 2), ('waves', 2, 2), ('blink', 2, 3))}
BOSS_COMBO = {'boss_yukionna': (5, .14), 'boss_abbot': (4, .22), 'boss_brother': (3, .24), 'boss_sensei': (3, .34),
              'boss_mokujin': (2, .36), 'boss_shogun': (2, .33)}                         # combo: how many cuts, seconds per cut (default 3, .33)
BOSS_TEMPO = {'boss_mutant': .83, 'boss_yukionna': .62, 'boss_brother': .68, 'boss_sensei': .7, 'boss_tengu': .8,
              'boss_kitsune': .85, 'boss_abbot': .85}           # shorter wind-ups and recoveries: the fast ones
BOSS_MOBILE = ('warp', 'hop', 'blink', 'dashcut', 'pounce', 'charge', 'rush', 'slide', 'ricochet', 'leap', 'stomp', 'iai',
               'vault', 'airdash')                              # moves that get a boss away from a wall
BOSS_PARRIES = {'boss_sensei': (.2, .3)}                       # chance to parry your cut (phase 1, phase 2)
SENSEI_WAVES = ([('ronin', 1)], [('ninja', 1), ('ronin', -1)], [('kunoichi', 1)], [('kunoichi', 1), ('ronin', -1), ('ronin', 1)])
CHAIR_H = 62                                                    # the Sensei's high wooden chair
BOSS_PARRYABLE = ('cleave', 'claw', 'counter', 'iai', 'riposte', 'combo', 'thrust', 'rush', 'airdash')   # red telegraph: can be parried; the rest: dodge
BOSS_PHASES = {'boss_shogun': (1 / 3,), 'boss_brother': (2 / 3, 1 / 3), 'boss_sensei': (.5,)}                  # HP fractions where the next phase starts (default: half)
BOSS_SPEED = {'boss_destroyer': 70, 'boss_chaos': 150, 'boss_mutant': 175, 'boss_shogun': 120, 'boss_nio': 80, 'boss_abbot': 130,
              'boss_wanderer': 115, 'boss_kitsune': 170, 'boss_mossoni': 85, 'boss_tengu': 160, 'boss_yukionna': 240,
              'boss_sensei': 135, 'boss_mokujin': 75, 'boss_tomoe': 130, 'boss_brother': 210}
BOSS_TIMING = {  # wind-up (telegraph), action, recovery (the punish window) in seconds
    'cleave': (.6, .35, .5), 'charge': (.55, 1.6, .9), 'stomp': (.55, 0, .8), 'barrage': (.5, .1, .6),
    'blink': (.25, 1.1, .55), 'rift': (.5, .2, .6), 'blades': (.55, .3, .7), 'crossdash': (.5, .9, .6),
    'claw': (.35, .6, .7), 'leap': (.5, 0, .8), 'acid': (.5, .15, .7), 'quake': (.7, .2, .9),
    'iai': (.55, .5, .75), 'waves': (.5, .1, .7), 'counter': (.25, 1.1, .45), 'riposte': (0, .3, .9), 'summon': (.6, .2, .8),
    'whirl': (.55, 1.0, .8), 'roots': (.5, .2, .6), 'gust': (.45, .1, .6), 'combo': (.35, 1.0, .45), 'sweep': (.4, .35, .55),
    'dashcut': (.35, .6, .5), 'warp': (.2, .5, .25), 'hop': (.3, 0, .2), 'pounce': (.5, 0, .45), 'ricochet': (.35, 0, .5),
    'rush': (.4, 0, .6), 'thrust': (.4, .4, .55), 'twin': (.4, .6, .55), 'gale': (.55, .8, .6), 'risecut': (.3, 0, .45),
    'airdash': (.3, 0, .5), 'slide': (.3, .45, .45), 'vault': (.55, 0, .5)}
# every boss fights in its own arena, with its own hazard: (name, jp, wall top, wall bottom, accent, hazard)
ARENAS = {'boss_destroyer': ("THUNDER SUBSTATION", "変電所", (4, 8, 16), (12, 30, 52), (90, 220, 255), 'volt'),
          'boss_mutant': ("TOXIC CISTERN", "毒の貯水槽", (4, 10, 6), (18, 34, 16), (150, 255, 90), 'sludge'),
          'boss_shogun': ("TENSHU THRONE", "天守", (14, 6, 8), (60, 20, 16), (255, 204, 80), 'fire'),
          'boss_chaos': ("SHOGUN'S FOUNDRY", "鋳造所", (8, 3, 12), (34, 10, 24), (200, 80, 255), None),
          'boss_nio': ("THE THUNDER GATE", "雷門", (14, 6, 6), (54, 20, 14), (255, 170, 70), None),
          'boss_abbot': ("HALL OF THE GREAT BELL", "鐘楼", (12, 6, 8), (50, 22, 16), (255, 160, 60), None),
          'boss_wanderer': ("THE HANGING GROVE", "樹海", (2, 10, 6), (12, 34, 20), (110, 230, 130), None),
          'boss_kitsune': ("THOUSAND TORII", "千本鳥居", (10, 4, 10), (40, 14, 16), (255, 120, 40), None),
          'boss_mossoni': ("SUNKEN BOG", "沼地", (6, 12, 10), (26, 38, 22), (170, 220, 90), None),
          'boss_tengu': ("CLOUD PLATFORM", "雲の舞台", (30, 44, 90), (140, 160, 210), (220, 240, 255), None),
          'boss_yukionna': ("FROZEN SHRINE", "氷の社", (6, 14, 30), (40, 80, 120), (150, 220, 255), None),
          'boss_sensei': ("THE MOUNTAIN DOJO", "山の道場", (20, 18, 30), (70, 56, 50), (220, 230, 255), None),
          'boss_mokujin': ("TRAINING HALL", "稽古場", (24, 12, 8), (80, 44, 24), (255, 170, 90), None),
          'boss_tomoe': ("HALL OF BLADES", "刀の間", (20, 8, 10), (72, 30, 26), (255, 90, 90), None),
          'boss_brother': ("THE OLD HOME", "生家", (6, 6, 16), (34, 24, 40), (230, 40, 60), None)}
# how each new arena is drawn: style, seed, the big character on its wall
ARENA_STYLE = {'boss_nio': ('gate', 23, "雷"), 'boss_abbot': ('bell', 29, "鐘"), 'boss_wanderer': ('grove', 31, "迷"),
               'boss_kitsune': ('torii', 37, "狐"), 'boss_mossoni': ('swamp', 41, "沼"), 'boss_tengu': ('cliff', 43, "風"),
               'boss_yukionna': ('ice', 47, "雪"), 'boss_sensei': ('dojo', 53, "師"), 'boss_mokujin': ('dojo', 59, "木"),
               'boss_tomoe': ('dojo', 61, "刀"), 'boss_brother': ('dojo', 67, "兄")}
ARENA_W = 640                                                  # the underground boss arena under every fifth district
BOSS_X = ARENA_W - 190                                         # where the boss lands in the arena
BOSS_LEFT, BOSS_RIGHT = 24, ARENA_W - 24                        # how far the boss may go
CAVE_X = END_X - 200                                            # the hole down to the boss (a little left of the sealed gate)
HOLE_W = 56
HOLE_X = CAVE_X - HOLE_W // 2
# ---- level design: every five districts the city changes. Each theme: rooftop colours, props, the mix of building
# chunks it is made of, and a tint over the sky. A district is paced: a calm start, traversal and fights in turn,
# ambush plazas where enemies drop from the roofs, one hidden high cache, and a last plaza before the gate.
# Three acts of five districts, each a different part of the city with its own sky and weather, its own street hazard,
# its own mix of enemies (roster: kind -> weight) and its own boss and arena at the end.
THEMES = [
    dict(name="NEON SHINJUKU", jp="新宿", act="I", sub="The streets where it began", env='city', weather='rain',
         hazard=None, street=(255, 60, 160),
         slab=(20, 8, 34), line=(40, 20, 62), edge=(0, 230, 255), under=(255, 40, 140),
         glow=(40, 6, 26), tint=None, props=('ac', 'tank', 'ant', 'sign', 'sakura', 'sakura', 'shrine'),
         roster={'ronin': 5, 'ninja': 3, 'yari': 2, 'kunoichi': 1.5, 'oni': 1},
         weights={'stairs': 2, 'tower': 1.6, 'mover': 1.3, 'elevator': 1, 'crumble': 1.1, 'pad': 1, 'skyscraper': 1.7,
                  'bridge': 1.3, 'scaffold': 1.1}),
    dict(name="RYUGU DOCKS", jp="竜宮", act="II", sub="Salt, rust and gunpowder", env='docks', weather='fog',
         hazard='steam', street=(80, 255, 200),
         slab=(12, 26, 34), line=(30, 56, 68), edge=(80, 255, 200), under=(255, 150, 40),
         glow=(10, 30, 26), tint=None, props=('crate', 'crate', 'tank', 'ant', 'sign', 'ac'),
         roster={'ronin': 2.5, 'ninja': 2, 'yari': 2, 'teppo': 2.5, 'tate': 2, 'kunoichi': 1.5, 'oni': 1.5},
         weights={'stairs': 1, 'containers': 3, 'crane': 1.6, 'mover': 1.5, 'crumble': 1.2, 'pad': 1, 'bridge': 1,
                  'scaffold': 1.4}),
    dict(name="TEMPLE HEIGHTS", jp="寺町", act="III", sub="Where the Shogun waits", env='temple', weather='snow',
         hazard=None, street=(255, 200, 80),
         slab=(42, 10, 12), line=(84, 28, 24), edge=(255, 200, 80), under=(255, 60, 40),
         glow=(40, 12, 6), tint=None, props=('lantern', 'lantern', 'sakura', 'sakura', 'shrine', 'bell'),
         roster={'ronin': 1, 'ninja': 2, 'sohei': 3, 'onryo': 2.5, 'kunoichi': 2, 'teppo': 1.2, 'tate': 1.2, 'oni': 2},
         weights={'stairs': 1.6, 'pagoda': 2.4, 'tower': 1, 'bridge': 1.6, 'elevator': 1, 'pad': 1, 'crumble': 1.4,
                  'skyscraper': .5}),
]
THEMES += [
    dict(name="AOKIGAHARA FOREST", jp="青木ヶ原", act="IV", sub="The sea of trees", env='forest', weather='spores',
         hazard=None, street=(90, 220, 140),
         slab=(12, 26, 18), line=(26, 52, 34), edge=(110, 230, 140), under=(200, 255, 120),
         glow=(8, 30, 14), tint=None, props=('lantern', 'shrine', 'shrine', 'bell'),
         roster={'wanderer': 3, 'bandit': 3, 'hunter': 2, 'ninja': 1.5, 'kunoichi': 1.5, 'oni': 1.2},
         weights={'stairs': 1.6, 'tower': 1.2, 'bridge': 2.2, 'crumble': 1.8, 'pad': 1, 'elevator': .6, 'scaffold': 1.4,
                  'mover': 1}),
    dict(name="KIRIGAMINE PEAKS", jp="霧ヶ峰", act="V", sub="The monastery above the clouds", env='peaks', weather='blizzard',
         hazard=None, street=(160, 210, 255),
         slab=(26, 30, 46), line=(54, 62, 90), edge=(190, 230, 255), under=(120, 180, 255),
         glow=(14, 20, 40), tint=None, props=('lantern', 'bell', 'shrine', 'sakura'),
         roster={'tengu': 3, 'yamabushi': 3, 'yukionna': 2, 'sohei': 1.5, 'ninja': 1.5, 'oni': 1.2, 'teppo': 1},
         weights={'stairs': 2, 'pagoda': 2, 'tower': 1.4, 'bridge': 1.8, 'crumble': 1.8, 'pad': 1.4, 'elevator': 1}),
    dict(name="TENSHIN DOJO", jp="天真道場", act="VI", sub="Where blades are born", env='dojo', weather='petals',
         hazard=None, street=(255, 150, 60),
         slab=(46, 24, 14), line=(90, 52, 30), edge=(255, 180, 90), under=(255, 90, 50),
         glow=(40, 16, 6), tint=None, props=('lantern', 'sakura', 'sakura', 'bell', 'shrine'),
         roster={'deshi': 3, 'mokujin': 2.5, 'senpai': 2, 'yari': 1.5, 'sohei': 1.2, 'tate': 1, 'oni': 1},
         weights={'stairs': 1.4, 'pagoda': 1.6, 'tower': 1.2, 'bridge': 1.4, 'crumble': 1, 'pad': 1.2, 'elevator': 1,
                  'scaffold': 1}),
]
# where a run takes place: (name, jp, line under the preview, the theme of each act (None: not built yet), preview colours)
LOCATIONS = [("NEON SHINJUKU", "新宿", "Rain waits for you", (0, 0, 0), ((40, 10, 60), (255, 60, 160))),
             ("TEMPLE HEIGHTS", "寺町", "Snow on the thousand steps", (2, 2, 2), ((50, 14, 12), (255, 200, 80))),
             ("AOKIGAHARA FOREST", "青木ヶ原", "The trees remember", (3, 3, 3), ((8, 26, 16), (90, 220, 140))),
             ("KIRIGAMINE PEAKS", "霧ヶ峰", "Above the clouds, the wind", (4, 4, 4), ((20, 26, 44), (160, 210, 255))),
             ("TENSHIN DOJO", "天真道場", "Where blades are born", (5, 5, 5), ((40, 20, 10), (255, 150, 60)))]
LOC_HP = (1.0, 1.35, 1.7, 2.05, 2.4)                           # enemy HP per location: Neon Shinjuku is the easiest
KIND_FROM = {'yari': 2, 'kunoichi': 3, 'oni': 3}                # act one eases them in district by district
PLAZA_W = 230                                                   # open ground where an ambush waits
TALK_LINES = ["Rain again...", "The Shogun pays well.", "Did you hear that?", "My feet are killing me.",
              "Ramen after the shift?", "...heh.", "Quiet night.", "Who's up on the roofs?", "I hate this district."]
PHONE_LINES = ["Yes, boss.", "No sign of him.", "...uh-huh.", "I'll call you back.", "Tell her I'm working late.",
               "The rain? Still raining."]


class Enemy(Body):
    def __init__(s, x, plat, kind):
        look = kind if kind in LOOKS else None                 # a new location's enemy: an older fighter in its own body
        if look:
            kind = LOOKS[look]
        w, h, s.hp, s.spd, s.wind, s.reach, s.dmg = KINDS[kind]
        s.look = look or kind
        if look:
            s.hp = max(1, int(round(s.hp * LOOK_HP.get(look, 1))))
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
        s.flash = s.dodgecd = s.blinkcd = 0.0       # hit flash while armoured in an attack / dodge and blink cooldowns
        s.tier, s.combo, s.atk2 = 0, 0, None           # district tier (every 5 districts), follow-up slashes, oni smash
        if kind == 'kunoichi':
            s.chains = {'hair': [[x, s.y] for _ in range(5)], 'band': [[x, s.y] for _ in range(4)]}
        if kind == 'onryo':                                     # hovers above the roof, long hair trailing
            s.y -= 14
            s.chains = {'hair': [[x, s.y] for _ in range(6)]}
        s.pref, s.rhythm = R(.85, 1.15), R(0, 6.3)             # AI temperament: spacing and footsie rhythm
        s.aimx = s.aimy = 0.0                                   # teppo: where the rifle points
        s.guard, s.lx, s.ly = 0, 0.0, 0.0                       # tate: blows taken on the shield / onryo: lunge direction


# ---------------------------------------------------------------- game
KIND_NAMES = {'ronin': "RONIN", 'ninja': "SHINOBI", 'yari': "YARI", 'kunoichi': "KUNOICHI", 'oni': "ONI", 'teppo': "TEPPO",
              'tate': "TATE", 'sohei': "SOHEI", 'onryo': "ONRYO", 'wanderer': "WANDERER", 'bandit': "BANDIT",
              'hunter': "HUNTER", 'tengu': "TENGU", 'yamabushi': "YAMABUSHI", 'yukionna': "YUKI-ONNA", 'mokujin': "MOKUJIN",
              'deshi': "DESHI", 'senpai': "SENPAI"}


class CardFoe:
    """Just enough of an enemy for pose_enemy (the animated cards on the START screen)."""
    def __init__(s, kind):
        s.kind = LOOKS.get(kind, kind)
        s.wind = KINDS[s.kind][4]
        s.trav, s.st, s.hurt, s.t, s.anim, s.vx, s.g, s.throwT, s.combo = None, 'chase', 0, 0.0, 0.0, 0, True, 0, 0


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
        s.rain, s.snow, s.LT = [], [], {}                    # weather; baked backgrounds of the docks and the temple
        s.apply_settings()
        s.splash = []
        s.t, s.dt, s.fade, s.selT = 0.0, 1 / 60, 1.0, 0.0
        s.wipe, s.wipe_fn = 0.0, None
        s.train, s.trainT, s.blimp, s.lightT, s.lightning = None, 4.0, 0.0, R(8, 16), 0.0
        s.click, s.moved = False, False
        s.fingers, s.tedit_sel, s.drag, s.atk_rep = {}, None, None, 0.0   # touch: finger id -> [x, y, control, ...]
        s.ptr = (-99, -99)                                     # touch: where the last tap was (menus read it as the mouse)
        s.touch_map = 'direct' if pg.get_sdl_version() >= (2, 0, 18) else 'window'
        s.fnorm = s.mpos = None                                # this frame's finger-down / fake click (auto calibration)
        if TOUCH:                                              # every menu reads the mouse: on a phone that is the last tap
            pg.mouse.get_pos = lambda: (int(s.ptr[0]), int(s.ptr[1]))
        if pg.mixer.get_init():
            pg.mixer.set_num_channels(32)
            pg.mixer.set_reserved(2)                         # channels 0+1: the two music layers
        s.new_run()
        s.go('menu')
        if ANDROID and not s.settings['tcal']:                 # first launch on a phone: calibrate the touch screen
            s.start_tcal('menu')

    def go(s, state, fade=.6):
        s.state, s.state_t, s.sel, s.fade = state, s.t, 0, fade
        if state != 'play':
            s.fingers = {}                                     # no stuck touch buttons across screens
        menus = ('menu', 'stats', 'settings', 'controls', 'skins', 'exit', 'victory', 'locsel', 'upgrades', 'teleport',
                 'tcal', 'touchedit')
        s.play_music('menu' if state in menus else 'fight')

    # ---------- settings, music, input
    def apply_settings(s):
        global LANG
        st = s.settings
        LANG = st.get('lang', 'ru')
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
        k = .35 if getattr(s, 'state', '') in ('pause', 'kiosk', 'gift') else 1.0
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
        if name == 'fight' and os.path.exists(os.path.join(ASSETS, 'level.mp3')):
            try:                                                # districts: the Pixel Combat loop
                pg.mixer.music.load(os.path.join(ASSETS, 'level.mp3'))
                pg.mixer.music.play(-1, fade_ms=900)
                s.layer_ch = None
                s.music_now = name
                s.music_volume()
                return
            except pg.error:
                pass
        if name == 'fight':                                     # fallback: two synced layers (calm + combat)
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
        return h


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

    def bind_name(s, kind, a):
        if TOUCH and s.last_input == 'touch':                    # phones: the on-screen button's name
            lab = TOUCH_LABELS.get(a, a.upper())
            return TOUCH_RU.get(lab, lab) if LANG == 'ru' else lab
        if kind == 'kb':
            name = pg.key.name(s.settings['kb'][a]).upper() or '?'
            return name.replace('LEFT ', '').replace('RIGHT ', 'R') if len(name) > 6 else name
        return PAD_NAMES.get(s.settings['pad'].get(a), '-')

    def handle_event(s, ev):
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
                return                                              # (phones: touch only, no sensor "gamepad")
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
        elif ev.type == pg.MOUSEWHEEL:
            s.wheel = getattr(s, 'wheel', 0) + ev.y
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

    def wipe_to(s, fn, label=None):
        """Persona-style transition; fn runs when the screen is covered. label: where you are going, shown big."""
        if s.wipe_fn is None:
            s.wipe, s.wipe_fn, s.wipe_label = 0.0, fn, label
            sfx('wipe')

    # ---------- runs and levels
    def act_theme(s, lvl):
        """The theme of the district: the chosen location's act (an endless run cycles through them)."""
        seq = LOCATIONS[getattr(s, 'loc', 0)][3] or (0, 1, 2)
        i = (lvl - 1) // 5
        return THEMES[seq[i % len(seq)] if getattr(s, 'endless', False) else seq[min(len(seq) - 1, i)]]

    def lvl_label(s, lvl):
        return f"{tr('DISTRICT')} {lvl}" + ("" if getattr(s, 'endless', False) else f"/{LEVELS}")

    def new_run(s):
        """A run = LEVELS districts in a row (or no end at all). Coins are only kept if you survive (or leave with an exit key)."""
        s.lvl, s.score, s.kills, s.gtime, s.run_done = 1, 0, 0, 0.0, False
        s.admin_run = False
        s.runst = {'mythic': 0, 'oni': 0, 'shinobi': 0, 'slams': 0, 'parries': 0, 'supers': 0, 'levels': 0}
        s.buffs, s.maxhp, s.hp_keep, s.superk, s.vampk = {}, 5 + s.upg('vital'), 5 + s.upg('vital'), 0.0, 0
        s.glass_keep, s.timed, s.ward, s.wardT, s.scarsN, s.gifts, s.oni_glass, s.medic_left = 0, {}, False, 0.0, 0, [], 0, 0
        s.end_kind = 'victory'
        s.build_level()
        s.start_level()

    def start_level(s):
        p = s.pl
        if s.lvl == 1:                            # opening: manga panel (blade, hood up), dialog, camera pulls back
            p.x, p.face = 110, 1
            s.cine_t, s.dl, s.dc, s.cine_phase, s.cine_out = 0.0, 0, 0.0, 'inspect', 0.0
            s.banner_until = s.t + 6.0
            p.pose = dict(POSE_INSPECT)
            s.go('cine', 1.0)
        else:                                     # walk in from the left; a neon shinobi gate slams shut behind
            s.gifts = (['random'] * (2 if s.lvl % 3 == 0 else 1) if s.buff('joker') else []) + ['scar'] * min(5, getattr(s, 'scarsN', 0))
            s.scarsN = 0
            p.x, p.face = -16, 1
            s.enterT, s.enter_cam = 1.3, 1.6
            s.banner_until = s.t + 6.0
            s.go('play', 1.0)

    def buff(s, b):
        return s.buffs.get(b, 0)

    def pal(s, skin=None):
        """Palette of the equipped (or given) skin."""
        return SKINS.get(skin or s.stats['skin'], SKINS['shadow'])[2]

    def skin_perk(s, sid):
        return s.stats['skin'] == sid

    def skill(s):
        return SKIN_SKILLS.get(s.stats['skin'])

    def skin_info(s):
        """Lines describing the equipped skin's perk and skill (None for the starting skin)."""
        sid = s.stats['skin']
        if sid == 'shadow' or sid not in SKIN_PERKS:
            return None
        lines = [tr(line).replace('{K}', s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'skill')) for line in SKIN_DESC[sid]]
        if SKIN_DIFF.get(sid, 1) > 1:
            lines.append(f"{tr('MORE ENEMIES')}: x{SKIN_DIFF[sid]:g}")
        return lines

    def draw_banner(s):
        """Top-of-screen card with the equipped skin's perk and skill, fading out."""
        lines = s.skin_info()
        left = s.banner_until - s.t
        a = min(1, left / .6)
        y = 34
        pg.draw.polygon(scr, INK, [(20, y), (W - 20, y - 2), (W - 24, y + 14 + 12 * len(lines)), (16, y + 16 + 12 * len(lines))])
        pg.draw.line(scr, (255, 60, 90), (20, y), (W - 20, y - 2), 2)
        for i, line in enumerate(lines):
            col = (255, 230, 150) if i == 0 else (255, 200, 220)
            img = F_S.render(line, False, col)
            img.set_alpha(int(255 * a))
            scr.blit(img, (W // 2 - img.get_width() // 2, y + 5 + i * 12))

    def skin_dmg(s):
        return (1 if s.skin_perk('white') else 0) + s.upg('blade')

    def adm(s, k):
        """An admin option, only while the ADMIN switch is on (multipliers return their value, switches True/False)."""
        st = s.settings
        if not st.get('admin'):
            return 1 if k in ADMIN_CYCLE else False
        if k in ADMIN_CYCLE:
            vals = ADMIN_CYCLE[k]
            i = st.get(k, 0)
            return vals[i % len(vals)] if isinstance(i, int) else vals[0]
        return st.get(k, False)

    def can_pay(s, price):
        return s.adm('a_money') or s.stats['wallet'] >= price

    def pay(s, price):
        if not s.adm('a_money'):
            s.stats['wallet'] -= price

    def upg_cap(s):
        """How many levels of each upgrade can be bought now (grows with the locations cleared)."""
        return UPG_CAPS[min(3, len(s.stats.get('cleared', [])))]

    def level_cap(s, k, top):
        """How many levels of this upgrade may be owned right now."""
        if k in UPG_GATES:
            n = len(s.stats.get('cleared', []))
            return sum(1 for g in UPG_GATES[k] if n >= g)
        return min(top, s.upg_cap())

    def upg(s, k, skin=None):
        """Level of a permanent upgrade (0..3) on the worn skin (each skin is upgraded on its own)."""
        return s.stats.get('upg', {}).get(skin or s.stats['skin'], {}).get(k, 0)

    def super_need(s):
        return max(4, int(round((10 if s.buff('storm') else 20) * (1 - .1 * s.upg('focus')))))

    def build_level(s):
        G = Plat(-50, GY, LW + 100, ground=True)
        s.plats, s.pads, s.vents = [G], [], list(range(330, LW - 100, 270))

        s.towers, s.scaffolds, s.strings, s.sakuras = [], [], [], []
        s.theme = th = s.act_theme(s.lvl)
        s.cranes, s.plazas, s.chests = [], [], []                 # crane frames, ambush plazas, hidden treasure chests

        def st(x, y, w):
            p = Plat(x, y, w)
            if random.random() < .3:
                p.deco = (random.choice(JP_V[:8]), random.choice(NEON))
            for _ in range(random.choice((0, 1, 1, 2))):
                kind = random.choice(th['props'])
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
        kinds, weights = zip(*th['weights'].items())
        last = END_X - (420 if s.lvl % 5 == 0 else 300)           # (boss districts leave room for the cave)
        n, cache_done, prev = 0, False, None
        while x < last:
            n += 1
            if n == 1:                                  # a calm start: low, easy steps
                kind = 'stairs'
            elif last - x < 120:                        # the street before the gate (then the district ends)
                break
            elif not cache_done and x > LW * .45:       # one hidden cache for whoever climbs
                kind, cache_done = 'cache', True
            else:
                kind = random.choices(kinds, weights)[0]
                if kind == prev:                        # never the same chunk twice in a row
                    kind = random.choices(kinds, weights)[0]
            prev = kind
            if kind == 'plaza':                         # open street, banners on poles: enemies drop from the roofs
                s.plazas.append({'x0': x, 'x1': x + PLAZA_W, 'n': 3 + (s.lvl - 1) // 5, 'done': False})
                end = x + PLAZA_W
            elif kind == 'cache':                       # a jump pad, a high ledge, and a chest above the city
                s.pads.append([x + 10, G, 0.0])
                mid = st(x + 50, GY - R(165, 175), 70)
                top = st(mid.x + R(70, 90), mid.y - R(52, 56), 64)
                top.props = [('lantern', 8, WHITE)]
                s.chests.append([top.x + top.w - 20, top.y, False])
                end = top.x + top.w + 20
            elif kind == 'containers':                  # stacked cargo containers: steps up and down
                hs = random.choice(((1, 2, 3, 2), (1, 2, 2, 3), (2, 3, 2, 1), (1, 3, 2)))
                cols = [(255, 120, 40), (40, 150, 220), (200, 40, 50), (60, 170, 110), (230, 200, 60)]
                for i, hgt in enumerate(hs):
                    c = st(x + i * 58, GY - 52 * hgt, 56)
                    c.props, c.deco, c.win = [], None, []
                    c.box = random.choice(cols)
                    s.sakuras = [sk for sk in s.sakuras if sk[0] is not c]
                end = x + len(hs) * 58 + 20
            elif kind == 'crane':                       # a crane: climb its tower, ride the swinging hook across
                a = st(x, GY - R(50, 54), 64)
                b = st(x + 8, a.y - R(52, 56), 48)
                m = Plat(x + 120, b.y - R(36, 44), 52, 'move')
                m.axis, m.amp, m.spd = 'x', R(40, 55), R(.9, 1.2)
                s.plats.append(m)
                c = st(m.x0 + m.amp + 86, m.y + R(-8, 20), R(70, 90))
                s.cranes.append((x + 30, m.y - 40, m.x0 + m.amp + 60))
                end = c.x + c.w + 10
            elif kind == 'pagoda':                      # tiered temple roofs, narrower towards the top
                w, tiers = R(140, 160), random.randint(3, 4)
                base = x
                for i in range(tiers):
                    tw = w - i * 30
                    p = st(base + (w - tw) / 2, GY - 54 * (i + 1), tw)
                    p.eave, p.win = True, []
                    if i < tiers - 1:
                        p.props = [q for q in p.props if q[0] != 'sakura']
                top = s.plats[-1]
                top.props = [('bell', top.w / 2 - 6, (255, 200, 80))]
                end = x + w + 30
            elif kind == 'skyscraper':                  # tall zig-zag tower, billboard on the roof
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
        s.pl.glass = getattr(s, 'glass_keep', 0)
        s.en, s.parts, s.fx, s.coins, s.proj, s.gibs, s.ghosts, s.loot, s.trail = [], [], [], [], [], [], [], [], []
        s.cam = s.camy = s.shake = s.hitstop = s.flash = s.deadT = s.coinpop = s.pflash = s.slowmo = 0.0
        s.spawnT, s.coinT, s.enterT, s.superT, s.intensity = 4.5, 3.5, 0.0, -1.0, 0.0
        s.mult = SKIN_DIFF.get(s.stats['skin'], 1)  # the skin you wear decides how busy the streets are
        s.spawned, s.lvl_kills, s.spirit_kills = 0, 0, 0
        s.acid, s.orbs = [], []
        s.max_en = int(round(min(8 + s.lvl, 15) * s.mult))   # later districts are busier
        s.door = {'x': EXIT_X, 'k': 0.0, 'closing': False, 'kind': 'red'}
        s.kiosk = {'x': 205, 'used': False, 'cards': None} if s.lvl >= 2 else None
        if s.kiosk and (s.buff('joker') or s.buff('invis')):     # JOKER / INVISIBILITY: the kiosk stays shut
            s.kiosk['used'] = s.kiosk['closed'] = True
        s.keydoor = None
        s.noise = []                              # [x, y, time left]: fights the enemies can hear
        s.bwaves = []                             # crimson skill: [x, y, facing, age, hit ids]
        s.banner_until = 0.0
        for i in range(32):
            s.add_coin(i >= 28)                  # rarer coins: 28 gold + 4 mythic, slowly respawning
        s.boss, s.bossw, s.boss_msg = None, [], ('', 0.0)
        s.arena, s.arena_open, s.arena_t, s.hole, s.boss_card = False, False, 0.0, None, -99.0
        s.freezeT, s.hitn, s.blades, s.lines, s.puddles, s.claws = 0.0, 0, [], [], [], []
        s.spikes = []                                             # roots / spikes bursting out of the arena floor
        s.ahaz = None                                             # the boss arena's hazard (molten vents / tide / fire walls)
        if s.lvl % 5 == 0:                    # every fifth district: the gate is sealed, the way on is a cave down to the boss
            s.quota = int(round((6 + s.lvl // 2) * s.mult))
            s.exit_need = (s.quota + 1) // 2
            bosses = LOC_BOSSES[getattr(s, 'loc', 0)]              # the location's own three bosses
            s.boss_kind = (random.choice(bosses) if getattr(s, 'endless', False)          # endless: any of them
                           else bosses[min(len(bosses) - 1, (s.lvl - 1) // 5)])
            if getattr(s, 'loc', 0) >= 3:                         # Kirigamine / Tenshin Dojo: a closed gate, the ground whole
                s.hole = {'x': CAVE_X, 'open': False, 'k': 0.0, 'lid': None, 'door': True}
            else:
                G.w = HOLE_X - G.x                                # the street cracks open just left of the sealed gate
                lid = Plat(HOLE_X, GY, HOLE_W, ground=True)        # a stone seal lies in the hole until half are cut down
                s.plats += [Plat(HOLE_X + HOLE_W, GY, LW + 50 - HOLE_X - HOLE_W, ground=True), lid]
                s.hole = {'x': CAVE_X, 'open': False, 'k': 0.0, 'lid': lid}
            s.vents = [v for v in s.vents if not CAVE_X - 90 < v < CAVE_X + 90]
            s.lamps = [lx for lx in s.lamps if not CAVE_X - 100 < lx < CAVE_X + 90]
            lo, hi = CAVE_X - 80, CAVE_X + 80                      # keep the broken ground clear: no rooftops, coins or strings over it
            gone = [q for q in s.plats if not q.ground and q.x < hi and q.x + q.w > lo]
            s.plats = [q for q in s.plats if q not in gone]
            s.sakuras = [sk for sk in s.sakuras if sk[0] not in gone]
            s.strings = [st_ for st_ in s.strings if st_[2] < lo or st_[0] > hi]
            s.coins = [c for c in s.coins if not (lo < c[0] < hi and c[1] < GY - 40)]
            s.towers = [tw for tw in s.towers if tw[0] + tw[1] < lo or tw[0] > hi]
            s.scaffolds = [sf for sf in s.scaffolds if sf[1] < lo or sf[0] > hi]
            n0 = max(4, s.max_en // 2)
        else:
            s.quota = int(round((8 + s.lvl) * s.mult))            # how many enemies this district holds
            s.exit_need = (s.quota + 1) // 2                      # the torii opens after killing at least this many
            n0 = max(4, s.max_en // 2)
        if s.buff('invis'):                                       # SHADOW CLOAK: the gate wants 3 spirit-touched
            s.exit_need = 3
        s.build_traps()
        for _ in range(min(n0, s.quota)):
            s.spawn_enemy(False)

    def finish_level(s):
        """Walked through the torii at the end of the district."""
        s.hp_keep, s.maxhp, s.glass_keep = s.pl.hp, s.pl.maxhp, s.pl.glass
        if s.buff('medic'):                                       # FIELD MEDIC runs out after 5 districts
            s.medic_left = getattr(s, 'medic_left', 5) - 1
            if s.medic_left <= 0:
                s.buffs.pop('medic', None)
        if s.arena:                                               # out of a boss arena: the boss's heart, +1 max HP, healed
            s.maxhp += 1
            s.hp_keep = s.maxhp
        s.runst['levels'] += 1
        if s.lvl >= LEVELS and not getattr(s, 'endless', False):
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
        kind = s.roster_kind()
        taken = {id(e.home) for e in s.en if not e.home.ground}
        sp = s.static_plats()
        for _ in range(60):
            p = random.choice(sp)
            if p.w < 50 or (not p.ground and id(p) in taken):          # max 1 enemy per rooftop
                continue
            x = R(max(p.x, 0) + 5, min(p.x + p.w, LW) - 22)
            if p.ground and any(e.home.ground and abs(e.x - x) < 80 for e in s.en):
                continue
            if any(abs(tp['y'] - p.y) < 2 and abs(tp['x'] - x - 6) < 46 for tp in s.traps):   # not on top of a trap
                continue
            if (not offscreen and x < 330) or abs(x - s.pl.x) < 160:
                continue
            if s.hole and x > CAVE_X - 220:                          # boss district: nobody at the way down or past the gate
                continue
            if offscreen and s.cam - 20 < x < s.cam + W + 20:
                continue
            e = s.scale_enemy(Enemy(x, p, kind))
            s.en.append(e)
            s.spawned += 1
            if p.ground and kind not in ('oni', 'onryo') and random.random() < .35 and len(s.en) < s.max_en:   # two chatting
                mate = s.scale_enemy(Enemy(x + 30, p, kind if kind in ('ronin', 'yari', 'teppo', 'sohei') else 'ronin'))
                e.act = mate.act = 'talk'
                e.face, mate.face = 1, -1
                s.en.append(mate)
                s.spawned += 1
            return

    def roster_kind(s):
        """Who walks these streets: the act's own mix of enemies (act one brings them in one district at a time)."""
        ros = [(k, w) for k, w in s.theme['roster'].items() if s.lvl >= KIND_FROM.get(k, 1)]
        return random.choices([k for k, _ in ros], [w for _, w in ros])[0]

    def diff(s):
        return DIFFS[s.settings.get('diff', 2)]

    def scale_enemy(s, e):
        """The Shogun's men get tougher a little every district (no sudden walls): more HP, faster, quicker to strike.
        The far locations hit harder, and late in a run the heavy hitters (oni, shield wall, monks) hit harder still."""
        L, loc = s.lvl - 1, getattr(s, 'loc', 0)
        e.tier = min(2, L // 5 + loc)                         # (the tier still dresses them up: gold trim, red war paint)
        e.hp = e.maxhp = max(1, int(round(e.maxhp * (1 + .09 * L) * LOC_HP[loc])))
        e.spd *= (1 + .02 * L) * (1 + .06 * loc)
        e.wind *= (1 - .015 * min(L, 30)) * (1 - .07 * loc)       # (an endless run stops speeding them up at some point)
        if loc >= 2:                                            # the far locations hit harder
            e.dmg += 1
        if e.tier >= 2 and e.kind in ('oni', 'tate', 'sohei'):
            e.dmg += 1
        dd = s.diff()                                           # difficulty: their health, their attack speed
        e.hp = e.maxhp = max(1, int(round(e.hp * dd[1])))
        e.wind /= dd[3]
        return e

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
        if s.buff('invis'):                                        # INVISIBILITY: no coins for you
            return
        n = (n + (2 if s.buff('bounty') else 0)) * (3 if s.buff('gamble') else 1)   # BOUNTY HUNTER adds, ALL IN multiplies
        for _ in range(n):
            s.loot.append([x, y, R(-90, 90), R(-240, -140), random.random() < .1, 0.0])

    def collect(s, mythic, x, y):
        v = (5 if mythic else (3 if s.buff('greed') else 1)) + ((3 if mythic else 1) if s.skin_perk('gold') else 0)   # GOLD RUSH
        s.score += v * (5 if s.buff('gamble') else 1)                                                    # GAMBLE
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
    def hurt_enemy(s, e, f, dmg=1, pierce=False):
        if e.kind.startswith('boss'):
            return s.hurt_boss(e, f, dmg)
        if getattr(e, 'warpin', 0) > 0:                                # not here yet
            return
        if (e.kind == 'tate' and not pierce and f == -e.face and not e.trav
                and e.st not in ('calm', 'stun', 'wind', 'slash')):    # the shield takes it: go round, slam, or break it
            e.guard = getattr(e, 'guard', 0) + 1
            e.x += f * 3
            s.fx.append(['spark', e.x + e.w / 2 + e.face * 8, e.y + e.h * .45, f, .14, .14, R(0, 1)])
            s.hitstop = .04
            sfx('block')
            if e.guard >= 4:                                       # four blows and the shield arm gives out
                e.guard, e.st, e.t, e.vx = 0, 'stun', 1.4, 0
                s.boss_msg = ('SHIELD BROKEN', 1.0)
                sfx('crack')
            else:
                e.cd = min(e.cd, .3)                               # ...and it answers with a bash
            return
        if e.st == 'calm':                                       # caught unaware: one silent cut
            dmg = max(dmg, e.hp)
        if e.st == 'stun':                                         # parried enemies take a deathblow
            dmg *= 2
            s.burst(e.x + e.w / 2, e.y + e.h / 2, 12, (255, 240, 200), spd=160, glowing=True, grav=300)
        if s.buff('execute') and e.hp - dmg <= e.maxhp * .5:       # EXECUTIONER
            dmg = e.hp
        e.hp -= dmg
        if e.st in ('wind', 'slash', 'smash') and e.hp > 0:        # mid-attack: the hit lands, but the swing goes on
            e.flash = .12
            e.x += f * 2
        else:
            e.hurt, e.kb, e.st, e.cd, e.vy = .22, f * 170, 'chase', .5, -90
        s.hitstop, s.shake = .05, 3
        s.burst(e.x + e.w / 2, e.y + e.h / 2, 10, (255, 30, 70), dirx=f)
        s.fx.append(['spark', e.x + e.w / 2 - f * 3, e.y + e.h * .45, f, .14, .14, R(0, 1)])
        sfx('hit')
        if e.hp <= 0:
            s.kill_enemy(e, f)

    def rage_k(s, d):
        """RAGE: +50% damage at 1 HP."""
        return d * 1.5 if s.buff('rage') and s.pl.hp <= 1 else d

    def blade_dmg(s, base):
        """A slash / the super: base + RAZOR EDGE + JACKPOT + skin, x3 UNTOUCHABLE, -70% SLAM MASTER, RAGE."""
        d = (base + s.buff('edge') + s.buff('jackpot') + s.skin_dmg()) * s.adm('a_dmg')
        d *= (3 if s.buff('untouch') else 1) * (.3 if s.buff('slammaster') else 1)
        return round(s.rage_k(d), 2)

    def slam_dmg(s, base):
        """The slam's shockwave: base + EARTHSHAKER + JACKPOT + upgrade, x4 SLAM MASTER, RAGE."""
        d = (base + s.buff('quake') + s.buff('jackpot') + s.upg('slam')) * s.adm('a_dmg') * (3 if s.buff('slammaster') else 1)
        return round(s.rage_k(d), 2)

    def kill_enemy(s, e, f):
        if e.dead:
            return
        e.dead = True
        s.kills += 1
        s.lvl_kills += 1
        if getattr(e, 'spirit', False):                            # SHADOW CLOAK: a spirit set free
            s.spirit_kills = getattr(s, 'spirit_kills', 0) + 1
            s.burst(e.x + e.w / 2, e.y + 6, 22, (150, 230, 255), spd=90, glowing=True, grav=-120)
            sfx('glint')
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
        if s.skin_perk('jade') and s.vampk % 12 == 0 and s.pl.hp < s.pl.maxhp:   # JADE BREATH
            s.pl.hp += 1
            s.burst(s.pl.x + s.pl.w / 2, s.pl.y, 10, (120, 255, 170), spd=60, glowing=True, grav=-40)
        s.hitstop, s.shake = .1, 5
        cx, cy = e.x + e.w / 2, e.y + e.h / 2
        sfx('kill')
        s.rumble(.5, .3, 120)
        if s.buff('medic') and not e.kind.startswith('boss') and random.random() < .05:  # FIELD MEDIC: a heart
            s.loot.append([cx, cy, R(-60, 60), R(-240, -160), 'heart', 0.0])
        if e.kind.startswith('boss'):                            # the boss: no gibs, it bursts into light (see boss_death)
            return
        if e.kind == 'ninja':                    # shinobi vanish in a smoke-bomb explosion
            s.runst['shinobi'] += 1
            s.fx.append(['boom', cx, cy, 1, .45, .45, 0])
            s.puff(cx, cy + 6, 14, col=(110, 90, 140))
            s.burst(cx, cy, 16, (255, 200, 90), spd=170, glowing=True, grav=200)
            sfx('boom')
            s.drop_loot(cx, cy, 3)
            return
        if e.kind == 'onryo':                    # the ghost comes apart into cold light and a last wail
            s.puff(cx, cy, 12, col=(170, 200, 230))
            s.burst(cx, cy, 24, (180, 230, 255), spd=140, glowing=True, grav=-60)
            s.fx.append(['wave', cx, cy, 1, .35, .35, 0])
            sfx('glint')
            s.drop_loot(cx, cy, 2)
            return
        if e.kind == 'oni':
            s.runst['oni'] += 1
        s.burst(cx, cy, 34, (255, 30, 70), spd=170, dirx=f)
        s.fx.append(['cut', cx, cy, f, .18, .18, 0])
        S = PAL_E[getattr(e, 'look', e.kind)]
        for half in (0, 1):                      # sliced in two
            s.gibs.append([cx, e.y + e.h * (.3 if half == 0 else .75), f * R(60, 150), R(-220, -100) if half == 0 else R(-60, 0),
                           0.0, R(-14, 14) if half == 0 else R(-4, 4), half, 5.0, e.w, e.h / 2, e.kind, S])
        s.drop_loot(cx, cy, 3 if e.kind == 'oni' else (1 if random.random() < .5 else 0))

    def parry_fx(s, x, y):
        s.parry_ok = True                                            # something was blocked: no whiff penalty
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

    def add_super(s, n):
        """Charge the super by n (capped at what it needs); a ping when it becomes full."""
        need, old = s.super_need(), s.superk
        s.superk = min(need, s.superk + n)
        if old < need <= s.superk:
            sfx('charge')

    def perfect_fx(s, slow=.35):
        """A perfect parry / dodge: short slow motion, white flash, glint."""
        s.slowmo = max(s.slowmo, slow)
        s.pflash = max(s.pflash, .2)
        sfx('glint')

    def parried(s, e):
        """A blow landed inside the parry window: no damage, the enemy reels and is open to a deathblow."""
        p = s.pl
        perfect = getattr(s, 'parry_len', 0) - p.parry <= .08          # parried in the first 0.08 s of the window
        s.add_super(2)
        p.parry, p.pcd = 0, .12
        e.st, e.t, e.hit, e.vx, e.cd = 'stun', 1.1, True, 0, 1.0
        e.kb = 0
        e.x -= e.face * 6
        s.parry_fx((p.x + p.w / 2 + e.x + e.w / 2) / 2, p.y + 10)
        s.hitstop, s.slowmo = .14, .35
        if perfect:                                                  # PERFECT: longer slow-mo, a bright flash, a glint
            s.perfect_fx(.55)
        s.runst['parries'] += 1
        if s.buff('thorns'):                                         # COUNTER EDGE: the deflection cuts back
            s.burst(e.x + e.w / 2, e.y + e.h / 2, 12, (255, 150, 90), spd=140, glowing=True, grav=200)
            if e.kind.startswith('boss'):
                if e.bs != 'dying':
                    s.hurt_enemy(e, 1 if e.x > p.x else -1, 2 * s.buff('thorns'))
            else:
                e.hp -= 2 * s.buff('thorns')
                if e.hp <= 0:
                    s.kill_enemy(e, 1 if e.x > p.x else -1)

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
                    s.hurt_enemy(e, f, s.blade_dmg(4), pierce=True)
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
        if p.inv > 0 or p.dead or p.dash > 0 or p.slam or s.superT >= 0 or p.shield > 0:   # dash, slam, super and spirit shield
            return
        if s.settings.get('god'):                                       # SETTINGS -> IMMORTALITY (for testing): no damage
            return
        s.hitn += 1
        if s.buff('armor') and s.hitn % max(2, 4 - s.buff('armor')) == 0:    # IRON HAORI: this one is blocked
            p.inv = .6
            s.parry_fx(p.x + p.w / 2 - f * 6, p.y + 10)
            sfx('block')
            return
        if getattr(s, 'ward', False):                                  # SPIRIT WARD: the ward breaks instead of you
            s.ward, s.wardT, p.inv = False, 240.0, .8
            s.burst(p.x + p.w / 2, p.y + p.h / 2, 24, (200, 160, 255), spd=150, glowing=True, grav=0)
            s.parry_fx(p.x + p.w / 2 - f * 6, p.y + 10)
            sfx('crack')
            return
        glass = getattr(p, 'glass', 0)
        if s.buff('gamble'):                                           # GAMBLE: one hit and it's over
            dmg = p.hp + glass
        elif p.hp + glass - dmg <= 0 and s.buff('second'):              # SECOND WIND: one deadly hit survived
            s.buffs['second'] -= 1
            if not s.buffs['second']:
                del s.buffs['second']
            p.hp, p.inv, p.glass = 1, 2.0, 0
            s.pflash, s.shake, s.hitstop = .2, 8, .15
            s.burst(p.x + p.w / 2, p.y + p.h / 2, 30, (120, 255, 200), spd=160, glowing=True, grav=-40)
            sfx('glint')
            return
        if s.buff('scars'):                                            # SCAR CARDS: every HP lost becomes a card
            s.scarsN = getattr(s, 'scarsN', 0) + min(dmg, p.hp + glass)
        if glass > 0:                                                  # glass HP breaks first, and is gone for good
            g = min(glass, dmg)
            p.glass, dmg = glass - g, dmg - g
            s.burst(p.x + p.w / 2, p.y + p.h / 2, 18, GLASS, spd=170, glowing=True, grav=300)
            sfx('crack')
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
        big = 3 if s.buff('slammaster') else 1                     # SLAM MASTER: three times the range, and you see it
        if big > 1:
            s.fx.append(['wave', x, y, 3, .55, .55, 0])
            s.burst(x, y, 20, (90, 200, 255), spd=260, glowing=True, grav=300)
        s.punch, s.tilt = 1.0, random.choice((-4, 4))          # camera: short zoom + tilt on the landing
        sfx('slam')
        s.rumble(1.0, .6, 320)
        for e in s.en:
            ex = e.x + e.w / 2
            if not e.dead and not e.trav and abs(ex - x) < (70 + 10 * s.upg('slam')) * big and abs(e.y + e.h - y) < 28 * min(2, big):
                s.hurt_enemy(e, 1 if ex > x else -1, s.slam_dmg(2), pierce=True)
                if not e.kind.startswith('boss'):
                    e.vy = -220
                    e.kb = (1 if ex > x else -1) * 230                  # shoved out of the samurai's body
                    e.hurt = max(e.hurt, .25)
        p.inv = max(p.inv, .5)                                      # a short breath of invulnerability after the slam

    def player_hits(s):
        p = s.pl
        f, cx = p.face, p.x + p.w / 2
        rk = 1 + .25 * s.buff('reach')                              # LONG BLADE
        if p.atkdir == 'up':
            hb = (p.x - 18 * rk, p.y - 42 * rk, p.w + 36 * rk, 46 * rk)
        elif p.atkdir == 'down':
            hb = (p.x - 18 * rk, p.y + p.h - 6, p.w + 36 * rk, 44 * rk)
        else:
            reach = (66 if p.step == 3 else 54) * rk
            hb = (cx if f > 0 else cx - reach, p.y - 14, reach, p.h + 26)
        if p.atk < p.atkT * .65:
            return
        fin = p.step == 3 and p.atkdir == 'side'                     # the combo finisher cuts for 2
        dmg = s.blade_dmg(2 if fin else 1)
        for e in s.en:
            if not e.dead and not e.trav and id(e) not in p.swing and ov(hb, e.rect()):
                p.swing.add(id(e))
                s.hurt_enemy(e, f if p.atkdir == 'side' else (1 if e.x > p.x else -1), dmg, pierce=p.atkdir == 'down')
                if fin:
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
        was_parry = p.parry > 0
        for a in ('inv', 'acd', 'atk', 'dcd', 'landT', 'cwin', 'skidT', 'turnT', 'startT', 'parry', 'pcd', 'skcd', 'shield'):
            setattr(p, a, getattr(p, a) - dt)
        if was_parry and p.parry <= 0 and not getattr(s, 'parry_ok', True):   # the window closed on nothing: longer recovery
            p.pcd = max(p.pcd, .75 - getattr(s, 'parry_len', .2))
        if p.g:
            p.airdash = 1 + s.buff('sky')                              # air dashes left (SKY DANCER adds more)
            p.air_jump = False
            p.runph += abs(p.vx) * dt * .105
            stepn = int(p.runph / math.pi)
            if stepn != p.stepn and abs(p.vx) > 60 and p.slide <= 0 and p.dash <= 0:   # footsteps per surface
                kind = 'water' if p.plat.ground else {'move': 'metal', 'crumble': 'wood'}.get(p.plat.kind, 'stone')
                sfx('step_' + kind)
                if kind == 'water':
                    s.burst(p.x + p.w / 2, p.y + p.h - 1, 3, (150, 160, 220), spd=40, life=(.15, .3), size=(1, 1.5), grav=500)
            p.stepn = stepn
        if 'super' in A and s.superk >= s.super_need() and not p.slam:  # SUPER: 20 kills (10 with Storm Heart)
            s.start_super()
            return
        if 'parry' in A and p.pcd <= 0 and not p.slam and p.dash <= 0:   # PARRY window
            p.parry, p.pcd, p.atk = .2 * (1.6 if s.buff('iron') else 1) * (1 + .15 * s.upg('guard')) * s.diff()[4], .5, 0
            s.parry_len, s.parry_ok = p.parry, False
            sfx('throw')
        if p.slam:                                                   # ground slam: hover, then plunge
            p.slamT += dt
            p.vx, p.vy = 0, (-30 if p.slamT < .12 else 820)
            for e in s.en:
                if not e.dead and not e.trav and id(e) not in p.swing and ov(p.rect(), e.rect()):
                    p.swing.add(id(e))
                    s.hurt_enemy(e, 1 if e.x > p.x else -1, 2)
        else:
            if 'dash' in A and p.dcd <= 0 and (p.g or p.airdash > 0) and p.landT <= 0:
                if d:
                    p.face = d
                cd = .5 * (.6 if s.buff('ghost') else 1) * (.7 if s.skin_perk('void') else 1)
                p.dash, p.dcd, p.slide, p.crouch, p.atk, p.tdash = .18 * (1.25 if s.buff('untouch') else 1), cd, 0, False, 0, False
                if s.buff('shadow'):                                   # SHADOW STEP: each enemy passed is cut once
                    p.swing = set()
                pr_ = pg.Rect(p.x - 40, p.y - 10, p.w + 80, p.h + 20)    # PERFECT DASH: slipping out of a blow in mid-swing
                for e_ in s.en:
                    if e_.dead or e_.trav:
                        continue
                    if (e_.kind.startswith('boss') and e_.bs == 'act' and abs(e_.x + e_.w / 2 - p.x - p.w / 2) < 110) or                        (not e_.kind.startswith('boss') and e_.st == 'slash' and pr_.colliderect(pg.Rect(e_.x - e_.reach * (e_.face < 0), e_.y, e_.w + e_.reach, e_.h))):
                        s.perfect_fx(.3)
                        s.add_super(1)
                        break
                if not p.g:
                    p.airdash -= 1
                s.shake = max(s.shake, 2)
                s.puff(p.x + p.w / 2, p.y + p.h, 5, -p.face)
                sfx('dash')
            if p.dash > 0:                                             # long dash, passes through enemies
                p.dash -= dt
                p.vx, p.vy = p.face * (560 if p.tdash else 470), 0
                if p.tdash or s.buff('shadow'):                        # gold skill / SHADOW STEP: the dash itself cuts
                    for e in s.en:
                        if not e.dead and not e.trav and id(e) not in p.swing and ov(p.rect(), e.rect()):
                            p.swing.add(id(e))
                            s.hurt_enemy(e, p.face, 2 if p.tdash else s.rage_k(1), pierce=not p.tdash)
                            s.burst(e.x + e.w / 2, e.y + e.h / 2, 8, (255, 230, 120), spd=120, glowing=True, grav=0)
            elif p.landT > 0:
                p.vx = 0
            elif p.atk > 0 and p.step == 3 and p.atkdir == 'side':      # finisher lunge
                p.vx = p.face * 160 * (p.atk / p.atkT) if p.atk < p.atkT * .65 else 0
            else:
                p.crouch = False                               # (no crouching any more)
                # sharp movement: full speed at once, stop on the spot (a quick plant pose + dust sells it)
                top = 185 * (1.15 if s.buff('swift') else 1) * (1.15 if s.skin_perk('crimson') else 1) * (1.3 if s.skin_perk('azure') else 1)
                tgt = 0 if p.crouch else d * top * s.adm('a_speed')
                if p.g and d and d != p.face and abs(p.vx) > 100:    # instant turn
                    p.turnT = .06
                elif p.g and not d and abs(p.vx) > 120 and p.skidT <= 0:   # hard stop
                    p.skidT = .08
                elif p.g and d and abs(p.vx) < 20:                   # explosive start
                    p.startT = .06
                p.vx = tgt if p.g else p.vx + (tgt - p.vx) * min(1, dt * 22)
                if d:
                    p.face = d
            if 'jump' in A and p.dash <= 0 and p.landT <= 0:
                if p.g:
                    if down and not p.plat.ground:
                        p.y += 3                                       # down + jump on a rooftop: drop through
                    else:
                        p.vy, p.crouch, p.slide = -JUMP_V * s.adm('a_jump'), False, 0
                        p.jy0 = p.y
                        sfx('jump')
                        s.puff(p.x + p.w / 2, p.y + p.h, 4)
                elif s.skin_perk('azure') and not p.air_jump and not down:   # azure: second jump in the air
                    p.vy, p.air_jump = -JUMP_V * .9 * s.adm('a_jump'), True
                    p.jy0 = p.y
                    sfx('jump')
                    s.burst(p.x + p.w / 2, p.y + p.h, 8, (120, 230, 255), spd=80, glowing=True, grav=0)
                elif down:                                             # down + jump in the air: slam
                    p.slam, p.slamT, p.swing, p.atk = True, 0.0, set(), 0
                    sfx('dash')
            if not jump_held and p.vy < 0 and not p.launched:          # released early: a lower jump, never under half
                full = (JUMP_V * s.adm('a_jump')) ** 2 / (2 * GRAV)
                more = max(full * .52 - (getattr(p, 'jy0', p.y) - p.y), 120 ** 2 / (2 * GRAV))
                cut = math.sqrt(2 * GRAV * more)                       # (a tap = 50 % height, held = 100 %, in between = in between)
                if p.vy < -cut:
                    p.vy = -cut
            sk = s.skill()
            if 'skill' in A and sk and p.skcd <= 0 and p.dash <= 0 and p.parry <= 0:
                p.skcd = sk[2] * (1 - .15 * s.upg('skin'))
                if sk[1] == 'wave':                                   # crimson: blood wave flies forward
                    s.bwaves.append([p.x + p.w / 2 + p.face * 10, p.y + p.h * .45, p.face, 0.0, set()])
                    s.burst(p.x + p.w / 2 + p.face * 8, p.y + p.h * .45, 10, (255, 60, 90), spd=90, glowing=True, grav=0, dirx=p.face)
                    sfx('bwave')
                    s.shake = max(s.shake, 2)
                elif sk[1] == 'heal':                                 # jade: meditation heals 1 HP
                    if p.hp < p.maxhp:
                        p.hp += 1
                    s.burst(p.x + p.w / 2, p.y + p.h / 2, 20, (120, 255, 170), spd=70, glowing=True, grav=-60)
                    sfx('myth')
                elif sk[1] == 'tstep':                                # gold: a lightning dash that cuts through
                    if d:
                        p.face = d
                    p.dash, p.tdash, p.swing, p.atk, p.dcd = .24, True, set(), 0, max(p.dcd, .3)
                    s.burst(p.x + p.w / 2, p.y + p.h / 2, 14, (255, 230, 120), spd=140, glowing=True, grav=0, dirx=-p.face)
                    s.shake = max(s.shake, 4)
                    sfx('super')
                elif sk[1] == 'freeze':                               # void: time stops for everyone but you
                    s.freezeT = 2.5
                    s.pflash = .12
                    sfx('glint')
                else:                                                 # white: spirit shield, no damage taken
                    p.shield = 1.5
                    s.burst(p.x + p.w / 2, p.y + p.h / 2, 18, (230, 230, 255), spd=110, glowing=True, grav=0)
                    sfx('glint')
            if 'atk' in A and p.acd <= 0 and not p.slam and p.dash <= 0:
                dirn = 'up' if up else ('down' if down and not p.g else 'side')
                if dirn == 'side' and p.atkdir == 'side' and p.cwin > 0:
                    p.step = p.step % (3 if p.g else 2) + 1           # 3-hit combo on the ground, 2 in the air
                else:
                    p.step = 1
                p.atkdir = dirn
                p.atkT = (.26 if (p.step == 3 and dirn == 'side') else .18) * max(.6, .8 ** s.buff('quick'))
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
        nh = 16 if p.crouch else 28
        if nh != p.h:
            p.y += p.h - nh
            p.h = nh
        fly, noclip = s.adm('a_fly'), s.adm('a_noclip')
        if fly or noclip:                                          # admin: fly with up/down (and jump), noclip through everything
            p.slam = False
            p.vy = -230 if (up or jump_held) else (230 if down else 0)
            if not p.g or p.vy:
                p.vx = d * 185 * s.adm('a_speed')
        if noclip:
            p.x += p.vx * dt
            p.y = min(GY - p.h, p.y + p.vy * dt)
            p.g = p.y >= GY - p.h - .5
            p.plat = s.plats[0] if p.g else None
        else:
            p.phys(dt, s.plats, 900 if p.slam else 600)
        if p.vy >= 0:
            p.launched = False
        if p.slam and p.g:
            s.slam_impact()
        elif p.g and not p.was_g:
            s.puff(p.x + p.w / 2, p.y + p.h, 4)
            sfx('land')
        p.was_g = p.g
        busy = d or A or not p.g or abs(p.vx) > 5 or p.atk > 0 or p.crouch or p.parry > 0
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
        if s.arena:                                                    # boss arena: walls, and the way out once it's dead
            hi = ARENA_W - (0 if s.arena_open else 14) - p.w
            p.x = max(14, min(hi, p.x))
            if s.arena_open and p.x + p.w >= ARENA_W - 2:
                s.finish_level()
                return
        elif p.x + p.w / 2 > END_X - 30 and s.hole:                    # the red gate is sealed: the way on is down
            p.x, p.vx = END_X - 30 - p.w / 2, min(p.vx, 0)
            s.boss_msg = ('THE GATE IS SEALED', .4)
        if p.x + p.w / 2 > END_X:                                      # through the torii: district cleared
            if s.boss_alive():                                          # not before the boss is down
                p.x, p.vx = END_X - p.w / 2, min(p.vx, 0)
                s.boss_msg = ('DEFEAT THE BOSS', .4)
            elif s.exit_kills() < s.exit_need:
                p.x, p.vx = END_X - p.w / 2, min(p.vx, 0)
                s.boss_msg = (s.exit_msg(), .4)
            else:
                s.finish_level()
            return
        if s.kiosk and not s.kiosk['used'] and not s.kiosk.get('closed') and abs(p.x + p.w / 2 - s.kiosk['x']) < 28 and p.g and 'use' in A:
            if not s.kiosk['cards']:                                   # 3 cards (4 with EXTRA CARD), see roll_kiosk
                s.kiosk['cards'] = s.roll_kiosk()
            sfx('kiosk')
            s.go('kiosk', 0)
        if s.door.get('exit') and s.door['k'] <= 0 and abs(p.x + p.w / 2 - s.door['x']) < 34 and 'use' in A:
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
        if p.dead or s.enterT > 0 or s.cloaked(e):                 # (SHADOW CLOAK: nobody sees you)
            return
        sight = {'sleep': 0, 'meditate': 90, 'talk': 110, 'phone': 105, 'tea': 120, 'smoke': 130}.get(e.act, 180)
        sight *= 1 + .04 * min(10, max(0, s.lvl - 1))                # deeper districts: sharper eyes
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


    # ---------- bosses (every fifth district): one of three, picked at random, fought in the arena under the street
    def make_boss(s, kind):
        e = Enemy(BOSS_X, s.plats[0], kind)
        e.st, e.face, e.trav = 'boss', -1, None
        if kind in BOSS_CHAINS:                                        # scarves, capes, long hair, the kitsune's tail
            e.chains = {k: [[e.x, e.y] for _ in range(n)] for k, n in BOSS_CHAINS[kind].items()}
        e.bs, e.bt, e.batk, e.bphase, e.bcd = 'enter', 0.0, None, 1, 0.0
        e.bvy, e.bvx, e.bhit, e.bvanish, e.bdone, e.bidx = 0.0, 0.0, 0.0, False, False, -1
        e.hp = e.maxhp = max(1, int(round(e.maxhp * LOC_HP[getattr(s, 'loc', 0)] * s.diff()[2])))   # later locations / difficulty
        if getattr(s, 'endless', False):                               # endless run: bosses keep growing past district 15
            e.hp = e.maxhp = int(round(e.maxhp * (1 + .08 * max(0, s.lvl - 15))))
        e.y = -e.h - 60                                                # waits above the arena, then drops in
        e.squash, e.history, e.combo, e.hpshow, e.dest = 0.0, [], 0, float(e.hp), 0.0
        e.wallT, e.bstag = 0.0, 0.0
        if kind == 'boss_sensei':                                      # he watches from his high chair in the dark
            e.bs, e.x, e.y = 'chair', ARENA_W / 2 - e.w / 2, GY - CHAIR_H - e.h
            s.sensei = {'t': 0.0, 'claps': 0, 'lit': 0.0, 'wave': 0, 'wt': 0.0, 'clapT': -9.0,
                        'bg': [[x, k, True] for x, k in ((40, 'ronin'), (78, 'ninja'), (116, 'ronin'), (154, 'kunoichi'),
                                                         (478, 'ronin'), (514, 'kunoichi'), (550, 'ninja'), (586, 'ronin'),
                                                         (622, 'ronin'))]}
        return e

    def tick_tokens(s, dt):
        s.tok_cool = max(0.0, getattr(s, 'tok_cool', 0.0) - dt)

    def boss_alive(s):
        return s.boss is not None and not s.boss.dead

    def boss_box(s, e, reach, y0, y1):
        x0 = e.x + e.w / 2 if e.face > 0 else e.x + e.w / 2 - reach
        return (x0, y0, reach, y1 - y0)

    def boss_hit(s, e, box, dmg):
        """Each strike hits the samurai once, if its box touches him. A red (parryable) strike met with a parry is
        deflected: steel rings, the super charges, the boss is thrown off balance."""
        p = s.pl
        if not e.bdone and not p.dead and ov(box, (p.x, p.y, p.w, p.h)):
            e.bdone = True
            if p.parry > 0 and e.batk in BOSS_PARRYABLE:
                s.parry_fx(p.x + p.w / 2 + p.face * 8, p.y + 10)
                s.runst['parries'] += 1
                s.add_super(1.5)
                p.vx = e.face * 140
                p.pcd = min(p.pcd, .12)                                # a good parry is ready again at once
                e.bstag = .6                                           # a longer recovery: your opening
                if e.y >= GY - e.h - 1 and e.batk not in ('counter',):  # (on the ground: the rest of the combo is broken)
                    e.bs, e.bt, e.bvx = 'rec', 0.0, 0.0
                s.hitstop = max(s.hitstop, .08)
                return
            s.hurt_player(e.face, dmg)

    def boss_land(s, e, waves=True):
        s.shake = max(s.shake, 9)
        s.rumble(.7, .4, 220)
        s.puff(e.x + e.w / 2, GY, 10)
        e.squash = .3                                                  # squash on impact, then stretch back
        sfx('slam')
        if waves:
            for d in (-1, 1):                                          # a shockwave along the ground both ways
                s.bossw.append([e.x + e.w / 2, GY, d, 0.0, False, 250, (255, 80, 100)])

    def boss_start(s, e):
        """What happens the moment a wind-up ends."""
        p = s.pl
        k = e.batk
        if k == 'stomp':                                               # leaps up and crashes down where you stand
            e.bvy = -500
            e.bvx = max(-270, min(270, (p.x + p.w / 2 - e.x - e.w / 2) / 1.05))
        elif k == 'leap':
            e.bvy, e.bvx = -520, e.face * 260                          # leap at the samurai
        elif k == 'cleave':
            e.bidx = -1
        elif k == 'charge':                                            # shoulder first across the arena
            e.bvx = e.face * 390
            s.shake = max(s.shake, 4)
            sfx('dash')
        elif k == 'crossdash':                                         # dashes to the far side, leaving a cut in the air
            e.dest = BOSS_LEFT + 10 if e.x + e.w / 2 > ARENA_W / 2 else BOSS_RIGHT - e.w - 10
            e.bvx = (1 if e.dest > e.x else -1) * 640
            e.face = 1 if e.bvx > 0 else -1
            e.bidx = e.x + e.w / 2
            sfx('dash')
        elif k == 'blades':                                            # blades fall from the ceiling on marked spots
            n = 4 if e.bphase == 1 else 6
            xs = [p.x + p.w / 2] + [R(BOSS_LEFT + 20, BOSS_RIGHT - 20) for _ in range(n - 1)]
            for i, x in enumerate(xs):
                s.blades.append([x, -30.0, 0.0, .55 + i * .12, False, BOSS_BLADE.get(e.kind, 'blade')])
            sfx('glint')
        elif k == 'quake':                                             # fists into the ground: shockwaves + falling rubble
            s.boss_land(e)
            for i in range(3 if e.bphase == 1 else 5):
                s.blades.append([R(BOSS_LEFT + 20, BOSS_RIGHT - 20), -30.0, 0.0, .5 + i * .15, False, 'rock'])
            s.shake = 12
        elif k == 'barrage':
            sx, sy = e.x + e.w / 2 + e.face * 12, e.y + e.h * .42
            tx, ty = p.x + p.w / 2, p.y + p.h * .5
            base = math.atan2(ty - sy, tx - sx)
            n = 3 if e.bphase == 1 else 5
            for i in range(n):                                         # a volley of shells aimed at the samurai
                a = base + (i - (n - 1) / 2) * .2
                s.proj.append([sx, sy, math.cos(a) * 230, math.sin(a) * 230, False, 3.0])
            sfx('bwave')
        elif k == 'beam':
            sfx('bwave')
        elif k == 'pulse':
            s.boss_land(e)                                             # the ground splits: jump over the shockwaves
        elif k == 'rift':
            for i in range(2 if e.bphase == 1 else 3):                 # rifts that drift toward the samurai
                s.orbs.append([e.x + e.w / 2, e.y + e.h * .35 - i * 24, 0.0, False])
            sfx('bwave')
        elif k == 'acid':
            sx, sy = e.x + e.w / 2, e.y + e.h * .4
            for i in range(3):                                         # three acid blobs lobbed in an arc
                s.acid.append([sx, sy, e.face * (150 + 50 * i), -(360 + 60 * i), 0.0, False])
            sfx('bwave')
        elif k == 'claw':
            e.bidx = -1
        elif k == 'blink':
            e.dest = 0.0
            sfx('glint')
        elif k == 'iai':                                               # the draw-cut: a flash across the floor
            e.dest = min(BOSS_RIGHT - e.w, max(BOSS_LEFT, e.x + e.face * 230))
            e.bvx = (1 if e.dest > e.x else -1) * 640
            e.bidx = e.x + e.w / 2
            sfx('unsheathe')
            sfx('dash')
        elif k == 'waves':                                             # three crescent waves along the floor (both ways later)
            for i in range(3):
                for d in ((e.face,) if e.bphase == 1 else (e.face, -e.face)):
                    s.bossw.append([e.x + e.w / 2 + d * 90, GY, d, -i * .45, False, 230,
                                    (255, 210, 90) if e.kind == 'boss_shogun' else s.BOSS_AURA.get(e.kind, (255, 210, 90))])
            s.shake = max(s.shake, 6)
            sfx('slam')
        elif k == 'counter':                                           # the stance: strike him now and he answers
            sfx('glint')
        elif k in ('whirl', 'combo', 'sweep'):
            e.bidx = -1
            sfx('unsheathe' if k == 'whirl' else 'eslash')
        elif k == 'roots':                                             # roots / ice burst out of the floor on marked spots
            n = 3 if e.bphase == 1 else 5
            xs = [p.x + p.w / 2] + [R(BOSS_LEFT + 30, BOSS_RIGHT - 30) for _ in range(n - 1)]
            for i, x in enumerate(xs):
                s.spikes.append([x, .55 + i * .14, 0.0, False])
            sfx('crack')
        elif k == 'gust':                                              # the fan: gusts of wind, low and high (parry them back)
            sx = e.x + e.w / 2 + e.face * 20
            hs = (GY - 12, GY - 44, GY - 12) if e.bphase == 1 else (GY - 12, GY - 44, GY - 12, GY - 44)
            for i, hy in enumerate(hs):
                s.proj.append([sx - e.face * i * 40, hy, e.face * 250, 0.0, False, 3.0])
            sfx('bwave')
        elif k == 'warp':                                              # a teleport with no strike: somewhere else entirely
            spots = [p.x + p.w / 2 + d * R(110, 170) for d in (-1, 1)] + [q.x + q.w / 2 for q in s.plats[1:]]
            spots = [x for x in spots if BOSS_LEFT + 50 < x < BOSS_RIGHT - 50] or [ARENA_W / 2]
            e.dest = random.choice(spots)
            sfx('glint')
        elif k in ('hop', 'pounce', 'vault'):                          # a jump: over you (hop / vault) or flat at you (pounce)
            tx = p.x + p.w / 2 + (e.face * 70 if k != 'pounce' else 0)
            e.bvy = {'hop': -430, 'pounce': -240, 'vault': -470}[k]
            air = 2 * -e.bvy / GRAV
            e.bvx = max(-560, min(560, (tx - e.x - e.w / 2) / max(.2, air)))
            sfx('jump')
        elif k == 'ricochet':                                          # springs to the nearer wall, then off it at you
            d = -1 if e.x + e.w / 2 < ARENA_W / 2 else 1
            e.bvx, e.bvy, e.bidx, e.face = d * 480, -300, 0, d
            sfx('jump')
        elif k == 'rush':                                              # rage: a charge that ends in a cut where you stood
            e.bvx, e.dest = e.face * 470, p.x + p.w / 2
            sfx('dash')
        elif k in ('thrust', 'twin'):
            e.bidx = -1
            sfx('eslash')
        elif k == 'gale':
            sfx('bwave')
        elif k == 'risecut':                                           # a rising cut that leaves the ground
            e.bvy, e.bvx = -470, e.face * 120
            sfx('eslash')
        elif k == 'airdash':                                           # up, then a dash down at you from the air
            e.bvy, e.bvx, e.bidx = -400, 0.0, 0
            sfx('jump')
        elif k == 'slide':                                             # low along the floor: jump it
            e.bvx = e.face * 420
            sfx('dash')
        elif k == 'dashcut':                                           # the samurai's own dash, blade out, through you
            e.dest = min(BOSS_RIGHT - e.w, max(BOSS_LEFT, p.x + p.w / 2 + e.face * 70 - e.w / 2))
            e.bvx = (1 if e.dest > e.x else -1) * 520
            e.face = 1 if e.bvx > 0 else -1
            sfx('dash')
        elif k == 'riposte':
            e.bdone = False
            sfx('eslash')
        elif k == 'summon':                                            # his shadows drop from the ceiling
            if sum(1 for o in s.en if not o.kind.startswith('boss') and not o.dead) < 2:
                for x in (BOSS_LEFT + 40, BOSS_RIGHT - 60):
                    o = s.scale_enemy(Enemy(x, s.plats[0], BOSS_MINION.get(e.kind, 'ninja')))
                    o.y, o.vy, o.g, o.st, o.alert = -40.0, 0.0, False, 'chase', .6
                    s.en.append(o)
                    s.puff(x, 30, 8, col=(110, 90, 140))
            sfx('throw')

    def boss_clamp(s, e):
        e.x = min(BOSS_RIGHT - e.w, max(BOSS_LEFT, e.x))

    def upd_boss(s, e, dt):
        p = s.pl
        e.bhit = max(0.0, e.bhit - dt)
        e.squash = max(0.0, e.squash - dt)
        e.hpshow += (e.hp - e.hpshow) * min(1, dt * 2.5)               # the white "damage taken" trail on the bar
        e.bt += dt
        dx = (p.x + p.w / 2) - (e.x + e.w / 2)
        dist = abs(dx)
        if e.bs == 'chair':                                            # the Sensei: claps, the lights come on, waves of pupils
            ss = s.sensei
            e.face = 1 if dx > 0 else -1
            if s.arena_t < .8:
                return
            ss['t'] += dt
            T = ss['t']
            if not ss['claps'] and T > .7:                        # he lifts his hand...
                ss['claps'] = 1
                e.handT = s.t
            if ss['claps'] == 1 and T > 1.25:                     # ...and snaps his fingers: it starts
                ss['claps'] = 2
                e.clapT = ss['clapT'] = s.t
                sfx('snap')
                s.burst(e.x + e.w / 2 + e.face * 8, e.y + 4, 5, (255, 240, 200), spd=40, glowing=True, grav=0)
            if T > 1.5:
                ss['lit'] = min(1.0, ss['lit'] + dt * 2.5)
                if ss['lit'] < .1:
                    sfx('glint')
            alive = sum(1 for o in s.en if o is not e and not o.dead)
            if T > 3.0 and alive == 0 and T - ss['wt'] > 1.0:
                if ss['wave'] < len(SENSEI_WAVES):
                    for kind, side in SENSEI_WAVES[ss['wave']]:
                        x = p.x + p.w / 2 + side * 110                 # they blink in at your sides, in front of the crowd
                        if not BOSS_LEFT + 60 < x < BOSS_RIGHT - 90:   # (no room on that side: the other side, further)
                            x = p.x + p.w / 2 - side * 150
                        x = min(BOSS_RIGHT - 90, max(BOSS_LEFT + 60, x))
                        o = s.scale_enemy(Enemy(x, s.plats[0], kind))
                        o.st, o.alert, o.face = 'chase', .5, -side
                        o.locked = True                                # the Sensei's pupils only have eyes for you
                        o.warpin = .45                                 # they blink in: a streak of light, then the body
                        s.en.append(o)
                        s.burst(x + o.w / 2, GY - o.h / 2, 14, (255, 240, 220), spd=110, glowing=True, grav=0)
                        for f_ in ss['bg']:                            # one of the pupils at the back vanishes from his place
                            if f_[2] and (f_[0] < ARENA_W / 2) == (side < 0):
                                f_[2] = False
                                s.puff(f_[0], GY - 14, 8, col=(60, 50, 70))
                                break
                    sfx('dash')
                    ss['wave'] += 1
                    s.boss_msg = (f"{tr('WAVE')} {ss['wave']}", 1.2)
                    sfx('unsheathe')
                else:                                                  # enough: he steps down from his chair
                    e.bs, e.bt, e.bvy = 'descend', 0.0, -260.0
                    sfx('jump')
                ss['wt'] = T
            return
        if e.bs == 'descend':
            e.bvy += GRAV * dt
            e.y += e.bvy * dt
            e.x += (1 if dx > 0 else -1) * 40 * dt
            if e.bvy > 0 and e.y >= GY - e.h:
                e.y, e.bvy = GY - e.h, 0.0
                s.boss_land(e, waves=False)
                e.bs, e.bt = 'intro', 0.0
                s.boss_card = s.t
            return
        if e.bs == 'enter':                                            # drops from the ceiling once you have landed
            if s.arena_t < .8:
                return
            e.bvy += GRAV * 1.3 * dt
            e.y += e.bvy * dt
            if e.y >= GY - e.h:
                e.y, e.bvy = GY - e.h, 0.0
                s.boss_land(e, waves=False)
                s.punch, s.tilt = 1.0, -3 * e.face
                e.bs, e.bt = 'intro', 0.0
                s.boss_card = s.t
            return
        if e.bs in ('intro', 'roar'):                                  # the roar: title card / rage, can't be hurt
            e.face = 1 if dx > 0 else -1
            if e.bt - dt < .35 <= e.bt:
                sfx('charge')
                s.shake = 10
                s.rumble(.9, .9, 500)
                s.fx.append(['wave', e.x + e.w / 2, e.y + e.h * .3, 1, .6, .6, 0])
            if e.bt > (2.2 if e.bs == 'intro' else 1.3):
                e.bs, e.bt = 'pick', 0.0
            return
        if e.bs == 'dying':                                            # slow collapse, flashes, then it bursts
            if random.random() < .5:
                s.burst(e.x + R(0, e.w), e.y + R(0, e.h), 2, (255, 230, 200), spd=120, glowing=True, grav=-80)
            if e.bt - dt < 1.5 <= e.bt:
                s.boss_death(e)
            return
        if p.dead:
            e.bs, e.bt = 'idle', 0.0
            return
        if e.bs == 'idle':
            return
        if e.bs in ('pick', 'walk', 'rec') and not (e.bs == 'rec' and e.batk == 'charge'):
            e.face = 1 if dx > 0 else -1
        fast = 1.25 if e.bphase >= 2 else 1.0
        tempo = BOSS_TEMPO.get(e.kind, 1.0) / s.diff()[3]               # (novice: they attack slower)
        gap = min(e.x - BOSS_LEFT, BOSS_RIGHT - e.x - e.w)             # how close to a wall (no camping there)
        e.wallT = e.wallT + dt if gap < 50 else 0.0
        if e.bs == 'pick':
            moves = [(n, w) for n, w, ph in BOSS_ATTACKS[e.kind] if ph <= e.bphase]
            near = {'cleave', 'claw', 'blink', 'counter', 'combo', 'sweep', 'whirl', 'thrust', 'twin', 'slide'}
            names = [n for n, _ in moves]
            if len(moves) > 1 and e.history:                           # never the same attack twice in a row
                moves = [(n, w) for n, w in moves if n != e.history[-1]]
                names = [n for n, _ in moves]
            weights = [w * (.3 if (n in near) == (dist > 170) else 1.0) for n, w in moves]   # fits the distance
            e.batk = random.choices(names, weights)[0]
            mob = [n for n in names if n in BOSS_MOBILE]
            if e.wallT > .7 and mob:                                   # cornered: get away from the wall
                e.batk, e.wallT = random.choice(mob), 0.0
            e.history = (e.history + [e.batk])[-3:]
            e.bs, e.bt, e.bdone, e.combo = 'walk', 0.0, False, 0
        elif e.bs == 'walk':
            k = e.batk
            if e.kind in BOSS_KITE and k != 'blink':                   # keeps its distance, backs off when close
                step = -1 if dist < 140 else (1 if dist > 230 else 0)
                if step == -1 and gap < 70:                            # (never backs into a wall: casts instead)
                    step = 0
                ready = (step == 0 and e.bt > .35) or e.bt > .6
            elif k in ('cleave', 'claw', 'counter', 'combo', 'sweep', 'whirl', 'thrust', 'twin'):   # melee: closes in first
                close = (80 if e.h > 60 else 30) * (1.8 if k == 'whirl' else 1)
                step = 1 if dist > close else 0
                ready = step == 0 or e.bt > 1.8
            else:                                                      # ranged / leaps: a short pause, then go
                step = 0
                ready = e.bt > .3 / fast
            if step:
                e.x += e.face * step * BOSS_SPEED[e.kind] * fast * dt
                e.anim += dt * 7
                s.boss_clamp(e)
                if e.kind not in BOSS_KITE and e.h > 60 and int(e.anim / math.pi) != int((e.anim - dt * 7) / math.pi):
                    s.shake = max(s.shake, 2)                          # heavy footsteps
                    sfx('step_stone')
            if ready:
                e.bs, e.bt, e.bdone = 'tele', 0.0, False
                sfx('glint' if k in BOSS_PARRYABLE else 'charge')      # red = parry it, yellow = dodge it
        elif e.bs == 'tele':
            slow = 1.35 if (e.kind == 'boss_sensei' and e.batk == 'combo') else 1   # (the Sensei's red chain: a longer tell)
            if e.bt >= BOSS_TIMING[e.batk][0] * (.75 if e.bphase >= 2 else 1) * (.55 if e.combo else 1) * max(.75 / s.diff()[3], tempo) * slow:
                e.bs, e.bt, e.bdone = 'act', 0.0, False
                s.boss_start(e)
        elif e.bs == 'act':
            k = e.batk
            if k == 'cleave':                                          # huge overhead cut + a crack along the floor
                if e.bt - dt < .1 <= e.bt:
                    s.shake = max(s.shake, 7)
                    s.puff(e.x + e.w / 2 + e.face * 70, GY, 8)
                    s.bossw.append([e.x + e.w / 2 + e.face * 60, GY, e.face, 0.0, False, 210, (120, 240, 255)])
                    sfx('slam')
                if .06 < e.bt < .26:
                    s.boss_hit(e, s.boss_box(e, 110, e.y, e.y + e.h), 2)
            elif k == 'claw':                                          # three quick swipes, each a new hit
                idx = int(e.bt / .2)
                if idx != e.bidx:
                    e.bidx, e.bdone = idx, False
                    sfx('eslash')
                    s.claws.append([e.x + e.w / 2 + e.face * 46, e.y + e.h * .55, e.face, idx % 2, .22])
                e.x += e.face * 70 * dt                                 # a step into every rake
                s.boss_clamp(e)
                if e.bt % .2 < .14:
                    s.boss_hit(e, s.boss_box(e, 84, e.y + e.h * .25, e.y + e.h), 2)
            elif k == 'charge':                                        # runs until it hits the wall
                e.x += e.bvx * fast * dt
                s.boss_hit(e, (e.x, e.y + e.h * .3, e.w, e.h * .7), 2)
                if random.random() < .5:
                    s.puff(e.x + e.w / 2 - e.face * 16, GY, 1, -e.face)
                if e.x <= BOSS_LEFT or e.x + e.w >= BOSS_RIGHT:
                    s.boss_clamp(e)
                    s.shake, e.squash = 12, .3
                    s.rumble(1, .6, 300)
                    s.puff(e.x + e.w / 2 + e.face * e.w / 2, GY - 40, 14)
                    for _ in range(3):                                 # dust and stones shaken loose
                        s.blades.append([R(BOSS_LEFT + 20, BOSS_RIGHT - 20), -30.0, 0.0, .3 + R(0, .4), False, 'rock'])
                    sfx('slam')
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'crossdash':                                     # through the arena; the cut lands a moment later
                e.x += e.bvx * dt
                if (e.bvx > 0 and e.x >= e.dest) or (e.bvx < 0 and e.x <= e.dest):
                    e.x = e.dest
                    x0, x1 = sorted((e.bidx, e.x + e.w / 2))
                    s.lines.append([x0, x1, GY - 34, .5, False])
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'blink':                                         # vanishes, then reappears behind the samurai
                if e.bt < .45:
                    e.bvanish = True
                elif e.bt < .78:                                       # a ring flashes where he will appear: dodge now
                    if e.dest <= 0 or e.bt - dt < .45:
                        e.dest = min(BOSS_RIGHT - e.w / 2, max(BOSS_LEFT + e.w / 2, p.x + p.w / 2 - 34 * p.face))
                elif e.bvanish:
                    e.bvanish, e.bdone = False, False
                    e.x = e.dest - e.w / 2
                    e.dest = 0.0
                    s.boss_clamp(e)
                    e.face = 1 if p.x > e.x else -1
                    s.puff(e.x + e.w / 2, GY - 10, 8, col=(255, 90, 230))
                elif e.bt < 1.02:
                    s.boss_hit(e, s.boss_box(e, 58 if e.h > 60 else 36, e.y + e.h * .25, e.y + e.h), 2)
            elif k == 'iai':                                           # the blade is live the whole way across
                e.x += e.bvx * dt
                s.boss_hit(e, (e.x - 10, e.y + e.h * .3, e.w + 20, e.h * .7), 2)
                if random.random() < .7:
                    s.burst(e.x + e.w / 2, e.y + e.h * .55, 2, (255, 230, 160), spd=40, glowing=True, grav=0)
                if (e.bvx > 0 and e.x >= e.dest) or (e.bvx < 0 and e.x <= e.dest):
                    e.x = e.dest
                    s.shake = max(s.shake, 5)
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'riposte':                                       # the answer to a careless swing
                if .03 < e.bt < .2:
                    s.boss_hit(e, s.boss_box(e, 120 if e.h > 60 else 56, e.y, e.y + e.h), 2)
            elif k == 'whirl':                                         # the polearm spins: he advances, cutting both sides
                e.x += e.face * 150 * fast * dt
                s.boss_clamp(e)
                idx = int(e.bt / .25)
                if idx != e.bidx:
                    e.bidx, e.bdone = idx, False
                    sfx('eslash')
                r_ = 40 + e.w
                if idx % 2 == 0:                                       # every other turn cuts: gaps to slip through
                    s.boss_hit(e, (e.x + e.w / 2 - r_, e.y + e.h * .3, r_ * 2, e.h * .7), 2)
            elif k == 'combo':                                         # a chain of cuts, a step into each
                cn, ct = BOSS_COMBO.get(e.kind, (3, .33))
                if e.bt >= cn * ct:
                    e.bs, e.bt = 'rec', 0.0
                    return
                idx = min(cn - 1, int(e.bt / ct))
                if idx != e.bidx:
                    e.bidx, e.bdone = idx, False
                    e.face = 1 if dx > 0 else -1
                    sfx('eslash')
                e.x += e.face * (90 if e.h < 60 else 60) * dt
                s.boss_clamp(e)
                u = (e.bt % ct) / ct
                if .15 < u < .55:
                    s.boss_hit(e, s.boss_box(e, 26 + e.w * 1.6, e.y, e.y + e.h), 1 if e.h < 60 else 2)
            elif k == 'sweep':                                         # a low sweep of the staff: jump over it
                if .1 < e.bt < .3:
                    s.boss_hit(e, s.boss_box(e, 30 + e.w * 2.6, GY - 18, GY), 2)
            elif k == 'warp':
                if e.bt < .3:
                    e.bvanish = True
                elif e.bvanish:
                    e.bvanish = False
                    e.x, e.y = e.dest - e.w / 2, GY - e.h
                    s.boss_clamp(e)
                    e.face = 1 if p.x > e.x else -1
                    s.puff(e.x + e.w / 2, GY - 10, 8, col=s.BOSS_AURA[e.kind])
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k in ('hop', 'pounce', 'vault', 'risecut'):
                e.x += e.bvx * dt
                s.boss_clamp(e)
                e.bvy += GRAV * dt
                e.y += e.bvy * dt
                if k == 'pounce' or (k == 'risecut' and e.bvy < 120):
                    s.boss_hit(e, (e.x - 6, e.y, e.w + 12, e.h), 2)
                if e.bvy > 0 and e.y >= GY - e.h:
                    e.y, e.bvy, e.bvx = GY - e.h, 0.0, 0.0
                    s.puff(e.x + e.w / 2, GY, 5)
                    sfx('land')
                    if k == 'vault':                                   # lands behind you and cuts at once
                        e.face = 1 if dx > 0 else -1
                        e.batk, e.bs, e.bt, e.bdone, e.bidx = 'cleave', 'act', 0.0, False, -1
                    else:
                        e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'ricochet':
                e.x += e.bvx * dt
                e.bvy += GRAV * dt
                e.y += e.bvy * dt
                if e.bidx == 0 and (e.x <= BOSS_LEFT or e.x + e.w >= BOSS_RIGHT):
                    s.boss_clamp(e)
                    e.bidx, e.bdone = 1, False
                    e.bvx = max(-560, min(560, (p.x + p.w / 2 - e.x - e.w / 2) * 1.7))
                    e.bvy, e.face = -280, (1 if e.bvx > 0 else -1)
                    s.shake = max(s.shake, 5)
                    sfx('land')
                if e.bidx == 1:
                    s.boss_hit(e, (e.x - 6, e.y, e.w + 12, e.h), 2)
                s.boss_clamp(e)
                if (e.bvy > 0 and e.y >= GY - e.h) or e.bt > 2.5:
                    e.y, e.bvy, e.bvx = GY - e.h, 0.0, 0.0
                    s.boss_land(e, waves=False)
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'rush':
                e.x += e.bvx * dt
                s.boss_clamp(e)
                s.boss_hit(e, (e.x, e.y + e.h * .3, e.w, e.h * .7), 2)
                if random.random() < .5:
                    s.puff(e.x + e.w / 2 - e.face * 16, GY, 1, -e.face)
                if ((e.bvx > 0 and e.x + e.w / 2 >= e.dest - 30) or (e.bvx < 0 and e.x + e.w / 2 <= e.dest + 30) or e.bt > .9
                        or e.x <= BOSS_LEFT or e.x + e.w >= BOSS_RIGHT):
                    e.batk, e.bs, e.bt, e.bdone, e.bidx = 'cleave', 'act', 0.0, False, -1
                    return
            elif k == 'thrust':                                        # a long poke at chest height: parry it
                if e.bt < .2:
                    e.x += e.face * 150 * dt
                    s.boss_clamp(e)
                if .12 < e.bt < .32:
                    s.boss_hit(e, s.boss_box(e, 60 + e.w * 1.8, e.y + e.h * .3, e.y + e.h * .65), 2)
            elif k == 'twin':                                          # high, then low: duck the first, jump the second
                if .08 < e.bt < .22:
                    s.boss_hit(e, s.boss_box(e, 40 + e.w * 2, e.y, e.y + e.h * .55), 2)
                if e.bt - dt < .38 <= e.bt:
                    e.bdone = False
                    sfx('eslash')
                if .4 < e.bt < .55:
                    s.boss_hit(e, s.boss_box(e, 40 + e.w * 2.4, GY - 18, GY), 2)
            elif k == 'gale':                                          # the wind drags you in, then the fan comes down
                if e.bt < .7:
                    if not p.dead:
                        p.x += (1 if e.x > p.x else -1) * 120 * dt
                    if random.random() < .6:
                        yy = R(GY - 70, GY - 6)
                        s.parts.append([p.x + p.w / 2 - (1 if e.x > p.x else -1) * R(20, 80), yy, (1 if e.x > p.x else -1) * 260, 0,
                                        .3, .3, (220, 240, 255), 1, 0, False])
                else:
                    e.face = 1 if dx > 0 else -1
                    e.batk, e.bs, e.bt, e.bdone, e.bidx = 'cleave', 'act', 0.0, False, -1
                    return
            elif k == 'airdash':
                if e.bidx == 0:                                        # rising...
                    e.bvy += GRAV * dt
                    e.y += e.bvy * dt
                    if e.bvy >= -40:                                   # ...at the top: dash down at you
                        tx, ty = p.x + p.w / 2 - e.x - e.w / 2, p.y + p.h - e.y - e.h
                        d = max(1.0, math.hypot(tx, ty))
                        e.bvx, e.bvy, e.bidx, e.bdone = tx / d * 540, max(120, ty / d * 540), 1, False
                        e.face = 1 if e.bvx > 0 else -1
                        sfx('dash')
                else:
                    e.x += e.bvx * dt
                    e.y += e.bvy * dt
                    s.boss_clamp(e)
                    s.boss_hit(e, (e.x - 6, e.y, e.w + 12, e.h), 2)
                    if e.y >= GY - e.h or e.bt > 2.0:
                        e.y, e.bvy, e.bvx = GY - e.h, 0.0, 0.0
                        s.boss_land(e, waves=e.bphase >= 2)
                        e.bs, e.bt = 'rec', 0.0
                        return
            elif k == 'slide':
                e.x += e.bvx * dt
                s.boss_hit(e, (e.x - 4, GY - 14, e.w + 8, 14), 2)
                if random.random() < .6:
                    s.puff(e.x + e.w / 2, GY, 1, -e.face)
                if e.bt > .45 or e.x <= BOSS_LEFT or e.x + e.w >= BOSS_RIGHT:
                    s.boss_clamp(e)
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k == 'dashcut':                                       # through you, blade out; stops where he aimed
                e.x += e.bvx * dt
                s.boss_hit(e, (e.x - 6, e.y, e.w + 12, e.h), 2)
                if random.random() < .7:
                    s.burst(e.x + e.w / 2, e.y + e.h * .5, 2, s.BOSS_AURA[e.kind], spd=40, glowing=True, grav=0)
                if (e.bvx > 0 and e.x >= e.dest) or (e.bvx < 0 and e.x <= e.dest) or e.x <= BOSS_LEFT or e.x + e.w >= BOSS_RIGHT:
                    s.boss_clamp(e)
                    e.bs, e.bt = 'rec', 0.0
                    return
            elif k in ('stomp', 'leap'):
                e.x += e.bvx * dt
                s.boss_clamp(e)
                if k == 'leap':
                    s.boss_hit(e, (e.x, e.y, e.w, e.h), 2)
                e.bvy += GRAV * dt
                e.y += e.bvy * dt
                if e.bvy > 0 and e.y >= GY - e.h:
                    e.y, e.bvy, e.bvx = GY - e.h, 0.0, 0.0
                    s.boss_land(e, waves=k == 'stomp' or e.bphase >= 2)
                    e.bs, e.bt = 'rec', 0.0
                    return
            if k not in ('stomp', 'leap', 'charge', 'crossdash', 'iai', 'dashcut', 'combo', 'warp', 'hop', 'pounce', 'vault',
                         'risecut', 'ricochet', 'rush', 'gale', 'airdash', 'slide') and e.bt >= BOSS_TIMING[k][1]:
                if k == 'cleave' and e.bphase >= 2 and not e.combo:    # enraged: a second cleave right after
                    e.combo, e.bs, e.bt, e.bdone = 1, 'tele', 0.0, False
                    e.face = 1 if dx > 0 else -1
                else:
                    e.bs, e.bt = 'rec', 0.0
            elif k == 'charge' and e.bt > 1.6:
                e.bs, e.bt = 'rec', 0.0
        elif e.bs == 'rec':
            if e.bt >= BOSS_TIMING[e.batk][2] * (.75 if e.bphase >= 2 else 1) * tempo + e.bstag:
                e.bs, e.bt, e.bvanish, e.bstag = 'pick', 0.0, False, 0.0

    def boss_death(s, e):
        """The boss bursts into light; coins rain down; the gate at the end of the arena opens."""
        cx, cy = e.x + e.w / 2, e.y + e.h / 2
        s.kill_enemy(e, s.pl.face)
        for i in range(5):
            s.fx.append(['boom', cx + R(-30, 30), cy + R(-40, 40), 1, .5 + i * .1, .5 + i * .1, 0])
        s.burst(cx, cy, 70, (255, 230, 200), spd=260, life=(.6, 1.4), glowing=True, grav=150)
        s.burst(cx, cy, 40, (255, 70, 110), spd=200, glowing=True, grav=200)
        s.drop_loot(cx, cy, 18)
        s.shake, s.pflash, s.punch = 14, .2, 1.0
        s.rumble(1, 1, 600)
        sfx('boom')
        sfx('super')
        s.boss_msg = ('BOSS DEFEATED', 3.0)
        s.arena_open, s.arena_t = True, 0.0                            # (arena_t now times the gate opening)
        for o in s.en:                                                 # his summoned shadows go with him
            if o is not e and not o.dead:
                o.dead = True
                s.puff(o.x + o.w / 2, o.y + o.h / 2, 10, col=(110, 90, 140))
        if s.ahaz:
            s.ahaz['st'], s.ahaz['t'] = 'idle', -99.0                  # the arena calms down

    def hurt_boss(s, e, f, dmg):
        if e.dead or e.bs == 'dying':
            return
        if s.buff('invis') and not getattr(e, 'ambushed', False) and e.bs not in ('intro', 'chair', 'enter', 'descend'):
            e.ambushed = True                                          # SHADOW CLOAK: a strike out of the shadows
            e.hp = max(1, e.hp - e.maxhp * .1)
            s.boss_msg = ('SHADOW STRIKE', 1.4)
            s.hitstop, s.shake, s.pflash = .12, 6, .15
            s.burst(e.x + e.w / 2, e.y + e.h * .4, 30, (150, 160, 255), spd=170, glowing=True, grav=0)
            s.puff(e.x + e.w / 2, e.y + e.h * .5, 10, col=(60, 40, 100))
            sfx('glint')
        pc = BOSS_PARRIES.get(e.kind)
        pl = s.pl
        if (pc and e.bs in ('pick', 'walk') and s.t - getattr(e, 'parT', -9) > 2.5 and e.bstag <= 0
                and not (pl.slam or pl.dash > 0 or s.superT >= 0)
                and random.random() < pc[min(1, e.bphase - 1)]
                and (1 if pl.x > e.x else -1) == e.face):              # the Sensei reads a cut from the front: parried, he answers
            e.parT = s.t                                               # (never in his recovery, never twice in 2.5 s,
                                                                       #  never a slam, a dash-cut or the super)
            s.parry_fx(e.x + e.w / 2 - f * 6, e.y + e.h * .4)
            s.pl.vx = -f * 150                                         # you are only pushed back: no counter-cut, no damage
            s.pl.acd = max(s.pl.acd, .3)
            e.batk, e.bs, e.bt, e.bdone = 'hop', 'rec', 0.0, True
            s.boss_msg = ('PARRIED!', .7)
            return
        if e.bs in ('enter', 'intro', 'roar', 'idle', 'chair', 'descend') or e.bvanish:   # not fighting yet: the blade bounces off
            s.fx.append(['spark', e.x + e.w / 2 - f * 3, e.y + e.h * .45, f, .14, .14, R(0, 1)])
            sfx('block')
            return
        if e.bs == 'act' and e.batk == 'counter':                      # you struck into his stance: steel rings, he answers
            s.parry_fx(e.x + e.w / 2 - f * 10, e.y + e.h * .45)
            e.face = -f                                                # parried: you are pushed back, no counter-cut, no damage
            s.pl.vx = -f * 150
            s.pl.acd = max(s.pl.acd, .3)
            e.batk, e.bs, e.bt, e.bdone = 'hop', 'rec', 0.0, True
            s.boss_msg = ('PARRIED!', .7)
            return
        e.hp -= dmg
        s.add_super(.5)                                                # every hit on a boss charges the super a little
        e.bhit = .16
        if e.bs not in ('act',):                                       # a little recoil (never cancels its attack)
            e.x += f * 3
            s.boss_clamp(e)
        s.hitstop, s.shake = .05, 4
        s.burst(e.x + e.w / 2, e.y + e.h * .45, 10, (255, 60, 90), dirx=f)
        s.fx.append(['spark', e.x + e.w / 2 - f * 3, e.y + e.h * .45, f, .14, .14, R(0, 1)])
        sfx('hit')
        if e.hp <= 0:                                                  # slow-motion collapse, then it bursts (boss_death)
            e.hp, e.bs, e.bt, e.bvanish, e.bvy, e.bvx = 0, 'dying', 0.0, False, 0.0, 0.0
            e.y = GY - e.h
            s.slowmo, s.hitstop, s.shake, s.pflash = 1.4, .25, 10, .2
            s.proj = [pr for pr in s.proj if pr[4]]
            s.orbs, s.blades, s.lines, s.bossw, s.acid, s.puddles, s.claws, s.spikes = [], [], [], [], [], [], [], []
            sfx('kill')
        else:                                                          # the next phase: a roar, then faster and new moves
            cuts = BOSS_PHASES.get(e.kind, (.5,))
            if e.bphase <= len(cuts) and e.hp <= e.maxhp * cuts[e.bphase - 1]:
                e.bphase += 1
                e.bs, e.bt, e.bvanish, e.bvy, e.bvx = 'roar', 0.0, False, 0.0, 0.0
                e.y = GY - e.h
                s.boss_msg = (('THE SHOGUN RAGES', 2.4) if e.kind == 'boss_shogun' else
                              (('NO MORE HOLDING BACK', 2.4) if e.kind in ('boss_brother', 'boss_sensei') else ('ENRAGED', 2.0)))
                if e.kind == 'boss_shogun':
                    s.puff(e.x + e.w / 2, e.y + e.h / 2, 20, col=(160, 60, 220))
                    s.pflash = .2

    BOSS_AURA = {'boss_destroyer': (255, 150, 60), 'boss_chaos': (200, 80, 255), 'boss_mutant': (130, 255, 90),
                 'boss_shogun': (255, 200, 80), 'boss_nio': (255, 150, 60), 'boss_abbot': (255, 120, 60),
                 'boss_wanderer': (110, 230, 130), 'boss_kitsune': (255, 140, 40), 'boss_mossoni': (150, 230, 90),
                 'boss_tengu': (255, 90, 70), 'boss_yukionna': (140, 220, 255), 'boss_sensei': (200, 220, 255),
                 'boss_mokujin': (255, 180, 100), 'boss_tomoe': (255, 80, 100), 'boss_brother': (230, 40, 60)}

    @staticmethod
    def boss_title(b):
        return BOSS_TITLES[b.kind]

    def draw_boss(s, e, cx, oy):
        bx = e.x + e.w / 2 - cx
        if bx < -200 or bx > W + 200:
            return
        gy = GY + oy
        air = max(0.0, (GY - (e.y + e.h)))                               # a shadow on the floor, smaller when it's high
        zs = min(1.0, e.h / 110)                                         # the small bosses (sensei, brother): smaller halo
        sw = max(10, 70 * max(.4, zs) - air * .25)
        pg.draw.ellipse(scr, (6, 2, 10), (bx - sw / 2, gy - 4, sw, 8))
        if e.bvanish:
            if e.batk == 'blink' and e.dest > 0:                           # where he will come out of the dark
                k = .5 + .5 * math.sin(s.t * 30)
                pg.draw.ellipse(scr, qcol((255, 90, 230), .6 + .4 * k), (e.dest - cx - 22, gy - 6, 44, 10), 2)
                glow(scr, e.dest - cx, gy - 20, 30, qcol((90, 20, 80), k))
            if random.random() < .4:
                s.puff(e.x + e.w / 2 + R(-20, 20), GY - R(10, 80), 1, col=(255, 90, 230))
            return
        aura = (255, 40, 30) if e.kind == 'boss_shogun' and e.bphase >= 2 else s.BOSS_AURA[e.kind]
        pulse = .45 + (.2 * math.sin(s.t * 12) if e.bphase >= 2 else 0)
        if e.bphase >= 2:                                                  # enraged: a red fire under the halo
            glow(scr, bx, e.y + e.h * .55 + oy, int(84 * max(.45, zs)), qcol((255, 40, 40), .35 + .15 * math.sin(s.t * 9)))
        glow(scr, bx, e.y + e.h * .5 + oy, int(74 * max(.45, zs)), qcol(aura, pulse))         # a coloured halo: the boss reads against the night
        tele = e.bs == 'tele'
        if tele:                                                           # Dead Cells style: the danger zone shows first
            k = min(1, e.bt / max(.01, BOSS_TIMING[e.batk][0]))
            zone = None
            if e.batk == 'cleave':
                zone = s.boss_box(e, 110, e.y, GY)
            elif e.batk == 'claw':
                zone = s.boss_box(e, 84, e.y + e.h * .25, GY)
            elif e.batk == 'charge':
                zone = (e.x + e.w, GY - 70, BOSS_RIGHT - e.x - e.w, 70) if e.face > 0 else (BOSS_LEFT, GY - 70, e.x - BOSS_LEFT, 70)
            elif e.batk == 'iai':
                d = min(BOSS_RIGHT - e.w, max(BOSS_LEFT, e.x + e.face * 230)) - e.x
                zone = (e.x + e.w, GY - 70, d, 70) if d > 0 else (e.x + d, GY - 70, -d, 70)
            elif e.batk == 'combo':
                zone = s.boss_box(e, 26 + e.w * 1.6, e.y, GY)
            elif e.batk == 'sweep':
                zone = s.boss_box(e, 30 + e.w * 2.6, GY - 18, GY)
            elif e.batk == 'whirl':
                r_ = 40 + e.w
                zone = (e.x + e.w / 2 - r_, e.y + e.h * .3, r_ * 2, GY - e.y - e.h * .3)
            if zone and zone[2] > 0:
                area = pg.Surface((int(zone[2]), int(zone[3])), pg.SRCALPHA)
                area.fill((255, 40, 70, int(40 + 50 * k)))
                scr.blit(area, (zone[0] - cx, zone[1] + oy))
                pg.draw.line(scr, (255, 90, 110), (zone[0] - cx, gy - 1), (zone[0] + zone[2] - cx, gy - 1), 2)
        if tele:                                                           # red outline = parry it, yellow = dodge it
            tc = (255, 50, 60) if e.batk in BOSS_PARRYABLE else (255, 220, 60)
            glow(scr, bx, e.y + e.h * .5 + oy, int(80 * max(.45, zs)), qcol(tc, .25 + .3 * k))
            pg.draw.rect(scr, tc, (e.x - cx - 2, e.y + oy - 2, e.w + 4, e.h + 4), 2)
            if e.batk in ('charge', 'crossdash', 'iai', 'dashcut') and int(s.t * 12) % 2:   # dashed line along the floor where it will go
                if e.batk == 'crossdash':
                    dirx = 1 if e.x + e.w / 2 <= ARENA_W / 2 else -1
                    xe = BOSS_RIGHT - 10 if dirx > 0 else BOSS_LEFT + 10
                elif e.batk == 'iai':
                    dirx = e.face
                    xe = min(BOSS_RIGHT - e.w, max(BOSS_LEFT, e.x + e.face * 230)) + (e.w if e.face > 0 else 0)
                else:
                    dirx = e.face
                    xe = BOSS_RIGHT if dirx > 0 else BOSS_LEFT
                xs_ = e.x + e.w / 2
                for dxl in range(0, int(abs(xe - xs_)) - 8, 16):
                    xa = xs_ + dirx * dxl
                    pg.draw.line(scr, tc, (xa - cx, gy - 2), (xa + dirx * 9 - cx, gy - 2), 2)
        if s.state == 'play' and s.hitstop <= 0:
            e.pose = blend(e.pose, pose_boss(e, s.t), min(1, s.dt * (22 if e.bs == 'act' else 12)))
        sq = 1 - .22 * ease(e.squash / .3)                                 # landing squash, springing back
        ghost = None
        if e.bs == 'act' and e.batk in ('charge', 'crossdash', 'leap', 'iai', 'dashcut', 'whirl') and int(s.t * 40) % 2 == 0:
            ghost = (.25, aura)
        tele_flash = tele and e.bt > BOSS_TIMING[e.batk][0] * .6 and int(s.t * 22) % 2 == 0
        flash = e.bhit > 0 or tele_flash or (e.bs == 'dying' and int(s.t * 14) % 2 == 0)
        pal = PAL_E[e.kind]
        info, sx, sy = s.draw_char(e.x + e.w / 2, e.y + e.h, e.face, e.pose, pal, e.chains, cx, oy, flash,
                                   ghost=ghost, sq=(2 - sq, sq))
        hx, hy = sx + info['hc'][0], sy + info['hc'][1]
        if e.bs == 'act' and e.batk == 'counter':                          # the stance: a cold glint - don't swing into it
            k = .5 + .5 * math.sin(s.t * 14)
            glow(scr, hx, hy + 30, 50, qcol((40, 70, 110), k))
            if info['blade']:
                four_star(scr, sx + info['blade'][0], sy + info['blade'][1], 4 + 3 * k, (200, 230, 255))
            outlined('構', F_JPB, (170, 220, 255), hx, hy - 60, center=True, r=2)
        if tele and int(s.t * 10) % 2:                                     # the warning mark, blinking
            outlined('!', F_PM, (255, 230, 80), hx, hy - max(22, 58 * zs), center=True, r=2)
        if e.bs == 'dying':                                                # light breaking out of it
            for i in range(5):
                a = s.t * 2 + i * 1.256
                ln = 40 + 30 * math.sin(s.t * 9 + i)
                pg.draw.line(scr, (255, 240, 210), (bx, e.y + e.h * .45 + oy),
                             (bx + math.cos(a) * ln, e.y + e.h * .45 + oy + math.sin(a) * ln), 2)

    def draw_boss_hud(s):
        b = s.boss
        if b is not None and not b.dead and b.bs not in ('idle', 'enter', 'chair', 'descend'):
            bw, x, y = 300, W // 2 - 150, H - 20                           # Dead Cells style: a long bar along the bottom
            outlined(s.boss_title(b), F_PS, WHITE, W // 2, y - 19, center=True, r=1)
            pg.draw.polygon(scr, INK, [(x - 6, y - 3), (x + bw + 6, y - 4), (x + bw + 2, y + 9), (x - 2, y + 10)])
            pg.draw.rect(scr, (60, 0, 12), (x, y, bw, 6))
            pg.draw.rect(scr, (255, 240, 230), (x, y, bw * max(0, b.hpshow) / b.maxhp, 6))   # recent damage, fading
            col = (200, 80, 255) if b.bphase >= 3 else ((255, 60, 40) if b.bphase >= 2 else RED)
            pg.draw.rect(scr, col, (x, y, bw * max(0, b.hp) / b.maxhp, 6))
            for cut in BOSS_PHASES.get(b.kind, (.5,)):                     # where each next phase starts
                pg.draw.line(scr, WHITE, (x + bw * cut, y - 2), (x + bw * cut, y + 7))
        if b is not None and s.t - s.boss_card < 2.8:                     # the title card when it lands
            k = s.t - s.boss_card
            a = ease(k * 4) if k < 2.3 else max(0.0, 1 - (k - 2.3) * 2)
            off = (1 - a) * -W
            pg.draw.polygon(scr, INK, [(off, 52), (W + off, 44), (W + off, 98), (off, 104)])   # above the fight, not over it
            pg.draw.polygon(scr, RED, [(off, 52), (W + off, 44), (W + off, 48), (off, 56)])
            ransom(s.boss_title(b), W // 2 + off, 54, [F_PB, F_P], 77, s.t, center=True, tilt=-3)
            outlined(BOSS_SUBS[b.kind], F_S, (255, 200, 210), W // 2 + off, 90, center=True, r=1)
        msg, left = s.boss_msg
        if left > 0 and msg:
            outlined(msg, F_PM, (255, 220, 120), W // 2, 66, center=True, r=1)

    # ---------- level design: ambush plazas and hidden chests
    def update_plazas(s):
        p = s.pl
        if s.arena or p.dead:
            return
        for z in s.plazas:                                             # step into the open square: they drop from the roofs
            if False:                                                  # (ambushes removed)
                z['done'] = True
                s.boss_msg = ('AMBUSH!', 1.6)
                s.shake = max(s.shake, 4)
                s.punch, s.tilt = .6, 1.5
                sfx('unsheathe')
                for i in range(z['n']):
                    side = -1 if i % 2 == 0 else 1
                    ex = max(z['x0'] + 8, min(z['x1'] - 24, p.x + side * R(70, 110)))
                    e = s.scale_enemy(Enemy(ex, s.plats[0], s.ambush_kind()))
                    e.y, e.vy, e.g, e.st, e.face = GY - 230 - i * 30, 0.0, False, 'chase', -side
                    e.alert = .6
                    s.en.append(e)
                    s.spawned += 1
        for c in s.chests:                                             # [x, y, opened]: a stash above the city
            if not c[2] and abs(p.x + p.w / 2 - c[0] - 7) < 14 and abs(p.y + p.h - c[1]) < 6:
                c[2] = True
                s.drop_loot(c[0] + 7, c[1] - 8, 12)
                s.coins.append([c[0] + 7, c[1] - 24, True, 0.0])
                if s.buff('invis'):                                    # SHADOW CLOAK: the stash is all mythic coins
                    for k in (-1, 1):
                        s.coins.append([c[0] + 7 + k * 12, c[1] - 20, True, 0.0])
                s.burst(c[0] + 7, c[1] - 6, 24, (255, 220, 120), spd=120, glowing=True, grav=200)
                s.boss_msg = ('TREASURE!', 1.6)
                sfx('myth')

    def ambush_kind(s):
        kind = s.roster_kind()
        return 'ninja' if kind == 'onryo' else kind                # (ghosts don't drop from the roofs)

    # ---------- each act's street hazard: they hurt enemies too, so lure them in
    TRAP_T = {'wire': (3.4, .7, 1.1, 40), 'steam': (4.2, .9, .8, 18), 'spikes': (3.0, .5, 1.0, 28)}   # cycle, warning, live, width

    def build_traps(s):
        """Live cables torn down across the street (act I), steam geysers in the dock vents (II), bamboo spike traps (III)."""
        s.traps = []
        kind = s.theme.get('hazard')
        if not kind:
            return
        per, warn, on, w = s.TRAP_T[kind]
        per *= 1 - .05 * ((s.lvl - 1) % 5)                       # faster later in the act
        n = 3 + (s.lvl - 1) % 5
        banned = [(z['x0'] - 30, z['x1'] + 30) for z in s.plazas]
        if s.kiosk:
            banned.append((s.kiosk['x'] - 70, s.kiosk['x'] + 70))
        if s.hole:
            banned.append((CAVE_X - 140, CAVE_X + 140))
        roofs = [p for p in s.static_plats() if not p.ground and p.w >= 60 and p.x > 420]
        spots = list(s.vents) if kind == 'steam' else []
        random.shuffle(spots)
        for _ in range(80):
            if len(s.traps) >= n:
                break
            plat = None
            if spots:
                x = spots.pop()
            elif kind == 'spikes' and roofs and random.random() < .4:   # spikes also wait on the temple roofs
                plat = random.choice(roofs)
                x = plat.x + R(w / 2 + 6, plat.w - w / 2 - 6)
            else:
                x = R(440, END_X - 140)
            y = plat.y if plat else GY
            if x < 420 or any(a < x < b for a, b in banned) or any(abs(t['x'] - x) < 130 and t['y'] == y for t in s.traps):
                continue
            s.traps.append({'kind': kind, 'x': x, 'y': y, 'w': w, 't': R(0, per), 'per': per, 'warn': warn, 'on': on,
                            'live': False, 'arm': False, 'hit': set()})
        s.vents = [v for v in s.vents if all(abs(v - t['x']) > 1 for t in s.traps)]   # geysers draw their own grates

    def trap_box(s, tp):
        x, y, w = tp['x'], tp['y'], tp['w']
        if tp['kind'] == 'steam':
            return (x - w / 2, y - 100, w, 100)
        return (x - w / 2, y - (14 if tp['kind'] == 'spikes' else 10), w, 14 if tp['kind'] == 'spikes' else 12)

    def update_traps(s, dt):
        p = s.pl
        for tp in s.traps:
            per, on = tp['per'], tp['on']
            tp['t'] += dt
            ph = tp['t'] % per
            live = ph >= per - on
            tp['arm'] = per - on - tp['warn'] <= ph < per - on
            seen = abs(tp['x'] - (s.cam + W / 2)) < W * .7
            if live and not tp['live']:                            # it goes off
                tp['hit'] = set()
                if seen:
                    sfx({'wire': 'bwave', 'steam': 'dash', 'spikes': 'eslash'}[tp['kind']])
            tp['live'] = live
            x, y = tp['x'], tp['y']
            if tp['arm'] and seen and random.random() < dt * 14:   # the warning: sparks / a hiss / rattling tips
                if tp['kind'] == 'wire':
                    s.burst(x + R(-tp['w'] / 2, tp['w'] / 2), y - 2, 1, (120, 230, 255), spd=60, glowing=True, grav=300)
                elif tp['kind'] == 'steam':
                    s.parts.append([x + R(-4, 4), y - 2, R(-6, 6), R(-40, -20), .5, .5, (200, 200, 210), R(2, 3), -10, 2])
            if not live:
                continue
            if seen and tp['kind'] == 'steam' and random.random() < dt * 30:
                s.parts.append([x + R(-6, 6), y - 4, R(-14, 14), R(-260, -180), .45, .45, (230, 230, 240), R(4, 7), 60, 2])
            elif seen and tp['kind'] == 'wire' and random.random() < dt * 20:
                s.burst(x + R(-tp['w'] / 2, tp['w'] / 2), y - 3, 2, (160, 240, 255), spd=90, glowing=True, grav=200)
            box = s.trap_box(tp)
            if not p.dead and 'p' not in tp['hit'] and ov(box, p.rect()):
                tp['hit'].add('p')
                s.hurt_player(1 if p.x + p.w / 2 > x else -1, 1)
                if tp['kind'] == 'steam':                          # the geyser throws you up (handy, if you time it)
                    p.vy = min(p.vy, -430)
                    p.g = False
            for e in s.en:
                if not e.dead and not e.trav and not e.kind.startswith('boss') and id(e) not in tp['hit'] and ov(box, e.rect()):
                    tp['hit'].add(id(e))
                    s.hurt_enemy(e, 1 if e.x + e.w / 2 > x else -1, 2, pierce=True)

    def draw_traps(s, cx, oy):
        for tp in s.traps:
            x, y, w = tp['x'] - cx, tp['y'] + oy, tp['w']
            if x < -60 or x > W + 60:
                continue
            k = tp['kind']
            if k == 'wire':                                        # a fallen power cable, its torn end in a puddle
                pts = [(x - w / 2 + i * w / 8, y - 2 - abs(math.sin(i * 1.3)) * 2) for i in range(9)]
                pg.draw.lines(scr, (14, 12, 18), False, pts, 2)
                pg.draw.ellipse(scr, (30, 40, 70), (x + w / 2 - 6, y - 2, 14, 4))
                if tp['live']:
                    for i in range(2):
                        zz = [(px, py + R(-3, 3) - 1) for px, py in pts]
                        pg.draw.lines(scr, (160, 240, 255) if i else (60, 140, 255), False, zz, 1)
                    glow(scr, x, y - 3, int(w * .9), (20, 60, 90))
                elif tp['arm'] and int(s.t * 16) % 2:
                    glow(scr, x + R(-w / 2, w / 2), y - 3, 8, (20, 50, 80))
            elif k == 'steam':                                     # a grate in the street, a column of scalding steam
                pg.draw.rect(scr, (24, 30, 36), (x - w / 2 - 2, y - 2, w + 4, 3))
                for gx in range(int(x - w / 2), int(x + w / 2), 4):
                    scr.fill((70, 80, 90), (gx, y - 2, 2, 1))
                if tp['arm']:
                    glow(scr, x, y - 4, 12, qcol((60, 40, 20), .5 + .5 * math.sin(s.t * 20)))
                if tp['live']:
                    for i in range(7):
                        r = 7 + i * 2
                        yy = y - 8 - i * 14 - (s.t * 90) % 14
                        img = smoke_img(r, 150 - i * 12, (220, 224, 232))
                        scr.blit(img, (x - r - 1, yy - r - 1))
                    glow(scr, x, y - 40, 30, (40, 40, 46))
            else:                                                  # bamboo spikes: tips rattle, then shoot up
                pg.draw.rect(scr, (60, 40, 24), (x - w / 2, y - 2, w, 3))
                hgt = 14 if tp['live'] else (3 if tp['arm'] else 0)
                if hgt:
                    jit = R(-1, 1) if tp['arm'] and not tp['live'] else 0
                    for i in range(5):
                        sx_ = x - w / 2 + 3 + i * (w - 6) / 4 + jit
                        pg.draw.polygon(scr, (150, 170, 90), [(sx_ - 2, y - 2), (sx_ + 2, y - 2), (sx_, y - 2 - hgt)])
                        pg.draw.line(scr, (220, 230, 180), (sx_, y - 2), (sx_, y - 2 - hgt))
                    if tp['live']:
                        glow(scr, x, y - 8, 14, (40, 10, 6))

    # ---------- the way down: a cave carved like a shinobi mask, left of the sealed gate, and the arena under the street
    def update_hole(s, dt):
        h, p = s.hole, s.pl
        if not h or s.arena:
            return
        if h.get('door'):                                              # the gate: opens when half are cut down, you walk in
            near = abs(p.x + p.w / 2 - CAVE_X) < 26 and p.g and not p.dead
            if not h['open'] and s.exit_kills() >= s.exit_need:
                h['open'] = True
                s.shake = max(s.shake, 5)
                sfx('door')
                s.boss_msg = ('HE IS WAITING FOR YOU', 2.5)
            if h['open']:
                h['k'] = min(1.0, h['k'] + dt / .8)                    # the doors swing open
                if near and h['k'] >= 1 and 'use' in s.act and not h.get('in'):
                    h['in'] = True
                    sfx('door')

                    def walk_in():
                        s.enter_arena()
                        s.pl.y, s.pl.vy, s.pl.vx = GY - s.pl.h, 0.0, 0.0   # walked in through the door, not dropped
                        s.go('play', 0)
                    s.wipe_to(walk_in)
            elif near and 'use' in s.act:
                s.boss_msg = (s.exit_msg(), 1.0)
            return
        if not h['open'] and s.exit_kills() >= s.exit_need:          # half the district cut down: the seal bursts
            h['open'] = True
            s.shake, s.pflash = max(s.shake, 12), .15
            s.rumble(1, .8, 700)
            sfx('boom')
            sfx('slam')
            for _ in range(26):                                        # the stone seal blown into pieces
                s.parts.append([CAVE_X + R(-24, 24), GY - 2, R(-160, 160), R(-320, -120), R(.6, 1.1), 1.0,
                                random.choice(((90, 92, 110), (60, 62, 80), (120, 200, 255))), R(2, 4), 900, False])
            s.puff(CAVE_X, GY, 14, col=(90, 110, 150))
            s.boss_msg = ('THE GROUND BREAKS OPEN', 2.5)
        if h['open']:
            h['k'] = min(1.0, h['k'] + dt / .5)                        # the rim rocks jut up
            if random.random() < dt * 10:                              # cold blue light and mist rising from the shaft
                s.parts.append([CAVE_X + R(-20, 20), GY + 4, R(-6, 6), R(-40, -20), 1.0, 1.0, (70, 120, 190), R(3, 5), -8, 2])
            near = abs(p.x + p.w / 2 - CAVE_X) < 24 and p.g and not p.dead
            if not h.get('in') and near and h['k'] >= 1 and 'use' in s.act:   # you choose to go in: a hop, then down
                h['in'] = True
                h['lid'].solid = False
                p.x, p.vx, p.vy = CAVE_X - p.w / 2, 0, -230
                sfx('jump')
            if h.get('in'):
                p.x, p.vx = CAVE_X - p.w / 2, 0
                if p.y > GY + 20 and not p.dead:                       # in you go
                    s.shaft_t = 0.0
                    s.go('shaft', 0)
        elif p.g and p.plat is h['lid'] and not p.dead:
            s.boss_msg = (s.exit_msg(), .4)

    def st_shaft(s, dt):
        """The fall: down a narrow rock shaft past old carvings, then out through the arena's ceiling."""
        s.shaft_t += dt
        t = s.shaft_t
        scr.fill((4, 4, 10))
        off = t * 700
        for i in range(10):                                            # far back wall: dim rock strata sliding up slowly
            y = (i * 34 - off * .35) % (H + 34) - 17
            sr = random.Random(int((i * 34 - off * .35) // (H + 34)) * 31 + i)
            pts = [(W // 2 - 120 + j * 30, y + sr.randint(-3, 3)) for j in range(9)]
            pg.draw.lines(scr, (14, 14, 26), False, pts, 2)
        for side in (-1, 1):                                           # jagged walls racing upward
            base = int(off // 40)
            edge = []
            for i in range(14):                                        # (the shape belongs to the rock, so it scrolls with it)
                seg = i + base
                sr = random.Random(seg * 13 + side * 7)
                edge.append((W // 2 + side * (70 + sr.randint(0, 34) + 12 * math.sin(seg * 1.7)), i * 40 - (off % 40) - 20))
            pts = [(W // 2 + side * 240, -40)] + edge + [(W // 2 + side * 240, H + 40)]
            pg.draw.polygon(scr, (26, 28, 44), pts)
            for i, (ex, ey) in enumerate(edge):                         # the rock's face: stones, cracks, ledges, crystals
                seg = i + base
                sr = random.Random(seg * 101 + side * 17)
                inx = lambda d: ex + side * d                           # d pixels deeper into the wall
                for _ in range(sr.randint(1, 3)):                       # embedded stones, lit from the shaft
                    cx, cy, r = inx(sr.randint(14, 70)), ey + sr.randint(-14, 24), sr.randint(4, 9)
                    poly = [(cx + math.cos(a_) * r * sr.uniform(.7, 1.2), cy + math.sin(a_) * r * sr.uniform(.6, 1))
                            for a_ in [k * math.pi / 3 for k in range(6)]]
                    pg.draw.polygon(scr, (36, 38, 58), poly)
                    pg.draw.line(scr, (54, 58, 84), poly[4], poly[5])
                    pg.draw.lines(scr, (16, 16, 28), False, poly[0:3], 1)
                if sr.random() < .55:                                  # a crack running into the rock, with a branch
                    x0, y0 = ex + side * 2, ey + sr.randint(0, 30)
                    crack = [(x0, y0)]
                    for _ in range(sr.randint(3, 5)):
                        x0, y0 = x0 + side * sr.randint(6, 14), y0 + sr.randint(-7, 7)
                        crack.append((x0, y0))
                    pg.draw.lines(scr, (10, 10, 18), False, crack, 2)
                    bx_, by_ = crack[len(crack) // 2]
                    pg.draw.line(scr, (10, 10, 18), (bx_, by_), (bx_ + side * sr.randint(5, 10), by_ + sr.randint(4, 9)))
                    pg.draw.lines(scr, (44, 48, 72), False, [(x_, y_ + 1) for x_, y_ in crack], 1)
                if sr.random() < .3:                                   # a broken ledge sticking out into the shaft
                    ly = ey + sr.randint(4, 26)
                    lw = sr.randint(8, 16)
                    ledge = [(ex + side * 4, ly - 3), (ex - side * lw, ly - 1), (ex - side * (lw - 3), ly + 3), (ex + side * 4, ly + 5)]
                    pg.draw.polygon(scr, (30, 32, 50), ledge)
                    pg.draw.line(scr, (80, 90, 130), ledge[0], ledge[1])
                    if sr.random() < .5:                               # a few pebbles shaken loose from it
                        for k in range(3):
                            pyy = (ly + 6 + k * 9 + off * .25) % 40 + ly
                            scr.fill((60, 64, 90), (ex - side * sr.randint(2, lw), pyy, 2, 2))
                if sr.random() < .18:                                  # a cluster of glowing crystals in the rock
                    cx, cy = inx(sr.randint(10, 40)), ey + sr.randint(0, 24)
                    col = sr.choice([(90, 200, 255), (190, 110, 255)])
                    glow(scr, cx, cy, 14, tuple(c // 6 for c in col))
                    for k in range(3):
                        h_ = sr.randint(4, 9)
                        dx = (k - 1) * 3
                        pg.draw.polygon(scr, col, [(cx + dx - 1, cy), (cx + dx + 1, cy), (cx + dx + side * (k - 1), cy - h_)])
                if sr.random() < .2:                                   # roots hanging out of the rock
                    rx, ry = ex - side * 1, ey + sr.randint(0, 20)
                    root = [(rx, ry)]
                    for k in range(4):
                        root.append((rx - side * (k + 1) * 2 + sr.randint(-2, 2), ry + (k + 1) * 5))
                    pg.draw.lines(scr, (52, 40, 44), False, root, 1)
            pg.draw.lines(scr, (70, 80, 120), False, edge, 2)
        for i in range(24):                                            # speed lines and falling grit
            x = W // 2 + ((i * 37) % 120 - 60)
            y = (i * 53 - off * 1.6) % (H + 40) - 20
            pg.draw.line(scr, (90, 110, 160), (x, y), (x, y + 16), 1)
        glow(scr, W // 2, H, 120, qcol((20, 60, 110), min(1, t)), .5)  # the arena's light coming up from below
        p = s.pl
        P = pose_jump(400)
        P['coat'] = 6 + math.sin(t * 20) * 2
        s.draw_char(W // 2, H // 2 + 20 + math.sin(t * 9) * 3, p.face, P, s.pal(), p.chains, 0, 0)
        if t > 1.3:
            s.enter_arena()
            s.go('play', 0)
            s.fade = .5

    def enter_arena(s):
        """Through the cave: a stone hall under the city, the boss waiting above you in the dark."""
        p = s.pl
        s.arena, s.arena_t, s.hole = True, 0.0, None
        kind = s.boss_kind
        # ledges low enough for one jump (~66 px) and clear of the exit gate on the right wall
        three = [Plat(70, GY - 46, 76), Plat(ARENA_W // 2 - 38, GY - 82, 76), Plat(ARENA_W - 200, GY - 46, 76)]
        ledges = {'boss_mutant': [Plat(80, GY - 46, 70), Plat(ARENA_W - 190, GY - 46, 70)],
                  'boss_destroyer': three, 'boss_chaos': three, 'boss_wanderer': three, 'boss_yukionna': three,
                  'boss_sensei': [], 'boss_brother': three, 'boss_tengu': three,
                  'boss_shogun': [Plat(70, GY - 46, 70), Plat(ARENA_W - 200, GY - 46, 70)]}
        s.plats = [Plat(-50, GY, ARENA_W + 100, ground=True)] + ledges.get(kind, [Plat(60, GY - 46, 76), Plat(ARENA_W - 200, GY - 46, 76)])
        haz = ARENAS[kind][5]
        s.ahaz = {'kind': haz, 'st': 'idle', 't': 0.0, 'w': 0.0} if haz else None
        s.traps = []
        s.lamps, s.towers, s.scaffolds, s.strings, s.sakuras, s.pads, s.vents = [], [], [], [], [], [], []
        s.cranes, s.plazas, s.chests = [], [], []
        s.coins, s.proj, s.gibs, s.loot, s.parts, s.fx = [], [], [], [], [], []
        s.kiosk = s.keydoor = None
        s.door = {'x': -999, 'k': 1.0, 'closing': False, 'kind': 'gate'}
        s.camtop, s.cam, s.camy = 0, 0.0, 0.0
        s.quota = s.spawned                                            # no more street enemies down here
        p.x, p.y, p.vx, p.vy, p.face = 96, -40, 30, 300, 1        # drops through the hole in the arena's ceiling
        s.boss = s.make_boss(s.boss_kind)
        s.en = [s.boss]
        if not hasattr(s, 'arena_bgs'):
            s.arena_bgs = {}
        if kind not in s.arena_bgs:
            s.arena_bgs[kind] = s.bake_arena(kind)
        s.arena_bg = s.arena_bgs[kind]

    def update_boss_fx(s, dt):
        p = s.pl
        if s.adm('a_kills') and not s.arena:                           # admin: the kill quota is always met
            s.lvl_kills = max(s.lvl_kills, s.exit_need)
        b = s.boss
        if s.arena and b is not None and not s.arena_open and (b.dead or (b.hp <= 0 and b.bs != 'dying')):
            if not b.dead:
                b.hp, b.bs, b.bt = 0, 'dying', 0.0                     # make sure it goes through its death
            else:
                s.boss_msg = ('BOSS DEFEATED', 3.0)
                s.arena_open, s.arena_t = True, 0.0
        keep = []
        for b in s.blades:                                             # [x, y, vy, warning time, hit, 'blade' / 'rock']
            if b[3] > 0:
                b[3] -= dt
                keep.append(b)
                continue
            b[2] += 1400 * dt
            b[1] += b[2] * dt
            if not b[4] and not p.dead and ov((b[0] - 6, b[1] - 14, 12, 18), p.rect()):
                b[4] = True
                s.hurt_player(1 if p.x > b[0] else -1, 1)
            if b[1] >= GY - 4:                                         # hits the floor
                rock = b[5] == 'rock'
                s.burst(b[0], GY - 2, 8, (120, 100, 110) if rock else (220, 225, 240), spd=90, grav=400)
                s.shake = max(s.shake, 3 if rock else 2)
                sfx('crack' if rock else 'ping')
            else:
                keep.append(b)
        s.blades = keep
        for l in s.lines:                                              # [x0, x1, top y, fuse, -]: the delayed cross-cut
            was = l[3]
            l[3] -= dt
            if was > 0 >= l[3]:
                if not p.dead and ov((l[0], l[2], l[1] - l[0], GY - l[2]), p.rect()):
                    s.hurt_player(1 if p.x > (l[0] + l[1]) / 2 else -1, 2)
                for i in range(14):
                    s.burst(lerp(l[0], l[1], i / 13), l[2] + R(4, 50), 2, (255, 120, 240), spd=110, glowing=True, grav=0)
                s.shake = max(s.shake, 7)
                sfx('super')
        s.lines = [l for l in s.lines if l[3] > -.3]
        for q in s.puddles:                                            # [x, life]: acid eating at the floor
            q[1] -= dt
            if not p.dead and p.g and p.y + p.h >= GY - 2 and abs(p.x + p.w / 2 - q[0]) < 18:
                s.hurt_player(1 if p.x > q[0] else -1, 1)
            if random.random() < dt * 6:
                s.parts.append([q[0] + R(-14, 14), GY - 2, R(-5, 5), R(-30, -15), .5, .5, (150, 255, 120), 1.5, -20, True])
        s.puddles = [q for q in s.puddles if q[1] > 0]
        for c in s.claws:
            c[4] -= dt
        s.claws = [c for c in s.claws if c[4] > 0]
        for sp in s.spikes:                                            # roots: a warning on the floor, then up they come
            if sp[1] > 0:
                sp[1] -= dt
                if sp[1] <= 0:
                    s.burst(sp[0], GY - 2, 8, (110, 90, 70), spd=90, grav=400)
                    s.shake = max(s.shake, 3)
                    sfx('crack')
                continue
            sp[2] += dt
            if not sp[3] and sp[2] < .35 and not p.dead and ov((sp[0] - 9, GY - 40, 18, 40), p.rect()):
                sp[3] = True
                s.hurt_player(1 if p.x > sp[0] else -1, 1)
        s.spikes = [sp for sp in s.spikes if sp[1] > 0 or sp[2] < .5]
        if s.arena and random.random() < dt * 9:                       # the arena's air: embers / bubbles / gold ash
            kind = s.boss_kind
            if kind == 'boss_mutant':
                s.parts.append([R(0, ARENA_W), GY - 2, R(-4, 4), R(-30, -14), 1.6, 1.6, (150, 255, 90), 1, -4, True])
            elif kind == 'boss_destroyer':
                s.parts.append([R(0, ARENA_W), R(20, GY), R(-6, 6), R(-6, 6), .5, .5, (140, 220, 255), 1, 0, True])
            elif kind == 'boss_shogun':
                s.parts.append([R(0, ARENA_W), R(20, 60), R(-10, 10), R(10, 30), 4.0, 4.0,
                                random.choice(((255, 210, 120), (200, 60, 40))), 1, 2, True])
            elif ARENA_STYLE.get(kind, ('',))[0] in ('grove', 'swamp'):   # spores drifting up out of the moss
                s.parts.append([R(0, ARENA_W), GY - 2, R(-4, 4), R(-24, -10), 2.5, 2.5, (160, 255, 140), 1, -4, True])
            elif ARENA_STYLE.get(kind, ('',))[0] == 'torii':           # foxfire
                s.parts.append([R(0, ARENA_W), R(60, GY), R(-6, 6), R(-20, -6), 1.5, 1.5, (90, 170, 255), 1, -4, True])
            elif ARENA_STYLE.get(kind, ('',))[0] in ('cliff', 'ice'):  # snow
                s.parts.append([R(0, ARENA_W), 20, R(-30, -10), R(30, 50), 4.0, 4.0, (230, 240, 255), 1, 4, False])
            elif ARENA_STYLE.get(kind, ('',))[0] == 'dojo':            # dust in the light (petals in Tomoe's hall)
                col = (255, 170, 200) if kind == 'boss_tomoe' else (220, 200, 160)
                s.parts.append([R(0, ARENA_W), R(30, 80), R(-6, 6), R(4, 14), 4.0, 4.0, col, 1, 1, False])
            else:
                s.parts.append([R(0, ARENA_W), GY - 2, R(-8, 8), R(-50, -20), 2.5, 2.5,
                                random.choice(((255, 140, 60), (255, 80, 60))), 1, -6, True])
        s.update_arena_haz(dt)

    MOLTEN_X = (ARENA_W * .3, ARENA_W * .7)                            # the foundry's two molten channels in the floor
    SLUDGE_X = (150, 260, 380, 490)                                    # the cistern's four drains in the ceiling

    def update_arena_haz(s, dt):
        """Each arena fights back: the foundry's channels erupt, the drydock floods with acid, the throne hall burns."""
        h, b, p = s.ahaz, s.boss, s.pl
        if not h or not s.arena or b is None or b.dead or b.bs in ('enter', 'intro', 'dying', 'idle'):
            return
        h['t'] += dt
        if h['kind'] == 'fire':                                        # walls of fire close in from both sides in phase 2 / 3
            want = {1: 0.0, 2: 56.0, 3: 84.0}.get(b.bphase, 84.0)
            if want > h['w'] and h['w'] == 0:
                s.boss_msg = ('THE HALL IS BURNING', 2.0)
                sfx('boom')
            h['w'] += (want - h['w']) * min(1, dt * 1.5)
            fw = h['w']
            if fw > 4:
                if random.random() < dt * 30:
                    side = random.choice((0, 1))
                    x = R(0, fw) if side == 0 else ARENA_W - R(0, fw)
                    s.parts.append([x, GY - R(0, 20), R(-10, 10), R(-90, -40), .6, .6,
                                    random.choice(((255, 200, 80), (255, 110, 40))), 2, -40, True])
                if not p.dead and (p.x < fw - 6 or p.x + p.w > ARENA_W - fw + 6):
                    s.hurt_player(1 if p.x < ARENA_W / 2 else -1, 1)
            return
        ph2 = b.bphase >= 2
        idle, warn, on = {'molten': ((3.6 if ph2 else 5.5), 1.0, 1.1), 'tide': ((6.5 if ph2 else 9.5), 1.6, 2.4),
                          'volt': ((5.0 if ph2 else 7.5), 1.8, 1.4), 'sludge': ((3.4 if ph2 else 5.0), 1.1, 1.6)}[h['kind']]
        if h['st'] == 'idle' and h['t'] >= idle:
            h['st'], h['t'] = 'warn', 0.0
            if h['kind'] == 'volt':                                    # one half of the floor goes live (the ledges are safe)
                h['side'] = 0 if (p.x + p.w / 2) < ARENA_W / 2 else 1
                s.boss_msg = ('THE FLOOR IS LIVE', 1.4)
            elif h['kind'] == 'sludge':                                # two of the four drains above open up
                h['pipes'] = random.sample(range(4), 3 if ph2 else 2)
                s.boss_msg = ('THE DRAINS OVERFLOW', 1.4)
            else:
                s.boss_msg = ('THE FURNACE ROARS', 1.2) if h['kind'] == 'molten' else ('THE TIDE IS RISING', 1.6)
            sfx('charge')
        elif h['st'] == 'warn' and h['t'] >= warn:
            h['st'], h['t'] = 'on', 0.0
            s.shake = max(s.shake, 6)
            sfx('boom' if h['kind'] == 'molten' else 'bwave')
        elif h['st'] == 'on' and h['t'] >= on:
            h['st'], h['t'] = 'idle', 0.0
        if h['kind'] == 'volt':
            lo, hi = (12, ARENA_W / 2) if h.get('side', 0) == 0 else (ARENA_W / 2, ARENA_W - 12)
            if h['st'] == 'on' and not p.dead and p.g and p.y + p.h >= GY - 2 and lo - 4 < p.x + p.w / 2 < hi + 4:
                s.hurt_player(1 if p.x > ARENA_W / 2 else -1, 1)
            if h['st'] in ('warn', 'on') and random.random() < dt * (40 if h['st'] == 'on' else 10):
                s.parts.append([R(lo, hi), GY - 2, R(-40, 40), R(-120, -40), .3, .3,
                                random.choice(((160, 240, 255), (255, 255, 255))), R(1, 2), 300, True])
            return
        if h['kind'] == 'sludge':
            for i in h.get('pipes', ()):
                px_ = s.SLUDGE_X[i]
                if h['st'] == 'on' and not p.dead and abs(p.x + p.w / 2 - px_) < 16:
                    s.hurt_player(1 if p.x + p.w / 2 > px_ else -1, 1)
                if h['st'] == 'warn' and random.random() < dt * 10:
                    s.parts.append([px_ + R(-4, 4), 34, 0, R(40, 80), 1.0, 1.0, (150, 255, 90), 2, 400, True])
                if h['st'] == 'on' and random.random() < dt * 30:
                    s.parts.append([px_ + R(-10, 10), GY - 2, R(-60, 60), R(-120, -40), .5, .5, (150, 255, 90), R(1.5, 2.5), 400, True])
            return
        if h['st'] == 'on' and not p.dead:
            if h['kind'] == 'molten':
                for mx in s.MOLTEN_X:
                    if abs(p.x + p.w / 2 - mx) < 24 and p.y + p.h > GY - 130:
                        s.hurt_player(1 if p.x + p.w / 2 > mx else -1, 1)
                    if random.random() < dt * 40:
                        s.parts.append([mx + R(-16, 16), GY - 2, R(-20, 20), R(-320, -200), .5, .5,
                                        random.choice(((255, 220, 120), (255, 120, 40))), R(2, 3), 200, True])
            elif p.g and p.y + p.h >= GY - 2:                          # the acid tide: only the ledges are safe
                s.hurt_player(1 if p.x > ARENA_W / 2 else -1, 1)
        elif h['st'] == 'warn' and h['kind'] == 'molten' and random.random() < dt * 20:
            mx = random.choice(s.MOLTEN_X)
            s.parts.append([mx + R(-16, 16), GY - 2, R(-8, 8), R(-60, -30), .5, .5, (255, 160, 60), 2, 100, True])

    def draw_arena_haz(s, cx, oy):
        h = s.ahaz
        if not h:
            return
        gy = GY + oy
        if h['kind'] == 'volt':
            if h['st'] == 'idle':
                return
            lo, hi = (12, ARENA_W / 2) if h.get('side', 0) == 0 else (ARENA_W / 2, ARENA_W - 12)
            if h['st'] == 'warn':                                      # the plates hum and flash before they go live
                if int(s.t * 10) % 2:
                    for x in range(int(lo), int(hi), 24):
                        pg.draw.rect(scr, (60, 200, 255), (x - cx + 2, gy, 18, 2))
                return
            band = pg.Surface((int(hi - lo), 10), pg.SRCALPHA)
            band.fill((80, 200, 255, 60))
            scr.blit(band, (lo - cx, gy - 8))
            for j in range(3):                                         # crawling arcs along the floor
                pts, x = [], lo
                while x < hi:
                    pts.append((x - cx, gy - R(0, 9)))
                    x += R(10, 22)
                if len(pts) > 1:
                    pg.draw.lines(scr, ((140, 230, 255), (255, 255, 255), (90, 160, 255))[j], False, pts, 1)
            for x in (lo + 20, hi - 20):
                glow(scr, x - cx, gy - 6, 40, (20, 70, 110))
            return
        if h['kind'] == 'sludge':
            for i in h.get('pipes', ()):
                x = s.SLUDGE_X[i] - cx
                if h['st'] == 'warn':
                    if int(s.t * 12) % 2:
                        pg.draw.line(scr, (150, 255, 90), (x - 14, gy - 1), (x + 14, gy - 1), 2)
                    glow(scr, x, 34 + oy, 14, (40, 90, 20))
                elif h['st'] == 'on':                                  # a thick toxic stream from the drain to the floor
                    wob = math.sin(s.t * 20 + i) * 1.5
                    pg.draw.rect(scr, (70, 150, 40), (x - 9 + wob, 34 + oy, 18, gy - 34 - oy))
                    pg.draw.rect(scr, (150, 255, 90), (x - 5 + wob, 34 + oy, 10, gy - 34 - oy))
                    pg.draw.line(scr, (230, 255, 200), (x - 2 + wob, 34 + oy), (x - 2 + wob, gy), 1)
                    pg.draw.ellipse(scr, (120, 220, 70), (x - 20, gy - 5, 40, 8))
                    glow(scr, x, gy - 20, 40, (30, 80, 15))
            return
        if h['kind'] == 'molten':
            for mx in s.MOLTEN_X:
                x = mx - cx
                hot = 1.0 if h['st'] == 'on' else (.4 + .6 * min(1, h['t']) if h['st'] == 'warn' else .25)
                pg.draw.rect(scr, (40, 10, 4), (x - 24, gy - 1, 48, 5))
                pg.draw.rect(scr, qcol((255, 140, 40), hot), (x - 22, gy, 44, 3))
                glow(scr, x, gy, 30, qcol((120, 50, 10), hot))
                if h['st'] == 'on':                                    # the eruption: a column of fire
                    for i in range(4):
                        fl = 120 + 20 * math.sin(s.t * 30 + i)
                        wx = 12 - i * 2
                        pg.draw.polygon(scr, ((255, 90, 30), (255, 150, 50), (255, 210, 110), (255, 250, 210))[i],
                                        [(x - wx, gy), (x + wx, gy), (x + R(-3, 3), gy - fl * (1 - i * .18))])
                    glow(scr, x, gy - 60, 50, (120, 50, 10))
                elif h['st'] == 'warn' and int(s.t * 12) % 2:
                    pg.draw.line(scr, (255, 90, 60), (x - 22, gy - 1), (x + 22, gy - 1), 2)
        elif h['kind'] == 'tide':
            if h['st'] == 'idle':
                return
            k = min(1, h['t'] / 1.6) if h['st'] == 'warn' else 1.0
            lvl = 4 + 10 * k if h['st'] == 'on' else 3 * k
            top = gy - lvl
            water = pg.Surface((W, int(H - top) + 2), pg.SRCALPHA)
            water.fill((60, 200, 90, 90 if h['st'] == 'on' else 50))
            scr.blit(water, (0, top))
            pts = [(x, top + math.sin(x * .08 + s.t * 5) * 1.5) for x in range(0, W + 8, 8)]
            pg.draw.lines(scr, (170, 255, 170), False, pts, 1)
            if h['st'] == 'warn' and int(s.t * 6) % 2:                 # the siren lights
                for x in (12, W - 12):
                    glow(scr, x, gy - 120, 20, (110, 30, 10))
        else:
            fw = h['w']
            if fw < 2:
                return
            for side in (0, 1):
                for i in range(int(fw // 8) + 1):
                    x = (i * 8 if side == 0 else ARENA_W - i * 8) - cx
                    fl = 40 + 26 * math.sin(s.t * 13 + i * 1.7) + 20 * (1 - i * 8 / max(1, fw))
                    for j, col in enumerate(((200, 50, 20), (255, 130, 40), (255, 220, 120))):
                        hw = 8 - j * 2
                        pg.draw.polygon(scr, col, [(x - hw, gy), (x + hw, gy), (x + R(-2, 2), gy - fl * (1 - j * .25))])
                glow(scr, (fw / 2 if side == 0 else ARENA_W - fw / 2) - cx, gy - 30, int(fw) + 20, (110, 40, 10))

    def draw_boss_fx(s, cx, oy):
        gy = GY + oy
        for b in s.blades:
            x = b[0] - cx
            if b[3] > 0:                                               # the spot where it will land, flashing
                if int(s.t * 16) % 2:
                    pg.draw.line(scr, (255, 60, 80), (x - 10, gy - 1), (x + 10, gy - 1), 2)
                    pg.draw.line(scr, (120, 20, 40), (x, oy), (x, gy), 1)
                continue
            y = b[1] + oy
            if b[5] == 'rock':
                pg.draw.circle(scr, (70, 56, 66), (int(x), int(y)), 7)
                pg.draw.circle(scr, (120, 100, 110), (int(x) - 2, int(y) - 2), 3)
            elif b[5] == 'feather':                                    # a tengu feather, sharp as a blade
                pg.draw.polygon(scr, (40, 34, 40), [(x, y + 9), (x - 3, y - 6), (x, y - 12), (x + 3, y - 6)])
                pg.draw.line(scr, (230, 230, 240), (x, y + 8), (x, y - 11))
            elif b[5] == 'ice':                                        # an icicle
                pg.draw.polygon(scr, (200, 236, 255), [(x, y + 10), (x - 4, y - 10), (x + 4, y - 10)])
                pg.draw.line(scr, (255, 255, 255), (x - 1, y - 9), (x - 1, y + 4))
                glow(scr, x, y, 10, (30, 60, 90))
            elif b[5] == 'branch':                                     # a dead branch snapping off the canopy
                pg.draw.line(scr, (60, 44, 30), (x - 6, y - 8), (x + 5, y + 8), 3)
                pg.draw.line(scr, (60, 44, 30), (x, y), (x + 6, y - 6), 2)
                pg.draw.circle(scr, (60, 120, 60), (int(x + 6), int(y - 7)), 3)
            else:                                                      # a falling kunai
                pg.draw.polygon(scr, (230, 235, 250), [(x, y + 8), (x - 3, y - 4), (x + 3, y - 4)])
                pg.draw.line(scr, (90, 30, 50), (x, y - 4), (x, y - 14), 2)
                glow(scr, x, y, 10, (60, 40, 70))
        for l in s.lines:
            x0, x1, y0 = l[0] - cx, l[1] - cx, l[2] + oy
            if l[3] > 0:                                               # the cut hangs in the air...
                if int(s.t * 20) % 2:
                    for yy in (y0 + 12, y0 + 30, y0 + 48):
                        pg.draw.line(scr, (255, 90, 220), (x0, yy), (x1, yy), 1)
            else:                                                      # ...then lands all at once
                k = 1 + l[3] / .3
                pg.draw.rect(scr, (255, 220, 250), (x0, y0 + 6, x1 - x0, max(1, int(46 * k))))
                glow(scr, (x0 + x1) / 2, y0 + 30, int(max(20, (x1 - x0) / 2)), qcol((140, 40, 130), k), .3)
        sc_ = s.BOSS_AURA.get(s.boss.kind, (150, 230, 90)) if s.boss is not None else (150, 230, 90)
        for sp in s.spikes:                                            # [x, warning, time up, hit]: roots / ice from the floor
            x = sp[0] - cx
            if sp[1] > 0:
                if int(s.t * 16) % 2:
                    pg.draw.line(scr, sc_, (x - 10, gy - 1), (x + 10, gy - 1), 2)
                    for j in (-6, 0, 6):
                        pg.draw.line(scr, tuple(c // 2 for c in sc_), (x + j, gy - 1), (x + j * 1.4, gy - 5))
                continue
            k = min(1, sp[2] / .1) * (1 - max(0, sp[2] - .35) / .15)
            h_ = 42 * max(0, k)
            ice = s.boss is not None and s.boss.kind == 'boss_yukionna'
            for j, (dx_, hh) in enumerate(((-6, .7), (0, 1.0), (6, .8))):
                col = ((200, 236, 255) if ice else (70, 52, 36)) if j != 1 else ((240, 250, 255) if ice else (96, 72, 46))
                pg.draw.polygon(scr, col, [(x + dx_ - 4, gy), (x + dx_ + 4, gy), (x + dx_ + 1, gy - h_ * hh)])
            if not ice:
                pg.draw.circle(scr, (90, 170, 80), (int(x + 1), int(gy - h_ + 3)), 2)
        for c in s.claws:                                              # [x, y, face, rising, life]: three talon marks in the air
            k = c[4] / .22
            for j in range(3):
                ox_ = (j - 1) * 9
                if c[3]:
                    a0, a1 = (c[0] - cx + ox_ - c[2] * 22, c[1] + oy + 26), (c[0] - cx + ox_ + c[2] * 22, c[1] + oy - 30)
                else:
                    a0, a1 = (c[0] - cx + ox_ - c[2] * 24, c[1] + oy - 34), (c[0] - cx + ox_ + c[2] * 18, c[1] + oy + 28)
                mid = ((a0[0] + a1[0]) / 2 + c[2] * 8, (a0[1] + a1[1]) / 2)
                pg.draw.lines(scr, qcol((200, 255, 160), k), False, [a0, mid, a1], 3 if k > .5 else 2)
                pg.draw.lines(scr, qcol((255, 255, 240), k), False, [a0, mid, a1], 1)
            glow(scr, c[0] - cx, c[1] + oy, 30, qcol((40, 100, 30), k))
        for q in s.puddles:
            x = q[0] - cx
            k = min(1, q[1] / .5)
            glow(scr, x, gy - 2, 22, qcol((40, 110, 30), k), .3)
            pg.draw.ellipse(scr, (90, 200, 70), (x - 18 * k, gy - 3, 36 * k, 5))

    def bake_arena(s, kind):
        """Each act's boss fights in its own place, drawn once."""
        if kind == 'boss_destroyer':
            return s.bake_substation()
        if kind == 'boss_mutant':
            return s.bake_cistern()
        if kind == 'boss_shogun':
            return s.bake_throne()
        if kind in ARENA_STYLE:
            return s.bake_place(kind)
        return s.bake_hall()

    @staticmethod
    def bake_place(kind):
        """The new locations' arenas: a temple gate, a bell hall, a hanging grove, a thousand torii, a cloud platform,
        a frozen shrine and dojo halls - each drawn once, in its boss's colours."""
        style, seed, word = ARENA_STYLE[kind]
        _, _, top, bot, acc, _ = ARENAS[kind]
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, top), (GY, bot)])
        rnd = random.Random(seed)
        dark = tuple(c // 3 for c in bot)
        cx = ARENA_W // 2
        big = pg.transform.scale_by(F_JPB.render(word, False, tuple(min(255, c // 2 + 20) for c in acc)), 3)
        if style == 'gate':                                            # the temple gate: red pillars, a giant red lantern
            A.fill((10, 4, 4), (0, 0, ARENA_W, 22))
            for x in range(0, ARENA_W, 28):
                pg.draw.line(A, (50, 16, 12), (x, 0), (x, 22), 3)
            for px in (50, 170, ARENA_W - 170, ARENA_W - 50):
                pg.draw.rect(A, (150, 26, 20), (px - 12, 22, 24, GY - 22))
                pg.draw.line(A, (220, 80, 60), (px - 7, 24), (px - 7, GY))
                pg.draw.rect(A, (30, 20, 20), (px - 15, GY - 12, 30, 12))
            for sx_ in (100, ARENA_W - 100):                            # the guardians' alcoves, a dark statue in each
                pg.draw.rect(A, dark, (sx_ - 30, 50, 60, GY - 50))
                pg.draw.circle(A, (40, 20, 16), (sx_, 84), 12)
                pg.draw.polygon(A, (40, 20, 16), [(sx_ - 22, 98), (sx_ + 22, 98), (sx_ + 16, GY - 30), (sx_ - 16, GY - 30)])
            pg.draw.line(A, (40, 20, 16), (cx, 22), (cx, 40), 2)
            pg.draw.ellipse(A, (190, 30, 30), (cx - 40, 40, 80, 100))
            for yy in (40, 132):
                pg.draw.rect(A, (30, 16, 14), (cx - 30, yy, 60, 8))
            for yy in range(56, 128, 10):
                pg.draw.line(A, (150, 20, 20), (cx - 36, yy), (cx + 36, yy))
            A.blit(big, (cx - big.get_width() // 2, 90 - big.get_height() // 2))
        elif style == 'bell':                                          # the great bell hall, candles burning below
            for x in range(0, ARENA_W, 16):
                v = rnd.randint(-4, 4)
                A.fill((48 + v, 24 + v, 18 + v), (x, 20, 15, GY - 20))
            A.fill((10, 4, 4), (0, 0, ARENA_W, 20))
            pg.draw.rect(A, (30, 14, 10), (cx - 90, 20, 180, 10))
            pg.draw.line(A, (60, 50, 40), (cx, 30), (cx, 44), 3)
            pg.draw.polygon(A, (110, 86, 40), [(cx - 26, 44), (cx + 26, 44), (cx + 40, 132), (cx - 40, 132)])
            pg.draw.rect(A, (140, 110, 50), (cx - 42, 128, 84, 8))
            for yy in (60, 80, 100):
                pg.draw.line(A, (80, 62, 28), (cx - 30 - (yy - 44) * .15, yy), (cx + 30 + (yy - 44) * .15, yy), 2)
            for k in range(3):
                for j in range(4):
                    pg.draw.circle(A, (150, 124, 60), (cx - 12 + j * 8, 52 + k * 7), 2)
            pg.draw.line(A, (90, 60, 40), (cx + 60, 70), (cx + 140, 70), 7)       # the log striker on its ropes
            for rx in (cx + 70, cx + 130):
                pg.draw.line(A, (160, 140, 100), (rx, 30), (rx, 68))
            for bx, wd in ((80, "南無"), (ARENA_W - 80, "阿弥")):
                pg.draw.rect(A, (200, 190, 160), (bx - 13, 30, 26, 80))
                for i, ch in enumerate(wd):
                    g = F_JPB.render(ch, False, (40, 20, 20))
                    A.blit(g, (bx - g.get_width() // 2, 40 + i * 30))
            for x in range(40, ARENA_W - 30, 26):                      # rows of candles along the floor
                A.fill((230, 220, 200), (x, GY - 14, 3, 8))
                glow(A, x + 1, GY - 17, 8, (90, 50, 10))
                A.fill((255, 200, 90), (x, GY - 17, 3, 3))
        elif style == 'grove':                                         # giant trunks, roots, moss, a roped sacred tree
            for _ in range(40):
                x = rnd.randint(0, ARENA_W)
                pg.draw.line(A, tuple(c // 2 for c in bot), (x, 0), (x + rnd.randint(-10, 10), GY), rnd.randint(4, 12))
            for i, (px, w) in enumerate(((60, 60), (210, 40), (ARENA_W - 210, 46), (ARENA_W - 60, 64))):
                col = (24, 34, 24) if i % 2 else (30, 40, 28)
                pg.draw.rect(A, col, (px - w // 2, 0, w, GY))
                for k in range(5):
                    xx = px - w // 2 + 4 + k * (w // 5)
                    pg.draw.line(A, (18, 26, 18), (xx, 0), (xx + rnd.randint(-4, 4), GY), 2)
                for _ in range(6):
                    A.fill((50, 100, 50), (px - w // 2 + rnd.randint(0, w - 4), rnd.randint(10, GY - 10), 4, rnd.randint(6, 16)))
                for d in (-1, 1):
                    pts = [(px + d * w // 2, GY - 20)]
                    for k in range(4):
                        pts.append((pts[-1][0] + d * rnd.randint(10, 18), pts[-1][1] + rnd.randint(3, 6)))
                    pg.draw.lines(A, col, False, pts, 5)
            ry = 70                                                    # the shimenawa rope on the trunk behind the fight
            pg.draw.rect(A, (34, 44, 30), (cx - 34, 0, 68, GY))
            pg.draw.line(A, (200, 180, 120), (cx - 36, ry), (cx + 36, ry + 3), 5)
            for k in range(4):
                zx = cx - 26 + k * 17
                pg.draw.lines(A, (240, 240, 230), False, [(zx, ry + 4), (zx + 3, ry + 10), (zx - 1, ry + 15), (zx + 2, ry + 21)], 2)
            A.blit(big, (cx - big.get_width() // 2, 110))
            for x in range(0, ARENA_W, 13):                            # vines hanging from the canopy
                if rnd.random() < .4:
                    pg.draw.line(A, (40, 80, 40), (x, 0), (x + rnd.randint(-3, 3), rnd.randint(20, 70)), 1)
        elif style == 'torii':                                         # rows of red torii going back into the dark
            for i in range(7, 0, -1):
                k = i / 7
                w, h = 70 + 300 * k, 50 + 150 * k
                y0 = GY - h
                col = tuple(int(c * (.35 + .65 * k)) for c in (200, 40, 30))
                for sx_ in (-1, 1):
                    pg.draw.rect(A, col, (cx + sx_ * w / 2 - 5 * k - 2, y0, 6 + 8 * k, h))
                pg.draw.rect(A, (20, 10, 10), (cx - w / 2 - 14 * k, y0 - 10 * k - 4, w + 28 * k, 6 + 6 * k))
                pg.draw.rect(A, col, (cx - w / 2, y0 + 10 * k + 4, w, 3 + 4 * k))
            for sx_ in (110, ARENA_W - 110):                            # fox statues on their stones
                pg.draw.rect(A, (60, 60, 64), (sx_ - 16, GY - 30, 32, 30))
                pg.draw.polygon(A, (200, 196, 188), [(sx_ - 10, GY - 30), (sx_ + 10, GY - 30), (sx_ + 6, GY - 56), (sx_ - 6, GY - 56)])
                pg.draw.polygon(A, (200, 196, 188), [(sx_ - 6, GY - 56), (sx_ - 2, GY - 66), (sx_, GY - 56)])
                pg.draw.polygon(A, (200, 196, 188), [(sx_ + 6, GY - 56), (sx_ + 2, GY - 66), (sx_, GY - 56)])
                pg.draw.rect(A, (200, 40, 30), (sx_ - 8, GY - 44, 16, 5))
            A.blit(big, (cx - big.get_width() // 2, 40))
        elif style == 'cliff':                                         # high above the clouds, mountains all around
            for row, (col, base, amp) in enumerate((((90, 106, 150), GY - 100, 70), ((70, 84, 126), GY - 60, 50))):
                pts, x = [(0, GY)], 0
                while x <= ARENA_W:
                    pts.append((x, base - rnd.randint(0, amp)))
                    x += rnd.randint(30, 70)
                pts += [(ARENA_W, GY)]
                pg.draw.polygon(A, col, pts)
            for _ in range(50):
                x_, y_ = rnd.randint(0, ARENA_W), GY - rnd.randint(20, 40)
                pg.draw.ellipse(A, (200, 210, 236), (x_ - 30, y_ - 8, 60, 18))
            for x0, x1, y_ in ((0, 300, 30), (260, ARENA_W, 40)):     # prayer flags strung across the sky
                pts = [(lerp(x0, x1, j / 10), y_ + 12 * math.sin(j / 10 * math.pi)) for j in range(11)]
                pg.draw.lines(A, (70, 70, 90), False, pts)
                for j, (fx_, fy_) in enumerate(pts[1:-1]):
                    A.fill(((210, 60, 60), (240, 220, 80), (80, 170, 90), (70, 120, 220), (236, 236, 236))[j % 5], (fx_, fy_ + 1, 5, 7))
            for px in (30, ARENA_W - 30):                              # wooden posts holding the platform
                pg.draw.rect(A, (60, 40, 30), (px - 6, GY - 70, 12, 70))
            A.blit(big, (cx - big.get_width() // 2, 30))
        elif style == 'swamp':                                         # a sunken bog: dead trees, hanging moss, black water
            for _ in range(8):
                x, h = rnd.randint(20, ARENA_W - 20), rnd.randint(90, GY - 10)
                pg.draw.line(A, (20, 26, 18), (x, GY), (x + rnd.randint(-10, 10), GY - h), 6)
                for k in range(3):
                    by_ = GY - h + k * 22
                    d = rnd.choice((-1, 1))
                    pg.draw.line(A, (20, 26, 18), (x, by_), (x + d * rnd.randint(16, 30), by_ - rnd.randint(4, 14)), 3)
                    for j in range(4):
                        pg.draw.line(A, (60, 90, 50), (x + d * (6 + j * 5), by_ - 2), (x + d * (6 + j * 5), by_ + rnd.randint(6, 18)))
            for k in range(5):                                         # pools of black water along the floor
                px = 40 + k * 130 + rnd.randint(-20, 20)
                pg.draw.ellipse(A, (8, 14, 12), (px - 40, GY - 8, 80, 12))
                pg.draw.line(A, (60, 90, 70), (px - 30, GY - 3), (px + 20, GY - 3))
            for _ in range(14):                                        # glowing mushrooms
                x = rnd.randint(16, ARENA_W - 16)
                pg.draw.ellipse(A, (190, 230, 120), (x - 3, GY - 10, 6, 4))
                A.fill((150, 140, 110), (x, GY - 7, 1, 7))
                glow(A, x, GY - 9, 8, (30, 50, 10))
            A.blit(big, (cx - big.get_width() // 2, 36))
        elif style == 'ice':                                           # an ice cave: cracked blue walls, icicles, frozen pillars
            for _ in range(30):
                x, y = rnd.randint(0, ARENA_W), rnd.randint(20, GY)
                pts = [(x, y)]
                for k in range(4):
                    pts.append((pts[-1][0] + rnd.randint(-14, 14), pts[-1][1] + rnd.randint(4, 14)))
                pg.draw.lines(A, (120, 180, 220), False, pts, 1)
            A.fill((4, 8, 18), (0, 0, ARENA_W, 18))
            for x in range(0, ARENA_W, 7):
                h = rnd.randint(4, 26)
                pg.draw.polygon(A, (170, 220, 250), [(x, 17), (x + 7, 17), (x + 3, 17 + h)])
            for px in (90, 230, ARENA_W - 230, ARENA_W - 90):
                pg.draw.rect(A, (90, 150, 200), (px - 12, 18, 24, GY - 18))
                pg.draw.line(A, (200, 240, 255), (px - 6, 20), (px - 6, GY))
            pg.draw.rect(A, (40, 60, 90), (cx - 30, GY - 60, 60, 60))   # the frozen shrine
            pg.draw.polygon(A, (200, 230, 250), [(cx - 44, GY - 60), (cx + 44, GY - 60), (cx + 30, GY - 78), (cx - 30, GY - 78)])
            A.blit(big, (cx - big.get_width() // 2, 40))
        else:                                                          # a dojo hall: planks, shoji, weapon racks, a scroll
            for x in range(0, ARENA_W, 14):
                v = rnd.randint(-5, 5)
                A.fill(tuple(max(0, min(255, c + v)) for c in bot), (x, 20, 13, GY - 20))
            A.fill(tuple(c // 3 for c in top), (0, 0, ARENA_W, 20))
            night = kind == 'boss_brother'
            for i, x in enumerate(range(30, ARENA_W - 40, 74)):         # shoji windows: paper glowing with the light outside
                if abs(x + 30 - cx) < 70:
                    continue
                light = (40, 50, 90) if night else ((230, 236, 255) if kind == 'boss_sensei' else (240, 200, 140))
                pg.draw.rect(A, light, (x, 34, 60, 46))
                for gx in range(x, x + 61, 15):
                    pg.draw.line(A, (40, 24, 18), (gx, 34), (gx, 80))
                for gy_ in range(34, 81, 11):
                    pg.draw.line(A, (40, 24, 18), (x, gy_), (x + 60, gy_))
                pg.draw.rect(A, (40, 24, 18), (x, 34, 60, 46), 2)
            if night:                                                  # the moon in one window, red light from the other
                pg.draw.circle(A, (230, 230, 240), (104, 52), 9)
            for rx in (60, ARENA_W - 60):                              # weapon racks: bokken, staffs, a naginata
                pg.draw.rect(A, (50, 30, 20), (rx - 26, GY - 70, 52, 6))
                pg.draw.rect(A, (50, 30, 20), (rx - 26, GY - 30, 52, 6))
                for j in range(5):
                    pg.draw.line(A, (130, 90, 56) if j % 2 else (90, 60, 40), (rx - 20 + j * 10, GY - 82), (rx - 20 + j * 10, GY - 24), 2)
            pg.draw.rect(A, (226, 220, 200), (cx - 26, 26, 52, 100))  # the scroll with the hall's character
            pg.draw.rect(A, (60, 30, 20), (cx - 30, 24, 60, 4))
            pg.draw.rect(A, (60, 30, 20), (cx - 30, 124, 60, 4))
            ink = pg.transform.scale_by(F_JPB.render(word, False, (20, 14, 14)), 3)
            A.blit(ink, (cx - ink.get_width() // 2, 76 - ink.get_height() // 2))
            for x in range(0, ARENA_W, 40):                            # tatami edge
                pg.draw.rect(A, (70, 60, 30), (x, GY - 4, 38, 4))
        pg.draw.rect(A, (3, 1, 5), (0, 0, 10, GY))                      # side walls
        pg.draw.rect(A, (3, 1, 5), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_substation():
        """THUNDER SUBSTATION: steel panels, transformer banks, insulator stacks, two tesla coils, cables sagging overhead."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (4, 8, 16)), (GY, (12, 30, 52))])
        rnd = random.Random(19)
        for y in range(20, GY, 26):                                    # steel wall panels
            for x in range(0, ARENA_W, 40):
                v = rnd.randint(-3, 4)
                A.fill((14 + v, 22 + v, 36 + v), (x + 1, y + 1, 38, 24))
                pg.draw.line(A, (30, 44, 66), (x + 1, y + 1), (x + 38, y + 1))
        A.fill((2, 4, 8), (0, 0, ARENA_W, 20))
        for x0, x1, sag in ((10, 230, 26), (180, 470, 34), (410, 630, 22), (60, 600, 46)):   # cables overhead
            pts = [(x0 + (x1 - x0) * i / 12, 20 + sag * math.sin(math.pi * i / 12)) for i in range(13)]
            pg.draw.lines(A, (20, 26, 34), False, pts, 2)
        for bx in (120, 250, 390, 520):                                 # transformer banks with cooling fins
            pg.draw.rect(A, (22, 34, 50), (bx - 30, GY - 90, 60, 90))
            pg.draw.rect(A, (40, 58, 82), (bx - 30, GY - 90, 60, 90), 1)
            for fx in range(bx - 26, bx + 27, 5):
                pg.draw.line(A, (32, 48, 70), (fx, GY - 84), (fx, GY - 10))
            for ix in (bx - 16, bx, bx + 16):                          # insulator stacks on top
                for j in range(4):
                    pg.draw.ellipse(A, (120, 90, 70), (ix - 4, GY - 98 - j * 5, 8, 4))
                pg.draw.line(A, (80, 90, 100), (ix, GY - 116), (ix, GY - 90))
            pg.draw.polygon(A, (200, 170, 40), [(bx - 6, GY - 60), (bx + 6, GY - 60), (bx, GY - 50)])   # high-voltage sign
            pg.draw.line(A, (20, 20, 20), (bx, GY - 58), (bx, GY - 53))
        for cx_ in (ARENA_W * .25, ARENA_W * .75):                      # the tesla coils (their arcs are drawn live)
            cx_ = int(cx_)
            pg.draw.rect(A, (30, 36, 48), (cx_ - 6, 60, 12, GY - 60))
            for j in range(10):
                pg.draw.line(A, (150, 110, 60), (cx_ - 6, 64 + j * 6), (cx_ + 6, 64 + j * 6))
            pg.draw.ellipse(A, (70, 80, 100), (cx_ - 18, 46, 36, 16))
            pg.draw.ellipse(A, (120, 140, 170), (cx_ - 18, 46, 36, 16), 1)
        img = F_JPB.render("変電所", False, (40, 110, 160))
        A.blit(img, (ARENA_W // 2 - img.get_width() // 2, 34))
        for x in range(0, ARENA_W, 24):                                 # floor plates
            pg.draw.line(A, (30, 60, 90), (x, GY - 3), (x, GY))
        pg.draw.rect(A, (2, 3, 6), (0, 0, 10, GY))
        pg.draw.rect(A, (2, 3, 6), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_cistern():
        """TOXIC CISTERN: brick vaults over black water, rusted drains, moss and slime running down the walls."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (4, 10, 6)), (GY, (18, 34, 16))])
        rnd = random.Random(23)
        for row, y in enumerate(range(18, GY, 10)):                     # wet brick
            off = (row % 2) * 10
            for x in range(-20 + off, ARENA_W, 20):
                v = rnd.randint(-4, 4)
                A.fill((22 + v, 28 + v, 20 + v), (x + 1, y + 1, 18, 8))
        for i in range(6):                                              # the vaults: arches on thick piers
            x = i * 128 - 40
            pg.draw.rect(A, (10, 16, 10), (x + 30, 70, 68, GY - 70))
            pg.draw.circle(A, (10, 16, 10), (x + 64, 72), 34, draw_top_left=True, draw_top_right=True)
            pg.draw.arc(A, (40, 52, 34), (x + 28, 36, 72, 74), 0, math.pi, 3)
            pg.draw.rect(A, (30, 40, 26), (x + 4, 36, 22, GY - 36))
            pg.draw.line(A, (48, 60, 40), (x + 8, 40), (x + 8, GY))
        for i in range(30):                                             # slime streaks
            x = rnd.randint(10, ARENA_W - 10)
            y0 = rnd.randint(20, 100)
            pg.draw.line(A, (50, 90, 30), (x, y0), (x, y0 + rnd.randint(20, 90)), rnd.choice((1, 1, 2)))
        A.fill((2, 6, 2), (0, 0, ARENA_W, 22))
        for x in (150, 260, 380, 490):                                  # the drains (Game.SLUDGE_X)
            pg.draw.rect(A, (60, 44, 30), (x - 12, 18, 24, 16))
            pg.draw.rect(A, (100, 74, 46), (x - 12, 18, 24, 16), 1)
            pg.draw.ellipse(A, (6, 10, 4), (x - 8, 28, 16, 8))
        img = F_JPB.render("毒", False, (60, 120, 40))
        img = pg.transform.scale_by(img, 2)
        A.blit(img, (ARENA_W // 2 - img.get_width() // 2, 96))
        water = pg.Surface((ARENA_W, 30), pg.SRCALPHA)                  # toxic water line along the floor
        for y in range(30):
            water.fill((60, 140, 40, int(80 * y / 30)), (0, y, ARENA_W, 1))
        A.blit(water, (0, GY - 30))
        pg.draw.rect(A, (2, 4, 2), (0, 0, 10, GY))
        pg.draw.rect(A, (2, 4, 2), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_foundry():
        """SHOGUN'S FOUNDRY: riveted iron walls, a furnace mouth behind the fight, gears, chains, cooling blades on racks."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (10, 6, 6)), (GY, (46, 18, 8))])
        rnd = random.Random(11)
        for y in range(18, GY, 30):                                    # iron plates with rivets
            for x in range(0, ARENA_W, 48):
                v = rnd.randint(-4, 5)
                A.fill((30 + v, 18 + v, 14 + v), (x + 1, y + 1, 46, 28))
                for rx, ry in ((4, 4), (42, 4), (4, 24), (42, 24)):
                    A.fill((70, 44, 30), (x + rx, y + ry, 2, 2))
        A.fill((6, 3, 3), (0, 0, ARENA_W, 18))
        cx = ARENA_W // 2                                              # the furnace mouth (its fire is drawn live)
        pg.draw.rect(A, (20, 10, 8), (cx - 70, 40, 140, GY - 40))
        pg.draw.circle(A, (20, 10, 8), (cx, 60), 70, draw_top_left=True, draw_top_right=True)
        pg.draw.rect(A, (6, 2, 2), (cx - 52, 70, 104, GY - 70))
        pg.draw.circle(A, (6, 2, 2), (cx, 80), 52, draw_top_left=True, draw_top_right=True)
        for gx in range(cx - 48, cx + 50, 12):                         # the grill
            pg.draw.line(A, (40, 22, 16), (gx, 40), (gx, GY - 20), 2)
        for gx, gy, r in ((110, 70, 34), (ARENA_W - 120, 92, 26), (200, 150, 18)):   # gears
            pg.draw.circle(A, (36, 22, 18), (gx, gy), r)
            for i in range(10):
                a = i * math.tau / 10
                pg.draw.line(A, (36, 22, 18), (gx, gy), (gx + math.cos(a) * (r + 6), gy + math.sin(a) * (r + 6)), 5)
            pg.draw.circle(A, (14, 8, 6), (gx, gy), r // 3)
        for x in (60, 250, 390, 580):                                  # chains
            for y in range(18, 18 + rnd.randint(40, 90), 5):
                pg.draw.ellipse(A, (60, 44, 36), (x - 2, y, 4, 6), 1)
        for rx in (150, ARENA_W - 180):                                # racks of blades cooling
            pg.draw.line(A, (60, 36, 26), (rx, GY - 60), (rx + 40, GY - 60), 2)
            for i in range(5):
                pg.draw.line(A, (130, 120, 120), (rx + 4 + i * 8, GY - 58), (rx + 2 + i * 8, GY - 20), 1)
        img = pg.transform.scale_by(F_JPB.render("鋳", False, (90, 30, 10)), 2)
        A.blit(img, (cx - img.get_width() // 2, 108))
        pg.draw.rect(A, (3, 1, 2), (0, 0, 10, GY))
        pg.draw.rect(A, (3, 1, 2), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_drydock():
        """FLOODED DRYDOCK: stained concrete, pipes and valves, the ribs of a half-built hull, hazard stripes."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (4, 10, 12)), (GY, (14, 34, 30))])
        rnd = random.Random(13)
        for row, y in enumerate(range(18, GY, 20)):                    # concrete blocks
            off = (row % 2) * 20
            for x in range(-40 + off, ARENA_W, 40):
                v = rnd.randint(-3, 4)
                A.fill((18 + v, 30 + v, 30 + v), (x + 1, y + 1, 38, 18))
        stain = pg.Surface((ARENA_W, 70), pg.SRCALPHA)                 # the old waterline
        for y in range(70):
            stain.fill((40, 120, 60, int(70 * y / 70)), (0, y, ARENA_W, 1))
        A.blit(stain, (0, GY - 70))
        A.fill((2, 6, 6), (0, 0, ARENA_W, 18))
        for i in range(7):                                             # the hull's ribs behind the fight
            x = 150 + i * 56
            pg.draw.arc(A, (30, 50, 50), (x - 30, 40, 60, 200), math.pi * .5, math.pi * 1.5, 4)
            pg.draw.arc(A, (30, 50, 50), (x - 30 + 26, 40, 60, 200), math.pi * 1.5, math.pi * 2.5, 4)
        pg.draw.line(A, (30, 50, 50), (150, 46), (150 + 6 * 56 + 26, 46), 4)
        for y, col in ((34, (50, 70, 64)), (60, (60, 50, 40))):         # pipes and valves
            pg.draw.line(A, col, (10, y), (ARENA_W - 10, y), 6)
            for x in range(60, ARENA_W, 140):
                pg.draw.rect(A, tuple(c + 20 for c in col), (x - 4, y - 5, 8, 10))
                pg.draw.circle(A, (140, 40, 30), (x, y - 9), 4, 1)
        for x in range(0, ARENA_W, 16):                                # hazard stripes along the floor
            pg.draw.polygon(A, (200, 170, 40), [(x, GY - 8), (x + 8, GY - 8), (x + 4, GY - 2), (x - 4, GY - 2)])
        img = F_JPB.render("乾ドック", False, (60, 120, 90))
        A.blit(img, (ARENA_W // 2 - img.get_width() // 2, 100))
        pg.draw.rect(A, (2, 4, 4), (0, 0, 10, GY))
        pg.draw.rect(A, (2, 4, 4), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_throne():
        """TENSHU THRONE: gold folding screens with clouds, red lacquer pillars, the Shogun's crest above an empty seat."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (14, 6, 8)), (GY, (60, 20, 16))])
        rnd = random.Random(17)
        A.fill((8, 3, 4), (0, 0, ARENA_W, 22))
        for x in range(0, ARENA_W, 32):                                # ceiling beams
            pg.draw.line(A, (40, 14, 12), (x, 0), (x, 22), 3)
        for i, x in enumerate(range(24, ARENA_W - 24, 46)):            # byobu screens: gold leaf, painted clouds
            h0 = 34
            gold = (150, 112, 40) if i % 2 else (170, 128, 46)
            pg.draw.rect(A, gold, (x, h0, 44, GY - h0 - 30))
            pg.draw.rect(A, (90, 40, 20), (x, h0, 44, GY - h0 - 30), 1)
            for _ in range(2):
                cx_, cy_ = x + rnd.randint(6, 38), rnd.randint(h0 + 20, GY - 70)
                for j in range(3):
                    pg.draw.ellipse(A, (200, 170, 90), (cx_ - 12 + j * 7, cy_ - 4 + (j % 2) * 3, 14, 7))
            if rnd.random() < .5:                                      # a pine branch across the gold
                bx_, by_ = x + 4, rnd.randint(h0 + 30, GY - 80)
                pg.draw.line(A, (50, 30, 20), (bx_, by_), (bx_ + 36, by_ - 10), 2)
                pg.draw.ellipse(A, (40, 70, 40), (bx_ + 20, by_ - 18, 22, 9))
        cx, cy = ARENA_W // 2, 86                                      # the crest: three circles in a ring
        pg.draw.circle(A, (30, 10, 10), (cx, cy), 46)
        pg.draw.circle(A, (210, 160, 60), (cx, cy), 46, 3)
        for i in range(3):
            a = -math.pi / 2 + i * math.tau / 3
            pg.draw.circle(A, (210, 160, 60), (cx + math.cos(a) * 18, cy + math.sin(a) * 18), 13, 2)
        pg.draw.rect(A, (90, 20, 20), (cx - 40, GY - 46, 80, 46))       # the empty seat on its dais
        pg.draw.rect(A, (150, 110, 40), (cx - 40, GY - 46, 80, 46), 1)
        pg.draw.rect(A, (40, 12, 12), (cx - 60, GY - 12, 120, 12))
        for px in (64, 200, ARENA_W - 200, ARENA_W - 64):              # red lacquer pillars
            pg.draw.rect(A, (120, 20, 20), (px - 9, 22, 18, GY - 22))
            pg.draw.line(A, (200, 60, 50), (px - 5, 24), (px - 5, GY))
            pg.draw.rect(A, (40, 12, 10), (px - 12, GY - 10, 24, 10))
        for x in range(0, ARENA_W, 40):                                # tatami edge
            pg.draw.rect(A, (60, 50, 26), (x, GY - 4, 38, 4))
        pg.draw.rect(A, (3, 1, 2), (0, 0, 10, GY))
        pg.draw.rect(A, (3, 1, 2), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    @staticmethod
    def bake_hall():
        """The stone hall under the street, drawn once: brick walls, pillars, the Shogun's crest, banners, chains."""
        A = pg.Surface((ARENA_W, H))
        vgrad(A, [(0, (8, 3, 12)), (GY, (34, 10, 24))])
        rnd = random.Random(7)
        for row, y in enumerate(range(18, GY, 12)):                   # brick courses
            off = (row % 2) * 12
            for x in range(-24 + off, ARENA_W, 24):
                v = rnd.randint(-5, 6)
                A.fill((26 + v, 9 + v // 2, 22 + v), (x + 1, y + 1, 22, 10))
        A.fill((5, 2, 8), (0, 0, ARENA_W, 18))                        # ceiling
        for x in range(0, ARENA_W, 9):
            pg.draw.polygon(A, (5, 2, 8), [(x, 17), (x + 9, 17), (x + 4, 17 + rnd.randint(2, 9))])
        cx, cy = ARENA_W // 2, 96                                      # the crest behind the fight
        for r, col, wd in ((62, (90, 12, 26), 4), (54, (40, 6, 16), 0), (48, (120, 16, 34), 2)):
            pg.draw.circle(A, col, (cx, cy), r, wd)
        img = pg.transform.scale_by(F_JPB.render("鬼", False, (110, 16, 32)), 3)
        A.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
        for bx, word in ((168, "将軍"), (ARENA_W - 168, "決闘")):        # hanging banners
            pg.draw.rect(A, (120, 16, 30), (bx - 15, 18, 30, 96))
            pg.draw.polygon(A, (120, 16, 30), [(bx - 15, 114), (bx, 104), (bx + 15, 114)])
            pg.draw.rect(A, (70, 8, 18), (bx - 15, 18, 30, 96), 1)
            for i, ch in enumerate(word):
                g = F_JPB.render(ch, False, (20, 4, 10))
                A.blit(g, (bx - g.get_width() // 2, 34 + i * 30))
        for px in (64, ARENA_W - 64):                                  # stone pillars
            pg.draw.rect(A, (40, 20, 34), (px - 17, 18, 34, GY - 18))
            pg.draw.rect(A, (60, 32, 50), (px - 21, 18, 42, 10))
            pg.draw.rect(A, (60, 32, 50), (px - 21, GY - 14, 42, 14))
            pg.draw.line(A, (84, 46, 66), (px - 12, 28), (px - 12, GY - 14))
            pg.draw.line(A, (22, 10, 18), (px + 12, 28), (px + 12, GY - 14))
        for x in (110, 240, 400, 530):                                 # chains from the ceiling
            for y in range(18, 18 + rnd.randint(30, 70), 5):
                pg.draw.ellipse(A, (50, 40, 50), (x - 2, y, 4, 6), 1)
        pg.draw.rect(A, (3, 1, 5), (0, 0, 10, GY))                      # side walls
        pg.draw.rect(A, (3, 1, 5), (ARENA_W - 10, 0, 10, GY))
        return A.convert()

    def draw_arena_bg(s, cx, oy):
        scr.blit(s.arena_bg, (-cx, oy))
        kind, b = s.boss_kind, s.boss
        rage = b is not None and not b.dead and b.bphase >= 2
        if kind == 'boss_destroyer':                                   # tesla coils crackling, arcs jumping between them
            for i, cx_ in enumerate((ARENA_W * .25, ARENA_W * .75)):
                x = cx_ - cx
                glow(scr, x, 54 + oy, 34, qcol((20, 80, 130), .7 + .3 * math.sin(s.t * 9 + i)))
                if random.random() < (.5 if rage else .3):
                    for _ in range(2):
                        pts, a = [(x, 54 + oy)], R(0, math.tau)
                        for j in range(5):
                            pts.append((pts[-1][0] + math.cos(a) * 7 + R(-3, 3), pts[-1][1] + math.sin(a) * 5 + R(-3, 3)))
                        pg.draw.lines(scr, random.choice(((160, 230, 255), (255, 255, 255))), False, pts, 1)
            if random.random() < (.06 if rage else .02):              # a big arc across the hall
                pts, x0, x1 = [], ARENA_W * .25 - cx, ARENA_W * .75 - cx
                for j in range(17):
                    pts.append((lerp(x0, x1, j / 16), 54 + oy + math.sin(j / 16 * math.pi) * -14 + R(-6, 6)))
                pg.draw.lines(scr, (220, 245, 255), False, pts, 2)
                s.pflash = max(getattr(s, 'pflash', 0), .03)
                sfx('crack')
            for i, bx in enumerate((120, 250, 390, 520)):              # status lamps on the transformers
                on = int(s.t * 3 + i * 1.3) % 3 != 0
                col = ((255, 80, 60) if rage else (80, 255, 200)) if on else (20, 40, 40)
                scr.fill(col, (bx - cx + 20, GY - 82 + oy, 3, 3))
        elif kind == 'boss_mutant':                                    # drips from the drains, a slow green mist
            for i, x in enumerate((150, 260, 380, 490)):
                ph = (s.t * .9 + i * .37) % 1
                pg.draw.circle(scr, (150, 255, 90), (int(x - cx), int(34 + ph * (GY - 34) + oy)), 1)
                if int(s.t * 2 + i) % 3 == 0:
                    glow(scr, x - cx, 30 + oy, 12, (30, 70, 15) if not rage else (90, 40, 10))
            for i in range(4):
                x = (i * 190 + s.t * 12) % (ARENA_W + 160) - 80
                glow(scr, x - cx, GY - 18 + oy, 60, (14, 34, 10), .4)
        elif kind == 'boss_shogun':                                    # paper lanterns swaying on cords
            for i, lx in enumerate((130, 270, 370, 510)):
                sw = math.sin(s.t * 1.4 + i) * 3
                x = lx - cx + sw
                pg.draw.line(scr, (30, 10, 10), (lx - cx, 22 + oy), (x, 50 + oy))
                pg.draw.ellipse(scr, (220, 60, 40) if not (rage and b.bphase >= 3) else (150, 60, 220), (x - 6, 50 + oy, 12, 16))
                scr.fill((255, 210, 140), (x - 2, 54 + oy, 4, 8))
                glow(scr, x, 58 + oy, 22, (90, 40, 14))
            if rage:                                                   # the crest glows with his rage
                col = (100, 30, 160) if b.bphase >= 3 else (130, 70, 10)
                glow(scr, ARENA_W // 2 - cx, 86 + oy, 60, qcol(col, .5 + .3 * math.sin(s.t * 6)))
        else:
            for px in (64, ARENA_W - 64):                              # braziers flickering at the pillar feet
                x = px - cx
                f = .75 + .25 * math.sin(s.t * 13 + px) * math.sin(s.t * 7)
                glow(scr, x, GY - 22 + oy, int(34 * f), (110, 50, 16))
                pg.draw.polygon(scr, (255, 170, 60), [(x - 5, GY - 16 + oy), (x, GY - 30 - 5 * f + oy), (x + 5, GY - 16 + oy)])
            if rage:                                                   # the crest burns red when it is enraged
                glow(scr, ARENA_W // 2 - cx, 96 + oy, 70, qcol((120, 10, 20), .5 + .3 * math.sin(s.t * 6)))
        x = 96 - cx                                                    # the broken ceiling you fell through, light pouring in
        pg.draw.polygon(scr, (2, 2, 6), [(x - 30, oy), (x + 30, oy), (x + 22, 14 + oy), (x + 10, 22 + oy), (x - 4, 18 + oy),
                                         (x - 18, 24 + oy), (x - 26, 12 + oy)])
        glow(scr, x, 60 + oy, 60, qcol((40, 60, 100), .6 + .15 * math.sin(s.t * 2)), .6)
        if random.random() < .05:
            s.parts.append([96 + R(-14, 14), 20, R(-5, 5), R(20, 60), 1.2, 1.2, (90, 90, 110), 1.5, 300, False])
        x = ARENA_W - 14 - cx                                          # the way out: a red gate in the right wall
        k = ease(min(1, s.arena_t)) if s.arena_open else 0
        pg.draw.rect(scr, (8, 2, 6), (x - 26, GY - 70 + oy, 40, 70))
        for i in range(5):
            bx = x - 22 + i * 8
            pg.draw.line(scr, (190, 30, 50), (bx, GY - 66 + oy), (bx, GY - 66 + oy + 66 * (1 - k)), 2)
        sil_poly(scr, [(x - 32, GY - 74 + oy), (x + 20, GY - 74 + oy), (x + 22, GY - 80 + oy), (x - 34, GY - 80 + oy)], (40, 6, 14), (255, 100, 110))
        if s.arena_open:
            glow(scr, x - 6, GY - 36 + oy, 40, (90, 30, 40))
            if int(s.t * 3) % 2:
                outlined("出口  >>", F_JP, (255, 160, 170), x - 8, GY - 98 + oy, center=True, r=1)

    def draw_sensei_room(s, cx, oy):
        """The chair in the middle, the pupils standing at the back, the dark and the spotlights."""
        ss, b = getattr(s, 'sensei', None), s.boss
        if ss is None or b is None:
            return
        gy = GY + oy
        lit = ss['lit']
        if lit < 1:                                                    # the dark room
            dark = pg.Surface((W, H), pg.SRCALPHA)
            dark.fill((0, 0, 4, int(200 * (1 - lit) + 40)))
            scr.blit(dark, (0, 0))
        if lit > 0:                                                    # spotlights from the ceiling
            beam = pg.Surface((W, H), pg.SRCALPHA)
            for bx in (ARENA_W / 2, 96, ARENA_W - 96):
                xx = bx - cx
                pg.draw.polygon(beam, (255, 240, 200, int(34 * lit)), [(xx - 6, oy + 18), (xx + 6, oy + 18), (xx + 46, gy), (xx - 46, gy)])
            scr.blit(beam, (0, 0))
        x = ARENA_W / 2 - cx
        gy = GY + oy
        col, rim = (70, 46, 30), (140, 100, 60)
        for lx in (-14, 12):                                           # the high wooden chair
            pg.draw.rect(scr, col, (x + lx, gy - CHAIR_H, 4, CHAIR_H))
        pg.draw.rect(scr, col, (x - 18, gy - CHAIR_H - 2, 36, 5))
        pg.draw.line(scr, rim, (x - 18, gy - CHAIR_H - 2), (x + 18, gy - CHAIR_H - 2))
        pg.draw.rect(scr, col, (x - 16, gy - CHAIR_H - 40, 4, 40))
        pg.draw.rect(scr, col, (x + 12, gy - CHAIR_H - 40, 4, 40))
        pg.draw.rect(scr, col, (x - 16, gy - CHAIR_H - 42, 32, 5))
        pg.draw.line(scr, col, (x - 14, gy - 22), (x + 14, gy - 22), 2)
        for i, (fx, kind, here) in enumerate(ss['bg']):                # the pupils waiting at the back, in the shadows
            if here:
                S = PAL_BACK[kind]
                s.draw_char(fx, GY - 4, 1 if fx < ARENA_W / 2 else -1, pose_idle(s.t + i), S, None, cx, oy)

    def draw_arena_ledges(s, cx, oy):
        if s.boss_kind == 'boss_sensei':
            s.draw_sensei_room(cx, oy)
        body, top, hang = {'boss_destroyer': ((24, 36, 54), (110, 210, 255), (50, 60, 80)),    # insulated catwalks
                           'boss_mutant': ((40, 34, 24), (150, 230, 90), (60, 50, 34)),        # rusted grates on chains
                           'boss_shogun': ((70, 20, 16), (220, 170, 70), (40, 14, 12))       # lacquered balconies
                           }.get(s.boss_kind, ((44, 24, 36), (120, 70, 90), (50, 40, 50)))
        for p in s.plats[1:]:
            x, y = p.x - cx, p.y + oy
            for ch in (x + 6, x + p.w - 6):                           # hung from the ceiling
                pg.draw.line(scr, hang, (ch, oy + 18), (ch, y), 1)
            pg.draw.rect(scr, body, (x, y, p.w, 9))
            pg.draw.line(scr, top, (x, y), (x + p.w, y))
            pg.draw.line(scr, (10, 6, 8), (x, y + 9), (x + p.w, y + 9))

    HOLE_RIM = [(-60, 0), (-55, -9), (-50, -4), (-46, -20), (-41, -7), (-37, -27), (-33, -12), (-29, 0)]   # left rim rocks

    def draw_temple_door(s, x, gy, h):
        """Kirigamine and Tenshin Dojo: a whole gate with two wooden doors, chained until half are cut down, then they
        swing open on a dark hall - and a line over it."""
        dojo = s.theme.get('env') == 'dojo'
        post, rim = ((70, 44, 28), (200, 150, 100)) if dojo else ((150, 24, 30), (255, 130, 120))
        roof = (40, 26, 22) if dojo else (40, 44, 60)
        k = ease(h['k'])
        pg.draw.rect(scr, (6, 4, 8), (x - 30, gy - 72, 60, 72))                      # the dark hall behind
        if h['open']:
            glow(scr, x, gy - 30, 40, qcol((90, 30, 30) if not dojo else (100, 60, 20), .5 + .2 * math.sin(s.t * 3)))
        for sg in (-1, 1):                                                          # two doors, swinging inward
            w_ = 30 * (1 - .8 * k)
            dx0 = x + 30 - w_ if sg > 0 else x - 30
            pg.draw.rect(scr, (110, 70, 40) if dojo else (120, 20, 26), (dx0, gy - 70, w_, 70))
            for ly in range(int(gy - 64), int(gy - 4), 12):
                pg.draw.line(scr, (50, 30, 18) if dojo else (60, 8, 12), (dx0 + 1, ly), (dx0 + w_ - 1, ly))
            if w_ > 6:
                pg.draw.circle(scr, (220, 190, 90), (int(dx0 + (3 if sg > 0 else w_ - 3)), int(gy - 34)), 2)
        for px in (x - 36, x + 30):                                                 # posts, lintel, a heavy roof
            sil_poly(scr, [(px, gy), (px + 6, gy), (px + 6, gy - 78), (px, gy - 78)], post, rim)
        pg.draw.rect(scr, roof, (x - 38, gy - 80, 76, 6))
        sil_poly(scr, [(x - 50, gy - 80), (x + 50, gy - 80), (x + 40, gy - 92), (x - 40, gy - 92)], roof, rim)
        if not dojo:                                                                # snow on the temple roof
            pg.draw.line(scr, (220, 230, 250), (x - 40, gy - 92), (x + 40, gy - 92), 2)
        pg.draw.rect(scr, (24, 14, 10), (x - 14, gy - 79, 28, 11))
        g = F_JP.render("道場" if dojo else "山門", False, (230, 190, 110))
        scr.blit(g, (x - g.get_width() // 2, gy - 80))
        if not h['open']:                                                           # chained shut
            chain(scr, (x - 30, gy - 64), (x + 30, gy - 8))
            chain(scr, (x + 30, gy - 64), (x - 30, gy - 8))
            padlock(scr, x, gy - 36)
        else:
            a = .6 + .4 * math.sin(s.t * 3)
            outlined(tr("HE IS WAITING FOR YOU"), F_PS, qcol((255, 220, 200), a), x, gy - 112, center=True, r=1)
            p = s.pl
            if h['k'] >= 1 and abs(p.x + p.w / 2 - CAVE_X) < 26 and p.g:
                s.prompt(tr("ENTER"), x, gy - 70)

    def draw_boss_gate(s, x, gy, h):
        """Over the hole: the red door from the start of the run, but wrecked (in Tenshin Dojo: a whole wooden gate in
        the dojo's style). Chained shut while the seal holds."""
        dojo = s.theme.get('env') == 'dojo'
        if dojo:                                                       # an intact dojo gate: dark wood, a tiled roof, a board
            wood, rim = (70, 44, 28), (200, 150, 100)
            for px in (x - 36, x + 30):
                sil_poly(scr, [(px, gy), (px + 6, gy), (px + 6, gy - 74), (px, gy - 74)], wood, rim)
            sil_poly(scr, [(x - 46, gy - 74), (x + 46, gy - 74), (x + 38, gy - 84), (x - 38, gy - 84)], (40, 26, 22), rim)
            pg.draw.rect(scr, (40, 26, 22), (x - 30, gy - 70, 60, 5))
            pg.draw.rect(scr, (24, 14, 10), (x - 12, gy - 68, 24, 12))
            g = F_JP.render("道場", False, (230, 190, 110))
            scr.blit(g, (x - g.get_width() // 2, gy - 69))
        else:                                                          # the red door, smashed: one post snapped, the roof fallen
            red, rim = (150, 20, 30), (255, 120, 120)
            sil_poly(scr, [(x - 36, gy), (x - 30, gy), (x - 30, gy - 70), (x - 36, gy - 70)], red, rim)
            sil_poly(scr, [(x + 30, gy), (x + 36, gy), (x + 36, gy - 38), (x + 33, gy - 44), (x + 31, gy - 36)], red, rim)
            sil_poly(scr, [(x - 44, gy - 74), (x - 30, gy - 78), (x + 40, gy - 30), (x + 34, gy - 24)], (60, 12, 18), rim)
            pg.draw.line(scr, (20, 4, 8), (x - 34, gy - 50), (x - 31, gy - 40))   # cracks in the standing post
            for i, (dx, dy, a) in enumerate(((-56, -4, 20), (46, -3, -35), (58, -2, 10))):   # pieces of the panels in the street
                pts = [(x + dx, gy + dy), (x + dx + 14, gy + dy - 2), (x + dx + 12, gy + dy + 2), (x + dx - 1, gy + dy + 3)]
                pg.draw.polygon(scr, (120, 18, 28), pts)
                pg.draw.line(scr, (60, 8, 12), pts[0], pts[1])
            pg.draw.lines(scr, (176, 24, 38), False, [(x - 28, gy - 66), (x - 24, gy - 40), (x - 27, gy - 30)], 2)   # a torn noren
        if not h['open']:                                              # sealed: chains across, a talisman
            chain(scr, (x - 30, gy - 64), (x + 30, gy - 6))
            chain(scr, (x + 30, gy - 64), (x - 30, gy - 6))
            pg.draw.rect(scr, (230, 220, 190), (x - 6, gy - 46, 12, 20))
            g = F_JP.render("封", False, (170, 20, 30))
            scr.blit(g, (x - g.get_width() // 2, gy - 44))

    def draw_hole_rim(s, cx, oy):
        """The rocks around the broken street, behind you: a low cracked bump while sealed, jagged once burst."""
        h = s.hole
        x, gy = CAVE_X - cx, GY + oy
        if x < -90 or x > W + 90:
            return
        if h.get('door'):
            s.draw_temple_door(x, gy, h)
            return
        s.draw_boss_gate(x, gy, h)
        k = .3 + .7 * ease(h['k'])
        for sg in (-1, 1):
            pts = [(x + sg * -px, gy + py * k) for px, py in s.HOLE_RIM] if sg > 0 else [(x + px, gy + py * k) for px, py in s.HOLE_RIM]
            pg.draw.polygon(scr, (40, 38, 54), pts)
            pg.draw.lines(scr, (100, 100, 128), False, pts[:-1], 1)
        if h['open']:
            glow(scr, x, gy - 10, 46, qcol((20, 70, 130), .55 + .2 * math.sin(s.t * 4)), .7)
            p = s.pl
            if h['k'] >= 1 and not h.get('in') and abs(p.x + p.w / 2 - CAVE_X) < 24 and p.g:
                s.prompt(tr("ENTER"), x, gy - 70)

    def draw_hole_pit(s, cx, oy, gys):
        """The hole itself, cut into the street: a jagged shaft with blue light far below, or the glowing stone seal."""
        h = s.hole
        if h.get('door'):
            return
        x = CAVE_X - cx
        if x < -90 or x > W + 90:
            return
        for sg in (-1, 1):                                             # cracks running out through the asphalt
            for i, (dx, dy) in enumerate(((34, 3), (52, 6), (44, 10))):
                pg.draw.lines(scr, (10, 8, 16), False, [(x + sg * 26, gys + 1), (x + sg * (26 + dx * .5), gys + dy * .6),
                                                        (x + sg * (26 + dx), gys + dy)], 1)
        hw = HOLE_W // 2
        shaft = [(x - hw, gys), (x + hw, gys), (x + hw - 6, gys + 10), (x + hw - 2, gys + 24), (x + hw - 10, H),
                 (x - hw + 8, H), (x - hw + 2, gys + 22), (x - hw + 7, gys + 9)]
        pg.draw.polygon(scr, (3, 2, 8), shaft)
        pg.draw.lines(scr, (60, 64, 90), False, shaft[1:5], 1)
        pg.draw.lines(scr, (60, 64, 90), False, shaft[5:] + shaft[:1], 1)
        pulse = .5 + .5 * math.sin(s.t * 3)
        if h['open']:
            glow(scr, x, H - 2, 50, qcol((40, 120, 210), .6 + .3 * pulse), .6)
            glow(scr, x, gys + 8, 26, qcol((30, 100, 180), .5 + .3 * pulse), .5)
            return
        pg.draw.rect(scr, (66, 70, 90), (x - hw, gys - 2, HOLE_W, 6))   # the sealed lid: a stone slab, a blue shinobi seal
        pg.draw.line(scr, (130, 136, 160), (x - hw, gys - 2), (x + hw, gys - 2))
        glow(scr, x, gys + 1, 34, qcol((30, 110, 190), .5 + .4 * pulse), .4)
        pg.draw.line(scr, qcol((120, 220, 255), .5 + .5 * pulse), (x - hw, gys - 2), (x + hw, gys - 2))
        pts = [(x - 9, gys - 1), (x + 9, gys - 1), (x + 7, gys + 2), (x, gys + 3), (x - 7, gys + 2)]
        pg.draw.polygon(scr, qcol((100, 210, 255), .5 + .4 * pulse), pts, 1)

    def draw_seal(s, cx, oy):
        """The sealed red gate of a boss district: chains crossed over it and a paper talisman."""
        x, gy = END_X - cx, GY + oy
        if x < -60 or x > W + 60:
            return
        for a, b in (((x - 24, gy - 70), (x + 22, gy)), ((x + 22, gy - 70), (x - 24, gy))):
            n = 9
            for i in range(n):
                px, py = lerp(a[0], b[0], i / (n - 1)), lerp(a[1], b[1], i / (n - 1))
                pg.draw.ellipse(scr, (130, 120, 140), (px - 3, py - 2, 6, 5), 1)
        pg.draw.rect(scr, (230, 220, 190), (x - 6, gy - 46, 12, 22))
        g = F_JP.render("封", False, (170, 20, 30))
        scr.blit(g, (x - g.get_width() // 2, gy - 44))
        glow(scr, x, gy - 35, 18, qcol((120, 20, 30), .5 + .3 * math.sin(s.t * 5)))

    def upd_enemy(s, e, dt):
        if e.kind.startswith('boss'):
            return s.upd_boss(e, dt)
        p = s.pl
        for a in ('hurt', 'cd', 'alert', 'throwT', 'navcd', 'flash', 'dodgecd', 'blinkcd'):
            setattr(e, a, getattr(e, a) - dt)
        if e.kind == 'onryo':
            return s.upd_onryo(e, dt)
        if getattr(e, 'warpin', 0) > 0:                                # (blinking in: still for a moment, then he rushes you)
            e.warpin -= dt
            e.vx = 0
            if e.warpin <= 0:
                e.face = 1 if p.x > e.x else -1
                e.vx = e.face * 200
                s.puff(e.x + e.w / 2, e.y + e.h, 5, dirx=-e.face)
            return
        if e.trav:
            s.enemy_traverse(e, dt)
            return
        if s.cloaked(e) and e.st != 'calm' and e.hurt <= 0:        # SHADOW CLOAK: they lose you at once
            e.st, e.t, e.locked, e.vx, e.say = 'calm', R(1, 3), False, 0, None
        if s.cloaked(e):                                           # ...but they feel something when you pass close
            e.sense = max(0.0, getattr(e, 'sense', 0.0) - dt)
            pdx = (p.x + p.w / 2) - (e.x + e.w / 2)
            if abs(pdx) < 34 and abs((p.y + p.h) - (e.y + e.h)) < 30 and e.sense <= .3:
                if e.sense <= 0:
                    e.face = -e.face                               # a look over the shoulder
                e.sense = 1.1
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
        elif e.st in ('calm', 'notice') and getattr(e, 'locked', False) and not p.dead:
            e.st, e.alert = 'chase', .3
        elif e.st == 'calm':
            s.enemy_calm(e, dt, dx, dist, dy)
        elif e.st == 'notice':                                     # "?!" - a beat of surprise, then they draw
            e.vx = 0
            e.t -= dt
            if e.t <= 0:
                e.st, e.alert = 'chase', .6
                sfx('unsheathe')
        elif e.st == 'patrol' and getattr(e, 'locked', False) and not p.dead:   # (locked on: straight back to the fight)
            e.st, e.alert = 'chase', .3
        elif e.st == 'patrol':
            e.vx = e.face * 35 * e.spd
            e.t -= dt
            if e.t < 0:
                e.face, e.t = -e.face, R(1.5, 3.5)
            if s.hole and not s.arena and e.face > 0 and e.x > CAVE_X - 130:   # (a patrol turns back before the way down)
                e.face, e.t = -1, R(1.5, 3.5)
            if not p.dead and (dist < 190 and dy < 55 and (dx > 0) == (e.face > 0) or dist < 60 and dy < 30):
                e.st, e.alert = 'chase', .6
        elif e.st == 'chase':
            e.wound = False
            if dist > 10 or dy > 30:                                   # (no flip-flopping while standing right under / over you)
                if dist > 10:
                    e.face = 1 if dx > 0 else -1
            holders = sum(1 for o in s.en if o is not e and not o.dead and not o.trav and o.st in ('wind', 'slash', 'smash')
                          and abs(o.x - p.x) < 250)
            cap = 1 if s.lvl <= 2 else (2 if s.lvl < 10 else 3)        # attack tokens: how many may swing at you at once
            busy = 2 if (holders >= cap or getattr(s, 'tok_cool', 0) > 0) else 0   # (and never two on the same beat)
            if p.dash > 0 and dist < 110 and e.dodgecd <= 0 and random.random() < .4:   # you dash at them: they step back
                e.st, e.t, e.vx, e.dodgecd = 'back', .24, -e.face * 160 * e.spd, 1.6
            if p.parry > 0 and e.cd <= 0 and dist < e.reach + 20 and random.random() < .55:   # your guard is up: they wait it out
                e.cd = R(.25, .45)
            if p.acd > 0 and p.atk <= 0 and dist < e.reach + 20:        # you swung at nothing: they punish it
                e.cd = min(e.cd, .1)
            other_level = dy > 34
            if other_level and e.kind not in ('ninja', 'teppo'):       # you're on another level: wait at a distance, don't pace under you
                want = 70 * e.pref
                e.vx = (-e.face * 60 if dist < want - 10 else (e.face * 70 if dist > want + 40 else 0)) * e.spd
            elif e.kind == 'ninja':
                e.vx = (-e.face * 90 if dist < 80 else (e.face * 95 if dist > 160 else 0)) * e.spd
                if dist < 56 and dy < 40 and e.blinkcd <= 0:            # too close: smoke bomb, blinks away
                    s.enemy_blink(e)
                elif e.cd <= 0 and dy < 70 and dist < 240:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
            elif e.kind == 'kunoichi':                                 # circles at dash range, then cuts through
                e.vx = (-e.face * 70 if dist < 80 else (e.face * 110 if dist > e.reach - 12 else 0)) * e.spd
                if e.cd <= 0 and dist < e.reach and dy < 28 and busy < 2:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
            elif e.kind == 'yari':                                     # keeps you at the tip of his spear
                e.vx = (e.face * 80 if dist > e.reach - 6 else (-e.face * 60 if dist < 34 else 0)) * e.spd
                if dist < e.reach and dy < 28 and e.cd <= 0 and busy < 2:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
            elif e.kind == 'teppo':                                    # keeps his distance, then takes aim
                e.vx = (-e.face * 70 if dist < 130 else (e.face * 80 if dist > 240 else 0)) * e.spd
                if e.cd <= 0 and dist < e.reach and dy < 80 and busy < 2:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
                    e.aimx, e.aimy = p.x + p.w / 2, p.y + p.h * .45
            else:
                close = (e.w + p.w) / 2 + 4                            # never walk into the samurai's body
                if busy >= 2 and dist < e.reach + 44:                  # wait for a gap, sidestepping at the edge of reach
                    e.vx = (-e.face * 45 if dist < e.reach + 18 else 0) * e.spd
                elif e.cd > 0 and dist < e.reach + 30:                 # between swings: footsie at the edge of reach
                    ring = e.reach * e.pref + 6
                    sway = math.sin(s.t * 3.2 + e.rhythm)
                    e.vx = (-e.face * 70 if dist < ring - 8 else (e.face * 55 if dist > ring + 14 else e.face * 40 * sway)) * e.spd
                elif dist > close:
                    e.vx = e.face * (88 if dist > 90 else 70) * e.spd
                else:
                    e.vx = 0
                if dist < e.reach and dy < 28 and e.cd <= 0 and busy < 2:
                    e.st, e.t, e.vx = 'wind', e.wind, 0
                    e.atk2 = ('smash' if e.kind == 'oni' and e.tier >= 1 and e.plat is not None and e.plat.ground
                              and random.random() < .4 else None)
            if (e.kind in ('ronin', 'yari', 'kunoichi', 'teppo', 'sohei') and e.st == 'chase' and p.atk > p.atkT * .75 and dist < 72
                    and dy < 30 and e.dodgecd <= 0):                   # sees your swing coming: may hop out of it
                if random.random() < .25 + .15 * e.tier:
                    e.st, e.t, e.vx = 'back', .28, -e.face * 170 * e.spd
                    s.puff(e.x + e.w / 2, e.y + e.h, 3, -e.face)
                e.dodgecd = 2.2
            if (dist > 340 or dy > 280 or p.dead) and not (getattr(e, 'locked', False) and not p.dead):
                e.st, e.navx = 'patrol', None
        elif e.st == 'back':                                           # hop back out of reach
            e.wound = False
            e.t -= dt
            e.vx *= .9
            if e.t <= 0:
                e.st = 'chase'
        elif e.st == 'smash':                                          # oni: club into the ground, shockwaves both ways
            e.vx = 0
            was = e.t
            e.t -= dt
            if was > .18 >= e.t:
                s.shake = max(s.shake, 6)
                s.puff(e.x + e.w / 2 + e.face * 14, e.y + e.h, 8)
                sfx('slam')
                for d in (-1, 1):
                    s.bossw.append([e.x + e.w / 2 + d * 10, GY, d, 0.0, False, 170, (255, 140, 80)])
                hb = (e.x - 20, e.y, e.w + 40, e.h)
                if ov(hb, p.rect()):
                    s.hurt_player(e.face, e.dmg)
            if e.t <= 0:
                e.st, e.cd = 'chase', 1.4 * (1 - .15 * e.tier)
        elif e.st == 'stun':                                           # reeling after being parried
            e.vx *= .8
            e.t -= dt
            if e.t <= 0:
                e.st, e.cd = 'chase', .5
        elif e.st == 'wind':
            e.vx = 0
            if not getattr(e, 'wound', False):                         # just started: take a token, vary the rhythm, maybe a feint
                e.wound = True
                s.tok_cool = R(.25, .5)
                if e.kind in ('ronin', 'yari', 'sohei', 'oni') and e.combo == 0:
                    e.t = e.wind * R(.8, 1.35)
                    e.feint = random.random() < .12 + .05 * e.tier
            if getattr(e, 'feint', False) and e.t < e.wind * .45:      # a feint: the cut never comes, he hops back
                e.feint, e.wound = False, False
                e.st, e.t, e.vx, e.cd = 'back', .26, -e.face * 150 * e.spd, .35
                s.puff(e.x + e.w / 2, e.y + e.h, 3, -e.face)
            e.t -= dt
            if e.kind == 'teppo':
                e.face = 1 if dx > 0 else -1
                if e.t > .3:                                           # tracks you; locks on for the last moment
                    e.aimx, e.aimy = p.x + p.w / 2, p.y + p.h * .45
            if e.t <= 0:
                if e.kind == 'teppo':                                  # one shot down the line - parry it back
                    sx, sy = e.x + e.w / 2 + e.face * 16, e.y + e.h * .38
                    a = math.atan2(e.aimy - sy, e.aimx - sx)
                    s.proj.append([sx, sy, math.cos(a) * 430, math.sin(a) * 430, False, 1.6, 'bullet'])
                    s.puff(sx + e.face * 4, sy, 4, e.face, col=(200, 190, 180))
                    s.burst(sx, sy, 6, (255, 200, 120), spd=90, glowing=True, grav=0, dirx=e.face)
                    s.shake = max(s.shake, 2)
                    sfx('crack')
                    e.st, e.cd, e.throwT = 'chase', R(2.0, 2.8), .25
                elif e.kind == 'ninja':
                    tx, ty = p.x + p.w / 2, p.y + p.h / 2
                    sx, sy = e.x + e.w / 2, e.y + 8
                    base = math.atan2(ty - sy, tx - sx)
                    n = 3 if e.tier >= 1 else 1                         # later districts: a fan of three
                    for i in range(n):
                        a = base + (i - (n - 1) / 2) * .16
                        s.proj.append([sx, sy, math.cos(a) * 210, math.sin(a) * 210, False, 3.0])
                    e.st, e.cd, e.throwT = 'chase', R(1.3, 2.1) * (1 - .15 * e.tier), .25
                    sfx('throw')
                elif e.atk2 == 'smash':
                    e.st, e.t, e.atk2 = 'smash', .6, None
                    sfx('eslash')
                elif e.kind == 'kunoichi':                              # dash-cut straight through you
                    e.st, e.t, e.vx, e.hit = 'slash', .3, e.face * 380 * e.spd, False
                    sfx('dash')
                elif e.kind == 'sohei':                                 # the whirlwind: live on both sides for half a second
                    e.st, e.t, e.vx, e.hit = 'slash', .5, e.face * 50, False
                    sfx('bwave')
                else:
                    lunge = {'oni': 120, 'yari': 90, 'tate': 210}.get(e.kind, 160)
                    e.st, e.t, e.vx, e.hit = 'slash', .22 if e.kind in ('yari', 'tate') else .18, e.face * lunge, False
                    sfx('eslash')
        elif e.st == 'slash':
            e.t -= dt
            e.vx *= .97 if e.kind == 'kunoichi' else .85
            if not e.hit:
                if e.kind == 'kunoichi':                                # her blade is live for the whole dash
                    hb = (e.x - 4, e.y, e.w + 8, e.h)
                elif e.kind == 'sohei':
                    hb = (e.x - e.reach, e.y - 6, e.w + 2 * e.reach, e.h + 6)
                    if random.random() < .5:
                        s.burst(e.x + e.w / 2 + R(-e.reach, e.reach), e.y + e.h * .4, 1, (230, 230, 255), spd=30, grav=0)
                else:
                    hb = (e.x + e.w if e.face > 0 else e.x - e.reach, e.y - 6, e.reach, e.h + 6)
                if ov(hb, p.rect()) and p.parry > 0:
                    e.hit = True
                    s.parried(e)
                elif ov(hb, p.rect()):
                    e.hit = True
                    s.hurt_player(e.face, e.dmg)
                    if e.kind in ('oni', 'tate') and p.inv > .9:      # heavy blows throw you back
                        p.vx, p.vy = e.face * 260, -220
                elif e.kind not in ('kunoichi', 'sohei'):
                    e.hit = True
                if e.kind == 'kunoichi' and random.random() < .5:
                    s.burst(e.x + e.w / 2, e.y + e.h * .5, 1, (255, 120, 180), spd=20, glowing=True, grav=0)
            if e.t <= 0 and e.st == 'slash':
                cd = {'oni': 1.3, 'kunoichi': 1.4, 'tate': 1.5, 'sohei': 1.6}.get(e.kind, .9) * (1 - .1 * e.tier)
                if e.kind == 'ronin' and e.combo == 0 and random.random() < .5:   # a second cut (from the first district)
                    e.combo, e.st, e.t = 1, 'wind', .16
                else:
                    e.combo = 0
                    e.st, e.cd = 'chase', cd
                    if e.kind in ('ronin', 'yari') and random.random() < .45:   # step back out of reach
                        e.st, e.t, e.vx = 'back', .25, -e.face * 150 * e.spd
        if e.g and e.plat and (not e.plat.ground or s.hole):            # don't walk off rooftop edges (or into the hole)
            nx = e.x + e.vx * dt
            if nx < e.plat.x or nx + e.w > e.plat.x + e.plat.w:
                e.vx = 0
                if e.st == 'patrol':
                    e.face = -e.face
        e.phys(dt, s.plats)
        e.anim += abs(e.vx) * dt * .12
        if (not p.dead and p.dash <= 0 and e.st != 'slash' and not p.slam and abs((p.y + p.h) - (e.y + e.h)) < 12
                and not s.buff('invis') and ov(e.rect(), p.rect())):     # solid bodies: slide out of the samurai (cloaked: you pass through)
            side = -1 if dx > 0 else 1
            need = (e.w + p.w) / 2 + 1 - dist
            nx = e.x + side * min(need, 240 * dt + 1)
            if e.plat is None or e.plat.ground and not s.hole or e.plat.x <= nx <= e.plat.x + e.plat.w - e.w:
                e.x = max(0, min(LW - e.w, nx))

    def upd_onryo(s, e, dt):
        """The vengeful dead: drifts through roofs and walls toward you, shrieks, then lunges. Never touches the ground."""
        p = s.pl
        dx, dy = (p.x + p.w / 2) - (e.x + e.w / 2), (p.y + p.h * .4) - (e.y + e.h * .5)
        d = math.hypot(dx, dy) or 1.0
        e.g = False
        if s.buff('invis') and not s.arena and e.st != 'calm' and e.hurt <= 0:   # INVISIBILITY
            e.st = 'calm'
        if e.hurt > 0:
            e.x += e.kb * dt
            e.kb *= .85
        elif e.st == 'calm':                                       # drifting over the spot where it died
            e.y += math.sin(s.t * 2 + e.anim) * 6 * dt
            if not p.dead and d < 170 and not (s.buff('invis') and not s.arena):
                e.st, e.t = 'notice', .45
        elif e.st == 'notice':
            e.t -= dt
            if e.t <= 0:
                e.st, e.alert = 'chase', .6
                sfx('glint')
        elif p.dead:
            e.st = 'calm'
        elif e.st == 'wind':                                       # the shriek: draws back, aims
            e.t -= dt
            e.x -= e.face * 12 * dt
            if e.t > .2:
                e.lx, e.ly = dx / d, dy / d
            if e.t <= 0:
                e.st, e.t, e.hit = 'slash', .42, False
                sfx('dash')
        elif e.st == 'slash':                                      # the lunge, straight through the air
            e.t -= dt
            e.x += e.lx * 300 * e.spd * dt
            e.y += e.ly * 300 * e.spd * dt
            if not e.hit and ov(e.rect(), p.rect()):
                e.hit = True
                if p.parry > 0:
                    s.parried(e)
                else:
                    s.hurt_player(e.face, e.dmg)
            if random.random() < .6:
                s.burst(e.x + e.w / 2, e.y + e.h / 2, 1, (180, 230, 255), spd=20, glowing=True, grav=0)
            if e.t <= 0 and e.st == 'slash':
                e.st, e.cd = 'chase', R(1.6, 2.4)
        elif e.st == 'stun':
            e.t -= dt
            if e.t <= 0:
                e.st, e.cd = 'chase', .6
        else:                                                      # chase: floats in, keeps a little room, then strikes
            e.st = 'chase'
            e.face = 1 if dx > 0 else -1
            want = 1 if d > 110 else (-.6 if d < 70 else 0)
            sp = 58 * e.spd
            e.x += dx / d * sp * want * dt
            e.y += (dy / d * sp * want + math.sin(s.t * 3 + e.anim) * 14) * dt
            if e.cd <= 0 and d < 150:
                e.st, e.t = 'wind', e.wind
                e.lx, e.ly = dx / d, dy / d
            if d > 420:
                e.st = 'calm'
        e.anim += dt
        e.x = max(0.0, min(LW - e.w, e.x))
        e.y = max(s.camtop - 30, min(GY - e.h - 2, e.y))

    def enemy_blink(s, e):
        """Shinobi smoke bomb: vanishes in a puff and reappears a few steps back."""
        lo, hi = (e.plat.x, e.plat.x + e.plat.w - e.w) if e.plat and not e.plat.ground else (0, LW - e.w)
        if s.hole and e.plat and e.plat.ground:
            hi = min(hi, e.plat.x + e.plat.w - e.w)
            lo = max(lo, e.plat.x)
        s.puff(e.x + e.w / 2, e.y + e.h / 2, 8, col=(110, 90, 140))
        e.x = max(lo, min(hi, e.x - e.face * R(110, 150)))
        s.puff(e.x + e.w / 2, e.y + e.h / 2, 8, col=(110, 90, 140))
        e.blinkcd, e.cd = 3.5 - .6 * e.tier, min(e.cd, .4)
        sfx('throw')

    def separate_enemies(s):
        """Enemies have bodies: they never overlap each other (except while climbing in the background)."""
        front = [e for e in s.en if not e.trav and not e.kind.startswith('boss')]
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
        if d['closing'] and d['k'] < 1 and not d.get('exit'):
            if d['k'] == 0:
                sfx('door' if d['kind'] == 'red' else 'gate')
            d['k'] = min(1, d['k'] + dt / .6)
            if d['k'] >= 1:
                s.shake = max(s.shake, 5)
                s.puff(d['x'], GY, 8)
                s.rumble(.6, .3, 200)
        if d.get('exit'):                                       # the EXIT KEY: the red door slides open again
            d['k'] = max(0.0, d['k'] - dt / .8)
        elif d['closing'] and p.x < d['x'] + 16:                # no way back
            p.x, p.vx = d['x'] + 16, max(0, p.vx)

    def cloaked(s, e=None):
        """SHADOW CLOAK works on the streets (not in a boss arena) - and not on the spirit-touched: their spirit sees you."""
        return s.buff('invis') and not s.arena and not (e is not None and getattr(e, 'spirit', False))

    def exit_kills(s):
        """Kills that count for the gate: with SHADOW CLOAK only the spirit-touched ones."""
        return getattr(s, 'spirit_kills', 0) if s.buff('invis') else s.lvl_kills

    def exit_msg(s):
        return 'KILL 3 SPIRIT-TOUCHED' if s.buff('invis') else 'KILL HALF THE ENEMIES'

    def mark_spirits(s):
        """SHADOW CLOAK: keep a few spirit-touched enemies on the street (one more than you still need, at most 4)."""
        need = s.exit_need - getattr(s, 'spirit_kills', 0)
        if need <= 0 or s.arena:
            return
        alive = [e for e in s.en if getattr(e, 'spirit', False) and not e.dead]
        if len(alive) >= min(4, need + 1):
            return
        pool = [e for e in s.en if not e.dead and not e.trav and not e.kind.startswith('boss') and e.kind != 'onryo'
                and not getattr(e, 'spirit', False) and getattr(e, 'warpin', 0) <= 0]
        if pool:
            e = random.choice(pool)
            e.spirit = True
            s.puff(e.x + e.w / 2, e.y + 6, 6, col=(150, 220, 255))
        elif len(s.en) < s.max_en + 2:                             # (nobody left to touch: one more walks in)
            s.spawn_enemy(True)

    def upd_cards(s, dt):
        """Cards that tick: GOLD RUSH / BOUNTY HUNTER run out, the SPIRIT WARD comes back, UNTOUCHABLE hurts on touch."""
        p = s.pl
        for b, ends in list(getattr(s, 'timed', {}).items()):
            left = [t_ for t_ in ends if t_ > s.gtime]
            if len(left) != len(ends):
                s.timed[b] = left
                if left:
                    s.buffs[b] = len(left)
                else:
                    s.buffs.pop(b, None)
                    del s.timed[b]
        if s.buff('invis') and not s.arena:
            s.mark_spirits()
        if s.buff('ward') and not getattr(s, 'ward', False) and not p.dead:
            s.wardT -= dt
            if s.wardT <= 0:
                s.ward = True
                sfx('charge')
                s.burst(p.x + p.w / 2, p.y + p.h / 2, 16, (200, 160, 255), spd=90, glowing=True, grav=-40)
        if s.buff('untouch') and not p.dead and p.inv <= 0 and p.dash <= 0:
            for e in s.en:
                if (not e.dead and not e.trav and getattr(e, 'warpin', 0) <= 0 and ov(p.rect(), e.rect())
                        and not (e.kind.startswith('boss') and getattr(e, 'bs', '') in ('dying', 'intro', 'chair', 'enter', 'descend'))):
                    s.hurt_player(1 if p.x + p.w / 2 > e.x + e.w / 2 else -1, 1)
                    break

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
        s.update_hole(dt)
        s.update_plazas()
        s.update_traps(dt)
        s.arena_t += dt
        frozen = s.freezeT > 0                                 # void skin: TIME STOP
        s.freezeT = max(0.0, s.freezeT - dt)
        hdt = 0.0 if frozen else dt                            # enemies and their missiles stand still
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
        if not frozen:
            for e in s.en:
                s.upd_enemy(e, dt)
            s.separate_enemies()
        s.upd_cards(dt)
        near = any(e.st in ('chase', 'wind', 'slash') and not e.trav and abs(e.x - p.x) < 300 for e in s.en) or s.boss_alive()
        s.intensity += ((1.0 if near else 0.0) - s.intensity) * min(1, dt * (2.5 if near else .6))
        s.music_volume()
        for pr in s.proj:
            pr[0] += pr[2] * (dt if pr[4] else hdt)            # your deflected shuriken keep flying in a time stop
            pr[1] += pr[3] * (dt if pr[4] else hdt)
            pr[5] -= dt if pr[4] else hdt
            r = (pr[0] - 3, pr[1] - 3, 6, 6)
            if pr[4]:
                for e in s.en:
                    if not e.dead and not e.trav and ov(r, e.rect()):
                        if e.kind.startswith('boss'):                 # a boss takes it as a hit (and dies properly)
                            if e.bs != 'dying':
                                s.hurt_enemy(e, 1 if pr[2] > 0 else -1, 2)
                        else:
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
        s.boss_msg = (s.boss_msg[0], max(0.0, s.boss_msg[1] - dt))
        p = s.pl
        for a in s.acid:
            a[3] += 700 * hdt
            a[0] += a[2] * hdt
            a[1] += a[3] * hdt
            a[4] += hdt
            if not a[5] and not p.dead and ov((a[0] - 6, a[1] - 6, 12, 12), (p.x, p.y, p.w, p.h)):
                a[5] = True
                s.hurt_player(1 if a[2] > 0 else -1, 1)
            elif not a[5] and a[1] >= GY + 6:                  # splashes into a burning acid puddle
                s.puddles.append([a[0], 3.0])
                s.burst(a[0], GY - 2, 6, (150, 255, 120), spd=60, glowing=True, grav=300)
        s.acid = [a for a in s.acid if a[4] < 3.0 and a[1] < GY + 6 and not a[5]]
        for o in s.orbs:
            dxo = p.x + p.w / 2 - o[0]
            dyo = p.y + p.h / 2 - o[1]
            d = max(1.0, math.hypot(dxo, dyo))
            o[0] += dxo / d * 150 * hdt
            o[1] += dyo / d * 150 * hdt
            o[2] += hdt
            if not o[3] and not p.dead and ov((o[0] - 8, o[1] - 8, 16, 16), (p.x, p.y, p.w, p.h)):
                o[3] = True
                s.hurt_player(1 if dxo > 0 else -1, 1)
        s.orbs = [o for o in s.orbs if o[2] < 4.5 and not o[3]]
        for w in s.bossw:
            w[3] += hdt
            if w[3] > 0:
                w[0] += w[2] * w[5] * hdt
        s.bossw = [w for w in s.bossw if w[3] < 1.8 and -40 < w[0] < LW + 40]
        s.tick_tokens(hdt)
        s.update_boss_fx(hdt)
        for w in s.bossw:
            p = s.pl
            if w[3] > 0 and not w[4] and not p.dead and ov((w[0] - 10, GY - 18, 20, 18), (p.x, p.y, p.w, p.h)):
                w[4] = True
                s.hurt_player(w[2], w[7] if len(w) > 7 else 2)
        for bw in s.bwaves:
            bw[0] += bw[2] * 380 * dt
            bw[3] += dt
        s.bwaves = [bw for bw in s.bwaves if bw[3] < .75]
        for bw in s.bwaves:
            rect = (bw[0] - 10, bw[1] - 14, 20, 28)
            for e in s.en:
                if not e.dead and not e.trav and id(e) not in bw[4] and ov(rect, e.rect()):
                    bw[4].add(id(e))
                    s.hurt_enemy(e, bw[2], 2)
            for pr in s.proj:
                if not pr[4] and ov(rect, (pr[0] - 3, pr[1] - 3, 6, 6)):
                    pr[5] = 0
                    s.burst(pr[0], pr[1], 6, (255, 120, 160), spd=60, glowing=True, grav=0)
        s.en = [e for e in s.en if not e.dead and e.y < GY + 40]
        s.spawnT -= dt
        if s.spawnT <= 0 and len(s.en) < s.max_en and s.spawned < s.quota:
            s.spawnT = max(2.8, 4.6 - .12 * s.lvl) / s.mult
            s.spawn_enemy(True)
        s.coinT -= dt
        if s.coinT <= 0:
            s.coinT = 3.5
            if len(s.coins) < 32 and not s.arena:
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
            if s.buff('invis') and not c[2]:                   # SHADOW CLOAK: only the mythic coins are yours
                continue
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
                    if l[4] == 'heart':                         # FIELD MEDIC's heart
                        p.hp = min(p.maxhp, p.hp + 1)
                        sfx('glint')
                        s.burst(l[0], l[1], 10, (255, 90, 120), spd=60, glowing=True, grav=-40)
                    else:
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
        s.cam = max(0, min((ARENA_W if s.arena else LW) - W, s.cam))
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
        if kind == 'victory' and not getattr(s, 'endless', False) and not getattr(s, 'admin_run', False):
            loc = getattr(s, 'loc', 0)
            st[f'won{loc}'] = st.get(f'won{loc}', 0) + 1         # survived runs per location
            if loc not in st['cleared']:
                st['cleared'] = sorted(st['cleared'] + [loc])   # opens the next location and more upgrade levels
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

    def draw_char(s, wx, wy, f, P, S, chains, cx, oy, flash=False, ghost=None, sq=(1.0, 1.0), hide=False):
        D = s.spr
        D.fill((0, 0, 0, 0))
        info = paint(D, 48, 84, f, P, S, s.t, chains, (wx - 48, wy - 84))
        z = S.get('zoom', 1)
        zx, zy = z * sq[0], z * sq[1]                              # sq: squash & stretch (boss landings)
        if zx != 1 or zy != 1:                                     # the bosses: the same sprite, drawn bigger
            D = pg.transform.scale(D, (int(96 * zx), int(96 * zy)))
            info = {k: ((v[0] * zx, v[1] * zy) if isinstance(v, tuple) and len(v) == 2 else v) for k, v in info.items()}
        org = (wx - 48 * zx, wy - 84 * zy)
        m = pg.mask.from_surface(D)
        sx, sy = org[0] - cx, org[1] + oy
        if hide:                                                   # INVISIBILITY: only a cold shimmer of you
            s.ghosts.append([m, org[0], org[1], .1, (70, 80, 150), .1])
            return info, sx, sy
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
        if p.dash > 0 and p.tdash:
            ghost = (.35, (255, 220, 80) if int(s.t * 30) % 2 else (255, 255, 200))
        elif p.dash > 0:
            ghost = (.3, (0, 200, 255) if int(s.t * 30) % 2 else (255, 40, 150))
        elif p.slam and p.slamT > .12 and int(s.t * 60) % 2 == 0:
            ghost = (.25, (0, 160, 255))
        S = s.pal()
        if s.buff('reach'):                                         # LONG BLADE: you can see it
            S = dict(S, blade=int(S['blade'] * (1 + .25 * s.buff('reach'))))
        info, sx, sy = s.draw_char(p.x + p.w / 2, p.y + p.h, p.face, p.pose, S, p.chains, cx, oy, ghost=ghost,
                                   hide=s.buff('invis') and not s.arena and s.state == 'play')
        if getattr(s, 'ward', False):                                # SPIRIT WARD: a violet ring around you
            r_ = 22 + int(math.sin(s.t * 6) * 2)
            pg.draw.circle(scr, (200, 160, 255), (int(sx + 48), int(sy + 70)), r_, 1)
            glow(scr, sx + 48, sy + 70, r_ + 4, (40, 26, 70), .4)
        if p.shield > 0:
            glow(scr, sx + 48, sy + 42, 26 + int(math.sin(s.t * 20) * 3), (90, 90, 120))
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

    def draw_spirit(s, e, cx, oy):
        """A spirit-touched enemy (SHADOW CLOAK): a small ghost circling its head and wind curling round its body."""
        t, ph = s.t, id(e) % 97 * .1
        bx, top = e.x + e.w / 2 - cx, e.y + oy
        for i in range(3):                                         # wind streaks curling around the body
            k = (t * .9 + i / 3 + ph) % 1
            y = top + 6 + i * (e.h - 10) / 2
            x0 = bx - 14 + k * 28
            pg.draw.arc(scr, qcol((150, 230, 255), math.sin(k * math.pi) * .8), (x0 - 6, y - 3, 12, 6), 0, math.pi, 1)
        gx = bx + math.cos(t * 2.2 + ph) * 12                      # the spirit
        gy = top - 10 + math.sin(t * 3.1 + ph) * 3
        for j in range(4):                                         # its tail
            tx = bx + math.cos(t * 2.2 + ph - (j + 1) * .35) * 12
            ty = top - 10 + math.sin(t * 3.1 + ph - (j + 1) * .35) * 3 + j
            pg.draw.circle(scr, qcol((150, 230, 255), .6 - j * .14), (int(tx), int(ty)), max(1, 3 - j))
        glow(scr, gx, gy, 12, (30, 60, 80))
        pg.draw.circle(scr, (220, 245, 255), (int(gx), int(gy)), 4)
        for sg in (-1, 1):
            scr.fill((30, 40, 70), (int(gx + sg * 2) - 1, int(gy) - 1, 1, 2))

    def draw_enemy(s, e, cx, oy):
        if e.kind.startswith('boss'):
            return s.draw_boss(e, cx, oy)
        bx, by = e.x + e.w / 2 - cx, e.y + e.h + oy
        wi = getattr(e, 'warpin', 0)
        if wi > 0:                                                     # blinking in: a column of light that narrows to him
            k = wi / .45
            col = pg.Surface((24, int(by) + 2), pg.SRCALPHA)
            hw = max(1, int(10 * k))
            pg.draw.rect(col, (255, 240, 220, int(200 * k)), (12 - hw, 0, hw * 2, col.get_height()))
            pg.draw.rect(col, (255, 255, 255, 230), (11, 0, 2, col.get_height()))
            scr.blit(col, (bx - 12, 0))
            glow(scr, bx, by - e.h / 2, 26, qcol((255, 220, 200), .6 * k))
            if wi > .2 or int(wi * 40) % 2:                            # (the body flickers in at the end)
                return
        if bx < -50 or bx > W + 50:
            return
        if s.state == 'play' and s.hitstop <= 0:
            e.pose = blend(e.pose, pose_enemy(e, s.t), min(1, s.dt * 16))
        S = tier_pal(getattr(e, 'look', e.kind), e.tier, bool(e.trav))
        if e.kind == 'onryo':                                          # a cold light around the ghost, its shadow far below
            glow(scr, bx, by - e.h / 2, 24, qcol((40, 70, 100), .7 + .3 * math.sin(s.t * 5 + e.anim)))
            if e.st == 'wind' and int(s.t * 20) % 2:
                glow(scr, bx, by - e.h * .8, 16, (120, 20, 30))
        info, sx, sy = s.draw_char(e.x + e.w / 2, e.y + e.h, e.face, e.pose, S, e.chains, cx, oy, e.hurt > .1 or e.flash > 0)
        if e.kind == 'teppo' and e.st == 'wind' and info['blade'] and not e.trav:   # the red aiming line
            mx, my = sx + info['blade'][0], sy + info['blade'][1]
            ax, ay = e.aimx - cx, e.aimy + oy
            dd = math.hypot(ax - mx, ay - my) or 1
            ex_, ey_ = mx + (ax - mx) / dd * 420, my + (ay - my) / dd * 420
            locked = e.t <= .3
            if not locked or int(s.t * 24) % 2:
                pg.draw.line(scr, (255, 40, 50) if locked else (150, 20, 30), (mx, my), (ex_, ey_), 1)
            glow(scr, mx, my, 6, (110, 30, 10))
        if s.freezeT > 0:                                              # TIME STOP: frozen in violet
            glow(scr, bx, by - e.h / 2, 18, (40, 20, 70))
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
            if gb[11].get('head') == 'hat':
                sil_poly(scr, rot([(-10, -h / 2 - 5), (0, -h / 2 - 11), (10, -h / 2 - 5)], x, y, a), S['straw'], S['rim'])
        cut = rot([(-w / 2, h / 2 if half == 0 else -h / 2), (w / 2, h / 2 if half == 0 else -h / 2)], x, y, a)
        pg.draw.line(scr, (255, 30, 70), cut[0], cut[1], 2)

    # ---------- rendering: world
    def draw_bg_env(s, env, cam, oy):
        """The docks and the temple: their own skies and skylines (the city keeps its own draw_bg)."""
        if env not in s.LT:
            s.LT[env] = bake_env(env)
        L = s.LT[env]
        scr.blit(L['sky'], (0, 0))
        if env == 'docks':
            lx, ly = L['light']                                    # the lighthouse beam sweeping the fog
            x0, y0 = lx - cam * .15, ly + oy * .15
            a = s.t * 1.1
            ln = 260
            k = abs(math.cos(a))
            pts = [(x0, y0), (x0 + math.cos(a) * ln, y0 - 14 + math.sin(a) * 8), (x0 + math.cos(a) * ln, y0 + 14 + math.sin(a) * 8)]
            beam = pg.Surface((W, H), pg.SRCALPHA)
            pg.draw.polygon(beam, (200, 230, 210, int(26 * k)), pts)
            scr.blit(beam, (0, 0))
            glow(scr, x0, y0, 14, qcol((90, 90, 60), .5 + .5 * k))
        elif env == 'temple':
            for i in range(9):                                     # sky lanterns drifting up past the moon
                x = (i * 83 + s.t * (4 + i % 3) - cam * .05) % (W + 40) - 20
                y = (GY - 60) - (s.t * (6 + i % 4) + i * 41) % 200
                glow(scr, x, y, 8, (90, 40, 10))
                scr.fill((255, 190, 110), (x - 1, y - 2, 3, 4))
        scr.blit(L['far'], (-int(cam * .15), int(oy * .15)))
        s.bg_life_far(env, cam, oy)
        scr.blit(L['mid'], (-int(cam * .4), int(oy * .4)))
        s.bg_life_mid(env, cam, oy)
        if env == 'docks':
            fw = L['fog'].get_width() - W
            for i, (sp, yy) in enumerate(((8, GY - 120), (14, GY - 80))):
                off = int(s.t * sp + i * 90) % fw
                scr.blit(L['fog'], (-off, yy + oy * .5))
        scr.blit(L['haze'], (0, int(oy * .5)))
        scr.blit(L['near'], (-int(cam * .7), int(oy * .7)))

    def bg_life_far(s, env, cam, oy):
        """Things moving far away: sky traffic over the city, a ship on the horizon at the docks, crows over the temple."""
        t_ = s.t
        if env == 'city':                                        # two lanes of flying cars, each way
            for lane, (y0, sp, col) in enumerate(((58, 46, (255, 240, 200)), (66, -38, (255, 70, 90)), (96, 60, (200, 230, 255)),
                                                  (104, -52, (255, 90, 120)))):
                y = y0 + oy * .25 + math.sin(t_ * .7 + lane) * 1.5
                for j in range(6):
                    x = (j * 97 + lane * 41 + t_ * sp - cam * .25) % (W + 60) - 30
                    scr.fill(col, (x, y, 2, 1))
                    pg.draw.line(scr, tuple(c // 4 for c in col), (x - (8 if sp > 0 else -8), y), (x, y))
        elif env == 'docks':                                     # a freighter crossing the horizon, its lights in the fog
            x = (t_ * 6 - cam * .1) % (W + 300) - 150
            y = GY - 104 + oy * .15
            pg.draw.polygon(scr, (14, 26, 32), [(x, y), (x + 120, y), (x + 112, y + 8), (x + 6, y + 8)])
            pg.draw.rect(scr, (16, 30, 36), (x + 84, y - 12, 22, 12))
            for k in range(6):
                scr.fill((40, 60, 70), (x + 12 + k * 12, y - 6, 10, 6))
            scr.fill((255, 220, 140), (x + 88, y - 9, 2, 2))
            if int(t_ * 1.5) % 2:
                glow(scr, x + 104, y - 14, 6, (90, 10, 10))
            for i in range(5):                                   # gulls
                gx = (i * 120 + t_ * (22 + i * 4) - cam * .2) % (W + 40) - 20
                gy = 40 + i * 13 + math.sin(t_ * 2 + i) * 6 + oy * .2
                w = 2 + int(abs(math.sin(t_ * 8 + i)) * 2)
                pg.draw.lines(scr, (150, 170, 170), False, [(gx - 3, gy - w), (gx, gy), (gx + 3, gy - w)], 1)
        else:                                                    # crows crossing the snowy sky
            for i in range(4):
                gx = (i * 160 - t_ * (16 + i * 3) - cam * .2) % (W + 40) - 20
                gy = 50 + i * 17 + math.sin(t_ * 1.5 + i) * 5 + oy * .2
                w = 2 + int(abs(math.sin(t_ * 7 + i)) * 2)
                pg.draw.lines(scr, (20, 12, 16), False, [(gx - 4, gy - w), (gx, gy), (gx + 4, gy - w)], 2)

    def bg_life_mid(s, env, cam, oy):
        """Closer: windows switching on and off in the buildings, signals and lamps blinking."""
        t_ = s.t
        off = cam * .4
        rnd = random.Random(7)
        if env == 'forest':                                      # (no windows in the sea of trees)
            return
        cols = {'city': ((255, 220, 140), (140, 220, 255), (255, 120, 200)), 'docks': ((255, 200, 120), (120, 255, 200)),
                'temple': ((255, 170, 90), (255, 120, 60)), 'peaks': ((255, 190, 110),), 'dojo': ((255, 190, 110), (255, 140, 80))}[env]
        for i in range(40):                                      # windows lit at random moments, each on its own rhythm
            wx = rnd.uniform(0, 1500)
            wy = rnd.uniform(GY - 150, GY - 70)
            rate, ph = rnd.uniform(.05, .25), rnd.uniform(0, 6.3)
            x = (wx - off) % (W + 40) - 20
            if math.sin(t_ * rate * 6 + ph) > .55:
                c = cols[i % len(cols)]
                scr.fill(tuple(v // 2 for v in c), (x, wy + oy * .4, 3, 3))
                if i % 9 == 0:
                    glow(scr, x + 1, wy + oy * .4 + 1, 5, tuple(v // 6 for v in c))
        for i in range(5 if env in ('city', 'docks', 'temple') else 0):   # aircraft warning lights on the tall roofs
            x = (i * 230 + 80 - off) % (W + 40) - 20
            y = GY - 160 - (i % 3) * 18 + oy * .4
            if int(t_ * 1.2 + i * .37) % 2 == 0:
                scr.fill((255, 60, 60), (x, y, 2, 2))
                glow(scr, x + 1, y + 1, 6, (70, 10, 10))

    def draw_bg(s, cam, oy):
        env = s.theme.get('env', 'city')
        if env != 'city':
            return s.draw_bg_env(env, cam, oy)
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
        s.bg_life_far('city', cam, oy)
        for i in range(4):                                      # drones
            dxp = (i * 137 + s.t * (18 + i * 7)) % (W + 40) - 20
            dyp = 70 + i * 16 + math.sin(s.t * 1.3 + i) * 8 + oy * .3
            scr.fill((20, 14, 30), (dxp - 2, dyp, 5, 2))
            if int(s.t * 3 + i) % 2:
                glow(scr, dxp, dyp, 5, (90, 10, 10) if i % 2 else (10, 90, 30))
        scr.blit(L['mid'], (-int(cam * .4), int(oy * .4)))
        s.bg_life_mid('city', cam, oy)
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
        weather = s.theme.get('weather', 'rain')
        if weather in ('snow', 'blizzard', 'spores', 'petals'):    # snow / a peak blizzard / forest spores / sakura petals
            n = {'snow': 110, 'blizzard': 170, 'spores': 50, 'petals': 70}[weather]
            if len(s.snow) < n:
                s.snow += [[R(0, W), R(-H, 0), R(14, 34), R(0, 6), random.choice((1, 1, 2))] for _ in range(n - len(s.snow))]
            del s.snow[n:]
            for f in s.snow:
                if weather == 'spores':                            # glowing motes rising slowly between the trees
                    f[1] -= f[2] * .35 * s.dt
                    f[0] += math.sin(s.t * .9 + f[3]) * 8 * s.dt
                    if f[1] < -4:
                        f[0], f[1] = R(0, W), H + R(0, 20)
                    k = .5 + .5 * math.sin(s.t * 3 + f[3] * 2)
                    scr.fill((int(140 + 80 * k), 255, int(120 + 60 * k)), (f[0], f[1], 1, 1))
                    if f[4] > 1:
                        glow(scr, f[0], f[1], 4, qcol((30, 80, 30), k))
                    continue
                wind = {'snow': -10, 'blizzard': -80, 'petals': -22}[weather]
                f[1] += f[2] * (1.7 if weather == 'blizzard' else (.7 if weather == 'petals' else 1)) * s.dt
                f[0] += (math.sin(s.t * 1.3 + f[3]) * 14 + wind) * s.dt
                if f[1] > min(H, gys + R(0, max(1, H - gys))) or f[0] < -4:
                    f[0], f[1] = R(0, W + 60), R(-20, 0)
                if weather == 'petals':                            # pink petals turning over as they fall
                    flip = math.sin(s.t * 6 + f[3] * 3) > 0
                    scr.fill((255, 176, 204) if f[4] > 1 else (236, 130, 170), (f[0], f[1], 2 if flip else 1, 1 if flip else 2))
                else:
                    scr.fill((236, 230, 244) if f[4] > 1 else (200, 190, 214), (f[0], f[1], f[4], f[4]))
            return
        if weather == 'fog' and 'fog' in s.LT.get('docks', {}):   # the docks: a low fog bank rolling past in front
            fog = s.LT['docks']['fog']
            off = int(s.t * 22) % (fog.get_width() - W)
            scr.blit(fog, (-off, gys - 40))
        drizzle = weather == 'fog'
        for i, r in enumerate(s.rain):
            if drizzle and i % 2:
                continue
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

    def kiosk_keeper(s, x, y):
        """The kiosk's keeper: a deep hood around the neon mask, a ragged cloak down to the counter."""
        glow(scr, x, y, 90, (40, 20, 70), .5)
        cloak = [(x - 46, y + 8), (x - 74, y + 40), (x - 96, y + 56), (x - 86, y + 54), (x - 70, y + 58), (x + 70, y + 58),
                 (x + 86, y + 54), (x + 96, y + 56), (x + 74, y + 40), (x + 46, y + 8)]
        pg.draw.polygon(scr, (12, 8, 22), cloak)
        pg.draw.lines(scr, (70, 46, 120), False, cloak[:4], 1)
        pg.draw.lines(scr, (70, 46, 120), False, cloak[-4:], 1)
        for fx in (-50, -22, 22, 50):                                    # folds of the cloak
            pg.draw.line(scr, (26, 18, 44), (x + fx * .6, y + 18), (x + fx, y + 58), 2)
        sw = math.sin(s.t * 1.3) * 2
        hood = [(x - 2 + sw, y - 58), (x + 30, y - 36), (x + 42, y - 4), (x + 38, y + 24), (x + 16, y + 34), (x - 16, y + 34),
                (x - 38, y + 24), (x - 42, y - 4), (x - 30, y - 36)]
        pg.draw.polygon(scr, (16, 10, 28), hood)
        pg.draw.polygon(scr, (90, 56, 150), hood, 2)
        pg.draw.ellipse(scr, (4, 2, 8), (x - 32, y - 30, 64, 58))       # the dark inside of the hood
        s.shinobi_mask(x, y + 2, 2.6, .7 + math.sin(s.t * 3) * .2)

    def keeper_hand(s, x, y, side):
        """A brown, long-fingered hand gripping the edge of a card, the sleeve reaching back over the counter."""
        y += 18
        pg.draw.polygon(scr, (14, 10, 24), [(x - side * 2 - 7, y + 16), (x - side * 2 + 7, y + 16), (x - side * 6 + 6, H), (x - side * 6 - 6, H)])
        pg.draw.ellipse(scr, (122, 78, 44), (x - 9, y - 10, 18, 26))     # the palm, behind the card's edge
        pg.draw.ellipse(scr, (60, 34, 18), (x - 9, y - 10, 18, 26), 1)
        for j in range(4):                                               # long fingers curled over the edge
            fy = y - 7 + j * 5
            pg.draw.line(scr, (150, 100, 60), (x - side * 2, fy), (x + side * 9, fy + 1), 3)
            pg.draw.line(scr, (60, 34, 18), (x + side * 9, fy + 2), (x + side * 11, fy + 1))
            scr.fill((210, 190, 160), (x + side * 10 - (1 if side < 0 else 0), fy, 1, 1))   # pale nails
        pg.draw.line(scr, (150, 100, 60), (x - side * 6, y + 10), (x - side * 2, y + 15), 4)   # thumb

    def draw_door(s, d, cx, oy):
        """Start-of-district door: a red sliding door (district 1) or a neon shinobi gate. k: 0 open .. 1 shut."""
        x, gys, k = d['x'] - cx, GY + oy, d['k']
        if x < -60 or x > W + 60:
            return
        pg.draw.rect(scr, (8, 4, 10), (x - 16, gys - 62, 32, 62))                  # dark doorway
        if d['kind'] == 'red' and k < 1:                                          # red noren in the doorway, one caught by the wind
            sway = math.sin(s.t * 1.7) * 2
            fl = .5 + .5 * math.sin(s.t * 3.1) * math.sin(s.t * 1.3)
            left = [(x - 15, gys - 62), (x - 1, gys - 62), (x - 1 + sway, gys - 12), (x - 15 + sway * .6, gys - 10)]
            right = [(x + 1, gys - 62), (x + 15, gys - 62), (x + 15 + fl * 14, gys - 22 - fl * 6), (x + 3 + fl * 18, gys - 14 - fl * 8)]
            for pts in (left, right):
                pg.draw.polygon(scr, (176, 24, 38), pts)
                pg.draw.polygon(scr, (110, 12, 22), pts, 1)
                for j in (.33, .66):                                              # folds
                    pg.draw.line(scr, (130, 16, 28), (lerp(pts[0][0], pts[1][0], j), pts[0][1] + 2),
                                 (lerp(pts[3][0], pts[2][0], j), lerp(pts[3][1], pts[2][1], j) - 2))
            pg.draw.rect(scr, (60, 10, 16), (x - 16, gys - 63, 32, 4))                # the rod
            pg.draw.circle(scr, (240, 230, 220), (int(x - 6 + sway * .3), gys - 44), 4, 1)   # the clan crest, white on red
            pg.draw.circle(scr, (240, 230, 220), (int(x + 7 + fl * 5), gys - 45 + int(fl * 2)), 3, 1)
        if d['kind'] == 'red':
            clip0 = scr.get_clip()                                                # the panels slide behind the posts, never outside the gate
            scr.set_clip(pg.Rect(x - 16, gys - 62, 32, 62).clip(clip0))
            for sg in (-1, 1):                                                    # two sliding panels
                px = x + sg * (8 + 16 * (1 - ease(k))) - 8
                pg.draw.rect(scr, (170, 24, 34), (px, gys - 60, 16, 60))
                for ly in range(gys - 54, gys - 4, 10):
                    pg.draw.line(scr, (60, 8, 12), (px + 1, ly), (px + 14, ly))
                pg.draw.line(scr, (60, 8, 12), (px + 8, gys - 60), (px + 8, gys))
                scr.fill((230, 190, 90), (px + (12 if sg < 0 else 2), gys - 32, 2, 4))
            scr.set_clip(clip0)
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
        txt = f"[{key}] {tr(label)}"
        w = F_S.size(txt)[0] + 10
        pg.draw.polygon(scr, INK, [(x - w / 2, y), (x + w / 2, y - 2), (x + w / 2 - 3, y + 12), (x - w / 2 - 3, y + 14)])
        text(txt, F_S, WHITE, x, y + 1, True)

    def draw_kiosk(s, x, gys):
        """The Shinobi Kiosk: a little neon booth that sells one buff per district."""
        if x < -60 or x > W + 60:
            return
        used = s.kiosk['used'] or s.kiosk.get('closed')
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
        text("SHINOBI KIOSK" if not used else ("CLOSED" if s.kiosk.get('closed') else "SOLD OUT"), F_S, col, x, gys - 84, True)
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
        elif b == 'reach':                                            # long blade
            pg.draw.line(scr, col, (x - 10, y + 6), (x + 10, y - 6), 2)
            pg.draw.line(scr, WHITE, (x + 4, y - 2), (x + 10, y - 6), 2)
            pg.draw.line(scr, col, (x - 7, y + 1), (x - 4, y + 8), 2)
        elif b == 'quick':                                            # two quick slashes
            for i in (-4, 4):
                pg.draw.line(scr, col, (x - 8 + i, y + 8), (x + 6 + i, y - 8), 2)
        elif b == 'thorns':                                           # blades bursting out of a guard
            for a in range(6):
                ang = a * math.pi / 3
                pg.draw.line(scr, col, (x, y), (x + math.cos(ang) * 10, y + math.sin(ang) * 10), 2)
            pg.draw.circle(scr, INK, (x, y), 4)
        elif b == 'second':                                           # a cracked heart, mended
            pg.draw.circle(scr, col, (x - 4, y - 2), 5)
            pg.draw.circle(scr, col, (x + 4, y - 2), 5)
            pg.draw.polygon(scr, col, [(x - 9, y), (x + 9, y), (x, y + 9)])
            pg.draw.lines(scr, INK, False, [(x, y - 5), (x - 2, y), (x + 2, y + 3), (x, y + 7)], 1)
        elif b == 'armor':                                            # a lacquered breastplate
            pg.draw.rect(scr, col, (x - 8, y - 8, 16, 16), border_radius=3)
            for ly in (y - 3, y + 2):
                pg.draw.line(scr, INK, (x - 8, ly), (x + 8, ly))
        elif b == 'sky':                                              # wings of dashes
            for i in range(2):
                pg.draw.arc(scr, col, (x - 10 + i * 4, y - 8 + i * 4, 20 - i * 8, 16 - i * 8), 0, math.pi, 2)
        elif b == 'execute':                                          # a skull-ish mask
            pg.draw.circle(scr, col, (x, y - 2), 8)
            for sg in (-1, 1):
                pg.draw.circle(scr, INK, (x + sg * 3, y - 3), 2)
            pg.draw.rect(scr, col, (x - 4, y + 4, 8, 4))
        elif b == 'onigiri':                                          # rice ball with nori
            pg.draw.polygon(scr, col, [(x, y - 9), (x + 9, y + 7), (x - 9, y + 7)])
            pg.draw.rect(scr, (20, 40, 30), (x - 4, y + 1, 8, 6))
        elif b == 'bounty':                                           # a wanted poster coin stack
            for i in range(3):
                pg.draw.ellipse(scr, col, (x - 7, y + 4 - i * 5, 14, 6))
                pg.draw.ellipse(scr, INK, (x - 7, y + 4 - i * 5, 14, 6), 1)
        elif b == 'quake':                                            # cracks spreading from an impact
            pg.draw.line(scr, col, (x - 10, y + 6), (x + 10, y + 6), 2)
            pg.draw.lines(scr, col, False, [(x, y + 6), (x - 3, y), (x + 2, y - 4), (x - 1, y - 9)], 2)
            pg.draw.lines(scr, col, False, [(x - 6, y + 6), (x - 9, y + 1)], 1)
            pg.draw.lines(scr, col, False, [(x + 6, y + 6), (x + 9, y + 1)], 1)
        elif b == 'shadow':                                           # a body cut through by a dash line
            pg.draw.rect(scr, col, (x - 3, y - 8, 6, 16))
            pg.draw.line(scr, WHITE, (x - 10, y + 2), (x + 10, y - 2), 2)
        elif b == 'rage':                                             # a flame
            pg.draw.polygon(scr, col, [(x, y - 10), (x + 7, y + 2), (x + 3, y + 8), (x - 3, y + 8), (x - 7, y + 2)])
            pg.draw.polygon(scr, (255, 220, 90), [(x, y - 2), (x + 3, y + 4), (x, y + 7), (x - 3, y + 4)])
        elif b == 'medic':                                            # a heart with a cross
            for sg in (-1, 1):
                pg.draw.circle(scr, col, (x + sg * 4, y - 2), 5)
            pg.draw.polygon(scr, col, [(x - 9, y), (x + 9, y), (x, y + 9)])
            pg.draw.line(scr, WHITE, (x - 3, y), (x + 3, y), 2)
            pg.draw.line(scr, WHITE, (x, y - 3), (x, y + 3), 2)
        elif b == 'ward':                                             # a ring with a seal inside
            pg.draw.circle(scr, col, (x, y), 9, 2)
            pg.draw.circle(scr, col, (x, y), 3)
        elif b == 'glass':                                            # a glass diamond with a crack
            pts = [(x, y - 9), (x + 8, y), (x, y + 9), (x - 8, y)]
            pg.draw.polygon(scr, col, pts)
            pg.draw.polygon(scr, WHITE, pts, 1)
            pg.draw.lines(scr, INK, False, [(x - 3, y - 4), (x, y), (x - 1, y + 4)], 1)
        elif b == 'four':                                             # four little cards
            for i in range(4):
                pg.draw.rect(scr, col, (x - 10 + i * 5, y - 6 + (i % 2) * 2, 5, 11), 1)
        elif b == 'gamble':                                           # a die
            pg.draw.rect(scr, col, (x - 8, y - 8, 16, 16), border_radius=3)
            for dx_, dy_ in ((-4, -4), (0, 0), (4, 4)):
                pg.draw.circle(scr, INK, (x + dx_, y + dy_), 2)
        elif b == 'invis':                                            # a dotted outline of a figure
            for a in range(0, 360, 40):
                r_ = math.radians(a)
                scr.fill(col, (x + int(math.cos(r_) * 4) - 1, y - 5 + int(math.sin(r_) * 4) - 1, 2, 2))
            for yy in range(y + 1, y + 10, 3):
                scr.fill(col, (x - 6, yy, 2, 2))
                scr.fill(col, (x + 4, yy, 2, 2))
        elif b == 'jackpot':                                          # three sevens
            for i in (-6, 0, 6):
                pg.draw.lines(scr, col, False, [(x + i - 2, y - 6), (x + i + 2, y - 6), (x + i - 1, y + 6)], 2)
        elif b == 'untouch':                                          # a blade through a cracked heart, x3
            for sg in (-1, 1):
                pg.draw.circle(scr, RED, (x + sg * 4, y - 1), 5)
            pg.draw.polygon(scr, RED, [(x - 9, y + 1), (x + 9, y + 1), (x, y + 10)])
            pg.draw.lines(scr, INK, False, [(x, y - 3), (x - 2, y + 2), (x + 1, y + 5), (x, y + 9)], 1)
            pg.draw.line(scr, WHITE, (x - 11, y + 9), (x + 11, y - 9), 2)
            outlined("x3", F_S, col, x + 3, y - 12, r=1)
        elif b == 'slammaster':                                       # a big fist on the ground with waves
            pg.draw.rect(scr, col, (x - 5, y - 9, 10, 10), border_radius=2)
            pg.draw.line(scr, col, (x - 10, y + 6), (x + 10, y + 6), 2)
            for sg in (-1, 1):
                pg.draw.arc(scr, col, (x + sg * 6 - 5, y - 1, 10, 10), 0, math.pi, 1)
        elif b == 'joker':                                            # a black card with a red mark
            pg.draw.rect(scr, (10, 6, 14), (x - 7, y - 9, 14, 18))
            pg.draw.rect(scr, col, (x - 7, y - 9, 14, 18), 1)
            pg.draw.polygon(scr, col, [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)])
        elif b == 'scars':                                            # three claw scars
            for i in (-5, 0, 5):
                pg.draw.line(scr, col, (x + i - 3, y - 8), (x + i + 3, y + 8), 2)
        elif b == 'random':                                           # a question mark
            outlined("?", F_PM, col, x, y - 8, center=True, r=1)
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
        elif kind == 'crate':                                   # docks: a wooden cargo crate
            pg.draw.rect(scr, (90, 64, 40), (x, y - 11, 14, 11))
            pg.draw.rect(scr, (130, 96, 60), (x, y - 11, 14, 11), 1)
            pg.draw.line(scr, (60, 40, 24), (x, y - 11), (x + 14, y))
        elif kind == 'lantern':                                 # temple: a stone toro lantern, lit
            pg.draw.rect(scr, (90, 84, 90), (x + 4, y - 6, 4, 6))
            pg.draw.rect(scr, (110, 104, 110), (x + 1, y - 12, 10, 6))
            pg.draw.polygon(scr, (70, 64, 70), [(x - 1, y - 12), (x + 6, y - 17), (x + 13, y - 12)])
            scr.fill((255, 200, 110), (x + 4, y - 11, 4, 3))
            glow(scr, x + 6, y - 10, 10, (90, 50, 14))
        elif kind == 'bell':                                    # temple: a bronze bell under a small roof
            pg.draw.line(scr, (60, 30, 24), (x, y), (x, y - 20), 2)
            pg.draw.line(scr, (60, 30, 24), (x + 14, y), (x + 14, y - 20), 2)
            pg.draw.polygon(scr, (120, 30, 26), [(x - 4, y - 20), (x + 7, y - 26), (x + 18, y - 20)])
            sw = math.sin(s.t * 1.6 + x) * 1.5
            pg.draw.polygon(scr, col, [(x + 4 + sw, y - 17), (x + 10 + sw, y - 17), (x + 12 + sw, y - 7), (x + 2 + sw, y - 7)])
            glow(scr, x + 7, y - 12, 12, (70, 50, 10))
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
        if p.ground:                                               # street pieces (boss districts split the street)
            return
        x, y, w = p.x - cx, p.y + oy, p.w
        if x > W + 20 or x + w < -20 or y > H + 30 or y < -40:
            return
        if p.kind == 'static':
            th = s.theme
            box = getattr(p, 'box', None)
            if box:                                                # a cargo container down to the street
                gy = GY + oy
                body = tuple(c // 3 for c in box)
                pg.draw.rect(scr, body, (x + 1, y, w - 2, gy - y))
                for rx in range(int(x) + 5, int(x + w) - 3, 5):    # corrugated walls
                    pg.draw.line(scr, tuple(c // 2 for c in box), (rx, y + 3), (rx, gy - 1))
                for yy in range(int(y) + 52, int(gy), 52):         # the seam between stacked boxes
                    pg.draw.line(scr, (8, 8, 12), (x, yy), (x + w, yy), 2)
                pg.draw.rect(scr, box, (x, y, w, 4))
                pg.draw.line(scr, WHITE, (x, y), (x + w, y))
                return
            for kind, rx, col in p.props:
                s.draw_prop(kind, x + rx, y, col)
            for sx in range(int(x) + 4, int(x + w) - 2, 18):
                pg.draw.line(scr, th['slab'], (sx, y + 8), (sx, y + 16))
            pg.draw.rect(scr, th['slab'], (x, y, w, 8))
            pg.draw.line(scr, th['line'], (x, y + 3), (x + w, y + 3))
            pg.draw.line(scr, th['under'], (x, y + 8), (x + w, y + 8))
            glow(scr, x + w / 2, y + 9, int(w / 2), th['glow'], .2)
            pg.draw.line(scr, tuple(c // 4 for c in th['edge']), (x, y - 1), (x + w, y - 1))
            pg.draw.line(scr, th['edge'], (x, y), (x + w, y))
            if getattr(p, 'eave', False):                          # pagoda: a wooden storey under each roof
                bw, by = w - 26, y + 9
                pg.draw.rect(scr, (52, 14, 14), (x + 13, by, bw, 45))
                for px in (x + 13, x + 13 + bw - 3):
                    pg.draw.rect(scr, (90, 26, 20), (px, by, 3, 45))
                for i in range(max(1, int(bw // 22))):              # paper windows, lit from inside
                    wx = x + 19 + i * 22
                    if wx + 12 < x + 13 + bw:
                        scr.fill((255, 196, 120), (wx, by + 14, 10, 14))
                        pg.draw.line(scr, (90, 40, 20), (wx + 5, by + 14), (wx + 5, by + 27))
                        glow(scr, wx + 5, by + 21, 12, (70, 36, 10))
            if getattr(p, 'eave', False):                          # pagoda: upturned roof corners
                for sg, ex in ((-1, x), (1, x + w)):
                    pg.draw.polygon(scr, th['slab'], [(ex, y), (ex + sg * 10, y - 5), (ex + sg * 12, y - 4), (ex + sg * 2, y + 6)])
                    pg.draw.line(scr, th['edge'], (ex, y), (ex + sg * 11, y - 5), 2)
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
        if s.arena:
            s.draw_arena_bg(cx, oy)
        else:
            s.draw_bg(cx, oy)
            if s.theme['tint']:                         # each part of the city has its own sky
                scr.fill(s.theme['tint'], special_flags=pg.BLEND_RGB_MULT)
        for cx0, top, cx1 in s.cranes:                  # dock cranes: lattice tower and jib
            x0, x1, y = cx0 - cx, cx1 - cx, top + oy
            if x1 > -40 and x0 < W + 40:
                for px in (x0 - 6, x0 + 6):
                    pg.draw.line(scr, (60, 70, 60), (px, y), (px, GY + oy), 2)
                for yy in range(int(y), int(GY + oy), 14):
                    pg.draw.line(scr, (44, 52, 46), (x0 - 6, yy), (x0 + 6, yy + 14))
                pg.draw.line(scr, (230, 170, 40), (x0 - 20, y), (x1 + 10, y), 3)
                pg.draw.line(scr, (60, 70, 60), (x0, y - 18), (x1 + 10, y), 1)
                pg.draw.line(scr, (60, 70, 60), (x0, y - 18), (x0 - 20, y), 1)
                if int(s.t * 2) % 2:                    # warning light on the jib
                    glow(scr, x1 + 10, y, 6, (90, 10, 10))
        for z in s.plazas:                              # ambush plazas: banner poles at both ends
            for px in (z['x0'] + 6, z['x1'] - 6):
                x = px - cx
                if -20 < x < W + 20:
                    pg.draw.line(scr, (30, 20, 30), (x, GY + oy), (x, GY - 74 + oy), 2)
                    wave = math.sin(s.t * 3 + px) * 2
                    pg.draw.polygon(scr, (170, 20, 34), [(x + 1, GY - 72 + oy), (x + 14 + wave, GY - 68 + oy),
                                                         (x + 13 + wave, GY - 40 + oy), (x + 1, GY - 44 + oy)])
                    g = F_JP.render("戦", False, (20, 4, 8))
                    scr.blit(g, (x + 2 + wave / 2, GY - 64 + oy))
        for c in s.chests:                              # treasure chests on the hidden ledges
            x, y = c[0] - cx, c[1] + oy
            if -20 < x < W + 20:
                lid = -4 if c[2] else 0
                pg.draw.rect(scr, (110, 60, 30), (x, y - 9, 14, 9))
                pg.draw.rect(scr, (200, 160, 60), (x, y - 9, 14, 9), 1)
                pg.draw.rect(scr, (140, 80, 40), (x - 1, y - 13 + lid, 16, 5))
                if not c[2]:
                    glow(scr, x + 7, y - 8, 14, qcol((90, 70, 10), .6 + .3 * math.sin(s.t * 4)))
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
        if not s.arena:
            s.draw_torii(END_X - cx, oy)
            if s.hole:                                  # boss district: the gate is sealed, the cave is the way on
                s.draw_seal(cx, oy)
                s.draw_hole_rim(cx, oy)
            if END_X - cx < W + 40:                     # exit sign above the torii
                a = .6 + math.sin(s.t * 4) * .4
                outlined("封印  SEALED" if s.hole else "出口  EXIT >>", F_JP, qcol((255, 140, 160), a), END_X - cx, gys - 98,
                         center=True, r=1)
        if s.kiosk:
            s.draw_kiosk(s.kiosk['x'] - cx, gys)
        if s.door.get('exit') and s.door['k'] <= 0 and abs(s.pl.x - s.door['x']) < 40:
            s.prompt("LEAVE", s.door['x'] - cx, gys - 84)
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
        s.draw_traps(cx, oy)
        if s.arena:
            s.draw_arena_ledges(cx, oy)
        else:
            for p in s.plats[1:]:
                s.draw_plat(p, cx, oy)
        for e in s.en:                                  # enemies climbing/dropping between rooftops: darker, but never
            if e.trav:                                  # hidden behind a building's wall
                s.draw_enemy(e, cx, oy)
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
            if l[4] == 'heart':                                 # FIELD MEDIC's heart
                glow(scr, x, y, 12, (90, 10, 30))
                for sg in (-1, 1):
                    pg.draw.circle(scr, (255, 60, 90), (int(x + sg * 2), int(y - 1)), 3)
                pg.draw.polygon(scr, (255, 60, 90), [(x - 5, y), (x + 5, y), (x, y + 5)])
                continue
            if l[5] > .55:
                glow(scr, x, y, 10, (60, 45, 10))
            s.draw_coin(x, y, l[4], l[5] * 3)
        for gb in s.gibs:
            s.draw_gib(gb, cx, oy)
        for e in s.en:
            if not e.trav:
                sn = getattr(e, 'sense', 0.0)
                s.draw_enemy(e, cx - (int(math.sin(s.t * 70) * 1.5) if sn > .6 else 0), oy)   # (a shiver as you pass)
                if sn > 0 and not e.dead:
                    outlined("?", F_PS, (200, 200, 255), int(e.x + e.w / 2 - cx), int(e.y - 22 + oy - (1.1 - sn) * 6), center=True, r=1)
                if getattr(e, 'spirit', False) and not e.dead:
                    s.draw_spirit(e, cx, oy)
        for a in s.acid:
            x, y = a[0] - cx, a[1] + oy
            glow(scr, x, y, 12, qcol((80, 255, 90), .6))
            pg.draw.circle(scr, (150, 255, 120), (int(x), int(y)), 4)
        oc, oc2 = BOSS_ORB.get(s.boss.kind if s.boss is not None else '', ((200, 80, 255), (240, 170, 255)))
        for o in s.orbs:
            x, y = o[0] - cx, o[1] + oy
            glow(scr, x, y, 22, qcol(oc, .6))
            pg.draw.circle(scr, oc2, (int(x), int(y)), 5)
        s.draw_boss_fx(cx, oy)
        for w in s.bossw:
            if w[3] > 0:
                x, y = w[0] - cx, GY + oy
                glow(scr, x, y - 6, 16, qcol(w[6], .55))
                pg.draw.polygon(scr, w[6], [(x - 14 * w[2], y), (x, y - 14), (x + 14 * w[2], y)])
        for bw in s.bwaves:
            x, y = bw[0] - cx, bw[1] + oy
            k = 1 - bw[3] / .75
            c = 0 if bw[2] > 0 else math.pi
            glow(scr, x, y, 18, qcol((120, 10, 30), k))
            arc((255, 60, 90), x, y, 12, c, 1.1, 3)
            arc(WHITE, x, y, 12, c, .6, 1)
        s.draw_ghosts(cx, oy)
        if s.superT < 0:
            s.draw_player(cx, oy)
            s.draw_trail(cx, oy)
        for pr in s.proj:                               # shuriken
            x, y = pr[0] - cx, pr[1] + oy
            if len(pr) > 6:                             # a rifle ball: a hot streak
                sp = math.hypot(pr[2], pr[3]) or 1
                tx, ty = x - pr[2] / sp * 12, y - pr[3] / sp * 12
                glow(scr, x, y, 8, (40, 60, 70) if pr[4] else (90, 50, 20))
                pg.draw.line(scr, (120, 255, 255) if pr[4] else (255, 200, 120), (tx, ty), (x, y), 2)
                continue
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
                rx = (6 + (1 - k) * 76) * (d if d in (1, 3) else 1)      # (d = 3: SLAM MASTER's wide wave)
                if d == 3:                                             # (wide but soft: a faint rim fading to nothing)
                    pg.draw.ellipse(scr, qcol((120, 200, 255), .5 * k ** 1.8), (x - rx, y - rx * .2, rx * 2, rx * .4), 1)
                else:
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
        if s.arena and gys < H:                         # the arena floor: old stone slabs / iron / wet concrete / tatami
            acc = ARENAS[s.boss_kind][4]
            for gx in range(-60, W + 60, 40):
                wx = gx - (cx % 40)
                pg.draw.line(scr, tuple(c // 8 for c in acc), (wx, gys + 1), (W / 2 + (wx - W / 2) * 1.6, gys + FLOOR))
            for yy in (8, 20, 38):
                pg.draw.line(scr, tuple(c // 10 for c in acc), (0, gys + yy), (W, gys + yy))
            pg.draw.line(scr, tuple(c * 3 // 5 for c in acc), (0, gys), (W, gys))
            s.draw_arena_haz(cx, oy)
        elif gys < H:
            for lx in s.lamps:                          # light pools on the wet street
                x = lx - cx
                if -60 < x < W + 60:
                    glow(scr, x + 12, gys + 6, 50, (60, 40, 20), .22)
            for gx in range(-60, W + 60, 30):          # 2.5D perspective grid on the street
                wx = gx - (cx % 30)
                pg.draw.line(scr, (22, 10, 34), (wx, gys + 1), (W / 2 + (wx - W / 2) * 1.8, gys + FLOOR))
            for yy in (6, 14, 26, 42):
                pg.draw.line(scr, (18, 8, 28), (0, gys + yy), (W, gys + yy))
            pg.draw.line(scr, s.theme.get('street', (255, 60, 160)), (0, gys), (W, gys))
            glow(scr, W / 2, gys + 1, 240, (30, 8, 26), .03)
        if s.hole:
            s.draw_hole_pit(cx, oy, gys)
        if not s.arena:                                 # (no rain under the street)
            s.draw_rain(gys)
            if getattr(s, 'loc', 0) != 0:                   # (Neon Shinjuku: no cables across the sky)
                scr.blit(s.L['fg'], (-int(cx * 1.25), int(oy * 1.25)))
        if s.freezeT > 0:                               # TIME STOP: the world turns violet and still
            scr.fill((205, 190, 255), special_flags=pg.BLEND_RGB_MULT)
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
        for i in range(getattr(s.pl, 'glass', 0)):                    # glass HP: cyan-gray, gone for good once broken
            x, y = 14 + (s.pl.maxhp + i) * 13, 13
            pts = [(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]
            pg.draw.polygon(scr, INK, [(a + 1, b + 1) for a, b in pts])
            pg.draw.polygon(scr, GLASS, pts)
            pg.draw.polygon(scr, (225, 245, 250), pts, 1)
            pg.draw.line(scr, WHITE, (x - 2, y - 1), (x, y - 3))
        if getattr(s, 'ward', False):                                  # SPIRIT WARD ready
            x = 14 + (s.pl.maxhp + getattr(s.pl, 'glass', 0)) * 13 + 2
            pg.draw.circle(scr, (200, 160, 255), (x, 13), 5, 1)
            pg.draw.circle(scr, (200, 160, 255), (x, 13), 2)
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
            outlined(f"{tr('SUPER')} [{s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'super')}]", F_S, WHITE, 92, 28, r=1)
        if s.skill():                                           # (the cards you took are shown in the pause menu)
            sk = s.skill()
            dc = max(0, s.pl.skcd) / sk[2]
            text(f"{tr(sk[0])} [{s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'skill')}]", F_S, (255, 200, 220), 8, 44)
            pg.draw.rect(scr, INK, (8, 54, 60, 4))
            pg.draw.rect(scr, sk_col(sk) if dc <= 0 else (70, 60, 90), (9, 55, 58 * (1 - dc), 2))
            text(f"{tr('PERK:')} {tr(SKIN_PERKS[s.stats['skin']][0])}", F_S, SKIN_PERKS[s.stats['skin']][2], 8, 61)
        outlined(s.lvl_label(s.lvl), F_PS, WHITE, W // 2, 4, center=True, r=1)
        if s.buff('invis') and not s.arena:                        # SHADOW CLOAK: the spirit-touched you still need
            outlined(f"{tr('SPIRITS')} {s.exit_kills()}/{s.exit_need}", F_S, (150, 230, 255), W // 2, 17, center=True, r=1)
        else:
            outlined(f"{tr('ENEMIES')} {s.lvl_kills}/{s.exit_need}", F_S, (255, 200, 90), W // 2, 17, center=True, r=1)
        pop = s.coinpop / .25                              # Persona-style coin tag
        pg.draw.polygon(scr, INK, [(W - 118, 4), (W - 6, 2), (W - 12, 26), (W - 124, 28)])
        pg.draw.polygon(scr, RED, [(W - 118, 4), (W - 108, 4), (W - 114, 28), (W - 124, 28)])
        glow(scr, W - 96, 15, 10 + int(pop * 6), (60, 45, 10))
        pg.draw.ellipse(scr, (255, 205, 50), (W - 100, 11, 8, 8))
        img = F_PM.render(str(s.score), False, (255, 230, 120) if pop > 0 else WHITE)
        if pop > 0:
            img = pg.transform.scale_by(img, 1 + pop * .3)
        scr.blit(img, (W - 86, 15 - img.get_height() // 2))
        text(f"{tr('KILLS')} {s.kills}", F_S, (255, 120, 140), W - 112, 31)
        text(fmt_time(s.gtime), F_S, (200, 190, 230), W - 52, 31)

    def hint(s):
        """Short control reminder built from the current bindings."""
        kind = 'pad' if s.last_input == 'pad' else 'kb'
        n = lambda a: s.bind_name(kind, a)
        if kind == 'pad':
            return (f"{n('jump')} {tr('jump')}  {tr('DOWN+')}{n('jump')} {tr('slam')}  {n('atk')} {tr('slash')}  "
                    f"{n('parry')} {tr('parry')}  {n('dash')} {tr('dash')}  {n('crouch')} {tr('crouch')}")
        return (f"{n('jump')} jump  {n('down')}+{n('jump')} slam  {n('atk')} slash  {n('parry')} parry  "
                f"{n('dash')} dash  {n('crouch')} crouch")

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
        was = s.sel
        hov, best = None, 1e9                                            # the one row under the mouse (rows overlap a
        for i, (lab, _) in enumerate(items):                             #  little: take the nearest, never two)
            slide = (1 - ease((el - .05 - i * .07) * 4)) * -260
            w, h = font.size(tr(lab))
            r = pg.Rect(x0 + i * dx + slide - 8, y0 + i * dy - 2, w + 16, h + 2)
            if r.collidepoint(mx, my) and abs(my - r.centery) < best:
                hov, best = i, abs(my - r.centery)
        if hov is not None:
            if s.moved and hov != s.sel:
                s.sel, s.selT = hov, s.t
                sfx('sel')
            if s.click and (not TOUCH or hov == was):          # (touch: the first tap only picks it)
                fire = hov
        for i, (lab, _) in enumerate(items):
            slide = (1 - ease((el - .05 - i * .07) * 4)) * -260          # items fly in from the left
            x, y = x0 + i * dx + slide, y0 + i * dy
            on = i == s.sel
            w, h = font.size(tr(lab))
            r = pg.Rect(x - 8, y - 2, w + 16, h + 2)
            if on:
                pop = 1 + .35 * (1 - ease((s.t - s.selT) * 7))
                j = math.sin(s.t * 9) * 1.5
                jag = [(r.left - 8, r.bottom + 3 + j), (r.left + 6, r.top - 5), (r.right + 16, r.top - 2 - j), (r.right + 6, r.bottom + 6)]
                pg.draw.polygon(scr, RED, [(a + 7, b + 5) for a, b in jag])
                pg.draw.polygon(scr, WHITE, jag)
                pg.draw.polygon(scr, WHITE, [(r.right + 12, r.centery - 2), (r.right + 34, r.centery - 10 + j), (r.right + 16, r.centery + 5)])
                pg.draw.polygon(scr, INK, [(r.left - 18, r.centery + 2), (r.left - 6, r.centery - 6), (r.left - 4, r.centery + 6)])
                img = pg.transform.rotate(pg.transform.scale_by(font.render(tr(lab), False, INK), pop), -4)
                scr.blit(img, (r.centerx - img.get_width() // 2, r.centery - img.get_height() // 2))
            else:
                outlined(lab, font, WHITE, x, y - 1)
        if 'ok' in s.act:
            fire = s.sel
        if fire >= 0:
            sfx('sel')
            fn = items[fire][1]
            if wipe:
                s.wipe_to(fn, items[fire][0] if items[fire][0] not in ("QUIT",) else None)
            else:
                fn()

    def portrait(s, P, scale, skin=None, chains=None, crop=(20, 30, 58, 58), want_info=False, S=None):
        """Big outlined portrait of the hero's sprite in a skin (menu / stats / shop), or of any palette S."""
        S = S or s.pal(skin)
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
            if sl > 0:                                          # (swaying right: no dark gap at the screen's left edge)
                scr.blit(s.L['p_red'], (0, 0), (0, 0, sl, H))

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
    def loc_preview(s, i):
        """A wide picture of the location: the real backdrop for the built ones, a painted teaser for the rest."""
        if not hasattr(s, 'loc_pics'):
            s.loc_pics = {}
        if i in s.loc_pics:
            return s.loc_pics[i]
        name, jp, line, seq, (dark, acc) = LOCATIONS[i]
        if seq:                                                 # draw the district's own background off-screen
            keep = s.theme if hasattr(s, 'theme') else None
            s.theme = THEMES[seq[0]]
            s.draw_bg(700 + i * 300, 0)
            s.reflect(GY)
            img = scr.copy()
            if keep is not None:
                s.theme = keep
        else:
            img = pg.Surface((W, H))
            vgrad(img, [(0, tuple(c // 2 for c in dark)), (H, dark)])
            rnd = random.Random(i)
            if i == 2:                                          # forest: rows of dark cedar trunks, mist between them
                for row, (col, n) in enumerate((((14, 40, 26), 18), ((8, 26, 16), 12), ((4, 14, 8), 8))):
                    for _ in range(n):
                        x, w = rnd.randint(-20, W), rnd.randint(6, 14 + row * 8)
                        pg.draw.rect(img, col, (x, 0, w, H))
                        pg.draw.polygon(img, col, [(x - 30, 60 + row * 30), (x + w // 2, 10 + row * 20), (x + w + 30, 60 + row * 30)])
                    glow(img, W // 2, 150 + row * 30, 220, (20, 50, 30), .3)
            elif i == 3:                                        # peaks: layered mountains, snow caps, a moon in the haze
                pg.draw.circle(img, (200, 220, 255), (360, 60), 22)
                for row, col in enumerate(((40, 50, 80), (26, 32, 56), (14, 18, 34))):
                    pts, x = [(0, H)], 0
                    while x < W + 60:
                        pts.append((x, 90 + row * 40 + rnd.randint(-40, 30)))
                        x += rnd.randint(40, 90)
                    pts.append((W, H))
                    pg.draw.polygon(img, col, pts)
                    if row == 0:
                        for a_, b_ in zip(pts[1:-2], pts[2:-1]):
                            if a_[1] < b_[1]:
                                pg.draw.line(img, (220, 230, 250), a_, (a_[0] + 8, a_[1] + 6), 2)
            else:                                               # dojo: temple roofs over a courtyard, warm lamps
                for k, (x, y, w) in enumerate(((60, 130, 160), (260, 110, 180), (160, 160, 200))):
                    pg.draw.polygon(img, (20, 8, 4), [(x - 20, y), (x + w // 2, y - 40), (x + w + 20, y)])
                    pg.draw.rect(img, (34, 16, 8), (x, y, w, 90))
                    for lx in range(x + 14, x + w - 6, 30):
                        glow(img, lx, y + 30, 14, (90, 40, 10))
                        pg.draw.rect(img, (255, 170, 80), (lx - 3, y + 24, 6, 10))
            label = pg.transform.scale_by(F_JPB.render(jp, False, acc), 2)
            label.set_alpha(150)
            img.blit(label, (W // 2 - label.get_width() // 2, H // 2 - label.get_height() // 2))
        s.loc_pics[i] = img
        return img

    def foe_card(s, kind, j, lit=True):
        """One enemy card at its real size: black, white border, the enemy alive on it (idle, wind-up, strike),
        its name on a white tag."""
        cw, ch = 50, 62
        card = pg.Surface((cw, ch), pg.SRCALPHA)
        pg.draw.polygon(card, INK, [(1, 2), (cw - 1, 1), (cw - 2, ch - 1), (2, ch - 1)])
        if lit:
            ph = (s.t * .8 + j * .9) % 3.0
            e = CardFoe(kind)
            if ph < 2.0:
                e.st, e.vx, e.anim = 'chase', 0, s.t * 8 + j
            elif ph < 2.6:
                e.st, e.t = 'wind', e.wind * (1 - (ph - 2.0) / .6)
            else:
                e.st, e.t = 'slash', .18 * (1 - (ph - 2.6) / .4)
            S = dict(PAL_E[kind])
            S.pop('zoom', None)
            img = s.portrait(pose_enemy(e, s.t + j), 1, chains={'_': None}, crop=(23, 36, 50, 50), S=S)
            card.blit(img, (cw // 2 - img.get_width() // 2, ch - 12 - img.get_height()))
            pg.draw.rect(card, WHITE, (3, ch - 12, cw - 6, 10))
            name = F_S.render(tr(KIND_NAMES.get(kind, kind.upper())), False, INK)
            card.blit(name, (cw // 2 - name.get_width() // 2, ch - 13), pg.Rect(0, 0, cw - 8, 12))
        else:
            q = F_PM.render("?", False, (90, 80, 100))
            card.blit(q, (cw // 2 - q.get_width() // 2, 18))
        pg.draw.polygon(card, WHITE, [(1, 2), (cw - 1, 1), (cw - 2, ch - 1), (2, ch - 1)], 1)
        return card

    def enemy_deck(s, i, rx, kk):
        """Every enemy of the location, as a deck: the top card (on the right) is replaced every 2.2s by the next one,
        laid down on top of it; the older ones shift back under it."""
        seq = LOCATIONS[i][3]
        if seq:
            w = {}
            for th in seq:
                for k_, v in THEMES[th]['roster'].items():
                    w[k_] = w.get(k_, 0) + v
            kinds = sorted(w, key=lambda k_: -w[k_])
        else:
            kinds = [None, None, None]
        n = len(kinds)
        per = 2.2
        di = int(s.t / per)
        f = (s.t / per) % 1
        land = ease(min(1, f / .28))                             # the new card dropping onto the pile
        slots = [(rx + 84, 168, 6), (rx + 60, 162, -5), (rx + 36, 166, 7), (rx + 16, 164, -6)]   # top .. bottom
        for j in (3, 2, 1, 0):                                   # draw the bottom of the pile first
            kind = kinds[(di - j) % n]
            a0 = slots[min(3, j)]
            a1 = slots[max(0, j - 1)] if j > 0 else slots[0]
            if j == 3 and land >= 1:
                continue                                         # it has gone under the pile
            x = lerp(a1[0], a0[0], land) if j > 0 else a0[0]
            y = lerp(a1[1], a0[1], land) if j > 0 else a0[1] - (1 - land) * 70
            ang = lerp(a1[2], a0[2], land) if j > 0 else a0[2] + (1 - land) * 18
            img = s.foe_card(kind, j, lit=bool(seq) and j < 3)
            pg.draw.polygon(img, (0, 0, 0, 0), [(0, 0), (1, 0), (0, 1)])
            a_ = round(ang / 3) * 3                              # (whole steps: the pixels stay sharp)
            img = pg.transform.rotate(img, a_)
            sh = pg.transform.rotate(s.card_shadow(), a_)
            y += int((1 - kk) * 40 * (j + 1))
            scr.blit(sh, (x - sh.get_width() // 2 + 4, y - sh.get_height() // 2 + 4))
            scr.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
        if f < .02 and getattr(s, 'deck_snd', -1) != di and seq:
            s.deck_snd = di
            sfx('throw')

    def card_shadow(s):
        if not hasattr(s, '_cshadow'):
            s._cshadow = pg.Surface((50, 62), pg.SRCALPHA)
            pg.draw.polygon(s._cshadow, (120, 10, 24), [(1, 2), (49, 1), (48, 61), (2, 61)])
        return s._cshadow

    def enemy_cards(s, i):
        """The three enemies you meet most in that location, alive on their cards: idling, then winding up and striking."""
        seq = LOCATIONS[i][3]
        if not seq:
            return []
        w = {}
        for th in seq:
            for k_, v in THEMES[th]['roster'].items():
                w[k_] = w.get(k_, 0) + v
        kinds = sorted(w, key=lambda k_: -w[k_])[:3]
        if not hasattr(s, 'ecard_bg'):
            s.ecard_bg = {}
        out = []
        for j, kind in enumerate(kinds):
            col = (90, 220, 255), (150, 255, 90), (255, 200, 80)
            if kind not in s.ecard_bg:
                bg = pg.Surface((92, 96))
                vgrad(bg, [(0, (30, 16, 40)), (96, tuple(c // 4 for c in col[j]))])
                s.ecard_bg[kind] = bg
            card = s.ecard_bg[kind].copy()
            ph = (s.t * .8 + j * .9) % 3.0                          # idle 2s, wind-up .6s, strike .4s
            e = CardFoe(kind)
            if ph < 2.0:
                e.st, e.vx, e.anim = 'chase', (90 if j == 1 else 0), s.t * 8 + j
            elif ph < 2.6:
                e.st, e.t = 'wind', e.wind * (1 - (ph - 2.0) / .6)
            else:
                e.st, e.t = 'slash', .18 * (1 - (ph - 2.6) / .4)
            P = pose_enemy(e, s.t + j)
            S = dict(PAL_E[kind])
            S.pop('zoom', None)
            img = s.portrait(P, 2.0, chains={'_': None}, crop=(24, 40, 46, 47), S=S)
            card.blit(img, (46 - img.get_width() // 2, 96 - img.get_height()))
            pg.draw.rect(card, col[j], card.get_rect(), 2)
            out.append(card)
        return out

    def boss_cards(s):
        """The three act bosses as tilted portrait cards (made once)."""
        if not hasattr(s, 'bcards'):
            s.bcards = []
            for kind, col in zip(ACT_BOSS, ((90, 220, 255), (150, 255, 90), (255, 200, 80))):
                S = dict(PAL_E[kind])
                S.pop('zoom', None)
                img = s.portrait(pose_idle(.7), 2.0, chains={'_': None}, crop=(24, 24, 48, 62), S=S)
                card = pg.Surface((img.get_width() + 8, img.get_height() + 8))
                vgrad(card, [(0, (30, 16, 40)), (card.get_height(), tuple(c // 4 for c in col))])
                card.blit(img, (4, 4))
                pg.draw.rect(card, col, card.get_rect(), 2)
                s.bcards.append(card)
        return s.bcards

    def loc_track(s, was):
        """Remember a change of location, and which way it went (the name rolls in from that side)."""
        if s.locsel != was:
            s.loc_from, s.loc_dir, s.loc_chT = was, (1 if s.locsel > was else -1), s.t

    def loc_name_img(s, i):
        """The location's name in ransom letters: one word per row, each rising to the right, the rows close together.
        Letters are laid out one by one (no scaling, no rotating the whole word), so they stay sharp."""
        words = tr(LOCATIONS[i][0]).split(' ')
        out = pg.Surface((124, H - 40), pg.SRCALPHA)
        base = 112 - (len(words) - 1) * 22
        for j, word in enumerate(words):
            fonts = [F_P]
            tmp = pg.Surface((400, 120), pg.SRCALPHA)
            w = ransom(word, 0, 60, fonts, 51 + i * 7 + j, s.t, tilt=-8, surf=tmp, rise=.34)
            if w > 96:                                           # a long word: the smaller letters
                fonts = [F_PS]
                tmp = pg.Surface((400, 120), pg.SRCALPHA)
                w = ransom(word, 0, 60, fonts, 51 + i * 7 + j, s.t, tilt=-8, surf=tmp, rise=.34)
            out.blit(tmp, (6, base + j * 44 - 60))
        return out

    def loc_title(s, px):
        """Left column: the chosen location's name; on a change it rolls in from below (going down) or above."""
        e = ease(min(1, (s.t - getattr(s, 'loc_chT', -9)) * 4))
        d = getattr(s, 'loc_dir', 1)
        scr.set_clip(pg.Rect(0, 34, 116 + px, H - 34))
        items = [(s.locsel, (1 - e) * d * H)]
        if e < 1:
            items.append((getattr(s, 'loc_from', s.locsel), -e * d * H))
        for i, off in items:
            scr.blit(s.loc_name_img(i), (-2 - px // 3, 36 + off))
        scr.set_clip(None)

    def loc_open(s, i):
        """Neon Shinjuku is open from the start; each next location after a standard run of the one before it."""
        return i == 0 or (s.loc_open(i - 1) and (i - 1) in s.stats.get('cleared', []))

    def st_locsel(s, dt):
        """START: where the run takes place and how long it lasts (Persona-style panel cut in over the menu)."""
        for i in range(len(LOCATIONS)):                         # (pictures are drawn on the screen first, so before anything else)
            s.loc_preview(i)
        s.persona_bg()
        el = s.t - s.state_t
        mx, my = pg.mouse.get_pos()
        if not hasattr(s, 'locsel'):
            s.locsel, s.locmode, s.locscroll = 0, 0, 0.0
        if el < .02:
            s.selT = s.t
        n = len(LOCATIONS)
        was = s.locsel
        if 'up' in s.act:
            s.locsel, s.selT = (s.locsel - 1) % n, s.t
            sfx('sel')
        if 'down' in s.act:
            s.locsel, s.selT = (s.locsel + 1) % n, s.t
            sfx('sel')
        s.loc_track(was)
        if s.act & {'left', 'right'}:
            s.locmode = 1 - s.locmode
            sfx('sel')
        wh = getattr(s, 'wheel', 0)
        s.wheel = 0
        start = 'ok' in s.act
        if s.corner_back(mx, my) or 'back' in s.act:
            sfx('sel')
            s.wipe_to(lambda: s.go('menu', 0))
            return
        k = ease(el * 4)                                        # the red panel slashes in from the right
        px = int((1 - k) * W)
        panel = [(118 + px, 34), (W - 6 + px, 26), (W - 12 + px, H - 8), (110 + px, H - 4)]
        pg.draw.polygon(scr, INK, [(a + 7, b + 6) for a, b in panel])
        pg.draw.polygon(scr, RED, panel)
        pg.draw.polygon(scr, WHITE, panel, 2)
        if el < .3:                                             # the slash itself
            sx = W - int(el / .3 * (W + 200))
            pg.draw.polygon(scr, WHITE, [(sx, 0), (sx + 26, 0), (sx - 90, H), (sx - 116, H)])
        s.loc_title(px)
        # ---- the list (left half), scrolled to keep the selected one in view
        CH, top = 64, 44
        want = max(0, min(n * CH - (H - 56), s.locsel * CH - 70))
        s.locscroll += ((want - wh * 40) - s.locscroll) * min(1, dt * 12) if not wh else -wh * 40
        s.locscroll = max(0.0, min(n * CH - (H - 56), s.locscroll))
        clip = pg.Rect(124 + px, 36, 226, H - 48)
        scr.set_clip(clip)
        for i, (name, jp, line, seq, (dark, acc)) in enumerate(LOCATIONS):
            a = ease((el - .1 - i * .06) * 4)
            x, y = 132 + px + int((1 - a) * 300), top + i * CH - int(s.locscroll)
            on = i == s.locsel
            box = pg.Rect(x, y, 212, CH - 8)
            if box.collidepoint(mx, my) and clip.collidepoint(mx, my) and s.moved and not on:
                was = s.locsel
                s.locsel, s.selT = i, s.t
                sfx('sel')
                s.loc_track(was)
            pg.draw.rect(scr, WHITE if on else (34, 24, 40), box.move(4, 3) if on else box)
            pg.draw.rect(scr, (70, 64, 76) if not on else INK, box)
            strip = pg.transform.smoothscale(s.loc_preview(i).subsurface((0, 60, W, 70)), (200, 22))
            if not seq:
                strip.fill((120, 120, 120), special_flags=pg.BLEND_MULT)
            scr.blit(strip, (x + 6, y + 5))
            pg.draw.rect(scr, acc if on else (110, 100, 120), (x + 6, y + 5, 200, 22), 1)
            outlined(tr(name), F_S, WHITE, x + 10, y + 7, r=1)
            if not seq:                                         # not built yet
                outlined(tr("COMING SOON"), F_PS, (170, 160, 180), x + 106, y + 32, center=True, r=1)
                continue
            lk = not s.loc_open(i)                              # locked: chained shut until the location before is cleared
            for m_, (lab, sub) in enumerate((("STANDARD RUN", "15 districts"), ("INFINITE RUN", "No limit, random bosses"))):
                bx = pg.Rect(x + 6 + m_ * 102, y + 32, 98, 18)
                hot = on and s.locmode == m_
                if bx.collidepoint(mx, my) and clip.collidepoint(mx, my):
                    if s.moved and not hot:
                        s.locsel, s.locmode, s.selT = i, m_, s.t
                        sfx('sel')
                    if s.click:
                        s.locsel, s.locmode, start = i, m_, True
                pts = [(bx.x, bx.y), (bx.right, bx.y - 1), (bx.right - 3, bx.bottom), (bx.x - 3, bx.bottom + 1)]
                if hot:
                    pg.draw.polygon(scr, RED, [(a_ + 3, b_ + 2) for a_, b_ in pts])
                locked = m_ == 1 and i not in s.stats.get('cleared', []) and not lk   # infinite: after a standard run here
                pg.draw.polygon(scr, (150, 144, 156) if locked else (WHITE if hot else (210, 206, 214)), pts)
                img = F_PS.render(tr(lab), False, INK)
                if img.get_width() > 92:
                    img = F_S.render(tr(lab), False, INK)
                scr.blit(img, (bx.centerx - img.get_width() // 2, bx.centery - img.get_height() // 2))
                if locked:                                      # a chain across the infinite run
                    chain(scr, (bx.x - 2, bx.centery + 2), (bx.right + 2, bx.centery - 2))
                    padlock(scr, bx.centerx, bx.centery)
            if lk:                                              # the whole location chained: two chains crossed, a padlock
                shade = pg.Surface((box.w, box.h), pg.SRCALPHA)
                shade.fill((10, 4, 14, 120))
                scr.blit(shade, box)
                chain(scr, (box.x + 2, box.y + 4), (box.right - 2, box.bottom - 4))
                chain(scr, (box.right - 2, box.y + 4), (box.x + 2, box.bottom - 4))
                padlock(scr, box.centerx, box.centery + 2)
        scr.set_clip(None)
        tot = n * CH                                            # the scroll bar
        bar_h = (H - 48) * min(1, (H - 56) / tot)
        pg.draw.rect(scr, INK, (116 + px + 6, 40, 4, H - 52))
        pg.draw.rect(scr, WHITE, (116 + px + 6, 40 + (H - 52 - bar_h) * (s.locscroll / max(1, tot - (H - 56))), 4, bar_h))
        # ---- the preview (right): the place, the bosses waiting there, one line
        i = s.locsel
        name, jp, line, seq, (dark, acc) = LOCATIONS[i]
        kk = ease((s.t - s.selT) * 5)
        rx = 356 + px + int((1 - kk) * 60)
        pic = s.loc_preview(i).subsurface((170, 70, 114, 80)).copy()
        if not seq:
            pic.fill((120, 120, 120), special_flags=pg.BLEND_MULT)
        frame = pg.Rect(rx, 46, 114, 80)
        pg.draw.rect(scr, INK, frame.move(4, 4))
        scr.blit(pic, frame)
        pg.draw.rect(scr, WHITE, frame, 2)
        outlined(jp, F_JP, acc, rx + 4, 50, r=1)
        s.enemy_deck(i, rx, kk)
        for j, word in enumerate((tr(line).rsplit(' ', 1) if ' ' in tr(line) else [tr(line)])):   # the line, on two black tags
            img = F_PS.render(word, False, WHITE)
            tx, ty = min(rx + 4 + j * 20, W - 18 - img.get_width()), 210 + j * 18
            pg.draw.polygon(scr, INK, [(tx - 6, ty - 2), (tx + img.get_width() + 6, ty - 4), (tx + img.get_width() + 3, ty + 18), (tx - 9, ty + 19)])
            scr.blit(img, (tx, ty))
        if start:
            if not seq or not s.loc_open(s.locsel) or (s.locmode == 1 and s.locsel not in s.stats.get('cleared', [])):
                sfx('deny')
                s.boss_msg = ('', 0.0)
                return
            sfx('slash')
            s.loc, s.endless = s.locsel, s.locmode == 1
            s.wipe_to(s.new_run)

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
        s.p_items([("START", lambda: s.go('locsel', 0)), ("STATS", lambda: s.go('stats', 0)),
                   ("SETTINGS", lambda: s.go('settings', 0)), ("QUIT", s.quit)], 36, 124, dx=14, dy=31)
        ok = ANDROID or os.path.exists(os.path.join(ASSETS, 'level.mp3'))
        vtxt = VERSION + ("" if ok else "  - level.mp3 NOT FOUND in " + ASSETS)
        text(vtxt, F_S, (70, 130, 100) if ok else (255, 90, 90), W - 6 - F_S.size(tr(vtxt))[0], H - 14)

    SETTING_ROWS = [('SOUND', 'MASTER VOLUME', 'master', 'slider'), ('', 'MUSIC', 'music', 'slider'),
                    ('', 'EFFECTS', 'sfx', 'slider'), ('VIDEO', 'FULLSCREEN', 'fullscreen', 'toggle'),
                    ('', 'SCREEN SHAKE', 'shake', 'toggle'), ('', 'RAIN', 'rain', 'rain'),
                    ('', 'CRT FILTER', 'crt', 'toggle'), ('INPUT', 'GAMEPAD VIBRATION', 'rumble', 'toggle'),
                    ('', 'CONTROLS', None, 'open'), ('GAME', 'LANGUAGE', 'lang', 'lang'), ('', 'DIFFICULTY', 'diff', 'diff'),
                    ('', 'IMMORTALITY', 'god', 'toggle'), ('', 'ADMIN', 'admin', 'toggle')]   # (testing)
    SET_CATS = (('SOUND', "音", "Music and blade volume"), ('VIDEO', "映", "Screen, rain, CRT glow"),
                ('INPUT', "操", "Gamepad and keys"), ('GAME', "遊", "Language and tests"))

    def cat_rows(s, ci):
        """The settings rows of one category (the SETTING_ROWS between its section tag and the next)."""
        out, cur = [], None
        for row in s.SETTING_ROWS:
            if row[0]:
                cur = row[0]
            if cur == s.SET_CATS[ci][0]:
                out.append(row)
                if row[2] == 'admin' and s.settings.get('admin'):   # the admin list drops down under its switch
                    out += ADMIN_ROWS
        if ANDROID:                                             # (no window, no key bindings, no gamepad on a phone)
            out = [r for r in out if r[2] not in ('fullscreen', 'rumble') and r[1] != 'CONTROLS']
        if TOUCH and s.SET_CATS[ci][0] == 'INPUT':
            out += [('', 'TOUCH LAYOUT', 'touchedit', 'action'), ('', 'CALIBRATE TOUCH', 'tcal', 'action'),
                    ('', 'FLOATING STICK', 'float_stick', 'toggle'), ('', 'BUTTON OPACITY', 'touch_alpha', 'slider')]
        return out

    def corner_back(s, mx, my, on=False):
        """The "< BACK" tag in the top-left corner (as on the stats screen). Returns True when clicked."""
        r = pg.Rect(14, 6, 76, 22)
        hov = r.collidepoint(mx, my)
        on = on or hov
        k = ease((s.t - s.state_t) * 4)
        r = r.move(int((1 - k) * -120), 0)
        pts = [(r.x, r.y), (r.right, r.y - 2), (r.right - 4, r.bottom), (r.x - 4, r.bottom + 2)]
        if on:
            pg.draw.polygon(scr, RED, [(a + 4, b + 3) for a, b in pts])
        pg.draw.polygon(scr, WHITE if on else INK, pts)
        img = F_PS.render(tr("< BACK"), False, INK if on else WHITE)
        scr.blit(img, (r.centerx - img.get_width() // 2, r.y + 2))
        return hov and s.click

    def row_text(s, txt, selected, x, y):
        txt = tr(txt)
        if selected:                                    # black on the white highlight
            scr.blit(F_S.render(txt, False, INK), (x, y))
        else:
            text(txt, F_S, WHITE, x, y)

    def change_setting(s, row, delta, mx=None):
        global LANG
        _, _, key, kind = row
        st = s.settings
        if kind == 'lang':
            st['lang'] = LANG = 'en' if LANG == 'ru' else 'ru'
            s.save_settings()
            return
        if kind == 'slider':
            st[key] = round(max(0, min(1, (mx if mx is not None else st[key] + delta * .1))), 2)
        elif kind == 'toggle':
            st[key] = not st[key]
        elif kind == 'rain':
            st[key] = (st[key] + (delta or 1)) % len(RAIN_LEVELS)
        elif kind == 'diff':
            st[key] = (st.get(key, 2) + (delta or 1)) % len(DIFFS)
        elif kind == 'cycle':
            st[key] = (st.get(key, 0) + (delta or 1)) % len(ADMIN_CYCLE[key])
        elif kind == 'action' and key == 'touchedit':           # move / resize the on-screen controls
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
        elif kind == 'action' and key == 'teleport':            # admin: pick a location / district / boss to jump to
            sfx('sel')
            s.set_keep = True
            s.wipe_to(lambda: s.go('teleport', 0))
            return
        elif kind == 'action':                                  # admin buttons: they change the save itself
            sv = s.stats
            if key == 'skins_all':
                sv['skins'] = list(SKINS)
            elif key == 'skins_clear':
                sv['skins'], sv['skin'] = ['shadow'], 'shadow'
            elif key == 'upg_all':
                sv['upg'] = {sid: {u[0]: len(u[4]) for u in upgrade_list(sid)} for sid in SKINS}
            elif key == 'upg_clear':
                sv['upg'] = {}
            elif key == 'maps_all':
                sv['cleared'] = list(range(len(LOCATIONS)))
            elif key == 'maps_clear':
                sv['cleared'] = []
            save_stats(sv)
            sfx('buy')
            s.boss_msg = ('DONE', 1.0)
            return
        elif kind == 'open':
            s.set_keep = True                                   # come back into INPUT, not the category list
            s.wipe_to(lambda: s.go('controls', 0))
            return
        else:
            s.wipe_to(lambda: s.go('menu', 0))
            return
        s.apply_settings()
        s.save_settings()
        sfx('sel')
        if key == 'rumble' and st[key]:
            s.rumble(.6, .6, 200)

    def admin_teleport(s, loc, lvl, boss=None):
        """Admin: start a run straight in a location's district - or right in the arena of one of its bosses."""
        s.loc, s.endless = loc, False
        s.new_run()
        s.admin_run = True                                      # (a teleported run never opens a location)
        s.lvl = lvl
        s.build_level()
        if boss:                                                # (the boss districts are 5, 10 and 15)
            s.boss_kind = boss
            s.enter_arena()
            s.go('play', 0)
            s.fade = .5
        else:
            s.start_level()

    def st_teleport(s, dt):
        """Admin teleport: location and district at the top, every boss of every location in a grid below."""
        s.persona_bg()
        el = s.t - s.state_t
        mx, my = pg.mouse.get_pos()
        if not hasattr(s, 'tp_loc'):
            s.tp_loc, s.tp_lvl = 0, 1
        ransom("TELEPORT", 120, 14, [F_PB, F_P], 47, s.t, tilt=-6)
        nl = len(LOCATIONS)
        n = 3 + nl * 3
        s.sel %= n
        s.nav(n)
        fire, delta = 'ok' in s.act, 0
        if s.corner_back(mx, my) or 'back' in s.act:
            sfx('sel')
            s.set_keep = True                                   # back into the GAME settings, admin list open
            s.wipe_to(lambda: s.go('settings', 0))
            return
        if 'left' in s.act or 'right' in s.act:
            d = 1 if 'right' in s.act else -1
            if s.sel < 2:
                delta = d
            elif s.sel >= 3:                                     # in the boss grid: left / right jumps a column
                s.sel = 3 + (s.sel - 3 + d * 3) % (nl * 3)
                s.selT = s.t
                sfx('sel')

        def hover(i, r):
            if r.collidepoint(mx, my):
                if s.moved and s.sel != i:
                    s.sel, s.selT = i, s.t
                    sfx('sel')
                return True
            return False

        a = ease(el * 4)
        for i, (lab, val) in enumerate((("LOCATION", tr(LOCATIONS[s.tp_loc][0])), ("DISTRICT", f"{s.tp_lvl} / {LEVELS}"))):
            x, y, w = 40 + i * 6 - int((1 - a) * 400), 48 + i * 26, 300
            on = s.sel == i
            r = pg.Rect(x - 6, y - 2, w, 22)
            bar = [(x, y), (x + w, y - 2), (x + w - 6, y + 19), (x - 6, y + 21)]
            if on:
                pg.draw.polygon(scr, RED, [(px + 5, py + 4) for px, py in bar])
            pg.draw.polygon(scr, WHITE if on else INK, bar)
            ink = INK if on else WHITE
            scr.blit(F_PS.render(tr(lab), False, ink), (x + 10, y + 2))
            img = F_PS.render(val, False, ink)
            vx = x + 200
            scr.blit(img, (vx - img.get_width() // 2, y + 2))
            for sgn, ax in ((-1, vx - 86), (1, vx + 80)):        # the < > arrows, clickable
                ar = pg.Rect(ax - 2, y, 12, 18)
                hov = ar.collidepoint(mx, my)
                pts = [(ax + 8, y + 4), (ax, y + 9), (ax + 8, y + 14)] if sgn < 0 else [(ax, y + 4), (ax + 8, y + 9), (ax, y + 14)]
                pg.draw.polygon(scr, RED if hov else ink, pts)
                if hov and s.click:
                    s.sel, delta = i, sgn
            if hover(i, r) and s.click and not delta:
                delta = 1
        if delta and s.sel == 0:
            s.tp_loc = (s.tp_loc + delta) % nl
            sfx('sel')
        elif delta and s.sel == 1:
            s.tp_lvl = (s.tp_lvl - 1 + delta) % LEVELS + 1
            sfx('sel')
        x, y = 362 - int((1 - a) * 300), 54                       # the GO button
        on = s.sel == 2
        r = pg.Rect(x - 6, y - 4, 104, 34)
        box = [(x, y), (x + 96, y - 4), (x + 90, y + 28), (x - 6, y + 30)]
        if on:
            pg.draw.polygon(scr, RED, [(px + 6, py + 5) for px, py in box])
        pg.draw.polygon(scr, WHITE if on else INK, box)
        pg.draw.polygon(scr, WHITE, box, 1)
        img = F_P.render(tr("GO"), False, INK if on else WHITE)
        scr.blit(img, (x + 45 - img.get_width() // 2, y + 13 - img.get_height() // 2))
        if hover(2, r) and s.click:
            fire = True
        go = None
        if fire and s.sel == 2:
            go = (s.tp_loc, s.tp_lvl, None)
        outlined(tr("BOSSES"), F_PM, WHITE, 20, 104, r=1)        # every boss, one column per location
        cw = (W - 30) // nl
        for li in range(nl):
            x0 = 15 + li * cw
            acc = LOCATIONS[li][4][1]
            yb = 124 + int((1 - ease((el - .1 - li * .05) * 4)) * 200)
            pg.draw.polygon(scr, acc, [(x0 + 2, yb), (x0 + cw - 4, yb - 2), (x0 + cw - 6, yb + 12), (x0, yb + 13)])
            jp = F_JP.render(LOCATIONS[li][1], False, INK)
            scr.blit(jp, (x0 + cw // 2 - jp.get_width() // 2, yb))
            for bi, kind in enumerate(LOC_BOSSES[li]):
                i = 3 + li * 3 + bi
                on = s.sel == i
                by = yb + 18 + bi * 40
                r = pg.Rect(x0, by, cw - 6, 36)
                box = [(x0 + 2, by), (x0 + cw - 6, by - 2), (x0 + cw - 8, by + 34), (x0, by + 36)]
                if on:
                    pg.draw.polygon(scr, RED, [(px + 4, py + 4) for px, py in box])
                pg.draw.polygon(scr, WHITE if on else INK, box)
                pg.draw.polygon(scr, acc, box, 1)
                ink = INK if on else WHITE
                words = tr(BOSS_TITLES[kind]).split(' ')
                lines = [' '.join(words)] if F_S.size(' '.join(words))[0] <= cw - 14 else [' '.join(words[:len(words) // 2 or 1]),
                                                                                           ' '.join(words[len(words) // 2 or 1:])]
                for j, ln in enumerate(lines):
                    img = F_S.render(ln, False, ink)
                    scr.blit(img, (x0 + (cw - 6) // 2 - img.get_width() // 2, by + 3 + j * 10), pg.Rect(0, 0, cw - 10, 12))
                tag = F_S.render(f"{tr('DISTRICT')} {5 * (bi + 1)}", False, (150, 30, 50) if on else (150, 140, 170))
                scr.blit(tag, (x0 + (cw - 6) // 2 - tag.get_width() // 2, by + 24))
                if hover(i, r) and s.click:
                    fire = True
                if fire and s.sel == i:
                    go = (li, 5 * (bi + 1), kind)
        if go:
            sfx('slash')
            s.wipe_to(lambda go=go: s.admin_teleport(*go))

    def st_settings(s, dt):
        """Persona-style settings: four category buttons (sound, video, input, game), each opening its own list."""
        if getattr(s, 'set_seen', None) != s.state_t:          # just arrived: start on the category list
            s.set_seen = s.state_t
            if not getattr(s, 'set_keep', False):
                s.set_cat = None
            s.set_keep = False
            s.cat_t = s.t
            if s.set_cat is not None:
                s.sel = 0
        s.persona_bg()
        mx, my = pg.mouse.get_pos()
        if s.set_cat is None:
            s.settings_cats(mx, my)
        else:
            s.settings_rows(mx, my)

    def settings_cats(s, mx, my):
        el = s.t - s.cat_t
        ransom("SETTINGS", 120, 14, [F_PB, F_P], 29, s.t, tilt=-6)
        n = len(s.SET_CATS)
        s.sel %= n
        s.nav(n)
        go_in = 'ok' in s.act
        if s.corner_back(mx, my) or 'back' in s.act:
            sfx('sel')
            s.wipe_to(lambda: s.go('menu', 0))
            return
        for i, (name, jp, sub) in enumerate(s.SET_CATS):
            a = ease((el - .05 - i * .06) * 4)
            x, y = 34 + i * 22 - int((1 - a) * 320), 62 + i * 46
            on = i == s.sel
            w, h = 214, 36
            r = pg.Rect(x - 6, y - 4, w, h)
            if r.collidepoint(mx, my):
                if s.moved and not on:
                    s.sel, s.selT = i, s.t
                    sfx('sel')
                if s.click and (not TOUCH or on):
                    s.sel, go_in = i, True
            pop = 1 + .25 * (1 - ease((s.t - s.selT) * 7)) if on else 1
            j = math.sin(s.t * 9) * 1.5 if on else 0
            box = [(x, y), (x + w, y - 3 - j), (x + w - 10, y + h), (x - 8, y + h + 2)]
            if on:                                               # red shadow kicked out behind, a white blade on top
                pg.draw.polygon(scr, RED, [(px + 8, py + 6) for px, py in box])
                pg.draw.polygon(scr, WHITE, box)
                pg.draw.polygon(scr, INK, [(x + w - 4, y + 6), (x + w + 22, y + 10 + j), (x + w - 2, y + 18)])
            else:
                pg.draw.polygon(scr, INK, box)
                pg.draw.polygon(scr, (90, 70, 110), box, 1)
            jimg = pg.transform.scale_by(F_JPB.render(jp, False, RED if on else (120, 30, 50)), 1.6)
            scr.blit(jimg, (x + w - 50, y + h // 2 - jimg.get_height() // 2))
            img = F_P.render(tr(name), False, INK if on else WHITE)
            img = pg.transform.rotate(pg.transform.scale_by(img, pop), -3)
            scr.blit(img, (x + 10, y + h // 2 - img.get_height() // 2 - 2))
            if on:
                text(tr(sub), F_S, (60, 40, 70), x + 12, y + h - 9)
        ci = s.sel                                               # the preview card: what is inside, slid in from the right
        k = ease((s.t - s.selT) * 5)
        cx_ = 300 + int((1 - k) * 200)
        card = [(cx_, 64), (cx_ + 166, 58), (cx_ + 158, 224), (cx_ - 6, 230)]
        pg.draw.polygon(scr, RED, [(px + 6, py + 5) for px, py in card])
        pg.draw.polygon(scr, INK, card)
        pg.draw.polygon(scr, WHITE, card, 2)
        outlined(tr(s.SET_CATS[ci][0]), F_PM, WHITE, cx_ + 12, 68, r=1)
        prow = s.cat_rows(ci)
        step = max(13, min(22, 118 // max(1, len(prow))))         # (a long list is packed tighter...)
        fit = min(len(prow), 118 // step)
        if fit < len(prow):                                      # (...and what still doesn't fit becomes "+N")
            fit -= 1
        for i, row in enumerate(prow[:fit]):
            yy = 98 + i * step
            pg.draw.line(scr, (80, 60, 100), (cx_ + 10, yy + step - 7), (cx_ + 150, yy + step - 8))
            text(tr(row[1]), F_S, (220, 210, 240), cx_ + 12, yy + 2)
            text(s.setting_value(row), F_S, (0, 220, 255), cx_ + 150 - F_S.size(s.setting_value(row))[0], yy + 2)
        if fit < len(prow):
            text(f"+{len(prow) - fit}", F_S, (150, 140, 170), cx_ + 12, 98 + fit * step + 2)
        if go_in:                                                # in through the transition, with the category's own icon

            def enter(ci=ci):
                s.set_cat, s.cat_t, s.sel = ci, s.t, 0
            s.wipe_to(enter, s.SET_CATS[ci][0])

    def setting_value(s, row):
        kind, key = row[3], row[2]
        if kind == 'slider':
            return f"{int(round(s.settings[key] * 100))}%"
        if kind == 'lang':
            return "РУССКИЙ" if LANG == 'ru' else "ENGLISH"
        if kind == 'rain':
            return tr(RAIN_LEVELS[s.settings[key]][0])
        if kind == 'diff':
            return tr(DIFFS[s.settings.get(key, 2)][0])
        if kind == 'toggle':
            return tr("ON" if s.settings[key] else "OFF")
        if kind == 'cycle':
            return f"x{ADMIN_CYCLE[key][s.settings.get(key, 0)]:g}"
        if kind == 'action':
            return ">>" if key in ('teleport', 'touchedit', 'tcal') else tr("DO IT")
        return ">>"

    def settings_rows(s, mx, my):
        el = s.t - s.cat_t
        name, jp, _ = s.SET_CATS[s.set_cat]
        k_in = ease(el * 5)
        slash = int((1 - k_in) * W)                              # the category opens with a red katana slash across the screen
        if el < .35:
            pg.draw.polygon(scr, RED, [(W - slash - 60, 0), (W - slash + 40, 0), (W - slash - 120, H), (W - slash - 220, H)])
        ransom(name, 120, 14, [F_PB, F_P], 41 + s.set_cat, s.t, tilt=-6)
        jimg = pg.transform.scale_by(F_JPB.render(jp, False, (120, 20, 40)), 4)
        jimg.set_alpha(110)
        scr.blit(jimg, (W - jimg.get_width() - 10, H - jimg.get_height() - 4))
        rows = s.cat_rows(s.set_cat)
        n = len(rows)
        s.sel %= n
        s.nav(n)
        row = rows[s.sel]
        if 'left' in s.act or 'right' in s.act:
            if row[3] in ('slider', 'toggle', 'rain', 'lang', 'cycle', 'diff'):
                s.change_setting(row, 1 if 'right' in s.act else -1)
        compact = n > 6                                          # the admin list open: smaller rows
        dy, rh, fnt = ((11 if n > 17 else (12 if n > 15 else (14 if n > 13 else 15))), (10 if n > 17 else 11 if n > 15 else (12 if n > 13 else 13)), F_S) if compact else (30, 19, F_PS)
        if 'ok' in s.act:
            s.change_setting(row, 1)
        if s.corner_back(mx, my) or 'back' in s.act:
            sfx('sel')
            s.set_cat, s.cat_t, s.sel, s.selT = None, s.t, s.set_cat, s.t
            return
        for i, (sec, lab, key, kind) in enumerate(rows):
            a = ease((el - .08 - i * (.02 if compact else .05)) * 5)
            sub = (sec, lab, key, kind) in ADMIN_ROWS
            x, y, w = 50 + int((1 - a) * 90) + (i * 2 if compact else i * 6) + (22 if sub else 0), ((40 if n > 17 else (44 if n > 15 else 52)) if compact else 62) + i * dy, 388 - (22 if sub else 0)
            on = i == s.sel
            r = pg.Rect(x - 6, y - 2, w, min(rh + 3, dy))
            vx = x + 196 - (22 if sub else 0)                    # value area
            if r.collidepoint(mx, my) and s.moved and not on:
                s.sel, s.selT = i, s.t
                sfx('sel')
            bar = [(x, y), (x + w, y - 2), (x + w - 6, y + rh), (x - 6, y + rh + 2)]
            if on:
                j = math.sin(s.t * 9)
                pg.draw.polygon(scr, RED, [(x + 5, y + 5), (x + w + 5, y + 2 + j), (x + w - 1, y + rh + 5), (x - 1, y + rh + 7)])
                pg.draw.polygon(scr, WHITE, bar)
            else:
                pg.draw.polygon(scr, (40, 8, 20) if sub else INK, bar)
            ink = INK if on else WHITE
            img = fnt.render(tr(lab), False, ink)
            scr.blit(img, (x + 10, y + (0 if compact else 1)))
            if kind == 'slider':                                 # [-] ########## [+]  70%
                v = s.settings[key]
                minus, plus = pg.Rect(vx, y + 2, 16, 16), pg.Rect(vx + 18 + 112, y + 2, 16, 16)
                for btn, sign in ((minus, '-'), (plus, '+')):
                    hov = btn.collidepoint(mx, my)
                    pg.draw.rect(scr, RED if hov else (INK if on else (60, 50, 70)), btn)
                    pg.draw.rect(scr, WHITE if not on or hov else INK, btn, 1)
                    pg.draw.line(scr, WHITE if (hov or not on) else WHITE, (btn.x + 4, btn.centery), (btn.right - 5, btn.centery), 2)
                    if sign == '+':
                        pg.draw.line(scr, WHITE, (btn.centerx - 1, btn.y + 4), (btn.centerx - 1, btn.bottom - 5), 2)
                    if s.click and hov:
                        s.sel = i
                        s.change_setting(rows[i], -1 if sign == '-' else 1)
                bx0 = vx + 20
                for b_ in range(10):
                    filled = b_ < round(v * 10)
                    cell = pg.Rect(bx0 + b_ * 11, y + 4, 9, 12)
                    scr.fill((RED if on else (0, 200, 230)) if filled else ((60, 50, 70) if not on else (190, 180, 200)), cell)
                    if s.click and cell.inflate(2, 8).collidepoint(mx, my):   # click a cell: exactly that level
                        s.sel = i
                        s.change_setting(rows[i], 0, (b_ + 1) / 10)
                img = F_PS.render(f"{int(round(v * 100))}%", False, ink)
                scr.blit(img, (plus.right + 6, y + 1))
            else:
                val = s.setting_value((sec, lab, key, kind))
                img = fnt.render(val, False, WHITE)
                tw = img.get_width() + 14
                tx = vx + 70 - tw // 2
                lit = kind in ('rain', 'lang', 'open', 'action') or s.settings.get(key)
                pg.draw.polygon(scr, RED if lit else (70, 60, 80), [(tx, y + 1), (tx + tw, y), (tx + tw - 4, y + rh - 1), (tx - 4, y + rh)])
                scr.blit(img, (tx + 7, y + (0 if compact else 1)))
                arrows = kind not in ('open', 'action')
                lb, rb = pg.Rect(tx - 18, y - 1, 14, rh + 2), pg.Rect(tx + tw + 2, y - 1, 14, rh + 2)
                if arrows:                                       # < less   > more (they work with the mouse too)
                    for btn, ch in ((lb, "<"), (rb, ">")):
                        hov = btn.collidepoint(mx, my)
                        if hov:
                            pg.draw.rect(scr, RED, btn)
                        scr.blit(fnt.render(ch, False, WHITE if hov else (INK if on else (150, 140, 170))), (btn.x + 3, y + (0 if compact else 1)))
                if s.click and r.collidepoint(mx, my) and (not TOUCH or on):
                    s.sel = i
                    s.change_setting(rows[i], -1 if arrows and lb.collidepoint(mx, my) else 1)

    def st_controls(s, dt):
        """Rebind every action, for keyboard and for the Xbox pad."""
        s.persona_bg()
        el = s.t - s.state_t
        ransom("CONTROLS", 104, 22, [F_PB, F_P], 31, s.t, tilt=-6)
        names = [j.get_name() for j in s.joys.values()]
        status = (tr("PAD:") + " " + names[0][:16]) if names else "NO CONTROLLER CONNECTED"
        pg.draw.polygon(scr, (0, 200, 230) if names else (70, 60, 80), [(330, 6), (W - 8, 4), (W - 12, 18), (326, 20)])
        text(status, F_S, INK if names else WHITE, 338, 8)
        rows = BIND_ACTIONS + [('reset', "RESET TO DEFAULTS")]
        sk = s.skill()
        names = {a: lab for a, lab in rows}
        names['skill'] = f"{tr('SKILL')}: {tr(sk[0])}" if sk else "SKILL: NONE"
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
        if not s.capture and s.corner_back(mx, my):
            s.set_keep = True
            s.wipe_to(lambda: s.go('settings', 0))
        for i, (a, label) in enumerate(rows):
            sl = ease((el - .05 - i * .03) * 4)
            x, y = 14 + int((1 - sl) * 470), 50 + i * 13.6
            on = i == s.sel
            pg.draw.polygon(scr, WHITE if on and a in ('reset', 'back') else INK,
                            [(x, y), (x + 456, y - 2), (x + 452, y + 12), (x - 4, y + 14)])
            scr.fill(RED if i % 2 else (0, 200, 230), (x, y + 1, 3, 12))
            s.row_text(names[a] if a == 'skill' else label, on and a in ('reset', 'back'), x + 8, y + 1)
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
            s.set_keep = True
            s.wipe_to(lambda: s.go('settings', 0))
        if s.capture:
            pg.draw.polygon(scr, INK, [(60, 112), (W - 60, 106), (W - 66, 150), (54, 156)])
            pg.draw.polygon(scr, RED, [(60, 112), (W - 60, 106), (W - 66, 150), (54, 156)], 2)
            label = dict(BIND_ACTIONS)[s.capture[1]]
            outlined(tr("PRESS A KEY FOR " if s.capture[0] == 'kb' else "PRESS A PAD BUTTON FOR ") + tr(label),
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
        txt = "999999" if s.adm('a_money') else f"{s.stats['wallet']}"
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
        name = (s.name_buf + ("_" if int(s.t * 3) % 2 else " ")) if s.typing else (tr(st['name']) if st['name'] == PROFILE_DEFAULTS['name'] else st['name'])
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
            img = F_PS.render(tr(lab), False, INK if on else WHITE)
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

    def skin_sword(s, hx, y, L, sid, owned, k):
        """One skin's katana lying flat: blade to the left (away from us), the hilt end at hx. k: how close (0..1)."""
        S = SKINS[sid][2]
        acc, main_, dark = S['accent'] if 'accent' in S else S['belt'], S['coat'], S['coat_d']
        acc = SKIN_PERKS.get(sid, ("", "", acc))[2]
        hl = L * .26                                            # hilt length
        tsuba = hx - hl
        tip = tsuba - (L - hl)
        th = max(2, int(5 * k))                                  # blade thickness
        if owned:                                                # an owned blade burns in its skin's colour
            pulse = .6 + .4 * math.sin(s.t * 3 + len(sid))
            for j in range(3):
                glow(scr, lerp(tip, tsuba, .2 + j * .3), y, int(24 * k) + 6, qcol(tuple(c // 3 for c in acc), pulse * k))
        steel = (200, 206, 222) if owned else (96, 98, 112)
        edge = (250, 252, 255) if owned else (140, 142, 156)
        curve = 6 * k                                            # a little sori: the blade curves up toward the tip
        pts = [(tip, y - curve - th * .3), (tsuba, y - th / 2), (tsuba, y + th / 2), (tip + 10 * k, y - curve + th * .4)]
        pg.draw.polygon(scr, steel, pts)
        pg.draw.line(scr, edge, (tip + 2, y - curve - th * .2), (tsuba, y - th / 2), 1)
        if owned:                                                # the hamon in the skin colour
            pg.draw.line(scr, acc, (tip + 12 * k, y - curve + th * .1), (tsuba - 4, y + th * .15), 1)
        pg.draw.rect(scr, (210, 180, 90) if owned else (110, 100, 70), (tsuba - 3 * k - 1, y - th, 2 + 3 * k, th * 2))   # habaki
        pg.draw.ellipse(scr, acc if owned else (70, 66, 80), (tsuba - 2, y - 6 * k - 2, 4 + 2 * k, 12 * k + 4))     # tsuba
        pg.draw.rect(scr, dark, (tsuba + 2, y - th * .7 - 1, hl - 4, th * 1.4 + 2))                                   # tsuka
        for j in range(int((hl - 6) / max(3, 6 * k))):           # diamond wrap
            wx = tsuba + 4 + j * max(3, 6 * k)
            pg.draw.line(scr, main_ if owned else (60, 56, 70), (wx, y - th * .7), (wx + max(3, 6 * k) / 2, y + th * .7), 1)
            pg.draw.line(scr, main_ if owned else (60, 56, 70), (wx + max(3, 6 * k) / 2, y - th * .7), (wx, y + th * .7), 1)
        pg.draw.rect(scr, (210, 180, 90) if owned else (110, 100, 70), (hx - 3, y - th * .8 - 1, 4, th * 1.6 + 2))    # kashira
        if not owned:                                            # a lock on the hilt
            pg.draw.rect(scr, (200, 190, 120), (tsuba + hl * .4, y - 4, 8, 7))
            pg.draw.arc(scr, (200, 190, 120), (tsuba + hl * .4 + 1, y - 9, 6, 8), 0, math.pi, 1)
        return tsuba

    def skin_blade(s, px, py, ux, uy, L, th, sid, owned, on):
        """One skin's katana in the drum: the guard sits on the cut line at (px, py), the blade runs along (ux, uy) toward
        the far point on the left, the hilt goes the other way, in behind the samurai. Locked: plain grey steel.
        Unlocked: the skin's colours, a glowing edge, its own sparks, the name engraved on the blade."""
        nx, ny = -uy, ux
        acc = SKIN_PERKS.get(sid, ("", "", (200, 200, 220)))[2]
        S = SKINS[sid][2]
        tx, ty = px + ux * L, py + uy * L
        hl = 12 + th * 3.2                                       # hilt length (behind the cut)
        hx, hy = px - ux * hl, py - uy * hl
        if owned:                                                # the blade burns in the skin colour
            pulse = .6 + .4 * math.sin(s.t * 3 + len(sid))
            for j in range(4):
                q = .15 + j * .25
                glow(scr, px + ux * L * q, py + uy * L * q, int(8 + th * 2.2), qcol(tuple(c // 3 for c in acc), pulse))
        steel = (200, 206, 222) if owned else (132, 134, 144)    # the flat
        back = (118, 124, 146) if owned else (86, 88, 98)        # the back and the ridge side (shinogi-ji)
        edge = (250, 252, 255) if owned else (176, 178, 188)
        up = 1 if ny < 0 else -1                                 # which side of the blade faces up (the back)
        bx_, by_ = nx * up, ny * up                              # unit vector toward the back

        def at(q, side):                                         # a point on the blade: q along it, side -1 edge .. +1 back
            sori = 0.0 if on else -th * 1.6 * (q ** 2)           # the curve lifts toward the tip (the chosen one: straight)
            w = th * (1 - .3 * q) / 2
            return (px + ux * L * q + bx_ * (sori + side * w), py + uy * L * q + by_ * (sori + side * w))
        qs = [i / 16 * .9 for i in range(17)]
        kis = at(1.0, .4)                                        # kissaki: the back runs straight into the point
        backs = [at(q, 1) for q in qs]
        edges = [at(q, -1) for q in qs]
        ridge = [at(q, .35) for q in qs]
        pg.draw.polygon(scr, steel, backs + [kis] + edges[::-1])
        pg.draw.polygon(scr, back, backs + [kis] + ridge[::-1])
        pg.draw.line(scr, back, ridge[-1], kis)                  # yokote: the line where the point begins
        pg.draw.lines(scr, edge, False, edges + [kis], 1)        # the cutting edge
        if th > 3:                                               # hamon: a white wave just above the edge (the skin colour when owned)
            ham = [at(q, -.55 + .18 * math.sin(q * 46 + (s.t * 2 if owned else 0))) for q in qs]
            pg.draw.lines(scr, acc if owned else (160, 162, 172), False, ham, 1)
        if owned and th > 4:                                     # a light glint sliding along the flat
            g_ = (s.t * .5 + len(sid) * .13) % 1.4
            if g_ < .9:
                a_, b_ = at(g_, -.3), at(min(.9, g_ + .06), .2)
                pg.draw.line(scr, WHITE, a_, b_, 2)
        if th > 5:                                               # the skin's name engraved on the blade
            f = F_PS if th > 14 else F_S
            img = f.render(tr(SKINS[sid][0]), False, (40, 30, 50) if owned else (70, 70, 80))
            ang = -math.degrees(math.atan2(uy, ux)) + 180
            img = pg.transform.rotate(img, ang)
            mx_, my_ = px + ux * L * .42, py + uy * L * .42
            scr.blit(img, (mx_ - img.get_width() / 2, my_ - img.get_height() / 2))
        gold = (214, 182, 90) if owned else (120, 112, 96)
        pg.draw.line(scr, gold, (px - ux * 2, py - uy * 2), (px + ux * 3, py + uy * 3), max(2, int(th * .9)))   # habaki
        tw = th * 1.6 + 4                                        # tsuba
        pg.draw.line(scr, (S['belt'] if owned else (80, 80, 90)), (px + nx * tw, py + ny * tw), (px - nx * tw, py - ny * tw), max(2, int(th * .6) + 1))
        wrap_c, under = (S['coat'], S['coat_d']) if owned else ((90, 90, 100), (54, 54, 62))
        hw = th * .75 + 1
        pg.draw.polygon(scr, under, [(px + nx * hw, py + ny * hw), (hx + nx * hw, hy + ny * hw), (hx - nx * hw, hy - ny * hw),
                                     (px - nx * hw, py - ny * hw)])
        step = max(3, th * .9)
        q = step
        while q < hl - 2:                                        # the diamond wrap
            a_, b_ = (px - ux * q, py - uy * q), (px - ux * (q + step / 2), py - uy * (q + step / 2))
            pg.draw.line(scr, wrap_c, (a_[0] + nx * hw, a_[1] + ny * hw), (b_[0] - nx * hw, b_[1] - ny * hw), 1)
            pg.draw.line(scr, wrap_c, (a_[0] - nx * hw, a_[1] - ny * hw), (b_[0] + nx * hw, b_[1] + ny * hw), 1)
            q += step
        pg.draw.circle(scr, gold, (int(hx), int(hy)), max(1, int(hw * .7)))
        if sid == s.stats['skin']:                               # the equipped skin's own sparks running down the blade
            kind = {'crimson': 'drip', 'void': 'smoke', 'gold': 'bolt', 'jade': 'leaf', 'azure': 'wind'}.get(sid, 'spark')
            for j in range(4):
                q = (s.t * .35 + j / 4 + len(sid) * .1) % 1
                x_, y_ = px + ux * L * q * .95, py + uy * L * q * .95
                if kind == 'drip':
                    dy_ = ((s.t * 1.3 + j * .4) % 1) * 10
                    scr.fill((220, 30, 50), (x_, y_ + th / 2 + dy_, 1, 2))
                elif kind == 'smoke':
                    glow(scr, x_, y_ - th, 6, (40, 16, 70))
                    scr.fill((150, 100, 255), (x_, y_ - th - (s.t * 8 + j * 3) % 8, 1, 1))
                elif kind == 'bolt' and int(s.t * 6 + j) % 5 == 0:
                    pg.draw.lines(scr, (255, 240, 150), False, [(x_, y_), (x_ + 3, y_ - 4), (x_ - 1, y_ - 6), (x_ + 2, y_ - 10)], 1)
                elif kind == 'leaf':
                    scr.fill((130, 255, 170), (x_ + math.sin(s.t * 3 + j) * 3, y_ - th - 2, 2, 1))
                elif kind == 'wind':
                    pg.draw.line(scr, (170, 240, 255), (x_, y_ - th - 2), (x_ + 7, y_ - th - 2))
                else:
                    four_star(scr, x_, y_ - th * .3, 2 + (j % 2), acc)
        return hx, hy

    def blade_point(s, gx, y, ux, uy, L, th, q):
        """A point on the middle of a drum blade (following its curve), q: 0 at the guard .. 1 at the tip."""
        up = 1 if ux * 0 - uy * 1 < 0 else -1
        nx, ny = -uy * up, ux * up
        sori = -th * 1.6 * q * q
        return gx + ux * L * q + nx * sori, y + uy * L * q + ny * sori

    def scroll_roll(s, x, y, ux, uy, th, big=1.0):
        """The skin's scroll, rolled up and tied around its blade."""
        nx, ny = -uy, ux
        a, h = (4 + th * .35) * big, (th * .5 + 4 + th * .3) * big
        pts = [(x - ux * a + nx * h, y - uy * a + ny * h), (x + ux * a + nx * h, y + uy * a + ny * h),
               (x + ux * a - nx * h, y + uy * a - ny * h), (x - ux * a - nx * h, y - uy * a - ny * h)]
        pg.draw.polygon(scr, (236, 226, 204), pts)
        pg.draw.polygon(scr, (120, 70, 50), pts, 1)
        for sg in (-1, 1):                                       # the rolled edges and the red cord
            pg.draw.line(scr, (176, 30, 40), (x + ux * a * .6 * sg + nx * h, y + uy * a * .6 * sg + ny * h),
                         (x + ux * a * .6 * sg - nx * h, y + uy * a * .6 * sg - ny * h), 1)
        pg.draw.line(scr, (200, 40, 50), (x + nx * h, y + ny * h), (x + nx * (h + 4) - ux * 2, y + ny * (h + 4) - uy * 2), 1)

    def st_upgrades(s, dt):
        """Permanent upgrades: Persona plates down the screen, three levels each, paid with coins."""
        s.persona_bg()
        el = s.t - s.state_t
        st = s.stats
        sk = getattr(s, 'upg_skin', None) if getattr(s, 'upg_skin', None) in st['skins'] else st['skin']
        up = st.setdefault('upg', {}).setdefault(sk, {})           # the skin chosen on the drum (each one upgraded on its own)
        mx, my = pg.mouse.get_pos()
        ransom("UPGRADES", 100, 22, [F_P, F_PM], 23, s.t, tilt=-6)
        acc = SKINS[sk][2]['hilt']                                  # whose upgrades: on a tilted tag
        img = F_PS.render(tr(SKINS[sk][0]), False, INK)
        tx, ty = W - 16 - img.get_width(), 27                         # (under the wallet, clear of the title)
        pg.draw.polygon(scr, acc, [(tx - 6, ty - 2), (tx + img.get_width() + 8, ty - 4),
                                   (tx + img.get_width() + 4, ty + 15), (tx - 9, ty + 17)])
        scr.blit(img, (tx, ty))
        s.wallet_tag(W - 110, 8)
        ups = upgrade_list(sk)
        cap = s.upg_cap()
        n = len(ups)
        s.sel %= n
        s.nav(n)
        fire = 'ok' in s.act
        if cap < 5:                                              # what opens the next levels
            need = {0: "CLEAR NEON SHINJUKU TO UNLOCK UPGRADES", 3: "CLEAR ANOTHER LOCATION FOR LEVEL 4",
                    4: "CLEAR ANOTHER LOCATION FOR LEVEL 5"}[cap]
            img = F_S.render(tr(need), False, (255, 200, 120))
            scr.blit(img, (W - 14 - img.get_width(), 46 - 12))
        if s.corner_back(mx, my) or s.act & {'back', 'left'}:
            sfx('sel')
            s.wipe_to(lambda: s.go('skins', 0))
            return
        for i, (k, name, desc, jp, prices) in enumerate(ups):
            a = ease((el - .05 - i * .05) * 4)
            x, y, w = 30 + i * 5 + int((1 - a) * 460), 46 + i * 36, 420
            on = i == s.sel
            r = pg.Rect(x - 6, y - 2, w, 32)
            if r.collidepoint(mx, my):
                if s.moved and not on:
                    s.sel, s.selT = i, s.t
                    sfx('sel')
                if s.click:
                    s.sel, fire = i, True
            lvl = up.get(k, 0)
            shake = math.sin(s.t * 70) * 3 if on and s.t - getattr(s, 'denyT', -9) < .25 else 0
            x += shake
            box = [(x, y), (x + w, y - 3), (x + w - 8, y + 30), (x - 6, y + 32)]
            if on:
                pg.draw.polygon(scr, RED, [(px + 6, py + 5) for px, py in box])
            pg.draw.polygon(scr, WHITE if on else INK, box)
            ink = INK if on else WHITE
            jimg = pg.transform.scale_by(F_JPB.render(jp, False, RED if on else (140, 30, 50)), 1.4)
            scr.blit(jimg, (x + 4, y + 15 - jimg.get_height() // 2))
            scr.blit(F_PS.render(tr(name), False, ink), (x + 34, y + 1))
            scr.blit(F_S.render(tr(desc), False, (90, 30, 50) if on else (190, 180, 210)), (x + 34, y + 17))
            top = len(prices)
            cap = s.level_cap(k, top)
            for j in range(top):                                 # level pips (dark with a bar = still locked)
                px = x + 250 + j * 12 + (30 if top == 1 else 0)
                col = RED if j < lvl else ((200, 196, 210) if on else (70, 60, 84))
                if j >= lvl and j >= cap:
                    col = (40, 30, 46)
                pg.draw.polygon(scr, col, [(px, y + 8), (px + 9, y + 6), (px + 7, y + 20), (px - 2, y + 22)])
                if j >= lvl and j >= cap:
                    pg.draw.line(scr, (110, 90, 120), (px - 1, y + 14), (px + 8, y + 13))
            if lvl >= top:
                tag, col = tr("MAX"), (90, 80, 100)
            elif lvl >= cap:
                tag, col = tr("LOCKED"), (70, 60, 84)
            else:
                price = prices[lvl]
                tag, col = f"{price}", (255, 205, 50) if s.can_pay(price) else (110, 90, 110)
            img = F_PS.render(tag, False, INK)
            tx = x + w - 62
            pg.draw.polygon(scr, col, [(tx, y + 6), (tx + 50, y + 4), (tx + 47, y + 22), (tx - 3, y + 24)])
            scr.blit(img, (tx + 25 - img.get_width() // 2, y + 6))
            if lvl < top and lvl < cap:
                pg.draw.circle(scr, (255, 205, 50), (tx - 10, y + 14), 4)
        if fire:
            k, _, _, _, prices = ups[s.sel]
            lvl = up.get(k, 0)
            if lvl < len(prices) and lvl < s.level_cap(k, len(prices)) and s.can_pay(prices[lvl]):
                s.pay(prices[lvl])
                up[k] = lvl + 1
                save_stats(st)
                sfx('buy')
                sfx('glint')
            else:
                s.denyT = s.t
                sfx('deny')

    def skin_info_panel(s, sid, c1, k_in):
        """Under the samurai: the skin's name, what it gives, and its price - on black Persona plates, sliding in."""
        st = s.stats
        k = ease((s.t - s.selT) * 5)
        x0 = c1 + 18 + int((1 - k) * 60) + int((1 - k_in) * 200)
        acc = SKIN_PERKS.get(sid, ("", "", WHITE))[2]
        plate = [(x0 - 10, 168), (W - 4, 160), (W - 8, H - 4), (x0 - 22, H - 2)]
        pg.draw.polygon(scr, RED, [(a + 5, b + 4) for a, b in plate])
        pg.draw.polygon(scr, INK, plate)
        pg.draw.polygon(scr, WHITE, plate, 2)
        name = tr(SKINS[sid][0])                                 # the name on a white tag, tilted
        img = F_PS.render(name, False, INK)
        tag = [(x0 - 6, 156), (x0 + img.get_width() + 10, 152), (x0 + img.get_width() + 6, 170), (x0 - 10, 173)]
        pg.draw.polygon(scr, WHITE, tag)
        scr.blit(pg.transform.rotate(img, 2), (x0 + 1, 154))
        pg.draw.line(scr, acc, (x0 - 8, 176), (W - 12, 172), 1)
        yy = 180
        key = s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'skill')
        for j, para in enumerate(SKIN_DESC.get(sid, [])):
            for line in wrap(tr(para).replace('{K}', key), F_S, W - x0 - 12):
                if yy > H - 26:
                    break
                text(line, F_S, (255, 230, 150) if j == 0 else (190, 220, 255), x0 - 6, yy)
                yy += 10
            yy += 2
        st_txt = (tr("EQUIPPED") if st['skin'] == sid else (tr("OWNED - EQUIP") if sid in st['skins'] else f"{SKINS[sid][1]} {tr('COINS')}"))
        col = RED if st['skin'] == sid else ((0, 200, 230) if sid in st['skins'] else
                                             ((255, 205, 50) if s.can_pay(SKINS[sid][1]) else (90, 80, 100)))
        img = F_PS.render(st_txt, False, INK if col != RED else WHITE)
        tx, ty = W - img.get_width() - 22, H - 22
        pg.draw.polygon(scr, col, [(tx - 6, ty), (tx + img.get_width() + 8, ty - 2), (tx + img.get_width() + 4, ty + 16), (tx - 10, ty + 18)])
        scr.blit(img, (tx, ty))
        if SKIN_DIFF.get(sid, 1) > 1:
            text(f"{tr('MORE ENEMIES')}: x{SKIN_DIFF[sid]:g}", F_S, (255, 120, 140), x0 - 6, min(yy + 2, H - 36))

    def skin_scroll(s, x, y, sid, k, rot=0.0):
        """The skin's scroll: rolled up under the hilt, unrolling downward. k: 0 rolled .. 1 open."""
        name, price, _ = SKINS[sid]
        perk = SKIN_PERKS.get(sid, ("", "", WHITE))
        skill = SKIN_SKILLS.get(sid)
        w, hmax = 112, 132
        h = int(hmax * ease(k))
        surf = pg.Surface((w + 12, hmax + 40), pg.SRCALPHA)
        pg.draw.rect(surf, (90, 40, 30), (0, 0, w + 12, 7))                      # top rod
        pg.draw.rect(surf, (150, 90, 50), (0, 0, w + 12, 2))
        if h > 2:
            paper = pg.Rect(6, 7, w, h)
            pg.draw.rect(surf, (238, 228, 206), paper)
            pg.draw.rect(surf, (176, 30, 40), (6, 7, w, 4))
            pg.draw.rect(surf, (176, 30, 40), (6, 7, 3, h))
            pg.draw.rect(surf, (176, 30, 40), (w + 3, 7, 3, h))
            inner = surf.subsurface(paper)
            yy = 8
            img = F_PS.render(tr(name), False, INK)
            if img.get_width() > w - 10:
                img = F_S.render(tr(name), False, INK)
            inner.blit(img, (w // 2 - img.get_width() // 2, yy))
            yy += img.get_height() + 2
            pg.draw.line(inner, (176, 30, 40), (10, yy), (w - 10, yy))
            yy += 4
            key = s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'skill')
            for j, para in enumerate(SKIN_DESC.get(sid, [])):   # what the skin gives: perk, then skill
                for line in wrap(tr(para).replace('{K}', key), F_S, w - 14):
                    inner.blit(F_S.render(line, False, (150, 20, 40) if j == 0 else (40, 60, 140)), (8, yy))
                    yy += 10
                yy += 3
            jp = F_JPB.render("巻", False, (220, 200, 180))
            inner.blit(jp, (w - jp.get_width() - 6, h - jp.get_height() - 4 if h > 40 else 999))
        pg.draw.rect(surf, (90, 40, 30), (0, 7 + h, w + 12, 8))                   # the rolled part / bottom rod
        pg.draw.rect(surf, (238, 228, 206), (3, 8 + h, w + 6, 5))
        if k > .95:                                              # the stats hang under it on red cords
            st = s.stats
            tags = [f"{tr('MORE ENEMIES')}: x{SKIN_DIFF.get(sid, 1):g}"]
            tags.append(tr("EQUIPPED") if st['skin'] == sid else (tr("OWNED") if sid in st['skins'] else f"{price} {tr('COINS')}"))
            for j, tg in enumerate(tags):
                tx = 12 + j * 56
                sway = math.sin(s.t * 2 + j) * 2
                pg.draw.line(surf, (176, 30, 40), (tx + 20, 15 + h), (tx + 20 + sway, 22 + h))
                img = F_S.render(tg, False, WHITE)
                tw = min(54, img.get_width() + 6)
                pg.draw.rect(surf, INK, (tx + 20 + sway - tw // 2, 22 + h, tw, 12))
                surf.blit(img, (tx + 20 + sway - tw // 2 + 3, 23 + h), pg.Rect(0, 0, tw - 6, 12))
        if rot:
            surf = pg.transform.rotate(surf, rot)
        scr.blit(surf, (x - surf.get_width() // 2, y))

    def st_skins(s, dt):
        """Persona-style armoury: the screen cut by a katana stroke, a drum of the skins' swords on the left (blades pointing
        away, hilts running in behind the samurai), the chosen skin's scroll unrolling under its hilt, the samurai on the right."""
        s.persona_bg()
        el = s.t - s.state_t
        st = s.stats
        ids = list(SKINS)
        n = len(ids)
        mx, my = pg.mouse.get_pos()
        if el < .02 or not hasattr(s, 'skd'):                     # arriving: the drum starts on the equipped skin
            s.sel = ids.index(st['skin']) if st['skin'] in ids else 0
            s.skd, s.sk_open, s.sk_fall, s.sk_snd = float(s.sel), 0.0, [], False
            s.selT = s.t
        old = s.sel
        wh = getattr(s, 'wheel', 0)
        s.wheel = 0
        if 'up' in s.act or wh > 0:
            s.sel = (s.sel - 1) % n
        if 'down' in s.act or wh < 0:
            s.sel = (s.sel + 1) % n
        ub = pg.Rect(W - 112, 30, 100, 20)                       # UPGRADES > (top right, under the wallet)
        hov = ub.collidepoint(mx, my)
        if ('right' in s.act or (s.click and hov)) and ids[s.sel] not in st['skins']:   # not bought yet: no upgrades
            s.denyT = s.t
            sfx('deny')
        elif 'right' in s.act or (s.click and hov):
            sfx('sel')
            s.upg_skin = ids[s.sel]                                 # the skin you are looking at
            s.wipe_to(lambda: s.go('upgrades', 0))
            return
        if 'left' in s.act:
            sfx('sel')
            s.wipe_to(lambda: s.go('stats', 0))
            return
        fire = 'ok' in s.act
        if s.corner_back(mx, my) or 'back' in s.act:
            sfx('sel')
            s.wipe_to(lambda: s.go('stats', 0))
            return
        # --- the right third: cut off with one diagonal stroke
        k_in = ease(el * 3)
        c0, c1 = int(W * .66 + (1 - k_in) * 240), int(W * .54 + (1 - k_in) * 240)
        right = [(c0, 0), (W, 0), (W, H), (c1, H)]
        sid = ids[s.sel]
        acc = SKIN_PERKS.get(sid, ("", "", WHITE))[2]

        def draw_cut():
            pg.draw.polygon(scr, (10, 6, 16), right)
            glow(scr, (c0 + W) // 2 + 20, H // 2, 110, tuple(c // 5 for c in acc), .5)
            if el < .35:                                         # the stroke that cut it
                sx = int(el / .35 * (H + 40))
                pg.draw.line(scr, WHITE, (c0, 0), (lerp(c0, c1, min(1, sx / H)), min(H, sx)), 4)
            pg.draw.line(scr, RED, (c0 - 3, 0), (c1 - 3, H), 3)
            pg.draw.line(scr, WHITE, (c0, 0), (c1, H), 2)
        # --- the drum of swords
        s.skd += ((s.sel - s.skd + n / 2) % n - n / 2) * min(1, dt * 10)
        cy = 112
        VP = (-320, cy)                                          # the drum's axis is far away on the left: the blades fan out from it
        rows = []
        for i, sid_ in enumerate(ids):
            d = (i - s.skd + n / 2) % n - n / 2
            if abs(d) > 3.4:
                continue
            ang = d * .34
            kz = max(0.0, math.cos(ang))
            y = cy + math.sin(ang) * 150
            rows.append((kz, i, sid_, y, d))
        rows.sort()
        tsuba_sel = None
        for kz, i, sid_, y, d in rows:
            on = i == s.sel
            shake = math.sin(s.t * 70) * 2 if on and s.t - getattr(s, 'denyT', -9) < .25 else 0   # can't afford it: it shakes
            pick = ease(min(1, (s.t - s.selT) * 5)) if on else 0.0   # the chosen blade comes forward, toward us
            th = 3 + 9 * kz ** 3 + 9 * pick
            gx = lerp(c0, c1, max(0, min(1, y / H))) - 4 - th + int((1 - k_in) * 300) + shake   # the guard sits on the cut
            ux, uy = VP[0] - gx, VP[1] - y
            ln = math.hypot(ux, uy) or 1
            ux, uy = ux / ln, uy / ln
            L = (gx + 20) * (.92 + .08 * kz) * ease((el - .05 - abs(d) * .05) * 3)
            if L < 20:
                continue
            if on:
                y += 7 * pick                                    # its guard sits a little lower: the blade points up-left, straight
            s.skin_blade(gx, y, ux, uy, L, th, sid_, sid_ in st['skins'], on)

            mxp, myp = gx + ux * L * .5, y + uy * L * .5
            if abs(my - (y + (my - y) * 0) - (uy / ux * (mx - gx) if ux else 0)) < max(6, th) and mx < gx and s.click:
                if on:
                    fire = True
                else:
                    s.sel = i
            if on:
                tsuba_sel = (gx, y, ux, uy, L, th)
        if s.sel != old:                                         # the drum turns: a click, the open scroll falls off
            s.selT = s.t
            sfx('sel')
            s.sk_open, s.sk_snd = 0.0, False
        draw_cut()
        # --- the scroll under the chosen hilt: it waits a second, then unrolls fast
        # --- the samurai of that skin, mirrored (facing the swords), as on the stats screen
        P = pose_idle(s.t)
        kk = (s.t * .5) % 4
        if kk < .4:
            P = with_attack(P, 'side', kk / .4, 1)
        P['hood'] = 0.0
        if sid not in s.skin_chains:
            s.skin_chains[sid] = {'scarf': [[48, 60] for _ in range(5)], 'hair': [[48, 55] for _ in range(5)]}
        img = pg.transform.flip(s.portrait(P, 3.4, sid, s.skin_chains[sid]), True, False)
        ax = W - img.get_width() + 20 + int((1 - ease((s.t - s.selT) * 6)) * 40) + int((1 - k_in) * 200)
        scr.blit(img, (ax, 158 - img.get_height() + 30))
        s.skin_info_panel(sid, c1, k_in)
        # --- header: title, wallet, the chosen skin's name
        ransom("SKINS", 104, 22, [F_PB, F_P], 17, s.t, tilt=-6)
        s.wallet_tag(W - 110, 8)
        pts = [(ub.x, ub.y), (ub.right, ub.y - 2), (ub.right - 4, ub.bottom), (ub.x - 4, ub.bottom + 2)]
        pg.draw.polygon(scr, WHITE if hov else INK, pts)
        img = F_PS.render(tr("UPGRADES >"), False, INK if hov else WHITE)
        scr.blit(img, (ub.centerx - img.get_width() // 2, ub.y + 1))
        if fire:
            price = SKINS[sid][1]
            if sid in st['skins']:
                st['skin'] = sid
                sfx('glint')
            elif s.can_pay(price):                                # buy it and wear it: the blade lights up
                s.pay(price)
                st['skins'].append(sid)
                st['skin'] = sid
                sfx('buy')
                sfx('glint')
            else:
                s.denyT = s.t
                sfx('deny')
            save_stats(st)

    # ---------- opening cinematic, dialog, kiosk
    def dialog_box(s, dt):
        """Persona-style dialog box. Returns True when all lines are done."""
        if s.dl >= len(DIALOG):
            return True
        name, txt = DIALOG[s.dl]
        txt, name = tr(txt), tr(name).replace("{NAME}", s.stats['name'])     # the whole line is translated, then typed out
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
        if s.act & {'ok', 'jump', 'atk'}:
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
        elif s.cine_phase == 'hood' and t >= 2.9:                   # (no dialog: straight into the run)
            s.cine_phase, s.cine_out = 'out', 0.0
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
            outlined(tr("ESC skip"), F_S, WHITE, W - 6 - F_S.size(tr("ESC skip"))[0], 8 + bh, r=1)
            if s.act & {'back', 'pause'}:
                s.cine_phase, s.cine_out = 'out', 0.0

    def normal_card(s, used=()):
        """A normal card from a category not in `used` (one per category per kiosk); once-per-run cards you own are out.
        Returns (category, card)."""
        for skip in (used, ()):
            pool = [(c, b, w) for c, cards in CARD_CATS.items() if c not in skip for b, w in cards.items()
                    if not (b in ONCE_CARDS and s.buff(b)) and not (b == 'second' and s.buff('gamble'))]
            if pool:
                r = random.uniform(0, sum(w for _, _, w in pool))
                for c, b, w in pool:
                    r -= w
                    if r <= 0:
                        return c, b
                return pool[-1][:2]
        return None, 'onigiri'

    def special_card(s, exclude=()):
        """A special card you don't have yet (None when you have them all)."""
        pool = [b for b in SPECIALS if not s.buff(b) and b not in exclude]
        return random.choice(pool) if pool else None

    def random_card(s, special=.5, exclude=()):
        """The RANDOM CARD (and JOKER / SCAR CARDS gifts): a special card with this chance, else a normal one. Never the key."""
        b = s.special_card(exclude) if random.random() < special else None
        return b or s.normal_card()[1]

    def roll_kiosk(s):
        """Every slot: 75% a normal card, 10% the exit key (never in the last district), 10% a special card, 5% a random
        card. At most one normal card of each category, one key and one random card per kiosk."""
        cards, used = [], set()
        last = s.lvl >= LEVELS and not getattr(s, 'endless', False)
        for _ in range(4 if s.buff('four') else 3):
            r, b = random.random(), None
            if .75 <= r < .85 and 'key' not in cards and not last:
                b = 'key'
            elif .85 <= r < .95:
                b = s.special_card(cards)
            elif r >= .95 and 'random' not in cards:
                b = 'random'
            if b is None:
                c, b = s.normal_card(used)
                used.add(c)
            cards.append(b)
        return cards

    def give_card(s, b):
        """Put card b into the run. Returns the card you really got (a random card turns into one)."""
        p = s.pl
        if b == 'random':
            b = s.random_card()
        if b == 'key':                                              # an exit door opens next to the kiosk
            s.door['exit'] = True                                   # the red door behind you opens again
            s.boss_msg = ('THE RED DOOR IS OPEN', 2.0)
            sfx('door')
        elif b == 'onigiri':                                        # eaten on the spot
            if p.hp >= p.maxhp and getattr(s, 'oni_glass', 0) < 3:   # (full already: a sliver of glass instead)
                s.oni_glass = getattr(s, 'oni_glass', 0) + 1
                p.glass += 1
            p.hp = min(p.maxhp, p.hp + 2)
        else:
            s.buffs[b] = s.buffs.get(b, 0) + 1
            if b in TIMED_CARDS:                                    # GOLD RUSH / BOUNTY HUNTER: one clock, a new copy adds time
                s.buffs[b] = 1
                old = s.timed.get(b, [s.gtime])
                s.timed[b] = [max(s.gtime, max(old)) + TIMED_CARDS[b]]
            if b == 'vital':
                p.maxhp += 1
                p.hp = min(p.maxhp, p.hp + 1)
            elif b == 'jackpot':                                    # +1 HP, +1 glass HP (the damage is in blade/slam_dmg)
                p.maxhp += 1
                p.hp += 1
                p.glass += 1
            elif b == 'glass':                                      # GLASS SKIN: 20% of your max HP as glass
                p.glass += max(1, int(round(p.maxhp * .2)))
            elif b == 'ward':
                s.ward = True
            elif b == 'medic':                                      # FIELD MEDIC: this district and the next 4
                s.medic_left = 5
            elif b == 'invis':
                s.exit_need = 3
                if s.kiosk:
                    s.kiosk['closed'] = True
            elif b == 'joker' and s.kiosk:
                s.kiosk['closed'] = True
        return b

    def apply_buff(s, b):
        p = s.pl
        got = s.give_card(b)
        if b == 'random':                                           # the card turns over in the kiosk to show what it became
            s.kiosk['reveal'] = (s.t, got)
            sfx('glint')
            return
        s.kiosk['used'] = True
        sfx('buy')
        s.burst(p.x + p.w / 2, p.y, 20, card_info(got)[2], spd=120, glowing=True, grav=100)
        s.go('play', 0)

    def card_back(s, cx_, y, w, h, title=None):
        """The face-down card: a premium black poker card - gold lattice, double gold border, a sheen sliding over it and
        a gold '?' medallion in the middle."""
        GOLD, GOLD_D = (214, 176, 92), (70, 54, 26)
        rc = pg.Rect(cx_ - w // 2, y, w, h)
        rad = max(2, min(7, w // 6))
        pg.draw.rect(scr, (12, 8, 18), rc, border_radius=rad)
        pg.draw.rect(scr, GOLD, rc, 1, border_radius=rad)
        if w < 12:
            return
        inner = rc.inflate(-6, -6)
        pg.draw.rect(scr, GOLD, inner, 1, border_radius=max(1, rad - 2))
        panel = rc.inflate(-12, -12)
        old = scr.get_clip()
        scr.set_clip(panel)
        for k in range(-h, w + h, 9):                              # a diamond lattice in dark gold
            pg.draw.line(scr, GOLD_D, (panel.x + k, panel.y), (panel.x + k + h, panel.bottom))
            pg.draw.line(scr, GOLD_D, (panel.x + k, panel.y), (panel.x + k - h, panel.bottom))
        sx = int((s.t * 70) % (w + h * 2)) - h                     # a sheen sliding across now and then
        for d in range(4):
            pg.draw.line(scr, (110, 90, 50) if d % 3 else (160, 132, 70), (panel.x + sx + d, panel.y), (panel.x + sx + d - h // 2, panel.bottom))
        scr.set_clip(old)
        for px, py in (panel.topleft, panel.topright, panel.bottomleft, panel.bottomright):   # gold corner studs
            pg.draw.polygon(scr, GOLD, [(px, py - 3), (px + 3, py), (px, py + 3), (px - 3, py)])
        if w < 34:
            return
        r_ = int(min(w, h) * .24)
        cy = y + h // 2 - (6 if title and w >= 60 else 0)
        glow(scr, cx_, cy, r_ + 16, (60, 44, 14), .6)
        pg.draw.circle(scr, (20, 12, 26), (cx_, cy), r_)
        pg.draw.circle(scr, GOLD, (cx_, cy), r_, 2)
        pg.draw.circle(scr, GOLD_D, (cx_, cy), r_ - 4, 1)
        img = (F_PB if r_ >= 18 else F_PM).render("?", False, (255, 222, 140))
        scr.blit(img, (cx_ - img.get_width() // 2, cy - img.get_height() // 2 + 1))
        if title and w >= 60:
            img = F_S.render(tr(title), False, GOLD)
            if img.get_width() <= w - 14:
                pg.draw.rect(scr, (12, 8, 18), (cx_ - img.get_width() // 2 - 3, y + h - 22, img.get_width() + 6, 11))
                scr.blit(img, (cx_ - img.get_width() // 2, y + h - 22))

    def draw_card(s, b, cx_, y, on=False, w=96, h=134, desc=True, bare=False):
        """One card standing on the counter, like a poker card: rounded corners, a framed face, the category's kanji in two
        corners and the icon in a medallion. Normal: cream. Exit key: rose. Special: black with gold and a shifting mythic
        edge. The random card is shown face-down (card_back)."""
        title, text_, col = card_info(b)
        rc = pg.Rect(cx_ - w // 2, y, w, h)
        rad = max(2, min(7, w // 6))
        if (b in SPECIALS or b == 'random') and not bare:          # mythic: a glow that walks through the colours
            hc = hue(s.t * 90 + cx_) if b in SPECIALS else (214, 176, 92)
            glow(scr, cx_, y + h // 2, w // 2 + 26, qcol(tuple(c // 2 for c in hc), .8), .5)
        if on and not bare:
            pg.draw.rect(scr, RED, rc.move(6, 5), border_radius=rad)
        if b == 'random':
            s.card_back(cx_, y, w, h, title)
            if on and not bare:
                pg.draw.rect(scr, (255, 222, 140), rc.inflate(4, 4), 2, border_radius=rad + 1)
            return
        dark = b in SPECIALS
        fill = (18, 12, 28) if dark else ((250, 228, 228) if b == 'key' else (244, 238, 224))
        trim = (214, 176, 92) if dark else tuple(int(c * .62) for c in col)   # (darker on the cream face)
        pg.draw.rect(scr, fill, rc, border_radius=rad)
        edge_c = qcol(col, .75 + .25 * math.sin(s.t * 2.5)) if dark else INK      # each special its own colour, softly pulsing
        pg.draw.rect(scr, edge_c, rc, 2 if dark else 1, border_radius=rad)
        if w < 50:                                                 # (mid-turn: just the card)
            return
        pg.draw.rect(scr, trim, rc.inflate(-8, -8), 1, border_radius=max(1, rad - 2))
        if dark:
            for k_ in range(4):                                    # sparkles drifting up the card
                sx_ = rc.x + 8 + (k_ * 37 + int(s.t * 20)) % (w - 16)
                sy_ = y + h - 8 - (k_ * 23 + int(s.t * 30)) % (h - 16)
                scr.fill(hue(s.t * 120 + k_ * 90), (sx_, sy_, 1, 1))
        kj = CARD_KANJI.get(card_cat(b), '札')                    # the corner index, poker style
        img = F_JP.render(kj, True, trim)
        scr.blit(img, (rc.x + 6, y + 5))
        scr.blit(pg.transform.rotate(img, 180), (rc.right - 6 - img.get_width(), rc.bottom - 5 - img.get_height()))
        for px, py, sg in ((rc.x + 6 + img.get_width() // 2, y + 8 + img.get_height(), 1),
                           (rc.right - 6 - img.get_width() // 2, rc.bottom - 8 - img.get_height(), -1)):
            pg.draw.polygon(scr, trim, [(px, py - 3 * sg), (px + 3, py), (px, py + 3 * sg), (px - 3, py)])
        my_ = y + int(h * .26)                                     # the medallion with the icon
        pg.draw.circle(scr, (8, 4, 14) if dark else INK, (cx_, my_), 16)
        pg.draw.circle(scr, trim, (cx_, my_), 16, 2)
        glow(scr, cx_, my_, 18, tuple(c // 3 for c in col))
        s.buff_icon(b, cx_, my_, col)
        tc, dc = ((255, 236, 190), (205, 195, 225)) if dark else (INK, (60, 48, 70))
        ty = my_ + 20
        img = F_PS.render(tr(title), False, tc)
        if img.get_width() > w - 12:                                # long RU title: smaller font, two lines if need be
            tl = wrap(tr(title), F_S, w - 12)
            for j, line in enumerate(tl[:2]):
                img = F_S.render(line, False, tc)
                scr.blit(img, (cx_ - img.get_width() // 2, ty + 2 + j * 10))
            ty += 6 if len(tl) > 1 else 0
        else:
            scr.blit(img, (cx_ - img.get_width() // 2, ty))
        if desc:
            lines = wrap(tr(text_), F_S, w - 14)[:5]
            sp = 10 if len(lines) <= 4 else 9
            for j, line in enumerate(lines):
                img = F_S.render(line, False, dc)
                scr.blit(img, (cx_ - img.get_width() // 2, ty + 18 + j * sp))

    def card_img(s, b, w=96, h=134, back=False, desc=True):
        """The card drawn on its own transparent surface (4 px margin), with the effects that live on its face, so it can
        be tilted, scaled and squashed."""
        global scr
        surf = pg.Surface((w + 8, h + 8), pg.SRCALPHA)
        keep, scr = scr, surf
        try:
            if back:
                s.card_back(w // 2 + 4, 4, w, h)
            else:
                s.draw_card(b, w // 2 + 4, 4, False, w=w, h=h, desc=desc, bare=True)
            if w >= 40:
                s.card_face_fx('back' if back else b, surf, pg.Rect(4, 4, w, h))
        finally:
            scr = keep
        return surf

    def card_face_fx(s, b, surf, rc):
        """Effects painted on the card itself: a foil shine on the rare cards and one effect for each special card."""
        t = s.t
        if b in SPECIALS or b in ('random', 'back'):              # FOIL: a bright band sweeps across now and then
            per = 2.5 if b in SPECIALS else 3.0
            pos = (t % per) / per * (rc.w + rc.h + 60) - rc.h * .5 - 30
            band = pg.Surface(surf.get_size())
            pg.draw.polygon(band, (46, 42, 36), [(rc.x + pos, rc.y), (rc.x + pos + 10, rc.y), (rc.x + pos + 10 - rc.h * .5, rc.bottom),
                                                 (rc.x + pos - rc.h * .5, rc.bottom)])
            pg.draw.polygon(band, (90, 84, 70), [(rc.x + pos + 3, rc.y), (rc.x + pos + 5, rc.y), (rc.x + pos + 5 - rc.h * .5, rc.bottom),
                                                 (rc.x + pos + 3 - rc.h * .5, rc.bottom)])
            surf.blit(band, (0, 0), special_flags=pg.BLEND_RGB_ADD)
        per = 2 * (rc.w + rc.h) - 8

        def edge(u):                                              # a point on the card's edge, u = 0..1 around it
            d = (u % 1) * per
            x0, y0, x1, y1 = rc.x + 2, rc.y + 2, rc.right - 3, rc.bottom - 3
            for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
                ln = abs(bx - ax) + abs(by - ay)
                if d <= ln:
                    k = d / ln if ln else 0
                    return int(ax + (bx - ax) * k), int(ay + (by - ay) * k)
                d -= ln
            return x0, y0
        if b == 'gamble':                                         # ALL IN: the edge pulses red/white, chips ride round it
            k = .5 + .5 * math.sin(t * math.tau / .4)
            pg.draw.rect(surf, (255, int(60 + 195 * k), int(60 + 195 * k)), rc, 2, border_radius=7)
            for i in range(4):
                x, y = edge(t * .18 + i / 4)
                pg.draw.circle(surf, (255, 200, 40), (x, y), 3)
                pg.draw.circle(surf, (150, 20, 30), (x, y), 3, 1)
        elif b == 'jackpot':                                      # JACKPOT: casino bulbs chasing round the edge
            n = per // 8
            for i in range(n):
                x, y = edge(i / n)
                lit = (i + int(t * 12)) % 3 == 0
                pg.draw.circle(surf, (255, 250, 200) if lit else (130, 100, 30), (x, y), 2 if lit else 1)
        elif b == 'scars':                                        # BLOOD TRADE: drops run down from the top edge
            for i in range(4):                                    # (along the edges, away from the text)
                ph = (t * .45 + i * .29) % 1
                x = (rc.x + 4, rc.x + 7, rc.right - 8, rc.right - 5)[i]
                y = rc.y + 6 + int(ph * 18) + (i % 2) * 40
                pg.draw.line(surf, (110, 10, 24), (x, y - 8), (x, y), 2)
                pg.draw.ellipse(surf, (230, 20, 40), (x - 1, y - 1, 3, 4))
        elif b == 'joker':                                        # JOKER: a fast rainbow edge
            pg.draw.rect(surf, hue(t * 400), rc, 2, border_radius=7)
        elif b == 'slammaster':                                   # SLAM MASTER: a little impact star every 3 s
            k = (t % 3) / .45
            if k < 1:
                cx, cy = rc.centerx, rc.bottom - 6
                for a in range(-4, 5):
                    ang = math.pi + (a + 4) * math.pi / 8
                    ln = 4 + 16 * k
                    pg.draw.line(surf, qcol((140, 220, 255), 1 - k), (cx, cy), (cx + math.cos(ang) * ln, cy + math.sin(ang) * ln * .6), 1)

    def show_card(s, b, cx, cy, rot=0.0, scale=1.0, sx=1.0, sy=1.0, alpha=255, flash=0.0, sel=False, lift=0.0,
                  back=False, desc=True, dissolve=0.0, seed=0, w=96, h=134, fx=True, lean=0.0):
        """A card centred at (cx, cy): tilted, scaled, squashed (sx: the flip), flashed white or dissolving, with its shadow
        and - for the special cards - the effects around it."""
        t = s.t
        special = fx and not back and b in SPECIALS
        if special and b == 'joker':                              # JOKER: every few seconds a crazy little jitter
            ph = t + seed * 1.7
            if (ph % 3.1) < .5:
                cx += math.sin(ph * 47) * 2
                cy += math.cos(ph * 39) * 1
        if special and b == 'slammaster':                         # SLAM MASTER: the card shakes as the counter cracks
            k = (t % 3) / .35
            if k < 1:
                cx += math.sin(t * 95) * 2.5 * (1 - k)
                cy += abs(math.cos(t * 70)) * 2 * (1 - k)
        if special and b == 'invis':                              # SHADOW CLOAK: fades in and out of sight
            alpha = int(alpha * (.78 + .22 * (.5 + .5 * math.sin(t * math.tau / 2.4))))
        img = s.card_img(b, w, h, back, desc)
        if flash > 0:
            img.fill((int(255 * min(1, flash)),) * 3, special_flags=pg.BLEND_RGB_ADD)
        if abs(lean) > .05:                                       # LEAN: light catches the side toward the cursor
            sheen = pg.Surface(img.get_size())
            iw = img.get_width()
            for x in range(iw):
                v = (x / iw - .5) * 2 * (1 if lean > 0 else -1)
                if v > 0:
                    sheen.fill((int(40 * abs(lean) * v * v),) * 3, (x, 0, 1, img.get_height()))
            img.blit(sheen, (0, 0), special_flags=pg.BLEND_RGB_ADD)
        fw, fh = max(1, int(img.get_width() * scale * sx)), max(1, int(img.get_height() * scale * sy))
        if (fw, fh) != img.get_size():
            img = pg.transform.scale(img, (fw, fh))
        if abs(rot) > 1.0:                                        # (small tilts are skipped: they break the pixel text)
            img = pg.transform.rotate(img, rot)
        if dissolve > 0:                                          # pixel dissolve: blocks drop out
            bs = 6
            for by in range(0, img.get_height(), bs):
                for bx in range(0, img.get_width(), bs):
                    if ((bx * 73856093) ^ (by * 19349663) ^ (seed * 83492791)) % 997 / 997 < dissolve:
                        img.fill((0, 0, 0, 0), (bx, by, bs, bs))
        r = img.get_rect(center=(int(cx), int(cy)))
        a = alpha / 255
        if fx and dissolve <= 0 and sx > .3 and (special or b == 'random' or back):   # the glow behind
            hc = (hue(t * 300) if b == 'joker' else card_info(b)[2]) if special else (214, 176, 92)
            if special and b == 'scars':                          # BLOOD TRADE: the glow beats like a heart
                hb = (t * 1.1) % 1
                beat = max(0, 1 - abs(hb - .06) / .06) + max(0, 1 - abs(hb - .3) / .06) * .8
                hc = (255, 40, 60)
                glow(scr, cx, cy, int(fw / 2) + 20 + int(10 * beat), qcol((120, 10, 20), .5 + .5 * beat), .5)
            glow(scr, cx, cy, int(fw / 2) + 26, qcol(tuple(c // 2 for c in hc), .8 * a), .5)
        if special and b == 'four' and sx > .5:                   # EXTRA CARD: a second card peeks out behind
            ghost = img.copy()
            ghost.set_alpha(int(120 * a))
            scr.blit(pg.transform.rotate(ghost, 8), r.move(10, -8))
        if alpha < 255:
            img.set_alpha(alpha)
        if sel:                                                   # the red shadow grows as the card lifts
            off = 3 + int(5 * min(1, lift / 8))
            scr.blit(silhouette(img, RED, alpha), r.move(off - round(lean * 4), off - 1))   # (the shadow leans away)
        elif dissolve <= 0:
            scr.blit(silhouette(img, (0, 0, 0), int(110 * a)), r.move(2, 3))
        scr.blit(img, r)
        if not special or dissolve > 0 or sx < .5:
            return r
        for i in range(4):                                        # gold motes rising off the top edge
            ph = (t * .7 + i / 4 + seed * .13) % 1
            x = r.x + 8 + ((i * 37 + seed * 11) % max(1, r.w - 16))
            y = r.y + 4 - ph * 22
            scr.fill(qcol(hue(t * 120 + i * 60) if b == 'joker' else (255, 220, 120), 1 - ph), (x, int(y), 1, 1))
        if b == 'untouch':                                        # UNTOUCHABLE: a ring pushes out from the card every 2 s
            k = (t % 2) / .7
            if k < 1:
                pg.draw.rect(scr, qcol((255, 80, 200), min(1, 1.3 - k)), r.inflate(int(6 + 26 * k), int(6 + 26 * k)), 2, border_radius=10)
        elif b == 'invis':                                        # SHADOW CLOAK: dark smoke drifting off the bottom
            for i in range(5):
                ph = (t * .5 + i / 5) % 1
                x = r.x + 12 + i * (r.w - 24) // 4 + math.sin(t * 2 + i) * 3
                pg.draw.circle(scr, qcol((70, 50, 110), 1 - ph), (int(x), int(r.bottom - 6 + ph * 16)), int(2 + ph * 4))
        elif b == 'slammaster':                                   # SLAM MASTER: the counter cracks under it every 3 s
            k = (t % 3) / .6
            if k < 1:
                for sg in (-1, 1):
                    pg.draw.lines(scr, qcol((140, 220, 255), 1 - k), False,
                                  [(cx, r.bottom - 2), (cx + sg * 10 * min(1, k * 2), r.bottom + 2), (cx + sg * 22 * min(1, k * 2), r.bottom)], 2)
        return r

    def start_pick(s, i):
        """A kiosk card is chosen: it is yours at once; the animation (and the turn-over of a random card) plays after."""
        b = s.kiosk['cards'][i]
        got = s.give_card(b)
        s.kiosk['pick'] = {'t0': s.t, 'i': i, 'b': got, 'rnd': b == 'random'}
        sfx('glint')

    def st_kiosk(s, dt):
        """The Shinobi Kiosk: pick one of three buffs (sometimes an exit key)."""
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        el = ease((s.t - s.state_t) * 4)
        cards = s.kiosk['cards']
        nc = len(cards)
        s.sel %= nc
        pk = s.kiosk.get('pick')
        if pk:                                                     # a card was chosen: any key skips the animation
            if (s.act & {'ok', 'back', 'use'} or s.click) and s.t - pk['t0'] > .1:
                pk['t0'] -= 9
            s.act, s.click, s.moved = set(), False, False
        if 'left' in s.act:
            s.sel, s.selT = (s.sel - 1) % nc, s.t
            sfx('sel')
        if 'right' in s.act:
            s.sel, s.selT = (s.sel + 1) % nc, s.t
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
        s.kiosk_keeper(240, 92 + oy)                                                    # the vendor
        pg.draw.polygon(scr, WHITE, win, 2)
        for px in (30, 442):                                                            # wooden posts
            pg.draw.rect(scr, (78, 44, 24), (px, 146 + oy, 9, H - 146 - oy))
            pg.draw.line(scr, (120, 74, 42), (px + 1, 146 + oy), (px + 1, H))
        counter = pg.Rect(30, 146 + oy, 421, H - 146 - oy)                              # long wooden counter
        pg.draw.rect(scr, (122, 74, 40), counter)
        pg.draw.rect(scr, (168, 110, 62), (counter.x, counter.y, counter.w, 4))
        for i, ly in enumerate(range(counter.y + 14, counter.bottom, 11)):              # planks
            pg.draw.line(scr, (86, 50, 26), (counter.x, ly), (counter.right, ly))
            for jx in range(counter.x + 40 + (i % 2) * 55, counter.right, 110):
                pg.draw.line(scr, (86, 50, 26), (jx, ly - 10), (jx, ly))
        pg.draw.rect(scr, (60, 34, 18), counter, 2)
        mx, my = pg.mouse.get_pos()
        fire = 'ok' in s.act
        el_raw = s.t - s.state_t
        ka = s.kiosk.setdefault('anim', {})
        f60 = min(3.0, dt * 60)
        p = s.pl
        pt = None
        if pk:                                                     # the pick: (a random card turns over first)
            pt = s.t - pk['t0'] - (.8 if pk['rnd'] else 0)
        order = sorted(range(nc), key=lambda j: -abs(j - (pk['i'] if pk else 0)))
        draw_order = sorted(range(nc), key=lambda j: (j == s.sel) or (pk is not None and j == pk['i']))   # chosen card on top
        for i in draw_order:
            b = cards[i]
            on = i == s.sel and not pk
            cx_ = (120 + i * 120) if nc == 3 else (64 + i * 117)                   # (EXTRA CARD: four in a row)
            cy_ = 128 + 67                                                         # cards stand in front of the counter
            a = ka.setdefault(i, {'l': 0.0, 'lv': 0.0, 'c': 1.0, 'cv': 0.0, 'r': 0.0, 'rv': 0.0})
            ti = el_raw - .07 * i                                  # DEAL-IN: one after another, on a little arc
            if ti - dt < 0 <= ti:
                sfx('throw')
            k = max(0.0, min(1.0, ti / .35))
            dy = (1 - out_back(k)) * 160
            rot = (1 - ease(k)) * 12 * (1 if i % 2 else -1)
            dx = (1 - ease(k)) * (i - (nc - 1) / 2) * -18
            sy = .94 + .06 * (ti - .35) / .08 if 0 <= ti - .35 < .08 else 1.0   # a squash as it lands
            hov = pg.Rect(cx_ - 48, cy_ - 67, 96, 134).collidepoint(mx, my)
            tl = 8.0 if on else 0.0                                # HOVER: lift, and lean toward the cursor
            tlean = max(-1.0, min(1.0, (mx - cx_) / 48)) if on and hov else 0.0
            a['l'] += (tl - a['l']) * (1 - math.exp(-dt * 16))     # (a smooth glide, no bounce: no shaking)
            a['r'] += (tlean - a['r']) * (1 - math.exp(-dt * 10))
            dy += (0 if on else round(math.sin(s.t * 1.6 + i * 1.3) * 1.2)) - round(a['l'])   # IDLE: a slow breath
            dx += round(a['r'] * 3)                                # (no rotation or scaling: they break the pixel text)
            ws = s.t - s.selT
            if on and ws < .25:                                    # a little sideways shake when it is chosen
                dx += round(math.sin(ws * 45) * 2.5 * math.exp(-ws * 14))
            if b == 'untouch' and hov and not on:                  # UNTOUCHABLE shies away from the cursor
                dx += -3 if mx > cx_ else 3
            kw = dict(rot=rot, sy=sy, sel=on, lift=a['l'], seed=i, lean=a['r'])
            if pk and i == pk['i']:                                # the chosen card
                b = pk['b']
                u = s.t - pk['t0']
                if pk['rnd'] and u < .8:                           # FLIP: squash to nothing, swap face, pop back with a lift
                    if u < .12:
                        b, kw['sx'] = 'random', max(.02, 1 - (u / .12) ** 2)
                    else:
                        kw['sx'] = max(.02, out_back((u - .12) / .16))
                    dy -= 10 * math.sin(math.pi * min(1, u / .28))
                    kw['scale'] = 1.08
                    if abs(u - .12) < .02:
                        pg.draw.line(scr, WHITE, (cx_, cy_ - 70 + dy), (cx_, cy_ + 70 + dy), 2)
                elif pt is not None and pt >= 0:
                    kw['flash'] = .7 * (1 - pt / .1) if pt < .1 else 0
                    kw['scale'] = 1.08 + .07 * out_back(pt / .1)
                    if pt >= .16:                                  # FLY to you, shrinking, with afterimages
                        tx, ty = p.x + p.w / 2 - s.cam, p.y + p.h / 2 - s.camy
                        def at(v):
                            v = in_cubic(v)
                            mx_, my_ = (cx_ + tx) / 2, min(cy_, ty) - 60
                            return ((1 - v) ** 2 * cx_ + 2 * (1 - v) * v * mx_ + v * v * tx,
                                    (1 - v) ** 2 * (cy_ + dy) + 2 * (1 - v) * v * my_ + v * v * ty)
                        v = min(1.0, (pt - .16) / .32)
                        for gi in (3, 2, 1):
                            if v - gi * .04 > 0:
                                gx, gy = at(v - gi * .04)
                                s.show_card(b, gx, gy, scale=1.15 - .8 * in_cubic(v - gi * .04), alpha=30 + 25 * (3 - gi), fx=False, seed=i)
                        gx, gy = at(v)
                        kw['scale'] = 1.15 - .8 * in_cubic(v)
                        kw['rot'] = 0
                        s.show_card(b, gx, gy, **kw)
                        continue
            elif pk and pt is not None and pt >= 0:                # the others fall away and dissolve, the far ones first
                d = .04 * order.index(i)
                v = max(0.0, min(1.0, (pt - .04 - d) / .19))
                dy += 60 * in_cubic(v) + 10 * v
                kw['rot'] += 10 * v * (1 if i > pk['i'] else -1)
                kw['dissolve'] = v
                kw['sel'] = False
                if v >= 1:
                    continue
            s.show_card(b, cx_ + dx, cy_ + dy, **kw)
            r = pg.Rect(cx_ - 48, cy_ - 67, 96, 134)
            if s.moved and r.collidepoint(mx, my) and not on and not pk:
                s.sel, s.selT = i, s.t
                sfx('sel')
            if s.click and r.collidepoint(mx, my) and not pk and (not TOUCH or on):
                s.sel, fire = i, True
        rv = pk
        if s.upg('roll') and not s.kiosk.get('rolled') and not rv:   # the Shadow Samurai's upgrade: one re-roll per district
            rb = pg.Rect(W // 2 - 60, H - 26, 120, 20)
            hov = rb.collidepoint(mx, my)
            pg.draw.polygon(scr, RED if hov else INK, [(rb.x, rb.y), (rb.right, rb.y - 2), (rb.right - 4, rb.bottom), (rb.x - 4, rb.bottom + 2)])
            pg.draw.polygon(scr, WHITE, [(rb.x, rb.y), (rb.right, rb.y - 2), (rb.right - 4, rb.bottom), (rb.x - 4, rb.bottom + 2)], 1)
            key = s.bind_name('pad' if s.last_input == 'pad' else 'kb', 'use')
            img = F_PS.render(f"[{key}] " + tr("ROLL CARDS"), False, WHITE)
            scr.blit(img, (rb.centerx - img.get_width() // 2, rb.y + 2))
            if 'use' in s.act or (hov and s.click):
                fire = False
                s.kiosk['rolled'] = True
                s.kiosk['cards'] = s.roll_kiosk()
                s.kiosk['anim'] = {}
                s.state_t = s.t                                  # the cards are dealt again
                sfx('throw')
                sfx('glint')
        if pk:
            if pt is not None and pt > .5:                         # it reached you: back to the street
                s.kiosk['used'], s.kiosk['pick'] = True, None
                sfx('buy')
                s.burst(p.x + p.w / 2, p.y, 20, card_info(pk['b'])[2], spd=120, glowing=True, grav=100)
                s.go('play', 0)
        elif fire and el_raw > .35 + .07 * (nc - 1):            # (not before the last card has landed)
            s.start_pick(s.sel)
        elif 'back' in s.act:
            s.go('play', 0)

    def st_gift(s, dt):
        """JOKER / SCAR CARDS: the kiosk's shutter comes down, black cards are left on the counter; take them and they
        turn over to show what you got."""
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        el = s.t - s.state_t
        cards, n = s.gift_cards, len(s.gift_cards)
        oy = int((1 - ease(el * 3)) * -200)
        sign = [(70, 8 + oy), (410, 4 + oy), (406, 34 + oy), (74, 38 + oy)]
        pg.draw.polygon(scr, INK, sign)
        pg.draw.polygon(scr, RED, sign, 2)
        outlined(tr(s.gift_title), F_PM, (255, 90, 110), 240, 8 + oy, center=True, r=1)
        win = [(40, 46 + oy), (440, 42 + oy), (446, 146 + oy), (34, 150 + oy)]
        pg.draw.polygon(scr, (20, 26, 52), win)
        sh = ease(min(1, max(0, (el - .35) / .6)))                    # the shutter rolls down
        if sh > 0:
            bot = 44 + oy + int(104 * sh)
            pg.draw.rect(scr, (58, 56, 70), (36, 44 + oy, 408, bot - 44 - oy))
            for ly in range(44 + oy + 6, bot, 7):
                pg.draw.line(scr, (34, 32, 44), (36, ly), (443, ly))
                pg.draw.line(scr, (90, 88, 104), (36, ly + 1), (443, ly + 1))
            pg.draw.rect(scr, (24, 22, 30), (36, bot - 4, 408, 4))
            if el - dt < .95 <= el:
                sfx('door')
                s.shake = 4
        pg.draw.polygon(scr, WHITE, win, 2)
        counter = pg.Rect(30, 146 + oy, 421, H - 146 - oy)
        pg.draw.rect(scr, (122, 74, 40), counter)
        pg.draw.rect(scr, (168, 110, 62), (counter.x, counter.y, counter.w, 4))
        for ly in range(counter.y + 14, counter.bottom, 11):
            pg.draw.line(scr, (86, 50, 26), (counter.x, ly), (counter.right, ly))
        w = min(96, (452 - (n - 1) * 8) // max(1, n))
        ch = min(134, int(w * 1.4))
        flip = s.gift_flip
        for i, b in enumerate(cards):
            cx_ = W // 2 + int((i - (n - 1) / 2) * (w + 8))
            ti = el - 1.0 - i * .07                                # dealt onto the counter one after another
            if ti < 0:
                continue
            if ti - dt < 0:
                sfx('throw')
            k = min(1.0, ti / .35)
            cy_ = 262 - ch / 2 + (1 - out_back(k)) * 160
            rot = (1 - ease(k)) * 12 * (1 if i % 2 else -1)
            sy = .94 + .06 * (ti - .35) / .08 if 0 <= ti - .35 < .08 else 1.0
            u = -1.0 if flip is None else s.t - flip - i * .25
            if u < .12:                                            # face down (and the first half of the turn)
                sx = 1.0 if u < 0 else max(.02, 1 - (u / .12) ** 2)
                if u >= 0:
                    cy_ -= 10 * math.sin(math.pi * min(1, u / .28))
                s.show_card(b, cx_, cy_, rot=rot, sx=sx, sy=sy, back=True, w=w, h=ch, seed=i)
                if 0 <= u and abs(u - .12) < .02:
                    pg.draw.line(scr, WHITE, (cx_, cy_ - ch / 2), (cx_, cy_ + ch / 2), 2)
                continue
            v = (u - .12) / .16                                    # face up: pops open
            cy_ -= 10 * math.sin(math.pi * min(1, u / .28))
            if b == 'slammaster' and u < .5:                       # SLAM MASTER lands with a thud
                cy_ -= 20 * (1 - in_cubic(min(1, (u - .12) / .3)))
                if u - dt < .42 <= u:
                    s.shake = 3
                    sfx('slam')
            if u > .45:                                            # then breathes like the kiosk cards
                cy_ += math.sin(s.t * 1.6 + i * 1.3) * 1.5
            s.show_card(b, cx_, cy_, rot=rot, sx=max(.02, out_back(v)), w=w, h=ch, desc=w >= 80, seed=i)
            rv_ = u - .43                                          # the reveal: a ring of light for the special cards
            if b in SPECIALS and 0 <= rv_ < .45:
                q = ease(rv_ / .3)
                rr = pg.Rect(0, 0, w, ch).inflate(int(6 + 24 * q), int(6 + 24 * q))
                rr.center = (cx_, int(cy_))
                glow(scr, cx_, cy_, int(w * .9), qcol(tuple(c // 2 for c in card_info(b)[2]), 1 - rv_ / .45), .7)
                pg.draw.rect(scr, qcol(card_info(b)[2], 1 - rv_ / .45), rr, 3, border_radius=10)
                if u - dt < .43:
                    sfx('myth')
                    s.shake = max(s.shake, 2)
            if b == 'jackpot' and 0 <= rv_ < .9:                   # JACKPOT: a shower of gold
                for j in range(24):
                    ph = rv_ / .9
                    x = cx_ - w // 2 - 10 + (j * 29) % (w + 20)
                    y = cy_ - ch / 2 - 30 + ph * (ch + 40) * (0.5 + (j % 6) * .1) - (j % 4) * 6
                    pg.draw.circle(scr, (255, 210, 60) if j % 3 else (255, 250, 200), (int(x), int(y)), 2)
                    scr.fill((150, 100, 20), (int(x) - 1, int(y) + 1, 2, 1))
        ready = el > 1.0 + n * .07 + .4
        if flip is None:
            if ready:
                outlined(tr("TAKE THE CARDS" if n > 1 else "TAKE THE CARD"), F_PS, WHITE, W // 2, 104, center=True, r=1)
                if s.act & {'ok', 'jump', 'atk', 'use'} or s.click:
                    s.gift_flip = s.t
                    for b in cards:
                        s.give_card(b)
                    sfx('kiosk')
                    sfx('glint')
        elif s.t - flip > .45 + (n - 1) * .25:
            outlined(tr("CONTINUE"), F_PS, WHITE if int(s.t * 2.5) % 2 else (150, 140, 170), W // 2, 104, center=True, r=1)
            if s.act & {'ok', 'jump', 'atk', 'use', 'back'} or s.click:
                p = s.pl
                s.burst(p.x + p.w / 2, p.y, 20, (255, 60, 80), spd=120, glowing=True, grav=100)
                sfx('buy')
                s.go('play', 0)

    def open_gifts(s):
        """Turn the waiting JOKER / SCAR CARDS tokens into real cards and show them."""
        got = []
        for g in s.gifts:
            b = s.random_card(.25 if g == 'random' else .2, exclude=got)     # JOKER 75/25, BLOOD TRADE 80/20
            got.append(b)
        s.gift_cards, s.gifts, s.gift_flip = got, [], None
        joker, scar = s.buff('joker'), s.buff('scars')
        s.gift_title = "JOKER" if joker and not scar else ("BLOOD TRADE" if scar and not joker else "FREE CARDS")
        s.go('gift', 0)

    def st_play(s, dt):
        if TOUCH:
            s.touch_tick(dt)
        if getattr(s, 'gifts', None) and s.enterT <= 0 and not s.pl.dead and s.superT < 0:   # JOKER / SCAR CARDS
            s.open_gifts()
            return
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
        s.draw_boss_hud()
        if TOUCH and s.superT < 0:
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
        if getattr(s, 'pfocus_t', None) != s.state_t:            # (a fresh pause: the menu has the focus)
            s.pfocus, s.pfocus_t = None, s.state_t
        on_cards = s.pfocus is not None
        keep = s.act
        if on_cards:                                             # the arrows / OK belong to the cards now
            s.act = s.act - {'up', 'down', 'ok'}
        s.p_items([("RESUME", lambda: s.go('play', 0)), ("RESTART", s.restart), ("MAIN MENU", s.to_menu)], 28, 108, wipe=False)
        s.act = keep
        if s.state == 'pause':
            s.pause_cards(el)

    def pause_cards(s, el):
        """The right side of the pause menu: the kiosk cards taken this run, as icons. Point at one (or press right and
        walk over them with the arrows / stick) to read what it does."""
        off = (1 - el) * 260
        x0, y0, pw = 268 + off, 14, W - 268 - 10
        pg.draw.polygon(scr, INK, [(x0 + 8, y0), (x0 + pw, y0 - 4), (x0 + pw, H - 10), (x0, H - 6)])
        pg.draw.polygon(scr, RED, [(x0 + 8, y0), (x0 + pw, y0 - 4), (x0 + pw - 2, y0 + 2), (x0 + 7, y0 + 5)])
        outlined(tr("YOUR CARDS"), F_PS, WHITE, x0 + 14, y0 + 8, r=1)
        cards = sorted(s.buffs.items())
        if not cards:
            s.pfocus = None
            outlined(tr("NO CARDS YET"), F_S, (170, 160, 190), x0 + 14, y0 + 34, r=1)
            outlined(tr("Find a shinobi kiosk"), F_S, (120, 110, 140), x0 + 14, y0 + 48, r=1)
            return
        cols, sz, gap = 7, 22, 4
        n = len(cards)
        A = s.act
        if s.pfocus is None:
            if 'right' in A:                                    # right: from the menu over to the cards
                s.pfocus = 0
                sfx('sel')
        else:
            f, r_, c_ = s.pfocus, s.pfocus // cols, s.pfocus % cols
            if 'left' in A:
                f = None if c_ == 0 else f - 1                  # (left of the first column: back to the menu)
            if 'right' in A and f + 1 < n and c_ + 1 < cols:
                f += 1
            if 'up' in A and r_ > 0:
                f -= cols
            if 'down' in A and f + cols < n:
                f += cols
            if f != s.pfocus:
                s.pfocus = f
                sfx('sel')
        mx, my = pg.mouse.get_pos()
        show = s.pfocus
        gy0 = y0 + 30
        for i, (b, k) in enumerate(cards):
            col = card_info(b)[2]
            x, y = x0 + 14 + (i % cols) * (sz + gap), gy0 + (i // cols) * (sz + gap)
            rc = pg.Rect(x, y, sz, sz)
            if rc.collidepoint(mx, my):                         # the mouse points at it
                show = i
                if s.moved and s.pfocus != i:
                    s.pfocus = i
            on = i == show
            if on:
                pg.draw.rect(scr, WHITE, rc.inflate(4, 4))
            pg.draw.rect(scr, (20, 12, 28), rc)
            pg.draw.rect(scr, hue(s.t * 90 + i * 40) if b in SPECIALS else col, rc, 1)   # specials: the mythic edge
            s.buff_icon(b, x + sz // 2, y + sz // 2, col)
            if k > 1:
                outlined(f"x{k}", F_S, WHITE, x + sz - 8, y + sz - 9, r=1)
        if show is None or show >= n:
            outlined(tr("Point at a card" if s.last_input != 'pad' else "Press right to look at them"),
                     F_S, (130, 120, 150), x0 + 14, gy0 + ((n - 1) // cols + 1) * (sz + gap) + 6, r=1)
            return
        b, k = cards[show]                                      # what the chosen card does
        title, desc, col = card_info(b)
        desc = tr(desc)
        if b in getattr(s, 'timed', {}):                         # GOLD RUSH / BOUNTY HUNTER: time left
            desc += f" ({fmt_time(max(0, max(s.timed[b]) - s.gtime))})"
        if b == 'medic':
            desc += f" ({getattr(s, 'medic_left', 5)} {tr('districts left')})"
        y = gy0 + ((n - 1) // cols + 1) * (sz + gap) + 6
        pg.draw.line(scr, col, (x0 + 14, y), (x0 + pw - 12, y))
        outlined(tr(title) + (f" x{k}" if k > 1 else ""), F_S, col, x0 + 14, y + 5, r=1)
        words, ln, yy = desc.split(), "", y + 18
        for w_ in words + [None]:                               # the description, wrapped to the panel
            if w_ is None or (ln and F_S.size(ln + " " + w_)[0] > pw - 28):
                text(ln, F_S, (210, 202, 224), x0 + 14, yy)
                yy += 11
                ln = w_ or ""
            else:
                ln = (ln + " " + w_).strip()

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
        s.result_rows([("DISTRICT", s.lvl, lambda v: f"{int(v)}" + ("" if getattr(s, 'endless', False) else f" / {LEVELS}")), ("TIME", s.gtime, fmt_time),
                       ("KILLS", s.kills, lambda v: str(int(v))), ("COINS LOST", s.score, lambda v: str(int(v)))], 112)
        s.p_items([("RETRY", s.new_run), ("MAIN MENU", s.to_menu)], 150, 194, font=F_PM, dy=28)

    def st_exit(s, dt):
        s.draw_world()
        scr.blit(s.dim, (0, 0))
        pg.draw.polygon(scr, RED, [(0, 10), (W, 0), (W, 80), (0, 94)])
        won = s.end_kind == 'victory'
        ransom("RUN COMPLETE" if won else "ESCAPED", W // 2, 42, [F_PB, F_P], 23, s.t, center=True, tilt=-4)
        outlined("All districts are behind you." if won else "The exit key turns. You live to cut another night.",
                 F_S, WHITE, W // 2, 70, center=True, r=1)
        num = lambda v: str(int(v))
        s.result_rows([("DISTRICTS", s.runst['levels'], lambda v: f"{int(v)}" + ("" if getattr(s, 'endless', False) else f" / {LEVELS}")), ("TIME", s.gtime, fmt_time),
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
        th = s.act_theme(s.lvl + 1)                                    # the part of the city you are heading into
        if s.lvl % 5 == 0:                                             # a new act: its own title card
            glow(scr, W // 2, 70, 120, qcol(tuple(c // 3 for c in th['street']), min(1, el)))
            ransom(f"{tr('ACT')} {('I', 'II', 'III')[min(2, s.lvl // 5)] if not getattr(s, 'endless', False) else s.lvl // 5 + 1}", W // 2, 26, [F_PB, F_P],
                   13 + s.lvl, s.t, center=True, tilt=-3)
            outlined(th['jp'], F_JPB, (220, 210, 230), W // 2, 60, center=True, r=1)
            outlined(tr(th['name']), F_PM, th['street'], W // 2, 78, center=True, r=1)
            outlined(tr(th['sub']), F_S, (220, 210, 230), W // 2, 100, center=True, r=1)
            outlined(s.lvl_label(s.lvl + 1), F_PS, RED, W // 2, 116, center=True, r=1)
            if el > 1.2:
                outlined(tr("THE BOSS'S HEART: +1 MAX HP"), F_S, (255, 120, 140), W // 2, 214, center=True, r=1)
            ph = tr(s.phrase)
            img = F_PM.render(ph[:n], False, WHITE)
            scr.blit(img, (W // 2 - F_PM.size(ph)[0] // 2, 140))
        else:
            outlined(s.lvl_label(s.lvl + 1), F_PS, RED, W // 2, 96, center=True, r=1)
            outlined(f"{th['jp']}  {tr(th['name'])}", F_JP, (200, 190, 230), W // 2, 78, center=True, r=1)
            ph = tr(s.phrase)
            img = F_PM.render(ph[:n], False, WHITE)
            scr.blit(img, (W // 2 - F_PM.size(ph)[0] // 2, 120))
        if el > 3.2 or (el > 1 and s.act & {'ok', 'jump', 'atk'}):
            s.lvl += 1
            s.build_level()
            s.start_level()

    def st_victory(s, dt):
        scr.fill((4, 2, 8))
        el = s.t - s.state_t
        glow(scr, W // 2, 110, 140, qcol((80, 20, 40), min(1, el / 2)))
        if el > .4:
            ransom(tr(VICTORY_LINES[0]).upper(), W // 2, 70, [F_PB, F_P], 41, s.t, center=True, tilt=-4)
        for i, line in enumerate(VICTORY_LINES[1:]):
            a = el - 1.4 - i * 1.1
            if a > 0:
                line = tr(line)
                vf = next((f_ for f_ in (F_PM, F_PS, F_S) if f_.size(line)[0] <= W - 16), F_S)   # long lines drop to a smaller font
                img = vf.render(line[:int(a * 35)], False, WHITE)
                scr.blit(img, (W // 2 - vf.size(line)[0] // 2, 118 + i * 26 + (F_PM.get_height() - vf.get_height()) // 2))
        if el > 5.5:
            outlined("press to continue", F_S, (200, 190, 230), W // 2, 236, center=True, r=1)
        if (el > 5.5 and s.act & {'ok', 'jump', 'atk'}) or el > 12:
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
                if ev.type in (pg.WINDOWMINIMIZED, pg.WINDOWHIDDEN):   # minimized: silence, and the run waits in the pause menu
                    s.minimized = True
                    if pg.mixer.get_init():
                        pg.mixer.pause()
                        pg.mixer.music.pause()
                    if s.state == 'play':
                        s.go('pause', 0)
                elif ev.type in (pg.WINDOWRESTORED, pg.WINDOWSHOWN, pg.WINDOWMAXIMIZED) and getattr(s, 'minimized', False):
                    s.minimized = False
                    if pg.mixer.get_init():
                        pg.mixer.unpause()
                        pg.mixer.music.unpause()
                s.handle_event(ev)
            if getattr(s, 'minimized', False):                   # nothing runs (and nothing plays) while it's minimized
                continue
            s.frame(dt)
            pg.display.flip()

    def frame(s, dt):
        if s.wipe_fn is not None:                # block input while the wipe covers the screen
            s.act, s.click = set(), False
        getattr(s, 'st_' + s.state)(dt)
        el = s.t - s.state_t
        if s.state in MENU_STATES and el < .6 and s.state not in ('pause', 'kiosk', 'gift'):   # the camera settles onto the menu
            k = ease(min(1, el / .6))
            z, a = 1 + .22 * (1 - k), -5 * (1 - k)
            img = pg.transform.rotozoom(scr.copy(), a, z)
            scr.blit(img, (W // 2 - img.get_width() // 2 + int((1 - k) * 30), H // 2 - img.get_height() // 2))
        if s.state in MENU_STATES and el < .5:   # Persona: a menu opens by shattering - black and red shards fly apart
            k = ease(min(1, el / .4))
            for j, (cx_, cy_, pts, col) in enumerate(SHARDS):
                vx_, vy_ = SHARD_DIR[j]
                ox, oy_ = vx_ * k * 520, vy_ * k * 520
                a = k * (2.4 if j % 2 else -2.4)
                ca, sa = math.cos(a), math.sin(a)
                poly = [(cx_ + ox + (px - cx_) * ca - (py - cy_) * sa, cy_ + oy_ + (px - cx_) * sa + (py - cy_) * ca) for px, py in pts]
                pg.draw.polygon(scr, col, poly)
                pg.draw.polygon(scr, WHITE, poly, 1)
        if s.fade > 0:                           # fade-in on screen changes
            s.black.set_alpha(int(min(1, s.fade) * 255))
            scr.blit(s.black, (0, 0))
            s.fade -= dt * 3
        if s.wipe_fn is not None:                # the next screen, straight away (a short fade-in)
            fn, s.wipe_fn = s.wipe_fn, None
            fn()
            s.fade = .3


def cut_halves(img):
    """The screen split along one diagonal katana stroke: (upper-left half, lower-right half)."""
    A = img.convert_alpha()
    B = A.copy()
    c0, c1 = W * .62, W * .38
    pg.draw.polygon(A, (0, 0, 0, 0), [(c0, 0), (W, 0), (W, H), (c1, H)])
    pg.draw.polygon(B, (0, 0, 0, 0), [(0, 0), (c0, 0), (c1, H), (0, H)])
    return A, B


MENU_ICONS = {"SETTINGS": 'gear'}


def wipe_icon(kind, x, y, r, a, col):
    """The big shape turning in the middle of a screen change: a star, a gear, a speaker, a monitor, a gamepad."""
    r = max(2, r)
    if kind == 'gear':
        for i in range(8):                                       # teeth
            q = a * .5 + i * math.tau / 8
            pts = [(x + math.cos(q + d) * r * rr, y + math.sin(q + d) * r * rr) for d, rr in ((-.18, .7), (-.12, 1.0), (.12, 1.0), (.18, .7))]
            pg.draw.polygon(scr, col, pts)
        pg.draw.circle(scr, col, (int(x), int(y)), int(r * .74))
        pg.draw.circle(scr, RED if col != RED else INK, (int(x), int(y)), int(r * .3))
    elif kind == 'sound':                                        # speaker and its waves
        w = math.sin(a * 2) * .06
        pg.draw.polygon(scr, col, [(x - r * .8, y - r * .25), (x - r * .45, y - r * .25), (x - r * .05, y - r * .65),
                                   (x - r * .05, y + r * .65), (x - r * .45, y + r * .25), (x - r * .8, y + r * .25)])
        for j, rr in enumerate((.45, .75)):
            rect = (x - r * rr + r * .05, y - r * rr, r * rr * 2, r * rr * 2)
            pg.draw.arc(scr, col, rect, -.9 - w, .9 + w, max(2, int(r * .13)))
    elif kind == 'monitor':                                      # screen on a stand
        tilt = math.sin(a) * .05
        pts = [(x - r, y - r * .62), (x + r, y - r * (.62 + tilt)), (x + r, y + r * .4), (x - r, y + r * (.4 + tilt))]
        pg.draw.polygon(scr, col, pts)
        pg.draw.polygon(scr, RED if col != RED else INK, [(x - r * .82, y - r * .48), (x + r * .82, y - r * (.48 + tilt)),
                                                         (x + r * .82, y + r * .26), (x - r * .82, y + r * (.26 + tilt))])
        pg.draw.polygon(scr, col, [(x - r * .14, y + r * .4), (x + r * .14, y + r * .4), (x + r * .3, y + r * .78), (x - r * .3, y + r * .78)])
        pg.draw.rect(scr, col, (x - r * .5, y + r * .74, r, r * .14))
    elif kind == 'pad':                                          # a gamepad
        pg.draw.ellipse(scr, col, (x - r, y - r * .5, r * .9, r))
        pg.draw.ellipse(scr, col, (x + r * .1, y - r * .5, r * .9, r))
        pg.draw.rect(scr, col, (x - r * .6, y - r * .5, r * 1.2, r * .7))
        hole = RED if col != RED else INK
        pg.draw.rect(scr, hole, (x - r * .7, y - r * .08, r * .4, r * .12))
        pg.draw.rect(scr, hole, (x - r * .56, y - r * .22, r * .12, r * .4))
        for dx_, dy_ in ((.5, -.12), (.62, 0), (.5, .12), (.38, 0)):
            pg.draw.circle(scr, hole, (int(x + r * dx_), int(y + r * dy_)), max(1, int(r * .07)))
    else:
        star(x, y, int(r), a, col)


MENU_STATES = ('menu', 'stats', 'settings', 'controls', 'skins', 'locsel', 'pause', 'kiosk', 'gift', 'upgrades', 'teleport')
SHARDS = [(70, 50, [(0, 0), (150, 0), (40, 110)], INK), (250, 30, [(150, 0), (330, 0), (230, 80)], RED),
          (410, 60, [(330, 0), (W, 0), (W, 140)], INK), (60, 200, [(0, 110), (120, 160), (0, H)], RED),
          (240, 150, [(120, 160), (300, 90), (330, 230)], INK), (430, 210, [(W, 140), (330, 230), (W, H)], RED),
          (190, 250, [(0, H), (120, 160), (300, H)], INK)]
SHARD_DIR = [(-.8, -.6), (.1, -1), (.8, -.6), (-1, .3), (.9, .45), (.7, .7), (-.4, .9)]   # where each shard flies


if __name__ == '__main__':
    Game().run()
