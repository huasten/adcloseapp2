[app]
title = 广告关闭器
package.name = adcloser
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0
requirements = python3,kivy,uiautomator2,adbutils,pillow
orientation = portrait
fullscreen = 0

[android]
p4a.branch = stable
android.api = 28
android.minapi = 21
android.sdk = 24
android.ndk = 25b
android.arch = armeabi-v7a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 0
