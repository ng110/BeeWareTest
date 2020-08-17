"""
based on fisheye.py from https://github.com/scikit-image/skimage-demos
"""

from skimage import transform
import numpy as np
from math import sqrt
from PIL import Image


def fishwarp(image, level=1):
#    print('fw', level, type(image), flush=True)
    def fisheye(xy):
        centre = np.mean(xy, axis=0)
        xc, yc = (xy - centre).T

        # Polar coordinates
        r = np.sqrt(xc**2 + yc**2)
        theta = np.arctan2(yc, xc)

#        r = fl*np.tan(level*0.1*r/centre[0])
        frac = level/10
        # if level > 0:
        #     phi = r/fl
        #     r = fl*(frac*np.tan(phi) + (1-frac)*phi)
        # elif level < 0:
        #     phi = np.arctan2(fl,r)
        #     r = fl*((1-frac)*np.tan(phi) + frac*phi)
        c = centre[0]
        if level > 0:
#            fl = 1/((3/(10*c*c))*level+0)
#            fl = centre[0] * 20 * 1.5**-level
            fl = sqrt(20*c*c/(3*level))
            r = fl*np.tan(r/fl)
        elif level < 0:
#            fl = 1/((-3/(10*c*c))*level+0)
#            fl = centre[0] * 20 * 1.5**level
            fl = sqrt(-20*c*c/(3*level))
            r = fl*np.arctan(r/fl)
#        print(level, centre, fl, flush=True)
#        r = fl*np.tan((pi/4)*r/fl)
#        r = 0.8 * np.exp(r**(level/2.1) / 1.8)

        return np.column_stack((r*np.cos(theta), r*np.sin(theta))) + centre
    return(transform.warp(image, fisheye, map_args={}, order=3, preserve_range=False))


def fishwarppil(image, level=1):
    print('zz', image.getextrema(), flush=True)
    nim = np.array(image)
    print('fwp',level, np.min(nim[:,:,0]), np.max(nim[:,:,0]), 
                       np.min(nim[:,:,1]), np.max(nim[:,:,1]), 
                       np.min(nim[:,:,2]), np.max(nim[:,:,2]), flush=True)
    nim = fishwarp(nim, level)
    print('xx', Image.fromarray(np.uint8(nim*255)).getextrema(), flush=True)
    return(Image.fromarray(np.uint8(nim*255)))
