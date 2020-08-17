import piexif
import exifread
from PIL import ExifTags, Image
from datetime import datetime, timedelta
from math import log10, ceil
import os


def _getitem(dictionary, key1, key2):
    try:
        val = dictionary[key1][key2]
        if type(val) is bytes:
            return val.decode()
        else:
            return val
    except KeyError:
        return None


class Exif():
    def __init__(self, path):
        try: 
            self.dict = piexif.load(path)
            if piexif.ExifIFD.SubjectLocation in self.dict['Exif']:
                print('SubjectLocation tag present in {}.'.format(path))
            if piexif.ExifIFD.SubjectArea in self.dict['Exif']:
                print('SubjectLocation tag present in {}.'.format(path))
        except:
            print("Unable to load exif data.")
            self.dict = {}
    @property
    def binary(self):
        return piexif.dump(self.dict)
    @binary.setter
    def binary(self,data):
        pass

    def write(self, outpath):
        piexif.insert(self.binary, outpath)

    @property
    def height(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.PixelYDimension)
    @height.setter
    def height(self, value):
        self.dict['Exif'][piexif.ExifIFD.PixelYDimension] = value

    @property
    def width(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.PixelXDimension)
    @width.setter
    def width(self, value):
        self.dict['Exif'][piexif.ExifIFD.PixelXDimension] = value

    @property
    def focallength(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.FocalLength)

    @property
    def focallength35(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.FocalLengthIn35mmFilm)

    @property
    def lens(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.LensModel)

    @property
    def camera(self):
        return _getitem(self.dict, '0th', piexif.ImageIFD.Model)

    @property
    def origtime(self):
        origtime = _getitem(self.dict, 'Exif', piexif.ExifIFD.DateTimeOriginal)
        try:
            origtimeval = datetime.strptime(origtime, "%Y:%m:%d %H:%M:%S")
        except TypeError:
            origtimeval = None
        return origtimeval
    @origtime.setter
    def origtime(self, value):
        self.dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = value

    @property
    def digtime(self):
        digtime = _getitem(self.dict, 'Exif', piexif.ExifIFD.DateTimeDigitized)
        try:
            digtimeval = datetime.strptime(digtime, "%Y:%m:%d %H:%M:%S")
        except TypeError:
            digtimeval = None
        return digtimeval

    @property
    def time(self):
        dt = _getitem(self.dict, '0th', piexif.ImageIFD.DateTime)
        subsec = _getitem(self.dict, 'Exif', piexif.ExifIFD.SubSecTime)
        if self.origtime:
            return self.origtime
        elif self.digtime:
            return self.digtime
        elif dt:
            if subsec:
                ss = int(subsec)
                ss = ss/10**(ceil(log10(ss)))
                us = round(ss*1000000)
                self.datetime = datetime.strptime(dt, "%Y:%m:%d %H:%M:%S") + timedelta(0, 0, us)
            else:
                self.datetime = datetime.strptime(dt, "%Y:%m:%d %H:%M:%S")
            return self.datetime
        else:
            return None
    @time.setter
    def time(self, value):
        self.dict['0th'][piexif.ImageIFD.DateTime] = value

    @property
    def orientation(self):
        orient = _getitem(self.dict, '0th', piexif.ImageIFD.Orientation)
        if not orient:
            return 1
        else:
            return orient
    @orientation.setter
    def orientation(self, value):
        self.dict['0th'][piexif.ImageIFD.Orientation] = value

    @property
    def orientation1st(self):
        orient = _getitem(self.dict, '1st', piexif.ImageIFD.Orientation)
        if not orient:
            return 1
        else:
            return orient
    @orientation1st.setter
    def orientation1st(self, value):
        self.dict['1st'][piexif.ImageIFD.Orientation] = value

    @property
    def software(self):
        return _getitem(self.dict, '0th', piexif.ImageIFD.Software)
    @software.setter
    def software(self, value):
        self.dict['0th'][piexif.ImageIFD.Software] = value.encode()

    @property
    def YCbCr(self):
        return _getitem(self.dict, '0th', piexif.ImageIFD.YCbCrPositioning)
    @YCbCr.setter
    def YCbCr(self, value):
        self.dict['0th'][piexif.ImageIFD.YCbCrPositioning] = value

    @property
    def compressedbpp(self):
        return _getitem(self.dict, 'Exif', piexif.ExifIFD.CompressedBitsPerPixel)
    @compressedbpp.setter
    def compressedbpp(self, value):
        self.dict['Exif'][piexif.ExifIFD.CompressedBitsPerPixel] = value

    def setcustomrendered(self):
        self.dict['Exif'][piexif.ExifIFD.CustomRendered] = 1
        
    # check this works
    def removethumbnail(self):
        self.dict['thumbnail'] = None
        


