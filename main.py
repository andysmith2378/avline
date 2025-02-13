import numpy as np
import math, svgwrite, skimage.draw
from PIL import Image
from random import randint, choice, random
from skimage.color import rgb2gray, rgba2rgb
from skimage.feature import canny
from skimage.transform import probabilistic_hough_line

ORIGINAL_IMAGE = "final.png"
STROKE_WIDTH = 1.25
LINE_CAP = 'round'
MAX_VARIANCE = 0.00001
COLOUR_VARIATION = 5
WIDTH_VARIATION = 0.5
HOUGH_LINE_LENGTH = 40
HOUGH_LINE_THRESHOLD = 10
HOUGH_LINE_GAP = 10
CANNY_DEVIATION = 2
TOO_RECTANGLE = 20.0
MAX_JUMP = 8
FIRST_JUMP = 8
MIN_FIRST_EDGE_DISP = 100
MIN_STROKE_LENGTH = 0.02
TOO_SHORT_IN_BATCH = 25
MIN_TRIES_PER_ORDER = 5000
MAX_TRIES_PER_ORDER_PER_ORDER = 200
MISSES_PER_BATCH = 32
FIRST_MISSES = 128
MAX_ORDER = 500

def colourVariation(colour, amount):
    return [max(0, min(255, element + randint(0, amount) - randint(0, amount)))
            for element in colour]

def widthVariation(wide, amount):
    maxchange = wide * amount
    return max(0, wide + maxchange * random() - maxchange * random())

def addLine(startrow, startcolumn, endrow, endcolumn):
    if startrow != endrow or startcolumn != endcolumn:
        pDisp, qDisp = endrow - startrow, endcolumn - startcolumn
        rows, columns = skimage.draw.line(startrow, startcolumn, endrow, endcolumn)
        channels = current[rows, columns]
        if np.sum(np.var(channels, 0)) / (pDisp * pDisp + qDisp * qDisp) < MAX_VARIANCE:
            linecolour = colourVariation(np.average(channels, 0), COLOUR_VARIATION)
            current[rows, columns] = linecolour
            svgdrawing.add(svgdrawing.line((startcolumn, startrow), (endcolumn, endrow),
                           stroke=
                           f'rgb({",".join([str(int(element)) for element in linecolour[:3]])})',
                           stroke_width=widthVariation(STROKE_WIDTH, WIDTH_VARIATION),
                           stroke_linecap=LINE_CAP))
            return True
    return False


def addBatch(current, numChannels, misses, p1, q1, p2, q2, lengthMinusOne, spanMinusOne, fine=None, jump=MAX_JUMP,
             lowsquare=TOO_SHORT_IN_BATCH):
    pOff, qOff = randint(-jump, jump), randint(-jump, jump)
    if fine is None:
        fine = choice(((0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 0),
                       (1, 0, 0, 0), (0, 0, 0, -1), (0, 0, -1, 0),
                       (0, -1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 0),), )
    tp1 = max(0, min(spanMinusOne, p1 + pOff + fine[0]))
    tq1 = max(0, min(lengthMinusOne, q1 + qOff + fine[1]))
    tp2 = max(0, min(spanMinusOne, p2 + pOff + fine[2]))
    tq2 = max(0, min(lengthMinusOne, q2 + qOff + fine[3]))
    dp = tp2 - tp1
    dq = tq2 - tq1
    if (numChannels < 4 or current[tp1, tq1, 3] > 0) and (dp * dp + dq * dq) > lowsquare and addLine(tp1, tq1, tp2, tq2):
        misses = 0
        p1, q1, p2, q2 = tp1, tq1, tp2, tq2
    else:
        misses += 1
    return misses, p1, q1, p2, q2


def squareDist(ends):
    colD = ends[1][0] - ends[0][0]
    rowD = ends[1][1] - ends[0][1]
    return colD * colD + rowD * rowD

if __name__ == '__main__':
    outbasename, outextension = ORIGINAL_IMAGE.split(".")
    originalImage = Image.open(ORIGINAL_IMAGE)
    originalImage.load()
    current = np.asarray(originalImage, dtype="int32")
    span, length, numChannels = current.shape
    try:
        greyscale = rgb2gray(rgba2rgb(originalImage))
    except ValueError:
        greyscale = rgb2gray(current)
    edges = canny(greyscale, sigma=CANNY_DEVIATION)
    svgdrawing = svgwrite.Drawing(".".join([outbasename, "svg"]), size=(span, length))
    lengthMinusOne, spanMinusOne = length - 1, span - 1
    houghSquare = HOUGH_LINE_LENGTH * HOUGH_LINE_LENGTH
    endpoints = probabilistic_hough_line(edges, threshold=HOUGH_LINE_THRESHOLD,
                                                line_length=HOUGH_LINE_LENGTH,
                                                line_gap=HOUGH_LINE_GAP)
    endpoints.sort(key=squareDist)
    endpoints.reverse()
    for (q1, p1), (q2, p2) in endpoints:
        misses = 0
        abPdiff, abQdiff = abs(p2 - p1), abs(q2 - q1)
        if abPdiff > 0 and abQdiff > 0 and (max(abPdiff, abQdiff) /
                                            min(abPdiff, abQdiff)) < TOO_RECTANGLE:
            if numChannels < 4 or current[p1, q1, 3] > 0:
                while misses < FIRST_MISSES:
                    misses, p1, q1, p2, q2 = addBatch(current, numChannels, misses, p1, q1, p2, q2, lengthMinusOne,
                                                      spanMinusOne, (0, 0, 0, 0),
                                                      FIRST_JUMP, houghSquare)
    svgdrawing.save()
    if MAX_ORDER > 0:
        numberlength = 1 + math.ceil(math.log10(MAX_ORDER))
        for order in range(MAX_ORDER):
            ordersleft = max(MIN_STROKE_LENGTH, 1.0 - order / MAX_ORDER)
            basename = f"{outbasename}{str(order).zfill(numberlength)}"
            filename = ".".join([basename, outextension])
            lengthdifference, spandifference = ordersleft * length, ordersleft * span
            for gen in range(max(MIN_TRIES_PER_ORDER, order * MAX_TRIES_PER_ORDER_PER_ORDER)):
                p1, q1 = randint(0, spanMinusOne), randint(0, lengthMinusOne)
                if numChannels < 4 or current[p1, q1, 3] > 0:
                    p2 = min(spanMinusOne, max(0, int(0.5 + p1 + random() * lengthdifference)))
                    q2 = min(lengthMinusOne, max(0, int(0.5 + q1 + random() * spandifference)))
                    if numChannels < 4 or current[p2, q2, 3] > 0:
                        if addLine(p1, q1, p2, q2):
                            misses = 0
                            while misses < MISSES_PER_BATCH:
                                misses, p1, q1, p2, q2 = addBatch(current, numChannels, misses, p1, q1, p2, q2,
                                                                  lengthMinusOne, spanMinusOne)
            svgdrawing.save()
            print(filename)