from PIL import Image
import numpy as np
from random import randint, choice, random
import math, skimage.draw
import svgwrite

ORIGINAL_IMAGE = "dandy01.png"
STROKE_WIDTH = 1.25
LINE_CAP = 'round'
MAX_VARIANCE = 0.000005
COLOUR_VARIATION = 5
WIDTH_VARIATION = 0.25
MAX_JUMP = 8
MIN_STROKE_LENGTH = 0.02
MIN_TRIES_PER_ORDER = 10000
MAX_TRIES_PER_ORDER_PER_ORDER = 40
MISSES_PER_BATCH = 32
MAX_ORDER = 1000

def colourVariation(colour, amount):
    return [max(0, min(255, element + randint(0, amount) - randint(0, amount)))
            for element in colour]

def widthVariation(wide, amount):
    maxchange = wide * amount
    return max(0, wide + maxchange * random() - maxchange * random())

def addLine(startrow, startcolumn, endrow, endcolumn):
    if startrow != endrow or startcolumn != endcolumn:
        xDisp, yDisp = endrow - startrow, endcolumn - startcolumn
        rows, columns = skimage.draw.line(startrow, startcolumn, endrow, endcolumn)
        channels = current[rows, columns]
        if np.sum(np.var(channels, 0)) / (xDisp * xDisp + yDisp * yDisp) < MAX_VARIANCE:
            linecolour = colourVariation(np.average(channels, 0), COLOUR_VARIATION)
            current[rows, columns] = linecolour
            svgdrawing.add(svgdrawing.line((startcolumn, startrow), (endcolumn, endrow),
                                           stroke=
                                           f'rgb({",".join([str(int(element)) for element in linecolour[:3]])})',
                                           stroke_width=widthVariation(STROKE_WIDTH, WIDTH_VARIATION),
                                           stroke_linecap=LINE_CAP))
            return True
    return False

if __name__ == '__main__':
    outbasename, outextension = ORIGINAL_IMAGE.split(".")
    originalImage = Image.open(ORIGINAL_IMAGE)
    originalImage.load()
    current = np.asarray(originalImage, dtype="int32")
    width, height, numChannels = current.shape
    svgdrawing = svgwrite.Drawing(".".join([outbasename, "svg"]), size=(height, width))
    widthMinusOne, heightMinusOne = width - 1, height - 1
    numberWidth = 1 + math.ceil(math.log10(MAX_ORDER))
    for order in range(MAX_ORDER):
        ordersleft = max(MIN_STROKE_LENGTH, 1.0 - order / MAX_ORDER)
        basename = f"{outbasename}{str(order).zfill(numberWidth)}"
        filename = ".".join([basename, outextension])
        widthdifference, heightdifference = ordersleft * width, ordersleft * height
        for gen in range(max(MIN_TRIES_PER_ORDER, order * MAX_TRIES_PER_ORDER_PER_ORDER)):
            x1, y1 = randint(0, widthMinusOne), randint(0, heightMinusOne)
            if numChannels < 4 or current[x1, y1, 3] > 0:
                x2 = min(widthMinusOne, max(0, int(0.5 + x1 + random() * widthdifference)))
                y2 = min(heightMinusOne, max(0, int(0.5 + y1 + random() * heightdifference)))
                if numChannels < 4 or current[x2, y2, 3] > 0:
                    if addLine(x1, y1, x2, y2):
                        misses = 0
                        while misses < MISSES_PER_BATCH:
                            xOff, yOff = randint(-MAX_JUMP, MAX_JUMP), randint(-MAX_JUMP, MAX_JUMP)
                            fine = choice(((0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 0),
                                           (1, 0, 0, 0), (0, 0, 0, -1), (0, 0, -1, 0),
                                           (0, -1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 0),),)
                            tx1 = max(0, min(widthMinusOne, x1 + xOff + fine[0]))
                            ty1 = max(0, min(heightMinusOne, y1 + yOff + fine[1]))
                            tx2 = max(0, min(widthMinusOne, x2 + xOff + fine[2]))
                            ty2 = max(0, min(heightMinusOne, y2 + yOff + fine[3]))
                            if addLine(tx1, ty1, tx2, ty2):
                                misses = 0
                                x1, y1, x2, y2 = tx1, ty1, tx2, ty2
                            else:
                                misses += 1
        svgdrawing.save()
        print(filename)