# Exif:
# CompressedBitsPerPixel
# SubsecTime
### Thumb:
# YCbCrPositioning
# XResolution
# YResolution
# ResolutionUnit
# DateTime
# dict['thumbnail'] is value or None
# ex.dict["1st"][piexif.ImageIFD.JPEGInterchangeFormat] and ex.dict["1st"][piexif.ImageIFD.JPEGInterchangeFormatLength] define location of bytes in file



# def get_exif_data(image):
#     """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
#     exif_data = {}
#     info = image._getexif()
#     if info:
#         for tag, value in info.items():
#             decoded = ExifTags.TAGS.get(tag, tag)
# #             if tag == 274:
# #                 print(decoded, value, flush=True)
#             if decoded == "GPSInfo":
#                 gps_data = {}
#                 for t in value:
#                     sub_decoded = ExifTags.GPSTAGS.get(t, t)
#                     gps_data[sub_decoded] = value[t]

#                 exif_data[decoded] = gps_data
#             else:
#                 exif_data[decoded] = value

#     return exif_data


def readdatetaken(path):
    file = open(path, 'rb')
    try:
        tags = exifread.process_file(file, stop_tag='DateTimeOriginal', strict=True, details=False)
        if 'EXIF DateTimeOriginal' in tags.keys():
            datetext = tags['EXIF DateTimeOriginal'].values
        elif 'DateTimeOriginal' in tags.keys():
            datetext = tags['DateTimeOriginal'].values
        elif 'DateTime' in tags.keys():
            datetext = tags['DateTime'].values
        elif 'Image DateTime' in tags.keys():
            datetext = tags['Image DateTime'].values
        else:
            print('{}: No date information.  Tags... {}'.format(os.path.basename(path),
                                                                tags), flush=True)
            datetext = '1900:01:01 00:00:00'
    except TypeError:
        print('{}: No date information.', flush=True)
        datetext = '1900:01:01 00:00:00'
    return(datetime.strptime(datetext, "%Y:%m:%d %H:%M:%S"))

def printalldates(path):
    file = open(path, 'rb')
    tags = exifread.process_file(file, stop_tag='DateTimeOriginal', strict=True, details=False)
    print(path)
    if 'EXIF DateTimeOriginal' in tags.keys():
        print('  1. EXIF DateTimeOriginal "{}"'.format(tags['EXIF DateTimeOriginal'].values))
    if 'DateTimeOriginal' in tags.keys():
        print('  2. DateTimeOriginal "{}"'.format(tags['DateTimeOriginal'].values))
    if 'DateTime' in tags.keys():
        print('  3. DateTime "{}"'.format(tags['DateTime'].values))
    if 'Image DateTime' in tags.keys():
        print('  4. Image DateTime "{}"'.format(tags['Image DateTime'].values))
    exifdict = piexif.load(path)
    print("  5. piexif.ExifIFD.DateTimeOriginal", _getitem(exifdict['Exif'], piexif.ExifIFD.DateTimeOriginal))
    print("  6. piexif.ExifIFD.DateTimeDigitized", _getitem(exifdict['Exif'], piexif.ExifIFD.DateTimeDigitized))
    print("  7. piexif.ImageIFD.DateTime", _getitem(exifdict['0th'], piexif.ImageIFD.DateTime))
    print("  8. piexif.ExifIFD.SubSecTime", _getitem(exifdict['Exif'], piexif.ExifIFD.SubSecTime))


# def readdatetaken2(path): (slower)
#     exif = Exif(path)
#     return exif.time

# def readdatetaken3(path): (slower)
#     exifdict = piexif.load(path)
#     dt = _getitem(exifdict['0th'], piexif.ImageIFD.DateTime)
#     subsec = _getitem(exifdict['Exif'], piexif.ExifIFD.SubSecTime)
#     origtime = _getitem(exifdict['Exif'], piexif.ExifIFD.DateTimeOriginal)
#     digtime = _getitem(exifdict['Exif'], piexif.ExifIFD.DateTimeDigitized)
#     if dt:
#         if subsec:
#             ss = int(subsec)
#             ss = ss/10**(ceil(log10(ss)))
#             us = round(ss*1000000)
#             return datetime.strptime(dt, "%Y:%m:%d %H:%M:%S") + timedelta(0, 0, us)
#         else:
#             return datetime.strptime(dt, "%Y:%m:%d %H:%M:%S")
#     elif origtime:
#         return origtime
#     elif digtime:
#         return digtime
#     else:
#         return None

def exifinsert(targetimage, exifsource, software='exifinsert', orientation=1):
    image = Image.open(targetimage)
    exif = Exif(exifsource)
    exif.width = image.size[0]
    exif.height = image.size[1]
    exif.orientation = orientation
    exif.removethumbnail()
    exif.software = software
    exif.write(targetimage)


