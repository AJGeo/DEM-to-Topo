# Author: AJ Bresler
# Copyright (c) 2020, AJ Bresler

import sys
import os
import numpy
import DemToTopoConsts
import DemToTopo_HSV_Merge
import DemToTopoUtills

from pathlib import Path
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import *


def main():
    # Get command line arguments.
    if len(sys.argv) != 4:
        Usage()
    if not sys.argv[1] or not sys.argv[2] or not sys.argv[3]:
        Usage()

    folder = sys.argv[1]
    color_altitude_file = sys.argv[2]
    file_extension = sys.argv[3]
    # Load the data from cvs file
    dem_file_list = get_dem_file_list(folder, file_extension)

    # Process each file
    for file_name in dem_file_list:
        print('Processing: ' + file_name, end="")
        out_cr_name = create_color_relief(folder, file_name, color_altitude_file)
        out_hill_shade_name = create_hill_shade(folder, file_name)
        out_slope_name = create_slope(folder, file_name)
        out_sl_hs_name = create_slope_hill_shade(folder, file_name, out_slope_name, out_hill_shade_name)
        out_topo_name = DemToTopo_HSV_Merge.hsv_merge(folder, file_name, out_sl_hs_name, out_cr_name)
        out_slope_water = create_slope_water(folder, file_name, out_slope_name)
        out_vector_water = create_slope_poly(folder, file_name, out_slope_water)
        rasterize_water_to_topo(folder, out_topo_name, out_vector_water)

        os.remove(out_cr_name)
        os.remove(out_hill_shade_name)
        os.remove(out_slope_name)
        os.remove(out_sl_hs_name)
        os.remove(out_slope_water)

        print('')

    print('Completed', end='\n')


def get_dem_file_list(folder, file_extension):
    dem_file_list = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file():
                if Path(entry.name).suffix == '.' + file_extension:
                    dem_file_list.append(entry.name)

    return dem_file_list


def create_color_relief(folder, scr_filename, color_altitude_file):
    out_filename = folder + DemToTopoUtills.add_file_name_marker_tif(scr_filename, DemToTopoConsts.COLOR_RELIEF_EXT)
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'color-relief', format='GTiff',
                       colorFilename=color_altitude_file)

    DemToTopoUtills.print_dot()
    return out_filename


def create_hill_shade(folder, scr_filename):
    out_filename = folder + DemToTopoUtills.add_file_name_marker_tif(scr_filename, DemToTopoConsts.HILL_SHADE_EXT)
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'hillshade', format='GTiff',
                       zFactor=5, scale=111120, azimuth=90, computeEdges=True)

    DemToTopoUtills.print_dot()
    return out_filename


def create_slope(folder, scr_filename):
    out_filename = folder + DemToTopoUtills.add_file_name_marker_tif(scr_filename, DemToTopoConsts.SLOPE_EXT)
    gdal.DEMProcessing(out_filename, folder + scr_filename, 'slope', format='GTiff',
                       scale=111120, azimuth=90, computeEdges=True)

    DemToTopoUtills.print_dot()
    return out_filename


def create_slope_hill_shade(folder, fn_dem, fn_sl, fn_hs):
    fn_sl_hs = folder + DemToTopoUtills.add_file_name_marker_tif(fn_dem, DemToTopoConsts.SLOPE_HILL_SHADE_EXT)

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

    DemToTopoUtills.print_dot()
    return fn_sl_hs


def create_slope_water(folder, fn_dem, fn_sl):
    fn_sl_water = folder + DemToTopoUtills.add_file_name_marker_tif(fn_dem, DemToTopoConsts.SLOPE_WATER_EXT)

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

    DemToTopoUtills.print_dot()
    return fn_sl_water


def create_slope_poly(folder, fn_dem, fn_sl_water):
    fn_sl_poly = folder + DemToTopoUtills.add_file_name_marker_shp(fn_dem, DemToTopoConsts.SLOPE_POLY_EXT)
    # print(fn_sl_poly)
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
            out_layer_file.CreateFeature(feat)

    out_datasource_file = None
    out_datasource_mem = None
    dn_sl = None

    fn_sl_poly_prj = folder + DemToTopoUtills.add_file_name_marker_prj(fn_dem, DemToTopoConsts.SLOPE_POLY_EXT)
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)

    spatial_ref.MorphToESRI()
    file = open(fn_sl_poly_prj, 'w')
    file.write(spatial_ref.ExportToWkt())
    file.close()
    file = None

    DemToTopoUtills.print_dot()
    return fn_sl_poly


def rasterize_water_to_topo(folder, out_topo_name, out_vector_water):
    ds_topo = gdal.Open(out_topo_name, GF_Write)
    ds_vector_water = ogr.Open(out_vector_water)
    layer_vector_water = ds_vector_water.GetLayer()

    gdal.RasterizeLayer(ds_topo, [1, 2, 3], layer_vector_water, burn_values=[DemToTopoConsts.RED_VAL,
                                                                             DemToTopoConsts.GREEN_VAL,
                                                                             DemToTopoConsts.BLUE_VAL])
    DemToTopoUtills.print_dot()


def Usage():
    print("""Usage: DemToTopo.py {DEM data folder} {Color Altitude File} {DEM file extension}

    where DEM data folder is the dataset path,
          Color Altitude Value Map File is the file path of the file
          DEM file extension (e.g. bil)
          intensity for the color dataset.
    """)
    sys.exit(1)

main()
# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
