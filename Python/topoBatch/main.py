import sys
import os
import numpy

from pathlib import Path
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import *


def main():
    # There must be 2 Arguments
    folder = ""
    dem_file_list = []
    if len(sys.argv[1:]) == 1:
        # Load the data from cvs file
        folder = sys.argv[1]
        dem_file_list = get_dem_file_list(folder)
        print(folder)
        print(dem_file_list)

    for file_name in dem_file_list:
        print('Processing: ' + file_name, end='\n')
        out_cr_name = create_color_relief(folder, file_name)
        out_hill_shade_name = create_hill_shade(folder, file_name)
        out_slope_name = create_slope(folder, file_name)
        out_sl_hs_name = create_slope_hill_shade(folder, file_name, out_slope_name, out_hill_shade_name)
        out_topo_name = hsv_merge(folder, file_name, out_sl_hs_name, out_cr_name)
        out_slope_water = create_slope_water(folder, file_name, out_slope_name)
        out_vector_water = create_slope_poly(folder, file_name, out_slope_water)
        rasterize_water_to_topo(folder, out_topo_name, out_vector_water)

        os.remove(out_cr_name)
        os.remove(out_hill_shade_name)
        os.remove(out_slope_name)
        os.remove(out_sl_hs_name)
        os.remove(out_slope_water)


def get_dem_file_list(folder):
    dem_file_list = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file():
                if Path(entry.name).suffix == '.bil':
                    dem_file_list.append(entry.name)

    return dem_file_list


def create_color_relief(folder, scr_filename):
    out_filename = folder + add_file_name_marker_tif(scr_filename, '_CR')
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'color-relief', format='GTiff',
                       colorFilename= 'D:/RepoGitDir/AJGeo/DEM-to-Topo/Data/ColorRelief02.txt')
    return out_filename


def create_hill_shade(folder, scr_filename):
    out_filename = folder + add_file_name_marker_tif(scr_filename, '_HS')
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'hillshade', format='GTiff',
                       zFactor=5, scale=111120, azimuth=90, computeEdges=True)
    return out_filename


def create_slope(folder, scr_filename):
    out_filename = folder + add_file_name_marker_tif(scr_filename, '_SL')
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'slope', format='GTiff',
                       scale=111120, azimuth=90, computeEdges=True)
    return out_filename


def create_slope_hill_shade(folder, fn_dem, fn_sl, fn_hs):
    fn_sl_hs = folder + add_file_name_marker_tif(fn_dem, '_SL_HS')

    ds_sl = gdal.Open(fn_sl)
    ds_hs = gdal.Open(fn_hs)

    driver_tiff = gdal.GetDriverByName('GTiff')
    ds_sl_hs = driver_tiff.CreateCopy(fn_sl_hs, ds_sl, strict=0)

    band_sl = ds_sl.GetRasterBand(1).ReadAsArray()
    band_hs = ds_hs.GetRasterBand(1).ReadAsArray()

    band_sl_hs = ((((band_sl / 90) * 255) * 0.7) + (band_hs * 0.3)) + 70

    ds_sl_hs.GetRasterBand(1).WriteArray(band_sl_hs)

    ds_sl = None
    ds_hs = None
    ds_sl_hs = None
    band_sl = None
    band_hs = None
    band_sl_hs = None

    return fn_sl_hs


def create_slope_water(folder, fn_dem, fn_sl):
    fn_sl_water = folder + add_file_name_marker_tif(fn_dem, '_SL_Water')

    ds_sl = gdal.Open(fn_sl)

    driver_tiff = gdal.GetDriverByName('GTiff')
    ds_sl_water = driver_tiff.CreateCopy(fn_sl_water, ds_sl, strict=0)
    ds_sl_water.GetRasterBand(1).SetNoDataValue(0)

    band_sl = ds_sl.GetRasterBand(1).ReadAsArray()

    band_sl_water = numpy.where(band_sl != 0, 2, band_sl)
    band_sl_water = numpy.where(band_sl_water == 0, 1, band_sl_water)
    band_sl_water = numpy.where(band_sl_water == 2, 0, band_sl_water)

    ds_sl_water.GetRasterBand(1).WriteArray(band_sl_water)

    ds_sl = None
    ds_sl_water = None
    band_sl = None
    band_sl_water = None

    return fn_sl_water


def create_slope_poly(folder, fn_dem, fn_sl_water):
    fn_sl_poly = folder + add_file_name_marker_shp(fn_dem, '_SL_poly')
    print(fn_sl_poly)
    dn_sl = gdal.Open(fn_sl_water)
    band_input = dn_sl.GetRasterBand(1)

    # create the spatial reference, WGS84
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(4326)

    driver_file = ogr.GetDriverByName("ESRI Shapefile")
    driver_mem = ogr.GetDriverByName('Memory')

    if os.path.exists(fn_sl_poly):
        driver_file.DeleteDataSource(fn_sl_poly)

    out_datasource_file = driver_file.CreateDataSource(fn_sl_poly)
    out_layer_file = out_datasource_file.CreateLayer("polygonized", source_srs, geom_type=ogr.wkbPolygon)

    out_datasource_mem = driver_mem.CreateDataSource('out')
    out_layer_mem = out_datasource_mem.CreateLayer("polygonized1", source_srs)

    gdal.Polygonize(band_input, band_input, out_layer_mem, -1, [], callback=None)

    for feat in out_layer_mem:
        # For each feature, get the geometry
        geom = feat.GetGeometryRef()
        area = geom.GetArea()
        if area > 0.0000009:
            print('Area: ' + str(area))
            out_layer_file.CreateFeature(feat)

    out_datasource_file = None
    out_datasource_mem = None
    dn_sl = None

    fn_sl_poly_prj = folder + add_file_name_marker_prj(fn_dem, '_SL_poly')
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)

    spatial_ref.MorphToESRI()
    file = open(fn_sl_poly_prj, 'w')
    file.write(spatial_ref.ExportToWkt())
    file.close()
    file = None

    return fn_sl_poly


def rasterize_water_to_topo(folder, out_topo_name, out_vector_water):
    ds_topo = gdal.Open(out_topo_name, GF_Write)
    ds_vector_water = ogr.Open(out_vector_water)
    layer_vector_water = ds_vector_water.GetLayer()

    gdal.RasterizeLayer(ds_topo, [1, 2, 3], layer_vector_water, burn_values=[35, 170, 181])


def hsv_merge(folder, fn_dem, scr_slope_hill_shade, scr_color_ref):
    hill_dataset = gdal.Open(scr_slope_hill_shade, GA_ReadOnly)
    color_data_set = gdal.Open(scr_color_ref, GA_ReadOnly)
    dst_color_filename = folder + add_file_name_marker_tif(fn_dem, '_Topo')
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


def add_file_name_marker_tif(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.tif'


def add_file_name_marker_shp(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.shp'


def add_file_name_marker_prj(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.prj'

# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


main()
# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
