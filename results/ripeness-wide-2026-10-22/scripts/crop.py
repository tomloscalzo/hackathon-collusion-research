"""Trim trailing white space at the bottom of rendered chart PNGs (keeps a 24 px margin).
Usage: python -X utf8 crop.py <charts dir>"""
import glob, os, sys
from PIL import Image

for fn in glob.glob(os.path.join(sys.argv[1], "*.png")):
    im = Image.open(fn).convert("RGB")
    w, h = im.size
    px = im.load()
    last = 0
    for y in range(h - 1, -1, -1):
        if any(px[x, y] != (255, 255, 255) for x in range(0, w, 2)):
            last = y
            break
    im.crop((0, 0, w, min(h, last + 24))).save(fn)
print("cropped")
