import heat_data
import colors
import csv
import tifffile
import cv2
import numpy as np
from tifffile import imsave


def to_avi(savepath, data, colormap, start, end):
    try:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fps = 8.7
        out = cv2.VideoWriter(savepath, fourcc, fps, (640, 480), True)
        for i in range(start, end):
            frame = data.frame(i, 640, 480)
            out.write(colors.colorize(frame, colormap))
        out.release()
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_tiffs(savepath, data, start, end):
    for i in range(start, end):
        frame = data.frame(i, 640, 480)
        if i == 1:
            dataCollection = data
        else:
            dataCollection = np.dstack((dataCollection, data))
    try:
        imsave(savepath, dataCollection)
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_tiff(savepath, frame):
    try:
        imsave(savepath, frame)
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_csvs(stem, data, start, end):
    for i in range(start, end):
        savepath = stem + '_f' + str(i) + '.csv'
        frame = data.frame(i, 640, 480)
        to_csv(savepath, frame)
    return


def to_csv(savepath, frame):
    try:
        with open(savepath, 'w', newline="") as f:
            writer = csv.writer(f)
            writer.writerows(frame)
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_pngs(stem, data, colormap, start, end):
    for i in range(start, end):
        savepath = stem + 'f_' + str(i) + '.png'
        frame = data.frame(i, 640, 480)
        to_png(savepath, frame, colormap)
    return


def to_png(savepath, frame, colormap):
    try:
        cv2.imwrite(savepath, colors.colorize(frame, colormap))
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return
