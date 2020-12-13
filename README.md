 # DEM 2 Topo
 
 ## Back Ground
 This came to be out of necessity and curiosity.
 We needed background maps of usable resolution up to continent level (and more). There is no budget, but there is free DEM data available...
 
 Play and experiment with the processes as described below.
 The sample output include Water-Body-from-DEM applied.
 
 This is what I come up with.
 
 ## Tools:
	- DGal (www.gdal.org)
	- hsv_merge.py, a python file courtesy of Frank Warmerdam
	- gdal_calc
	- Notepad++
	- Spreadsheet
	- Operating system scrip (ie. bat)

 ## TIP:
	- Write the output to a dedicated folder.
	
 ## Process
 ###### Create Color Relief from (every) DEM
 We will need a color ref image. The example file "ColorRelief02.txt" is an altitude based color bin definition. The values in the sample is based on the altitude found on the continent of Africa. Seems to work fine for the rest of the world.
 The following example creates a Color Relief file from the DEM file.
 gdaldem Color-relief s01_e037_1arc_v3.bil ColorRelief02.txt C:\GIS\STRM\AfriS\Relief2\s01_e037_Relief2.tif
 You can play with color schemes or use true color images.
 
 ######Create Hillshade from DEM
 gdaldem hillshade C:\GIS\STRM\AfriS\s01_e037_1arc_v3.bil C:\GIS\STRM\AfriS\Shade\s01_e037_shade.tif -z 5 -s 111120 -az 90 -compute_edges
 Reference the GDal documentation on hillshade
 
 ######Create Slope from DEM
 gdaldem slope C:\GIS\STRM\AfriS\s01_e037_1arc_v3.bil C:\GIS\STRM\AfriS\Slope\s01_e037_slope.tif -s 111120 -compute_edges -of GTiff
 Value range 0 to 90 degrees
 Reference the GDal documentation on slope
 
 ######Combine Hillshade and Slope
 gdal_calc.bat -A C:\GIS\STRM\AfriS\Slope\s01_e037_slope.tif -B C:\GIS\STRM\AfriS\Shade\s01_e037_shade.tif --outfile=C:\GIS\STRM\AfriS\Topo3\SlopeHillShadeComb\s01_e037_slope_hillshade.tif --calc="((((A/90)*255)*0.7)+(B*0.3))+70" --type=Byte --overwrite
 
 gdal_calc.bat -A D:\RepoGitDir\AJGeo\DEM-to-Topo\Data\s01_e037_slope.tif -B D:\RepoGitDir\AJGeo\DEM-to-Topo\Data\s01_e037_shade.tif --outfile=D:\RepoGitDir\AJGeo\DEM-to-Topo\Data\s01_e037_slope_hillshade.tif --calc="((((A/90)*255)*0.7)+(B*0.3))+70" --type=Byte --overwrite
 
 - Give a weight of 70% to Slope and 30% to Hillshade in combo
 - Slope is in degrees. Scale to 255 value range
 - Hillshade is in value range 0 to 255
 - Adjust value with increase of about 25% (value 70). This gives about middle distribution (bell curve) of values in value range. the higher the adjustment value the lighter the end product will be and vise-versa.
 
 ######Create Topo Image
 hsv_merge C:\GIS\STRM\AfriS\Relief2\s01_e037_Relief2.tif C:\GIS\STRM\AfriS\Topo3\SlopeHillShadeComb\s01_e037_slope_hillshade.tif s01_e037_ColorTopo3.tif
 
 ## 100s of files
  ######Step 1
	- dir *.bil > file.txt
	- Open the file in NotePad++
	- Remove non file lines
	- Make the remaining lines tab delimited and save.
	- Open in spreadsheet and remove columns that is not file names and save.
######Step 2
	- Use the file name list from Step 1 to create a spreadsheet with the commands for the processes as already described. Make marker tags columns where necessary to be replaced by nothing later.
	- Save spreadsheet file.
	- Export to TAB delimited BAT file.
	- Open delimited file on NotePad++ and replace TABs with SPACE and markers with nothing where applicable.
