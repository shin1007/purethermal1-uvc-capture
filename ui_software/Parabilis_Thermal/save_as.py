import heat_data
import colors
import csv
import tifffile
import cv2
import numpy as np
from tifffile import imsave
from PIL import Image, TiffImagePlugin


def to_csvs(stem, data, start, end):
    for i in range(start, end+1):
        savepath = stem + '_f' + str(i) + '.csv'
        frame = data.frame(i, 640, 480)
        to_csv(savepath, frame)
    return 'Finished saving csv files'


def to_tiffs(savepath, data, colormap, start, end):
    try:
        images = []
        for i in range(1, end+1):
            frame = data.frame(i, 640, 480)
            bgr = colors.colorize(frame, colormap)
            # BGR2RGB conversion because of "Image.fromarray"
            rgb_image = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            images.append(Image.fromarray(rgb_image))

        images[0].save(savepath, compression='tiff_deflate',
                       save_all=True, append_images=images[1:])
        return 'Saved ' + savepath
    except:
        return 'Error while saving ' + savepath


def to_pngs(stem, data, colormap, start, end):
    for i in range(start, end+1):
        savepath = stem + 'f_' + str(i) + '.png'
        frame = data.frame(i, 640, 480)
        to_png(savepath, frame, colormap)
    return 'Finished saving png files'


def to_avi(savepath, data, colormap, start, end):
    try:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fps = 8.7
        out = cv2.VideoWriter(savepath, fourcc, fps, (640, 480), True)
        print(data)
        for i in range(start, end+1):
            frame = data.frame(i, 640, 480)
            bgr = colors.colorize(frame, colormap)
            out.write(bgr)
        out.release()
        return 'Saved ' + savepath
    except:
        return 'Error while saving ' + savepath


def to_csv(savepath, frame):
    try:
        with open(savepath, 'w', newline="") as f:
            writer = csv.writer(f)
            writer.writerows(frame)
        return'Saved ' + savepath
    except:
        return'Error while saving ' + savepath


def to_tiff(savepath, frame, colormap):
    try:
        bgr = colors.colorize(frame, colormap)
        if(cv2.imwrite(savepath, bgr)):
            print('Saved ' + savepath)
        else:
            return 'Error while saving ' + savepath
    except:
        return 'Error while saving ' + savepath


def to_png(savepath, frame, colormap):
    try:
        bgr = colors.colorize(frame, colormap)
        if (cv2.imwrite(savepath, bgr)):
            return 'Saved ' + savepath
        else:
            return 'Error while saving ' + savepath
    except:
        return'Error while saving ' + savepath
