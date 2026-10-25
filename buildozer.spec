[app]
title = Neon Ronin
package.name = neonronin
package.domain = org.neonronin
source.dir = .
source.include_exts = py,png,wav,ttf
source.include_patterns = assets/*,assets/fonts/*
source.exclude_dirs = bin,.buildozer,.github
version = 1.0
requirements = python3,pygame
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
