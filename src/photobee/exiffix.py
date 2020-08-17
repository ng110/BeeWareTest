import os
import time
import shutil
from datetime import datetime, timedelta
from math import cos, sin, radians
from exif import Exif, readdatetaken, printalldates
from time import gmtime
softwareName = 'photogui.py'


# files = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\IMG_20181229_134258137.jpg",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\IMG_20181229_134253778.jpg"]

# for f in files:
#     path = os.path.dirname(f)
#     name = os.path.basename(f)
#     print(path, name)
#     exif = Exif(f)
#     exif.software = 'exiffix'
#     exif.write(path+'\\out\\'+name)

# raise Exception

# files = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190981.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190969.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190949.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190937.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190935.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190915.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1190884.JPG"]
# exifs = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190982.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190968.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190950.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190936.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190936.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190916.JPG",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1190885.JPG"]
# raws = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190981.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190949.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190969.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190937.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190935.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190915.RW2",
# r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\raw\P1190884.RW2"]

# for f,e,r in zip(files,exifs,raws):
#     path = os.path.dirname(f)
#     name = os.path.basename(f)
#     rawdate = gmtime(os.path.getmtime(r))
#     print(path, name, rawdate)
#     date = time.strftime("%Y:%m:%d %H:%M:%S", rawdate)
#     print(path, name, date)
#     exif = Exif(e)
#     exif.software = 'exiffix'
#     exif.origtime = date
#     exif.orientation = 1
#     exif.write(path+'\\out\\'+name)


files = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1150539.JPG",
r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1150538.JPG",
r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\fix\P1150536.JPG"]
exifs = [r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1150537.JPG",
r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1150537.JPG",
r"C:\Users\ng110\Pictures\JenniYears\2018-12 Kent\P1150537.JPG"]
timeoffsets = [-5, 5, 10]

for f,e,t in zip(files,exifs,timeoffsets):
    path = os.path.dirname(f)
    name = os.path.basename(f)
    exif = Exif(e)
    origtime = exif.origtime
    delta = timedelta(0,t)
    print(path, name, origtime, type(origtime), delta, type(origtime+delta))
    exif.origtime = (origtime+delta).strftime("%Y:%m:%d %H:%M:%S")
    origtime2 = exif.origtime
    print(origtime2)
    exif.software = 'exiffix'
    exif.orientation = 1
    exif.write(path+'\\out\\'+name)

