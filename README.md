# Digital Elevation Model 2 Topographic

## Aim of project

## Aim software
> A batch process to produce:
> Digital Topographic image(s) with water areas with a area larger than approximate 3 hectares.
> Vector ESRI shape file of the water areas.

## Usage
> ### Parameters
> 1. The folder location containing the DEM data.
> 2. The path to the Color Altitude Value Map File.
> 3. The file extension of the DEM data in the location folder

### Invalid Parameters
> Invalid Parameters display an usage message to the user and exits the application.

## Dependencies
- import sys
- import os
- import numpy
- import DemToTopoConsts
- import DemToTopo_HSV_Merge
- import DemToTopoUtills
- from pathlib import Path
- from osgeo import gdal, ogr, osr
- from osgeo.gdalconst import *

## Input Data Detail
### Digital Elevation Model
> Geo referenced altitude data

> ### Color Altitude Value Map File
> Comma delimited text file. Each row is a altitude value marker to a RGB value.

> | Altitude | Red | Green | Blue |
> | --- | --- | --- | --- |
> | -32767 | 255 | 255 | 255 |
> | 0 | 35 | 170 | 181 |
> | 1 | 89 | 134 | 74 |
> | 600 | 245 | 245 | 176 |
> | 1000 | 218 | 177 | 118 |
> | 2500 | 184 | 156 | 138 |
> | 5800 | 250 | 250 | 250 |

> ### DEM file extension
> The DEM file extension identifying the DEM files to process

## Output Data Detail
1. The product of every DEM file processed is artificially coloured. The texture of the landscape a combination of a Hill-shade and slope process. Flat arias of approximate minimum 3000 square meters are identified and imprinted in to the topographic image.
2. A geographic vector file in the ESRI Shape file format is produced for every DEM file representing the identified water areas in this area.

## Process Breakdown
> ### Color Relief
> A Color Relief is created from the DEM data and the Color Altitude Value Map File. This will become the color source data for the topographic product.
The gdal Color-relief abstraction is used to generate the Color relief data.

> ### Hill-shade
> Hill-shade data is created from the DEM data. This will be used in part in the creation of the topographic texture.
> The gdal hillshade abstraction is used to generate the Hill-shade data.

> ### Slope
> Slope data is created from the DEM data. This will be used in part in the creation of the topographic texture.
> The gdal slope abstraction is used to generate the Slope data.

> ### Combine Hill-shade and Slope
> Combining Hill-shade and Slope data to result in the final texture data source for the topographic product.
> The slope data has a value range of 0-90
> The hill-shade data has a value range of 0-255
First the data ranges between the data sets are normalised. There after a standard 70% slope to 30% Hill-shade weight is applied. The final step corrects the value to normal distribution curve.

> ### Topographic Image
> Create the topographic image from the color relief and texture data. The code is a adoption of hsv_merge Project: GDAL Python Interface by Frank Warmerdam and Trent Hare.

> ### Water Area Mask
> From the slope data create a water mask. All slope data are marked off except for data with no incline.

> ### Water Area Vector Data
> From the Water Area Mask create a water area vector data set of water areas with a minimum size of approximate 3000 square meters.
> The gdal Polygonize abstraction is used to generate the Water Area Vector data.

> ### Water Area on Topographic Image
> To write the Water Area Vector Data to the topographic image the gdal RasterizeLayer abstraction is used.