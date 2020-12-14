# The hsv_merge code is subject to the following
# ******************************************************************************
#  $Id$
#
#  Project:  GDAL Python Interface
#  Purpose:  Script to merge greyscale as intensity into an RGB(A) image, for
#            instance to apply hillshading to a dem colour relief.
#  Author:   Frank Warmerdam, warmerdam@pobox.com
#            Trent Hare (USGS)
#
# ******************************************************************************
#  Copyright (c) 2009, Frank Warmerdam
#  Copyright (c) 2010, Even Rouault <even dot rouault at mines-paris dot org>
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
# ******************************************************************************

import numpy
import DemToTopoUtills
from osgeo import gdal
from osgeo.gdalconst import *


def hsv_merge(folder, fn_dem, scr_slope_hill_shade, scr_color_ref):
    hill_dataset = gdal.Open(scr_slope_hill_shade, GA_ReadOnly)
    color_data_set = gdal.Open(scr_color_ref, GA_ReadOnly)

    dst_color_filename = folder + DemToTopoUtills.add_file_name_marker_tif(fn_dem, '_Topo')
    datatype = GDT_Byte
    out_format = 'GTiff'

    # define output format, name, size, type and set projection
    out_driver = gdal.GetDriverByName(out_format)
    out_dataset = out_driver.Create(dst_color_filename, color_data_set.RasterXSize,
                                    color_data_set.RasterYSize, color_data_set.RasterCount, datatype)
    out_dataset.SetProjection(hill_dataset.GetProjection())
    out_dataset.SetGeoTransform(hill_dataset.GetGeoTransform())

    # assign RGB and hillshade bands
    r_band = color_data_set.GetRasterBand(1)
    g_band = color_data_set.GetRasterBand(2)
    b_band = color_data_set.GetRasterBand(3)
    if color_data_set.RasterCount == 4:
        a_band = color_data_set.GetRasterBand(4)
    else:
        a_band = None

    hill_band = hill_dataset.GetRasterBand(1)
    hill_band_no_data_value = hill_band.GetNoDataValue()

    # loop over lines to apply hillshade
    for i in range(hill_band.YSize):
        # load RGB and Hillshade arrays
        r_scan_line = r_band.ReadAsArray(0, i, hill_band.XSize, 1, hill_band.XSize, 1)
        g_scan_line = g_band.ReadAsArray(0, i, hill_band.XSize, 1, hill_band.XSize, 1)
        b_scan_line = b_band.ReadAsArray(0, i, hill_band.XSize, 1, hill_band.XSize, 1)
        hill_scan_line = hill_band.ReadAsArray(0, i, hill_band.XSize, 1, hill_band.XSize, 1)

        # convert to HSV
        hsv = rgb_to_hsv(r_scan_line, g_scan_line, b_scan_line)

        # if there's nodata on the hillband, use the v value from the color
        # dataset instead of the hillshade value.
        if hill_band_no_data_value is not None:
            equal_to_nodata = numpy.equal(hill_scan_line, hill_band_no_data_value)
            v = numpy.choose(equal_to_nodata, (hill_scan_line, hsv[2]))
        else:
            v = hill_scan_line

        # replace v with hillshade
        hsv_adjusted = numpy.asarray([hsv[0], hsv[1], v])

        # convert back to RGB
        dst_color = hsv_to_rgb(hsv_adjusted)

        # write out new RGB bands to output one band at a time
        outband = out_dataset.GetRasterBand(1)
        outband.WriteArray(dst_color[0], 0, i)
        outband = out_dataset.GetRasterBand(2)
        outband.WriteArray(dst_color[1], 0, i)
        outband = out_dataset.GetRasterBand(3)
        outband.WriteArray(dst_color[2], 0, i)
        if a_band is not None:
            aScanline = a_band.ReadAsArray(0, i, hill_band.XSize, 1, hill_band.XSize, 1)
            outband = out_dataset.GetRasterBand(4)
            outband.WriteArray(aScanline, 0, i)

    hill_dataset = None
    out_dataset = None
    r_band = None
    g_band = None
    b_band = None
    outband = None

    return dst_color_filename


# =============================================================================
# rgb_to_hsv()
#
# rgb comes in as [r,g,b] with values in the range [0,255].  The returned
# hsv values will be with hue and saturation in the range [0,1] and value
# in the range [0,255]
#
def rgb_to_hsv(r, g, b):
    maxc = numpy.maximum(r, numpy.maximum(g, b))
    minc = numpy.minimum(r, numpy.minimum(g, b))

    v = maxc

    minc_eq_maxc = numpy.equal(minc, maxc)

    # compute the difference, but reset zeros to ones to avoid divide by zeros later.
    ones = numpy.ones((r.shape[0], r.shape[1]))
    maxc_minus_minc = numpy.choose(minc_eq_maxc, (maxc - minc, ones))

    s = (maxc - minc) / numpy.maximum(ones, maxc)
    rc = (maxc - r) / maxc_minus_minc
    gc = (maxc - g) / maxc_minus_minc
    bc = (maxc - b) / maxc_minus_minc

    maxc_is_r = numpy.equal(maxc, r)
    maxc_is_g = numpy.equal(maxc, g)
    maxc_is_b = numpy.equal(maxc, b)

    h = numpy.zeros((r.shape[0], r.shape[1]))
    h = numpy.choose(maxc_is_b, (h, 4.0 + gc - rc))
    h = numpy.choose(maxc_is_g, (h, 2.0 + rc - bc))
    h = numpy.choose(maxc_is_r, (h, bc - gc))

    h = numpy.mod(h / 6.0, 1.0)

    hsv = numpy.asarray([h, s, v])

    return hsv


# =============================================================================
# hsv_to_rgb()
#
# hsv comes in as [h,s,v] with hue and saturation in the range [0,1],
# but value in the range [0,255].

def hsv_to_rgb(hsv):
    h = hsv[0]
    s = hsv[1]
    v = hsv[2]

    # if s == 0.0: return v, v, v
    i = (h * 6.0).astype(int)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    r = i.choose(v, q, p, p, t, v)
    g = i.choose(t, v, v, q, p, p)
    b = i.choose(p, p, t, v, v, q)

    rgb = numpy.asarray([r, g, b]).astype(numpy.uint8)

    return rgb
