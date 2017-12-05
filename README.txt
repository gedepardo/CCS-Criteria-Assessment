CCS Criteria Assessment geoprocessing python toolbox

Description: This script is an ESRI python toolbox, published as a geoprocessing service used for the purpose of 
performing the criteria assessment as part of the COSSAP Explorer web mapping application.

This toolbox performs a weighted sum of selected pre-canned resistance rasters processed within a specified extent
and weightings passed on from the application. The result of the tool is a cost raster in the format of a PNG.
Optional outputs from the tool area KMZ file as well as a PDF report containing information about the analysis performed.

There are two optional inputs from the tool which allows the functionality of creating exclusion areas from layers
(overide area to lowest value) and custom user defined areas (overide areas to either highest value or lowest value).

If layer/s are selected to be used as exclusions, the are inputted into parameter as a list. E.g.
["ENV01","ENV02"]. As a result, where these layers exist, the values will be calculated to be 1.

If based by user definition, the input into the tool is a user defined WKT line string in the form of a polygon.
Depending on the influence applied, the representing area will either be classified as 0 or the maximum value.

Processing extent is determined by a polygon WKT line string and the chosen criteria assesment rasters with weightings
for the weighted sum determined by a string in the form of python lists within a list, with each of the list elements
within the list representing the following;

[dataset name, more descriptive dataset name for report, weighted sum weight value].

Example of syntax for Lakes dataset and Reserves datasets would be '[["Lakes", "Lakes 250K", 0.5],["Reserves",
"National Parks and reserves", 0.5]]'.


:parameter Processing extent (WKT Linestring) (Required): WKT linestring in the form of a polygon used to determine
processing extent.
For example 'POLYGON((146.33072 -37.36326,148.44834 -37.30429,148.57743 -38.51559,146.27854 -38.31761,146.33072 -37.36326))'

:parameter Resistance Raster Weightings (Required): Determines the rasters choosen for the weighted sum in the form of a
string list. For example if Lakes and Reserves were the chosen layers and their weights were 0.2 and 0.5 respectively then
the syntax would be '[["Lakes", "Lakes 250K", 0.2],["Reserves", "National Parks and reserves", 0.5]]'.

:parameter Exclusion Raster/s (optional): List of pre-canned raster name/s that will be removed out of MCA and used to
classify areas of exclusion within the cost raster (cells classified to zero representing areas definately not suitable
for CO2) where overlayed. Inputted into parameter as a list. For Example ["ENV01","ENV02"]

:parameter Produce KMZ (Optional): Boolean type that determines if KMZ will be created as an additional output.

:parameter Produce PDF (Optional): Boolean type that determines if a PDF report about the analysis will be created as
an additional output.

:parameter User defined exclusion area/s (WKT Linestring) (optional): User defined influence area/s (WKT Linestring)
(optional): User defined WKT linestring in the form of a polygon that is added as a feature that represents areas
of postive or negative classification within the cost raster (cells classified to either 1 or the maximum value present)
where overlayed.
 
:parameter User defined influence (optional): The influence to apply to the user defined area/s. 
If positive, the maximum score present in the analysis prior to this step will be applied to the area/s defined.
If negative, a score of 1 will be applied to the area/s defined.

Limitations: The script is specifically designed to be used as a geoprocessing service used in the Multicriteria
selection functionality of the COSSAP explorer web mapping application.
This is a ESRI python toolbox written to the capabilities of version 10.2.

Author: G Stewart, R Coghlan

References: This script was originally based from the least cost path script used in the CIAP application created by
Rob Kay.