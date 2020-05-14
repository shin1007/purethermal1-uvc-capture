import h5py
import cv2


class heat_data(object):
    def __init__(self, fullpath):
        self.__fullpath = fullpath
        self.__raw_data = h5py.File(fullpath, 'r')
        self.__last_frame = len(self.__raw_data)

    @property
    def fullpath(self):
        return self.__fullpath

    @property
    def raw_data(self):
        return self.__raw_data

    @property
    def last_frame(self):
        return self.__last_frame

    def frame(self, num, width, height):
        raw_frame = self.raw_data[('image' + str(num))][:]
        if(width == 0 or height == 0):
            return raw_frame
        return cv2.resize(raw_frame, (width, height))
