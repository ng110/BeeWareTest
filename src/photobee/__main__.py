import sys
from photobee.app import main


## __main__.pyw
testpath = r"C:\Users\neil.griffin\OneDrive\Documents\photonotes"
#imfolder=r"P:\ST\Aykroyd NG1 C61187\Measurement\photos intray"


if __name__ == '__main__':
    if len(sys.argv) > 1:
#         imfolder = sys.argv[1:]
        imfolder = sys.argv[1]
    else:
        imfolder = testpath
    main(imfolder)

