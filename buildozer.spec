[app]
title = Neon Ronin
package.name = neonronin
package.domain = org.neonronin
source.dir = .
source.include_exts = py,png,wav,ttf
source.include_patterns = assets/*,assets/fonts/*
source.exclude_dirs = bin,.buildozer,.github
version = 1.0
# Python 3.10: the pygame recipe of python-for-android doesn't compile against 3.11 (longintrepr.h moved)
requirements = python3==3.10.12,hostpython3==3.10.12,pygame
orientation = landscape
fullscreen = 1
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #04020A
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
