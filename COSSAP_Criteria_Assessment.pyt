"""
Title: COSSAP Criteria Assessment geoprocessing python toolbox

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

"""


import arcpy
import os
import sys
import ast
sys.path.append(r'C:\Python27\ArcGIS10.2\Lib\site-packages')
from arcpy.sa import *

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Table, TableStyle, Image, Spacer
from reportlab.lib.units import mm

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "COSSAP Criteria Assessment"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [CA]


class CA(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "COSSAP Criteria Assessment"

        self.description = """This script is an ESRI python toolbox, published as a geoprocessing service used for the
        purpose of performing the criteria assessment as part of the COSSAP Explorer web mapping application."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(displayName="Processing extent (WKT Linestring)",
                                 name="wkt",
                                 datatype="GPString",
                                 parameterType="Required",
                                 direction="Input")

        param1 = arcpy.Parameter(displayName="Resistance Raster Weightings",
                                 name="wTable",
                                 datatype="GPString",
                                 parameterType="Required",
                                 direction="Input")

        param2 = arcpy.Parameter(displayName="Exclusion Rasters",
                                 name="exclusion_rasters",
                                 datatype="GPString",
                                 parameterType="Optional",
                                 direction="Input")

        param3 = arcpy.Parameter(displayName="Produce KMZ",
                                 name="KMZ_bool",
                                 datatype="GPBoolean",
                                 parameterType="Optional",
                                 direction="Input")

        param4 = arcpy.Parameter(displayName="Produce PDF Report",
                                 name="PDF_bool",
                                 datatype="GPBoolean",
                                 parameterType="Optional",
                                 direction="Input")

        param5 = arcpy.Parameter(displayName="User defined exclusion area/s (WKT Linestring)",
                                 name="user_wkt",
                                 datatype="GPString",
                                 parameterType="Optional",
                                 direction="Input")

        param6 = arcpy.Parameter(displayName="User defined influence",
                                 name="user_influ",
                                 datatype="GPString",
                                 parameterType="Optional",
                                 direction="Input")
                                 
        param7 = arcpy.Parameter(displayName="User defined exclusion area/s description",
                                 name="user_description",
                                 datatype="GPString",
                                 parameterType="Optional",
                                 direction="Input")                                 
                                 
        # Set a value list for influence parameter
        param6.filter.type = "ValueList"
        param6.filter.list = ["Positive", "Negative"]
                                 
        param8 = arcpy.Parameter(displayName="Cost Surface",
                                 name="cRasterPNG",
                                 datatype="DEFile",
                                 parameterType="Derived",
                                 direction="Output")

        param9 = arcpy.Parameter(displayName="Cost Raster KMZ",
                                 name="cRasterKMZ",
                                 datatype="DEFile",
                                 parameterType="Derived",
                                 direction="Output")

        param10 = arcpy.Parameter(displayName="PDF Report",
                                 name="docPath",
                                 datatype="DEFile",
                                 parameterType="Derived",
                                 direction="Output")


        parameters = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        try:
            if arcpy.CheckExtension("spatial") == "Available":
                arcpy.CheckOutExtension("spatial")
            else:
                raise Exception
        except:
            return False  # tool cannot be executed
        return True  # tool can be executed

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # ---------------------------------------------------------------------------
        # FUNCTIONS
        # ---------------------------------------------------------------------------

        def AddMsgAndPrint(msg, severity=0):
            '''
            Message print function with a purpose of printing a input string message and displaying within an ESRI
            executed tool as different severity colours.

            severity 0 = standard message colour
            severity 1 = warning message colour
            severity 2 = error message colour

            :param msg: Text string of message that will print when executed as a ESRI tool
            :param severity: severity colour of message
            '''

            # Split the message on \n first, so that if it's multiple lines,
            #  a GPMessage will be added for each line
            try:
                for string in msg.split('\n'):
                    # Add appropriate geoprocessing message
                    #
                    if severity == 0:
                        arcpy.AddMessage(string)
                    elif severity == 1:
                        arcpy.AddWarning(string)
                    elif severity == 2:
                        arcpy.AddError(string)
            except:
                pass

        def feat_to_wkt(feature):
            '''
            Converts an input feature (line or poly) to WKT linestring

            :param Feature: input line or polygon featureclass
            :return: WKT geometry
            '''
            # Convert to WKT by field name (Shape)
            query = arcpy.SearchCursor(feature)
            for row in query:
                the_geom = row.getValue('Shape')  # Get Geometry field
                wkt = the_geom.WKT  # Convert to WKT, can also use WKB, JSON etc
            return wkt

        def getExtent(wkt):
            '''
            Buffers the area of interest bounding box, sent by the UI, by the buffPct parameter value

            :param wkt: input wkt linestring to get extent boundary information from
            :param buffPct: Decimal value (eg. 0.25) - representing percentage of the wkt extent.  This is used to
            enlarge the wkt extent to a specified percentage for user web interface purposes.
            :return: Extent values formatted as a string in the following form - "xMin, yMin, xMax, yMax"

            '''

            # create geometry object in Arcpy 10.1 +
            line = arcpy.FromWKT(wkt, arcpy.SpatialReference(4326))
            xMin = line.extent.XMin
            xMax = line.extent.XMax
            yMin = line.extent.YMin
            yMax = line.extent.YMax

            Extent = "{0} {1} {2} {3}".format(xMin, yMin, xMax, yMax)

            # return the extent
            arcpy.AddMessage(Extent)
            return Extent

        def createCostRaster(rrFgdb, wsTable, outCostRaster):
            '''
            Creates a cost raster using the weighted sum geoprocessing tool. Takes inputs of the location of the gdb
            containing the rasters that will be used in analysis (this is only used to acquire raster environment
            parameters (snap raster and cellsize) by importing them from one of the rasters. wsTable, which is the list
            object (passed originally from UI but has been modified since up till the point of use of this function)
            that references the rasters as well their respective weighted sum weights. The weight values can be any
            positive or negative decimal value. The weights do not need to add to any specific value such as 100
            (representing each raster's percent influence). In addition to this the ws table also holds the raster field
            containing the values. Field value is assumed to be always "VALUE".

            :param rrFgdb: the path to the file geodatabase in which the resistance rasters reside
            :param wsTable: the weighted sum table that defines the rasters and weights associated with each resistance
            raster to be used in the weighted sum analysis
            :param outCostRaster: the path and filename for the cost raster output from the weighted sum tool
            '''

            # Set Snap Raster environment so that the cost raster lines up with master index
            arcpy.env.snapRaster = os.path.join(rrFgdb, wsTable[0][0])  # the path to the first raster listed in wsTable

            # Set the environment cell size to ensure output matches inputs
            arcpy.env.cellSize = os.path.join(rrFgdb, wsTable[0][0])  # the path to the first raster listed in wsTable

            # Set parallel processing factor - Use half of the cores on the machine. The weighted sum tool honors the
            # Parallel Processing Factor environment and will divide and perform operations across multiple processes
            arcpy.env.parallelProcessingFactor = "50%"

            # print weighted sum table so format can be inspected
            message = "Weighted sum table: {0}".format(wsTable)
            AddMsgAndPrint(message, severity=0)

            # Execute WeightedSum to create cost raster
            outWS = WeightedSum(WSTable(wsTable))

            # Save out the weighted sum to tif
            #outWS.save(os.path.join(arcpy.env.scratchFolder,"costraster"))
            
            background_value = 0
            nodata_value = "0"
            pixel_type = "8_BIT_UNSIGNED"
            scale_pixel_value = "NONE"

            # convert it to png
            arcpy.CopyRaster_management(outWS, outCostRaster, "", background_value, nodata_value, "", "",
                                        pixel_type, scale_pixel_value)

            # clean up in memory workspaces
            arcpy.Delete_management(outWS)

        def to_weighted_sum_format(table_list, gdb_path):
            '''
            Takes string input passed from the resistance_raster_weightings parameter and converts
            it to a form to be utilised in the weighted sum tool.

            :param table: input list representing a table that includes raster names (file and label) and weightings
            :return: output list representing a table with correct specifications used for weighted sum tool.
            '''

            # Remove the raster label elements from the weightings table so that it matches the format required by
            # the arcgis weighted sum tool
            for row in table_list:
                row.remove(row[1])

            # Add additional elements of the raster attribute ("VALUE") and replace raster name with absolute path name
            for item in table_list:
                # replace first element (dataset name) in each list with the complete path
                item[0] = os.path.join(gdb_path, item[0])
                # Insert "VALUE" into nested lists in weighted sum table in the second element position
                item.insert(1, "VALUE")
            return table_list            
            
        def userWKT_to_rast(wkt, output_raster, cellsize=0.001):
            '''
            Converts the user inputted wkt to a simple binary integer raster with preset score values of 0 and -1.
            Cells representing the defined feature (wkt) have a value of -1 and everything else has a value of 0. The
            -1 value is only temporary as it is reclassified in a separate function depending on the influence defined
            by the user.

            :param wkt: wkt inputted from user
            :param output_raster: Path name of output binary integer raster
            :param cellsize: cell size of raster
            :return: raster
            '''
            # Convert wkt to geometry
            geom = arcpy.FromWKT(wkt, arcpy.SpatialReference(4326))
            # Convert geometry to feature
            fc = os.path.join(arcpy.env.scratchFolder,"user_feature.shp")
            arcpy.CopyFeatures_management(geom,fc)
            # Repair the geometry
            arcpy.RepairGeometry_management(fc)
            # Add score attribute
            arcpy.AddField_management(fc, "SCORE", "SHORT")
            # Calculate score field with score value
            arcpy.CalculateField_management(fc, "SCORE", -1, "PYTHON_9.3")
            # Convert to raster
            raster = "in_memory\\user_raster"
            #raster = os.path.join(arcpy.env.scratchFolder,"user_raster_debug")
            arcpy.FeatureToRaster_conversion(fc, "SCORE", raster, cellsize)
            # convert null to 0
            outCon = Con(IsNull(raster),0, raster)
            # save output
            outCon.save(output_raster)
            # Clean up in memory workspace
            arcpy.Delete_management(fc)
            arcpy.Delete_management(raster)

        def userWKT_apply_influence(exclude_raster, input_raster, output_raster, influence='Negative'):
            '''
            Applies the influence to the user defined WKT polygon.  If a positive influence is selected,
            the user defined region will be assigned the max value from the input cost raster in the output
            cost raster.  If a negative influence is selected, the user defined region will be assigned a 
            value of 1 in the output cost raster.

            :param exclude_raster: raster used to override the input raster where overlayed
            :param input_raster: Input raster to apply exclude raster values to
            :param influence: Scoring influence on cells representing wkt feature (negative =0, positive=max value from input_raster)
            :param output_raster: name and path of output raster
            :return: raster
            '''

            if influence == 'Negative':
                outCon = Con(arcpy.Raster(exclude_raster) < 0, 1, arcpy.Raster(input_raster))
            if influence == 'Positive':
                costMaxResult = arcpy.GetRasterProperties_management(input_raster, "MAXIMUM")
                costMax = int(costMaxResult.getOutput(0))
                outCon = Con(arcpy.Raster(exclude_raster) < 0, costMax, arcpy.Raster(input_raster))
            else:
                arcpy.AddMessage("userWKT_apply_influence: Could not define. Influence not applied to Cost Raster")
            
            #outCon.save (os.path.join(arcpy.env.scratchFolder, 'apply_influence_debug.tif'))

            # Set parameters for copy raster tool to convert to png format
            pixel_type = "8_BIT_UNSIGNED"
            scale_pixel_value = "NONE"

            # outCon.save throws an error when writing to PNG so CopyRaster must be used instead
            arcpy.CopyRaster_management(outCon, output_raster, "", "", "", "", "", pixel_type, scale_pixel_value)

            arcpy.Delete_management(outCon)

        def combine_exclusions(rasters, output):
            """
            Takes input rasters that have been choosen as 'exclusion rasters' and extracts the exclusion cells from
            each raster and combines them to create one raster

            :param rasters: List of exclusion rasters
            :param output: Raster representing all exclusion rasters
            :return:
            """
            combined_list = []
            for raster in rasters:
                extract = arcpy.sa.ExtractByAttributes(raster,' "EXCLUSION" = 1 ')
                extract1 = Con(extract >= 0, 1, 0)
                extract1.save(os.path.join(arcpy.env.scratchFolder, '{0}'.format(os.path.basename(raster))))
                arcpy.Delete_management(extract)
                combined_list.append(extract1)

            # Merge all together
            arcpy.MosaicToNewRaster_management(combined_list, arcpy.env.scratchFolder, os.path.basename(output), "",
                                                      "8_BIT_UNSIGNED", number_of_bands=1)

        def exclude_layer(input_raster, exclude_raster, output_raster):
            """
            Applies the lowest value to input raster in areas where exclude raster overlays.

            :param input_raster: Input raster to apply exclude raster values to
            :param exclude_raster: raster used to overide the input raster where overlayed
            :param output_raster: name and path of output raster
            :return: raster
            """

            # Apply conditional expression to apply lowest value to input raster where exclude raster overlays
            # http://resources.arcgis.com/en/help/main/10.2/index.html#//009z00000005000000

            # check if exclusion is withing area of interest by checking if raster has values
            rastercheck = arcpy.GetRasterProperties_management(arcpy.Raster(exclude_raster), 'ALLNODATA')
            if "{0}".format(rastercheck) == '0':
                outCon = arcpy.sa.Con(IsNull(exclude_raster), arcpy.Raster(input_raster), exclude_raster)
                #outCon.save(os.path.join(arcpy.env.scratchFolder, 'excludeded.tif'))

                # Set parameters for copy raster tool to convert to png format
                # background_value = 0
                # nodata_value = "0"
                pixel_type = "8_BIT_UNSIGNED"
                scale_pixel_value = "NONE"

                # outCon.save throws an error when writing to PNG so CopyRaster must be used instead
                arcpy.CopyRaster_management(outCon, output_raster, "", "", "", "", "", pixel_type, scale_pixel_value)
                # Clean up
                arcpy.Delete_management(outCon)

            # Clean up
            arcpy.Delete_management(rastercheck)

        def to_pdf_format(list):
            '''
            Takes a specific list table from the script input parameter and converts
            it to a form to be used in pdf report

            :param table: input list representing a table that includes raster names (file and label) and weightings
            :return: output list representing a table of Raster and weighting
            '''
            # Create a template weights table (list) with headings of "Resistance Raster" and "Weighting".
            # This weights table will contain data for pdf report
            wData = [["ReqID","Criteria Assessment Layer", "Weighting"]]

            # Add the relevant data (list containing resistance raster & weight) into the wData table
            for item in list:
                vals = []
                vals.extend([item[0], item[1], item[2]])
                wData.append(vals)
            return wData

        def convertToKmz(inData, outFile, outScale):
            '''
            Converts a raster of vector dataset to KMZ

            :param inData: Input spatial data (feature class or raster)
            :param outFile: Path name of output kmz file
            :param outScale: Scale of output kmz file
            :return: Returns the outFile
            '''

            #pixels = 1000
            pixels = ""
            #dpi = 320
            dpi = ""
            # Convert dataset to layer
            desc = arcpy.Describe(inData)
            if desc.dataType == "RasterDataset":
                layer = arcpy.MakeRasterLayer_management(inData, os.path.basename(inData) + "_layer")
                # symbolize with pre-made symbology layer file.  Disabled while using CV2 module to apply colourmap
                #arcpy.ApplySymbologyFromLayer_management(layer, symbology)
            elif desc.dataType == "FeatureClass":
                layer = arcpy.MakeFeatureLayer_management(inData, os.path.basename(inData) + "_layer")
                #arcpy.ApplySymbologyFromLayer_management(layer, symbology)

            # Convert cost distance raster layer to kml
            arcpy.LayerToKML_conversion(layer, outFile, outScale, "COMPOSITE", "", pixels, dpi)
            # clean up workspace
            arcpy.Delete_management(layer)


        def rescale(inRaster, minValue, maxValue, outRaster):
            """
            Rescales the raster values to the range provided.

            :param inRaster: Input raster to rescale
            :param minValue: the min value to rescale to
            :param maxValue: the max value to rescale to
            :param outRaster: name and path of output raster
            :return: raster
            """
            band1Min = arcpy.GetRasterProperties_management(inRaster, "MINIMUM")
            band1Max = arcpy.GetRasterProperties_management(inRaster, "MAXIMUM")
            rasterMax = int(band1Max.getOutput(0))
            rasterMin = int(band1Min.getOutput(0))
            
            rescaleRaster = ((arcpy.Raster(inRaster) - rasterMin) * (int(maxValue) - int(minValue)) / (rasterMax - rasterMin)) + int(minValue)
            
            pixel_type = "8_BIT_UNSIGNED"
            scale_pixel_value = "NONE"
          
            # rescaleRaster.save throws an error when writing to PNG so CopyRaster must be used instead
            arcpy.CopyRaster_management(rescaleRaster, outRaster, "", "", "", "", "", pixel_type, scale_pixel_value)

            # Clean up
            arcpy.Delete_management(rescaleRaster)
            
        def get_rast_min_max(raster):
            '''
            Gets the min and max values from an input raster and returns them in a list.

            :param raster: Input raster to get min max values from
            :return: list containing min and max values accordingly
            '''
            min_max = []
            rast = arcpy.Raster(raster)
            min_max.append(rast.minimum)
            min_max.append(rast.maximum)
            return min_max

        # def applyCustomColorMap(inputImg, colourRampFile, invertColours="No"):
        #     """
        #     Reads in a .clr file and converts it to a lookup-table for CV2 to apply to the input file.
        #
        #     :param inputImg: Input raster to convert to colour
        #     :param colourRampFile: .clr file saved from ArcGIS
        #     :param invertColours: optional parameter to invert the colours
        #     :return: image with colour ramp applied
        #     """
        #
        #     # create three empty lists to store values in
        #     band1 = []
        #     band2 = []
        #     band3 = []
        #
        #     # read in .clr file and append columns 2, 3 and 4 to lists
        #     with open(colourRampFile, 'r') as file:
        #         for row in file:
        #             a, b, c, d = row.split()
        #             band1.append(int(b))
        #             band2.append(int(c))
        #             band3.append(int(d))
        #
        #     # if invert is "Yes", reverse the order of each list
        #     if invertColours == "Yes":
        #         band3.reverse()
        #         band1.reverse()
        #         band2.reverse()
        #
        #     # create 256x1 array with 3 bands and then populate with list values
        #     lut = np.zeros((256, 1, 3), dtype=np.uint8)
        #     lut[:, 0, 0] = band3
        #     lut[:, 0, 1] = band2
        #     lut[:, 0, 2] = band1
        #     # apply lookup-table to image
        #     im_color = cv2.LUT(inputImg, lut)
        #
        #     return im_color


        # ---------------------------------------------------------------------------
        # MAIN
        # ---------------------------------------------------------------------------

        # ------------- Passed parameter variables ---------

        # param0 (Input)
        WKT = parameters[0].valueAsText

        # param1 (Input)
        resistance_raster_weightings = parameters[1].valueAsText

        # param2 (Input)
        exclusion_rasters = parameters[2].valueAsText

        # ------------- Output parameter variables ---------

        # param8 (Output)
        costRaster = os.path.join(arcpy.env.scratchFolder,"costRaster.png")

        # param9 (Output)
        cRasterKmz = os.path.join(arcpy.env.scratchFolder, "costRaster.kmz")

        # param10 (Output)
        PDF_name = "Report.pdf"
        PDF_doc = os.path.join(arcpy.env.scratchFolder, PDF_name)

        # -------------- Hard coded variables --------------

        # Pre-canned raster geodatabase (Hard coded)
        rrFgdb = r"\\prod\apps\applications\ags_dev\service_data_gp\COSSAP\CriteriaAssessment\COSSAP_Criteria_Assessment_Rasters.gdb"

        # PDF report image locations (Hard coded)
        pdf_cover_image = r"\\prod\apps\applications\ags_dev\service_data_gp\COSSAP\CriteriaAssessment\cover.jpg"
        pdf_legend_image = r"\\prod\apps\applications\ags_dev\service_data_gp\COSSAP\CriteriaAssessment\legend.jpg"

        # -------------- Environment variables --------------

        # Set environment variables
        # Overwrite outputs
        arcpy.env.overwriteOutput = True

        # Disable pyramid building throughout script
        arcpy.env.pyramid = "PYRAMIDS 0"

        # --------------------------------------------------------
        # GENERATE BOUNDING BOX FROM WKT LINESTRING
        # --------------------------------------------------------

        # Get the area of interest that will be used to filter the resistance raster
        message = "WKT: {0}".format(WKT)
        AddMsgAndPrint(message, severity=0)

        # Get extent bounds of area of interest
        message = "Getting extents of area of interest"
        AddMsgAndPrint(message, severity=0)
        wktBBox = getExtent(WKT)
        message = "Area of interest bounds: {0}".format(wktBBox)
        AddMsgAndPrint(message, severity=0)

        # Set Processing Extent environment variable so that the cost raster is only generated over the area of interest
        arcpy.env.extent = wktBBox

        # ---------------------------------------------------------
        # CREATE COST RASTER FROM RESISTANCE RASTERS
        # ---------------------------------------------------------

        # The resistance raster weightings are inputed from UI as a string (unicode) representation of a list. Therefore
        # it needs to be converted from a string to a list object in order to iterate through ect..
        resistance_raster_weightings = ast.literal_eval(resistance_raster_weightings)
        # repeat above step into separate list for PDF report to extract Raster strings from
        resistance_raster_weightings_PDF = list(resistance_raster_weightings)

        # Remove exclusion layers from the resistance_raster_weightings list
        if exclusion_rasters:
            resistance_raster_weightings = [x for x in resistance_raster_weightings if x[0] not in exclusion_rasters]

        # Weightings for each resistance raster - formated like
        # [[inRaster01, string of raster name, weight01], [inRaster02, string of raster name, weight02],
        # [inRaster03, string of raster name, weight03]]

        wTable = resistance_raster_weightings
        message = "Weightings: {0}".format(wTable)
        AddMsgAndPrint(message, severity=0)

        # Get list of resistance rasters(string names) used in the analysis from input weightings table parameter
        # (to be used in the GENERATE MODEL REPORT PDF part of script)
        rrUsed = [x[1] for x in wTable]

        # Get a list representing a table containing the data raster and weight
        # (to be used in the GENERATE MODEL REPORT PDF part of script)
        wData = to_pdf_format(wTable)

        # Convert wTable into correct form for input into the weighted sum tool
        wsTable = to_weighted_sum_format(wTable, rrFgdb)

        # Create the cost raster from the resistance rasters
        message = "Creating cost raster"
        AddMsgAndPrint(message, severity=0)
        createCostRaster(rrFgdb, wsTable, costRaster)
        message = "Cost raster complete"
        AddMsgAndPrint(message, severity=0)


        # -----------------------------------------------------------
        # SCALE COSTRASTER.PNG TO 0-255 BIT
        # -----------------------------------------------------------

        # Rescale cost raster so it draws correctly in UI
        message = "Rescaling cost raster"
        AddMsgAndPrint(message, severity=0)
        rescale(costRaster, "0", "255", costRaster)
        message = "Rescaling complete"
        AddMsgAndPrint(message, severity=0)

        # ---------------------------------------------------------
        # POST PROCESSING OF COST RASTER (EXCLUSIONS)
        # ---------------------------------------------------------

        # If user has selected any layers to be used as exclusions, convert each raster to exclusion rasters (setting
        # raster score to be one value). Once this is done merge them all together and perform raster conditional
        # evaluation (exclude layer function) with the cost raster to override raster values to lowest value (to represent
        # excluded areas)

        if parameters[2].value:
            message = "Applying exclusion rasters to cost raster"
            AddMsgAndPrint(message, severity=0)
            # The exclusion rasters are inputed from UI as a string (unicode) representation of a list. Therefore
            # it needs to be converted from a string to a list object in order to iterate through ect..
            exclusion_rasters = ast.literal_eval(exclusion_rasters)

            # Modify the exclusion raster list by replacing raster name with absolute path name of raster in pre-canned gdb
            for index, item in enumerate(exclusion_rasters):
                exclusion_rasters[index] = os.path.join(rrFgdb, item)
            message = "Exclusion rasters:{0}".format(exclusion_rasters)
            AddMsgAndPrint(message, severity=0)

            # Combine exclusions layers together (only cells that are allocated for exclusion) and apply the
            # exclude_layer function to this output
            combine_exc = os.path.join(arcpy.env.scratchFolder, "combined_exc")
            combine_exclusions(exclusion_rasters, combine_exc)
            exclude_layer(costRaster, combine_exc, costRaster)

        # If user has inputted a defined area WKT for input as exclusion, create a raster from WKT and perform raster
        # conditional evaluation (exclude layer function) with the cost raster to override raster values to lowest value
        # (to represent excluded areas)

        if parameters[5].value:
            message = "Adding user defined wkt parameters for exclusion"
            AddMsgAndPrint(message, severity=0)
            # user_defined_raster = os.path.join(rrFgdb, "User_Input")
            user_defined_raster = os.path.join(arcpy.env.scratchFolder, "User_Input")
            userWKT_to_rast(parameters[5].valueAsText, user_defined_raster)

            # Apply user defined exclusion and influence to cost raster
            userWKT_apply_influence(user_defined_raster, costRaster, costRaster, parameters[6].valueAsText)

            # Delete the resulting raster from pre-canned gdb
            message = "Deleting user defined raster"
            AddMsgAndPrint(message, severity=0)
            arcpy.Delete_management(user_defined_raster)

        # Create copy of scaled costRaster to be added in PDF report (for some reason on the server, only jpg images
        # can be added in report. Without making a fuss of getting developers to look for jpg instead of png, this step
        # is added).
        report_costRaster = os.path.join(arcpy.env.scratchFolder, "costRaster_report.jpg")
        arcpy.CopyRaster_management(costRaster, report_costRaster, "", "", "", "", "", "8_BIT_UNSIGNED")

        # #convert to colour image
        # message = "Converting to Pseudocolour"
        # AddMsgAndPrint(message, severity=0)
        
        # # this approach takes a 0-255 colour ramp *.clr saved out from ArcGIS and applies it to the png.
        # # when setting colour ramp in ArcGIS use the Colourmap_0_256.tif as the input file to ensure the full 0-255 valuerange is assigned
        # colourrampFile = r'\\prod\apps\applications\ags_dev\service_data_gp\COSSAP\MCA\costRaster_colourramp.clr'
        # im = cv2.imread(costRaster, cv2.IMREAD_GRAYSCALE);
        # im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR);
        # # if 'invert' is selected in ArcGIS to achieve the desired colour ramp, change the below to "Yes"
        # invertColours = "No"
        # im_color = applyCustomColorMap(im, colourrampFile, invertColours)
        
        # # use below instead to just use a precanned CV2 colour ramp
        # im_grey = cv2.imread(costRaster, cv2.IMREAD_GRAYSCALE)
        # im_color = cv2.applyColorMap(im_grey, cv2.COLORMAP_SUMMER)
        
        # #write out new colour png inplace of old file
        # # by writing out to the existing costraster, the world file is linked to the cv2 export
        # cv2.imwrite(costRaster, im_color)
        # message = "Pseudocolour conversion complete"
        # AddMsgAndPrint(message, severity=0)   

        # -----------------------------------------------------------
        # CREATE OUTPUT KMZs
        # -----------------------------------------------------------

        # Convert cost raster to kmz if requested
        if parameters[3].value == True:
            message = "Converting cost raster to kmz in location of {0}".format(cRasterKmz)
            AddMsgAndPrint(message, severity=0)
            convertToKmz(costRaster, cRasterKmz, "")
            message = "Conversion complete"
            AddMsgAndPrint(message, severity=0)

        # -------------------------------------------------------------
        # GENERATE MODEL REPORT PDF
        # -------------------------------------------------------------

        # Define paragraph styles that will be used in the report
        styles = getSampleStyleSheet()
        styleNormal = styles['Normal']
        styleHeading1 = styles['Heading1']
        styleHeading2 = styles['Heading2']
        styleHeading3 = styles['Heading3']
        styleHeading4 = styles['Heading4']
        title_style = ParagraphStyle('title', fontSize=48, leading=48)
        Table_text_style = ParagraphStyle('table text', fontSize=8)

        # Add custom style - use Normal as base
        styleTableBody = styles['Normal']

        # Modify normal style
        #styleTableBody.fontName = 'Times-Roman'

        # Set output parameter value
        doc = SimpleDocTemplate(PDF_doc, pagesize=A4, title="Report")

        story = []

        # Add cover image
        story.append(Image(pdf_cover_image, 184 * mm, 150 * mm))

        # Add main heading
        title_text = 'Criteria Assessment Report'
        story.append(Paragraph(title_text, title_style))

        # Add page break
        story.append(PageBreak())

        # Add Description heading
        story.append(Paragraph("Description", styleHeading2))

        # Add report description
        story.append(Paragraph(
            "This model generates a cost surface based on the input path or area created by the user and the input data "
            "layer variables chosen to generate a heat map surface. There are three components to the assessment. "
            "Firstly the user chooses the input layers and weights them according to preference. The heat map surface "
            "is then created by intersecting the chosen scored datasets and applying the individual weightings through a "
            "weighted sum operation. If the weightings are not changed they will be treated as equally weighted. "
            "Secondly the user can then define layers to be used as total exclusion zones. These will over write all "
            "weighted sum outputs with a score of 1 in the final heat map surface. Thirdly the user can input their "
            "own simple area and define it as either positive or negative weight. This will over write the weighted sum "
            "output with either the lowest value (if negative chosen) or the  highest value (if positive chosen). This "
            "function is only used if the user has prior knowledge about their area that is not available as a layer "
            "within the application. This function is used for reporting purposes and will feed through to the report. "
            "output",
            styleNormal))

        # Add space before next paragraph
        story.append(Spacer(1, 12))

        story.append(Paragraph(
            "The functionality of the Criteria Assessment tool is based on pre-set rating scores, and applies user set "
            "weightings to evaluate assessment criteria. This information should only be used for first-pass analysis to "
            "indicate areas for potential detailed investigation. The criteria assessment is indicative only, and should "
            "only be used as a preliminary step in the decision process to locate potential CCS sites.",
            styleNormal))

        # Add page break so that table all on one page - if it isn't SPAN in table style will throw error
        story.append(PageBreak())

        story.append(Paragraph("Criteria assessment data layers", styleHeading2))
        story.append(Paragraph(
            "Described in the table below is all of the criteria assessment data layers that are part of this geoprocessing "
            "service.",
            styleNormal))

        # Add space before table
        story.append(Spacer(1, 12))

        # Hard coded list containing all the rows of text used in data layers table
        data = [['ReqID', 'Metric', 'Layer', 'Unit', 'Score', 'Values'],
                ['EXP01', Paragraph('Site lies within close proximity to high density', Table_text_style), Paragraph('Petroleum Borehole locations',Table_text_style),
                 'Density', '1', '0'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '2', '0 - 4466.23'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '3', '4466.23 - 8932.46'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '4', '8932.46 - 13398.79'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '5', '13398.79 - 17864.92'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '6', '17864.92 - 22331.15'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '7', '22331.15 - 31263.62'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '8', '31263.62 - 49128.54'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '9', '49128.54 - 102723.31'],
                ['EXP01', 'Site lies within an area within reach of cluster of petroleum boreholes', 'Petroleum Borehole locations','Density', '10', '>102723.31 '],

                ['EXP02',Paragraph('Site lies within an area within reach of cluster of 2D seismic survey data', Table_text_style),
                 Paragraph('2D Seismic surveys',Table_text_style), 'Density', '1', '0'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '2', '0 - 10.1'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '3', '10.1 - 20.2'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '4', '20.2 - 40.3'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '5', '40.3 - 60.5'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '6', '60.5 - 90.7'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '7', '90.7 - 131'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '8', '131 - 191.4'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '9', '191.4 - 312.3'],
                ['EXP02','Site lies within an area within reach of cluster of 2D seismic survey data',
                 '2D Seismic surveys', 'Density', '10', '> 312.3'],

                ['EXP03', Paragraph('Site lies within an area that has 3D seismic survey data', Table_text_style),
                 Paragraph('3D Seismic surveys',Table_text_style), Paragraph('Frequency of surveys',Table_text_style), '1', 'No surveys'],
                ['EXP03', 'Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '5', '1 or 2 surveys'],
                ['EXP03','Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '6', '3 surveys'],
                ['EXP03', 'Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '7', '4 surveys'],
                ['EXP03', 'Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '8', '6 surveys'],
                ['EXP03', 'Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '9', '8 surveys'],
                ['EXP03', 'Site lies within an area that has 3D seismic survey data',
                 '3D Seismic surveys', 'Frequency of surveys', '10', '9 to 11 surveys'],

                ['EXP04', Paragraph('Site is not within mining area', Table_text_style),
                 'Mining areas', 'Distance (km)', '1', '0 - 5'],
                ['EXP04', 'Site is not within mining area',
                 'Mining areas', 'Distance (km)', '5', '5 - 10'],
                ['EXP04', 'Site is not within mining area',
                 'Mining areas', 'Distance (km)', '10', '>10'],

                ['ENV01', Paragraph('Site does not lie within an existing land resource and environmental use', Table_text_style),
                 Paragraph('Existing land resources and uses',Table_text_style), 'Attribute', '1', Paragraph('National Park, Conservation area, Marine Park, Protection area, Sanctuary',Table_text_style)],
                ['ENV01', 'Site does not lie within an existing land resource and environmental use',
                 'Existing land resources and uses', 'Attribute', '2', Paragraph('Reserve, Habitat area, Management area',Table_text_style)],
                ['ENV01','Site does not lie within an existing land resource and environmental use',
                 'Existing land resources and uses', 'Attribute', '10', 'No Data'],

                ['ENV02', Paragraph('Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora', Table_text_style),
                 Paragraph('Ecological significance and known habitat of rare fauna or flora',Table_text_style), 'Attribute', '1', Paragraph('Area with a species that has an extinct status',Table_text_style)],
                ['ENV02', 'Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora',
                 'Ecological significance and known habitat of rare fauna or flora', 'Attribute', '2', Paragraph('Area with a species that has an extinct in the wild status',Table_text_style)],
                ['ENV02', 'Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora',
                 'Ecological significance and known habitat of rare fauna or flora', 'Attribute', '4', Paragraph('Area with a species that has a critical endagered status',Table_text_style)],
                ['ENV02', 'Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora',
                 'Ecological significance and known habitat of rare fauna or flora', 'Attribute', '6', Paragraph('Area with a species that has an endagered status', Table_text_style)],
                ['ENV02', 'Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora',
                 'Ecological significance and known habitat of rare fauna or flora', 'Attribute', '8', Paragraph('Area with a species that has conservation status',Table_text_style)],
                ['ENV02', 'Site is not located in an area that has ecological significance and or is habitat to rare fauna or flora',
                 'Ecological significance and known habitat of rare fauna or flora', 'Attribute', '10', 'No Data'],

                ['ENV03', Paragraph('Site is not located within certain vegetation',Table_text_style), Paragraph('Existing Vegetation',Table_text_style),
                 'Attribute', '1', 'Mangrove, Rainforrest'],
                ['ENV03', 'Site is not located within certain vegetation','Existing Vegetation',
                 'Attribute', '5', 'Forrest or Shrub'],
                ['ENV03', 'Site is not located within certain vegetation','Existing Vegetation',
                 'Attribute', '10', 'No vegetation, unknown'],

                ['ENV04', Paragraph('Site is not located in an area that is prone to frequent water observations', Table_text_style), 'Flooding history',
                 'Attribute', '0', 'No data (offshore)'],
                ['ENV04','Site is not located in an area that is prone to frequent water observations', 'Flooding history',
                 'Attribute', '1', 'Appearance of water'],
                ['ENV04', 'Site is not located in an area that is prone to frequent water observations', 'Flooding history',
                 'Attribute', '10', 'No appearance of water'],

                ['ENV05', Paragraph('Site is not located within wetlands or lakes',Table_text_style), 'Wetlands and lakes',
                 'Attribute', '1', Paragraph('Lake, Reservoir, watercourse area, wetland',Table_text_style)],
                ['ENV05', 'Site is not located within wetlands or lakes', 'Wetlands and lakes',
                 'Attribute', '10', 'No Data'],

                ['ENV07', Paragraph('Site located in an area of rainfall of X mm/year', Table_text_style), 'Annual rainfall',
                 'Annual rainfall', '0', 'No Data'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '1', '>= 1000'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '2', '937.5 - 1000'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '3', '875 - 937.5'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '4', '812.5 - 875'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '5', '750 - 812.5'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '6', '687.5 - 750'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '7', '625 - 687.5'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '8', '562.5 - 625'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '9', '500 - 562.5'],
                ['ENV07', 'Site located in an area of rainfall of X mm/year', 'Annual rainfall',
                 'Annual rainfall', '10', '<= 500'],

                ['GDW01', Paragraph('Site lies within an area within reach of cluster of groundwater boreholes', Table_text_style), 'Groundwater',
                 'Density', '1', '0'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '2', '0 - 111.1'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '3', '111.1 - 2222.2'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '4', '2222.2 - 3333.3'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '5', '3333.3 - 4444.4'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '6', '4444.4 - 6666.7'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '7', '6666.7 - 10000'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '8', '10000 - 15555.5'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '9', '15555.5 - 30000'],
                ['GDW01','Site lies within an area within reach of cluster of groundwater boreholes','Groundwater',
                 'Density', '10', '30000 - 219889'],

                ['GPL01', Paragraph('Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)', Table_text_style),
                 'Geopolitical','Distance (km)', '0', 'No Data (offshore)'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '1', '>= 100'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '2', '90.6 - 100'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '3', '81.2 - 90.6'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '4', '71.9 - 81.2'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '5', '62.5 - 71.9'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '6', '53.1 - 62.5'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '7', '43.8 - 53.1'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopolitical', 'Distance (km)', '8', '34.4 - 43.8'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Geopoltical', 'Distance (km)', '9', '25 - 34.4'],
                ['GPL01', 'Site boundary X km from a road that provides connection between regional centres (National Highway, Arterial Road or Sub-Arterial Road)',
                 'Environmental', 'Distance (km)', '10', '<= 25'],

                ['GPL02', Paragraph('Site boundary X km from an area of population density of 5 people per square kilometre', Table_text_style),'Geopolitical', 'Distance (km)', '0', 'No Data (offshore)'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre', 'Distance (km)', '1', '<= 5'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '2', '5 - 6.9'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '3', '6.9 - 8.8'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '4', '8.8 - 10.6'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '5', '10.6 - 12.5'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '6', '12.5 - 14.4'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '7', '14.4 - 16.3'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '8', '16.3 - 18.1'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '9', '18.1 - 20'],
                ['GPL02', 'Site boundary X km from an area of population density of 5 people per square kilometre','Geopolitical', 'Distance (km)', '10', '>= 20'],

                ['GPL03', Paragraph('Site does not lie within an existing land area of cultural and historical significance', Table_text_style),
                 'Geopolitical', 'Attribute', '2', Paragraph('Indigenous area, Heritage area, Historic, Indigenous, Natural',Table_text_style)],
                ['GPL03', 'Site does not lie within an existing land area of cultural and historical significance','Geopolitical', 'Attribute', '4', 'Recreational Area'],
                ['GPL03', 'Site does not lie within an existing land area of cultural and historical significance','Geopolitical', 'Attribute', '10', 'No Data'],

                ['GPL04', Paragraph('Site boundary X km from a rail that proves connection between regional centres', Table_text_style),'Geopolitical', 'Distance (km)', '0', 'No Data (offshore)'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '1', '>= 100'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '2', '90.6 - 100'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '3', '81.3 - 90.6'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '4', '71.9 - 81.3'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '5', '62.5 - 71.9'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '6', '53.1 - 62.5'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '7', '43.8 - 53.1'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '8', '34.4 - 43.8'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '9', '25 - 34.4'],
                ['GPL04', 'Site boundary X km from a rail that provides connection between regional centres','Geopolitical', 'Distance (km)', '10', '<= 25'],

                ['GPL05', Paragraph('Site boundary X km from a major utility easement', Table_text_style),'Geopolitical', 'Distance (km)', '1', '> 100'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '2', '90.6 - 100'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '3', '81.3 - 90.6'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '4', '71.9 - 81.3'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '5', '62.5 - 71.9'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '6', '53.1 - 62.5'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '7', '43.8 - 53.1'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '8', '34.4 - 43.8'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '9', '25 - 34.4'],
                ['GPL05', 'Site boundary X km from a major utility easement','Geopolitical', 'Distance (km)', '10', '<=25'],

                ['GPL06', Paragraph('Site boundary X km from industrial facilities', Table_text_style),'Geopolitical', 'Distance (km)', '1', '> 100'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '2', '90.6 - 100'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '3', '81.3 - 90.6'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '4', '71.9 - 81.3'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '5', '62.5 - 71.9'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '6', '53.1 - 62.5'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '7', '43.8 - 53.1'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '8', '34.4 - 43.8'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '9', '25 - 34.4'],
                ['GPL06', 'Site boundary X km from industrial facilities','Geopolitical', 'Distance (km)', '10', '<= 25'],

                ['GPL07', Paragraph('Site does not lie within a prohibited area', Table_text_style),'Prohibited areas', 'Attribute', '1', 'All prohibited feature types'],
                ['GPL07', 'Site does not lie within a prohibited area', 'Prohibited areas','Attribute', '10', 'No Data'],

                ['GEOL01',Paragraph('Site overlies a basin with CO2 storage characteristics', Table_text_style), 'CO2 basin suitability','Attribute', '0', 'No Data'],
                ['GEOL01','Site overlies a basin with CO2 storage characteristics','CO2 basin suitability', 'Attribute', '1', 'Unsuitable'],
                ['GEOL01','Site overlies a basin with CO2 storage characteristics','CO2 basin suitability', 'Attribute', '4', 'Unlikely'],
                ['GEOL01','Site overlies a basin with CO2 storage characteristics','CO2 basin suitability', 'Attribute', '6', 'Possible'],
                ['GEOL01','Site overlies a basin with CO2 storage characteristics','CO2 basin suitability', 'Attribute', '8', 'Suitable'],
                ['GEOL01','Site overlies a basin with CO2 storage characteristics','CO2 basin suitability', 'Attribute', '10', 'Highly Suitable'],

                ['GEOL02',Paragraph('Sites crustal temperature at 5km depth is of temperature that does not affect the storage of CO2', Table_text_style),'CO2 basin suitability', 'Temperature (C)', '0', 'No Data (Offshore)'],
                ['GEOL02',Paragraph('Sites crustal temperature at 5km depth is of temperature that does not affect the storage of CO2', Table_text_style),'CO2 basin suitability', 'Temperature (C)', '1', 'Highly Suitable'],
                ['GEOL02',Paragraph('Sites crustal temperature at 5km depth is of temperature that does not affect the storage of CO2', Table_text_style),'CO2 basin suitability', 'Temperature (C)', '10', 'Highly Suitable'],

                ['GEOL03', Paragraph('Site boundary X km from known or anticipated major geological fault',Table_text_style), 'Major geological fault', 'Distance (km)', '0', 'No Data (Offshore)'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '1', '<=2.5'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '2', '2.5 - 8.4'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '3', '8.4 - 14.4'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '4', '14.4 - 20.3'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '5', '20.3 - 26.3'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '6', '26.3 - 32.2'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '7', '32.2 - 38.1'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '8', '38.1 - 44.1'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '9', '44.1 - 50'],
                ['GEOL03','Site boundary X km from known or anticipated major geological fault','Major geological fault', 'Distance (km)', '10', '> 50'],

                ['GPYL01',Paragraph('Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', Table_text_style),'Earthquake hazard', Paragraph('Earthquake hazard probability',Table_text_style), '0', 'No Data'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '1', '>0.08'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '2', '0.07625 - 0.08'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '3','0.0725 - 0.07625'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '4','0.06875 - 0.0725'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '5','0.065 - 0.06875'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '6','0.06125 - 0.065'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '7','0.0575 - 0.06125'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '8','0.05375 - 0.0575'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '9','0.05 - 0.05375'],
                ['GPYL01', 'Site within an area with earthquake hazard X with annual probablility of exceedance of 1/500', 'Earthquake hazard', 'Earthquake hazard probability', '10','<=0.05'],

                ['GPYL02', Paragraph('Site is situated in ideal cost effective height below sea level',Table_text_style), 'Bathymetry depth', 'Elevation (m)', '1', '<-2000'],
                ['GPYL02','Site is situated in ideal cost effective height below sea level','Bathymetry depth', 'Elevation (m)', '2', '-2000 - -1000'],
                ['GPYL02','Site is situated in ideal cost effective height below sea level','Bathymetry depth', 'Elevation (m)', '4', '-1000 - -500'],
                ['GPYL02','Site is situated in ideal cost effective height below sea level','Bathymetry depth', 'Elevation (m)', '6', '-500 - -300'],
                ['GPYL02','Site is situated in ideal cost effective height below sea level','Bathymetry depth', 'Elevation (m)', '8', '-300 - -200'],
                ['GPYL02','Site is situated in ideal cost effective height below sea level','Bathymetry depth', 'Elevation (m)', '10', '>-200'],

                ['GPYL03',Paragraph('Site is not located in an area that has an unstable slope degree', Table_text_style),Paragraph('Unstable ground conditions',Table_text_style),
                 Paragraph('Slope angle (degrees)',Table_text_style), '0', 'No Data (offshore)'],
                ['GPYL03','Site is not located in an area that has an unstable slope degree','Unstable ground conditions', 'Slope angle (degrees)', '1', '>30'],
                ['GPYL03','Site is not located in an area that has an unstable slope degree','Unstable ground conditions', 'Slope angle (degrees)', '4', '15 - 30'],
                ['GPYL03','Site is not located in an area that has an unstable slope degree','Unstable ground conditions', 'Slope angle (degrees)', '6', '5 - 15'],
                ['GPYL03','Site is not located in an area that has an unstable slope degree','Unstable ground conditions', 'Slope angle (degrees)', '8', '2 - 5'],
                ['GPYL03','Site is not located in an area that has an unstable slope degree','Unstable ground conditions', 'Slope angle (degrees)', '10', '0 - 2'],
                ]

        # Set the table stylings
        t = Table(data, colWidths=[17 * mm, 39 * mm, 32 * mm, 25 * mm, 12 * mm, 40 * mm], hAlign="CENTRE")

        # This is where the style of the table is specified, such as the text ect and what rows will be spanned and for
        # how many rows
        t.setStyle(TableStyle([
                               ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                               ('FONTSIZE', (0, 1), (-1, -1), 8),

                               ('VALIGN', (0, 1), (3, 1), 'TOP'),
                               ('SPAN', (0, 1), (0, 10)),
                               ('SPAN', (1, 1), (1, 10)),
                               ('SPAN', (2, 1), (2, 10)),
                               ('SPAN', (3, 1), (3, 10)),

                               ('VALIGN', (0, 11), (3, 11), 'TOP'),
                               ('SPAN', (0, 11), (0, 20)),
                               ('SPAN', (1, 11), (1, 20)),
                               ('SPAN', (2, 11), (2, 20)),
                               ('SPAN', (3, 11), (3, 20)),

                               ('VALIGN', (0, 21), (3, 21), 'TOP'),
                               ('SPAN', (0, 21), (0, 27)),
                               ('SPAN', (1, 21), (1, 27)),
                               ('SPAN', (2, 21), (2, 27)),
                               ('SPAN', (3, 21), (3, 27)),

                               ('VALIGN', (0, 28), (3, 28), 'TOP'),
                               ('SPAN', (0, 28), (0, 30)),
                               ('SPAN', (1, 28), (1, 30)),
                               ('SPAN', (2, 28), (2, 30)),
                               ('SPAN', (3, 28), (3, 30)),

                               ('VALIGN', (0, 31), (3, 31), 'TOP'),
                               ('SPAN', (0, 31), (0, 33)),
                               ('SPAN', (1, 31), (1, 33)),
                               ('SPAN', (2, 31), (2, 33)),
                               ('SPAN', (3, 31), (3, 33)),

                               ('VALIGN', (0, 34), (3, 34), 'TOP'),
                               ('SPAN', (0, 34), (0, 39)),
                               ('SPAN', (1, 34), (1, 39)),
                               ('SPAN', (2, 34), (2, 39)),
                               ('SPAN', (3, 34), (3, 39)),

                               ('VALIGN', (0, 40), (3, 40), 'TOP'),
                               ('SPAN', (0, 40), (0, 42)),
                               ('SPAN', (1, 40), (1, 42)),
                               ('SPAN', (2, 40), (2, 42)),
                               ('SPAN', (3, 40), (3, 42)),

                               ('VALIGN', (0, 43), (3, 43), 'TOP'),
                               ('SPAN', (0, 43), (0, 45)),
                               ('SPAN', (1, 43), (1, 45)),
                               ('SPAN', (2, 43), (2, 45)),
                               ('SPAN', (3, 43), (3, 45)),

                               ('VALIGN', (0, 46), (3, 46), 'TOP'),
                               ('SPAN', (0, 46), (0, 47)),
                               ('SPAN', (1, 46), (1, 47)),
                               ('SPAN', (2, 46), (2, 47)),
                               ('SPAN', (3, 46), (3, 47)),

                               ('VALIGN', (0, 48), (3, 48), 'TOP'),
                               ('SPAN', (0, 48), (0, 58)),
                               ('SPAN', (1, 48), (1, 58)),
                               ('SPAN', (2, 48), (2, 58)),
                               ('SPAN', (3, 48), (3, 58)),

                               ('VALIGN', (0, 59), (3, 59), 'TOP'),
                               ('SPAN', (0, 59), (0, 68)),
                               ('SPAN', (1, 59), (1, 68)),
                               ('SPAN', (2, 59), (2, 68)),
                               ('SPAN', (3, 59), (3, 68)),

                               ('VALIGN', (0, 69), (3, 69), 'TOP'),
                               ('SPAN', (0, 69), (0, 79)),
                               ('SPAN', (1, 69), (1, 79)),
                               ('SPAN', (2, 69), (2, 79)),
                               ('SPAN', (3, 69), (3, 79)),

                               ('VALIGN', (0, 80), (3, 80), 'TOP'),
                               ('SPAN', (0, 80), (0, 90)),
                               ('SPAN', (1, 80), (1, 90)),
                               ('SPAN', (2, 80), (2, 90)),
                               ('SPAN', (3, 80), (3, 90)),

                               ('VALIGN', (0, 91), (3, 91), 'TOP'),
                               ('SPAN', (0, 91), (0, 93)),
                               ('SPAN', (1, 91), (1, 93)),
                               ('SPAN', (2, 91), (2, 93)),
                               ('SPAN', (3, 91), (3, 93)),

                               ('VALIGN', (0, 94), (3, 94), 'TOP'),
                               ('SPAN', (0, 94), (0, 104)),
                               ('SPAN', (1, 94), (1, 104)),
                               ('SPAN', (2, 94), (2, 104)),
                               ('SPAN', (3, 94), (3, 104)),

                               ('VALIGN', (0, 105), (3, 105), 'TOP'),
                               ('SPAN', (0, 105), (0, 114)),
                               ('SPAN', (1, 105), (1, 114)),
                               ('SPAN', (2, 105), (2, 114)),
                               ('SPAN', (3, 105), (3, 114)),

                               ('VALIGN', (0, 115), (3, 115), 'TOP'),
                               ('SPAN', (0, 115), (0, 124)),
                               ('SPAN', (1, 115), (1, 124)),
                               ('SPAN', (2, 115), (2, 124)),
                               ('SPAN', (3, 115), (3, 124)),

                               ('VALIGN', (0, 125), (3, 125), 'TOP'),
                               ('SPAN', (0, 125), (0, 126)),
                               ('SPAN', (1, 125), (1, 126)),
                               ('SPAN', (2, 125), (2, 126)),
                               ('SPAN', (3, 125), (3, 126)),

                               ('VALIGN', (0, 127), (3, 127), 'TOP'),
                               ('SPAN', (0, 127), (0, 132)),
                               ('SPAN', (1, 127), (1, 132)),
                               ('SPAN', (2, 127), (2, 132)),
                               ('SPAN', (3, 127), (3, 132)),

                               ('VALIGN', (0, 133), (3, 133), 'TOP'),
                               ('SPAN', (0, 133), (0, 135)),
                               ('SPAN', (1, 133), (1, 135)),
                               ('SPAN', (2, 133), (2, 135)),
                               ('SPAN', (3, 133), (3, 135)),

                               ('VALIGN', (0, 136), (3, 136), 'TOP'),
                               ('SPAN', (0, 136), (0, 146)),
                               ('SPAN', (1, 136), (1, 146)),
                               ('SPAN', (2, 136), (2, 146)),
                               ('SPAN', (3, 136), (3, 146)),

                               ('VALIGN', (0, 147), (3, 147), 'TOP'),
                               ('SPAN', (0, 147), (0, 157)),
                               ('SPAN', (1, 147), (1, 157)),
                               ('SPAN', (2, 147), (2, 157)),
                               ('SPAN', (3, 147), (3, 157)),

                               ('VALIGN', (0, 158), (3, 158), 'TOP'),
                               ('SPAN', (0, 158), (0, 163)),
                               ('SPAN', (1, 158), (1, 163)),
                               ('SPAN', (2, 158), (2, 163)),
                               ('SPAN', (3, 158), (3, 163)),

                               ('VALIGN', (0, 164), (3, 164), 'TOP'),
                               ('SPAN', (0, 164), (0, 169)),
                               ('SPAN', (1, 164), (1, 169)),
                               ('SPAN', (2, 164), (2, 169)),
                               ('SPAN', (3, 164), (3, 169)),

                               ('HALIGN', (4, 1), (4, 169), 'MIDDLE'),
                               ('VALIGN', (4, 1), (4, 169), 'MIDDLE'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black)])
        )

        # Add to story
        story.append(t)

        # Add sub-heading
        story.append(Paragraph("Results", styleHeading2))

        # Add sub-heading
        story.append(Paragraph("Criteria assessment layers used in the analysis and weights", styleHeading3))

        # Insert table with criteria assessment list and weightings from variable assigned earlier
        # Set the table stylings for the pdf weightings table
        wt = Table(wData, colWidths=[1.7*cm, 9.3 * cm, 5.5 * cm], hAlign="CENTRE")
        wt.setStyle(TableStyle([
                                ('FONTSIZE', (0, 1), (-1, -1), 8),
                                #('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                #('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                                #('TEXTFONT', (0, 0), (-1, 0), 'Times-Bold'),
                                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
                                ]))

        # Add to story
        story.append(wt)
        story.append(Spacer(1, 12))

        # Reference dictionary for raster descriptions used for the purpose of printing exclusion layers information
        # choosen by user. Since resistance raster input parameter only carries this info, when a layer is choosen as exclusion
        # its removed from being inputted in weighted sum therefore its description information is not carried through.
        # Hence why this dictionary is hardcoded. Code Design not ideal but work around for now.
        raster_desc = {"EXP01": "Petroleum Borehole locations", "EXP02": "2D Seismic surveys",
                       "EXP03": "3D Seismic Surveys",
                       "EXP04": "Mining areas", "ENV01": "Existing land resources and uses",
                       "ENV02": "Ecological significance", "ENV03": "Existing vegetation",
                       "ENV04": "Flooding history",
                       "ENV05": "Wetlands and lakes", "ENV07": "Annual rainfall", "GDW01": "Groundwater Boreholes",
                       "GPL01": "Proximity to Roads", "GPL02": "Population distribution",
                       "GPL03": "Cultural and history and significance", "GPL04": "Proximity to railways",
                       "GPL05": "Proximity to pipe and transmission lines",
                       "GPL06": "Proximity to industrial facilities and major ports",
                       "GPL07": "Site boundary X km from a Prohibited area",
                       "GEOL01": "CO2 Storage Basin suitability",
                       "GEOL02": "Crustal temperature", "GEOL03": "Major geological fault",
                       "GPYL01": "Earthquake hazard potential", "GPYL02": "Bathymetry depth",
                       "GPYL03": "Unstable ground conditions"
                       }

        if parameters[2].value: #If exclusion rasters were enabled add the following text

            # Add page break so that table all on one page
            story.append(PageBreak())

            # Add sub-heading
            story.append(Paragraph("Excluded Feature Classes", styleHeading3))
            story.append(Paragraph("The following rasters were excluded from the analysis as directed by the user.",styleNormal))
            story.append(Spacer(1,12))

            # List to populate excusion layers used. First element added is the only heading of "Criteria Assessment Layer"
            exclusion_data = [['ReqID','Criteria Assessment Layer']]

            # Look for what exclusions have been selected by looking in the exclusion rasters list and using this to
            # reference the raster_desc dictionary (look a few lines above) to get the description and add it to the
            # exclusion_data list to be used to print to a table in report
            for e in exclusion_rasters:
                inRaster = e.split("\\")[-1]
                exclusion_data.append([inRaster, raster_desc[inRaster]])

            # Insert table with exclusion data list
            # Set the table stylings for the pdf weightings table
            et = Table(exclusion_data, colWidths=[1.7 * cm, 14.5 * cm], hAlign="CENTRE")
            et.setStyle(TableStyle([
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                # ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                # ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                # ('TEXTFONT', (0, 0), (-1, 0), 'Times-Bold'),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
            ]))

            # Add table to story
            story.append(et)

        if parameters[5].value:  # if custom influence area is selected add the following text
            # Add sub-heading
            story.append(Paragraph("Custom Influence", styleHeading3))

            # List to record the WKT polygon drawn by user. You will notice it has headings of the WKT (polygon),
            # its influence (positive or negative) and the description given by the user.
            user_influence_data = [['WKT','Influence','Description']]

            # Add the following paragraph
            story.append(Paragraph(
                "The following area has been included by the user as a {0} influence:".format(parameters[6].valueAsText),
                styleNormal))
            story.append(Spacer(1, 12))

            # List of values gathered from ui to put in table
            user_influence_data.append([Paragraph(parameters[5].valueAsText, Table_text_style),Paragraph(parameters[6].valueAsText, Table_text_style)])

            # If optional ui parameter given, add this too
            if parameters[7].value:
                user_influence_data[1].append([Paragraph(parameters[7].valueAsText, Table_text_style)])

            # Insert table with exclusion data list
            # Set the table stylings for the pdf weightings table
            et = Table(user_influence_data, colWidths=[10 * cm, 3.25 * cm,3.25*cm], hAlign="CENTRE")
            et.setStyle(TableStyle([
                ('FONTSIZE', (0, 1), (2, 1), 8),
                # ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                # ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                # ('TEXTFONT', (0, 0), (-1, 0), 'Times-Bold'),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('VALIGN', (0, 1), (2, 1), 'TOP')
            ]))

            story.append(et)

        # Add page break so that result image and its heading are on new page
        story.append(PageBreak())

        # Add sub-heading
        story.append(Paragraph("Criteria assessment output image result", styleHeading3))

        # Insert image of criteria assessment with correct aspect ratio size
        cost_img = Image(report_costRaster)
        cost_img._restrictSize(165*mm,165*mm)
        cost_img.hAlign = 'CENTRE'
        story.append(cost_img)
        
        # Immediately after this image insert the legend image into pdf
        story.append(Spacer(1, 12))
        legend_img = Image(pdf_legend_image)
        legend_img._restrictSize(20*mm,40*mm)
        legend_img.hAlign = 'LEFT'
        story.append(legend_img)

        # Add sub-heading
        story.append(Paragraph("Result metadata", styleHeading3))

        # Data for last table of result processing information
        west, south, east, north = wktBBox.split(" ")
        result_meta_data = [['Projection', 'Geographical'],['Datum','WGS84'],['Processing extent', Paragraph('North:{0}<br /> South:{1}<br />East:{2}<br />West:{3}'.format(north,south,east,west),Table_text_style)],
                            ['Output data format', 'KMZ'], ['Accuracy', Paragraph('The model output was derived from 0.001 cell size gridded data processed from various levels of accuracy',Table_text_style)], ['Licence and Restrictions', Paragraph('Commonwealth of Australia (Geoscience Australia) 2016. This product is released under CC-BY',Table_text_style)]]

        # Insert table with exclusion data list
        # Set the table stylings for the pdf weightings table
        rt = Table(result_meta_data, colWidths=[5 * cm,11.5 *cm], hAlign="CENTRE")
        rt.setStyle(TableStyle([
            ('FONTSIZE', (1, 0), (1, 5), 8),
            # ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('BACKGROUND', (0, 0), (0, 5), colors.lightgrey),
            # ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            # ('TEXTFONT', (0, 0), (-1, 0), 'Times-Bold'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))

        story.append(rt)

        # Add page break so that contact information and its heading are on new page
        story.append(PageBreak())

        # Add contacts sub-heading
        story.append(Paragraph("Contact information", styleHeading2))
        story.append(Paragraph("Organisation", styleHeading3))
        story.append(Paragraph("Geoscience Australia", styleNormal))
        story.append(Paragraph("", styleNormal))
        story.append(Paragraph("Contact details", styleHeading3))
        story.append(Paragraph("If you encounter any problems, please email clientservices@ga.gov.au quoting the CCS "
                               "application and the following issues", styleNormal))

        # Generate the content and write it to the pdf file if requested
        if parameters[4].value == True:
            message = "Building PDF in location of {0}".format(PDF_doc)
            AddMsgAndPrint(message, severity=0)
            doc.build(story)

        arcpy.SetParameterAsText(8, costRaster)
        arcpy.SetParameterAsText(9, cRasterKmz)
        arcpy.SetParameterAsText(10, PDF_doc)

        return