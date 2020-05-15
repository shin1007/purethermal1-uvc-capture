import heat_data
import colors
import csv
import tifffile
import cv2
import numpy as np
from tifffile import imsave
from PIL import Image, TiffImagePlugin


def to_csvs(stem, data, start, end):
    for i in range(start, end):
        savepath = stem + '_f' + str(i) + '.csv'
        frame = data.frame(i, 640, 480)
        to_csv(savepath, frame)
    print('Finished saving csv files')
    return


def to_tiffs(savepath, data, colormap, start, end):
    try:
        images = []
        for i in range(1, data.last_frame):
            frame = data.frame(i, 640, 480)
            bgr = colors.colorize(frame, colormap)
            # BGR2RGB conversion because of "Image.fromarray"
            rgb_image = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            images.append(Image.fromarray(rgb_image))

        images[0].save(savepath, compression='tiff_deflate',
                       save_all=True, append_images=images[1:])
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_pngs(stem, data, colormap, start, end):
    for i in range(start, end):
        savepath = stem + 'f_' + str(i) + '.png'
        frame = data.frame(i, 640, 480)
        to_png(savepath, frame, colormap)
    print('Finished saving csv files')
    return


def to_avi(savepath, data, colormap, start, end):
    try:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fps = 8.7
        out = cv2.VideoWriter(savepath, fourcc, fps, (640, 480), True)
        print(data)
        for i in range(start, end):
            frame = data.frame(i, 640, 480)
            bgr = colors.colorize(frame, colormap)
            out.write(bgr)
        out.release()
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
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


def to_tiff(savepath, frame, colormap):
    try:
        bgr = colors.colorize(frame, colormap)
        cv2.imwrite(savepath, bgr)
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return


def to_png(savepath, frame, colormap):
    try:
        bgr = colors.colorize(frame, colormap)
        cv2.imwrite(savepath, bgr)
        print('Saved ' + savepath)
    except:
        print('Error while saving ' + savepath)
    return
