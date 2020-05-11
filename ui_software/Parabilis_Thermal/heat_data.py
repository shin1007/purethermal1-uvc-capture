import h5py
import cv2


class heat_data():
    def __init__(self, fullpath):
        __fullpath = fullpath
        __raw_data = h5py.File(fullpath, 'r')
        __last_frame = len(self.raw_data)

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
        print('aaa')
        print(fullpath)
        print(raw_data)
        print(last_frame)
        print(num)
        raw_frame = raw_data[('image' + str(num))][:]
        print('bbb')
        return cv2.resize(raw_frame, (640, 480))
