from qgis.core import (QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer, QgsRasterLayer,QgsProject, QgsSingleBandPseudoColorRenderer, QgsRasterShader, QgsColorRampShader, Qgis)
from qgis import processing
from PyQt5.QtGui import QColor

#Define the class to grab the qgsprocessing stuff
class TasDryAspectCalc(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        
        #Ask the user for their input 
        self.addParameter(QgsProcessingParameterRasterLayer(
            "inputRaster","This script takes in an elevation model and calculates the 'dryness' of the aspect and slope,\nsuch that sleep NNW facing slopes are dry and steep SSE facing slopes are wet (like in real life in Tasmania)\n\nSelect your elevation model below", defaultValue=None, optional=False))
        
    def processAlgorithm(self, parameters, context, feedback):
        
        try:
            #Bring in the raster layer
            inputRasterLayer = self.parameterAsRasterLayer(parameters, "inputRaster", context)
            if not inputRasterLayer or not inputRasterLayer.isValid():
                feedback.reportError("Input raster is invalid")
                return {}

            #Set up gdal compression
            compressOptions = 'COMPRESS=LZW|PREDICTOR=2|NUM_THREADS=ALL_CPUS|TILED=YES|BIGTIFF=IF_SAFER'

            #Get the slope of the DEM
            slopeRaster = processing.run("gdal:slope", {'INPUT':inputRasterLayer,'BAND':1,'SCALE':1,'AS_PERCENT':False,'COMPUTE_EDGES':True,
                'ZEVENBERGEN':False,'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

            #Get the aspect of the DEM
            aspectRaster = processing.run("gdal:aspect", {'INPUT':inputRasterLayer,'BAND':1,'TRIG_ANGLE':False,'ZERO_FLAT':False,'COMPUTE_EDGES':True,
                'ZEVENBERGEN':False,'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

            #Calculate the dryness from the aspect and slope
            #In Tasmania the driest slope is 20° to the west of north
            finalRasterPath = processing.run("gdal:rastercalculator", {'INPUT_A':slopeRaster,'BAND_A':1,'INPUT_B':aspectRaster,'BAND_B':1,
                'FORMULA':'numpy.sin(A * numpy.pi / 180) * numpy.cos((B + 20) * numpy.pi / 180)','NO_DATA':None,'EXTENT_OPT':0,'PROJWIN':None,'RTYPE':5,
                'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

            #Add in the layer to the project
            finalRasterLayer = QgsRasterLayer(finalRasterPath, "Dry Aspect Raster")
            QgsProject.instance().addMapLayer(finalRasterLayer)

            """
            ############################################################################################
            Styling of the raster
            """

            #Set up a colour ramp that shows dryness to wetness
            colourStops = [(-1.0, QColor(17,0,66)),
                (-0.795674, QColor(0,32,100)),
                (-0.548076, QColor(0,91,112)),
                (-0.072116, QColor(58,183,115)),
                (0.08173, QColor(151,198,50)),
                (0.526442, QColor(255,225,108)),
                (1.0, QColor(255,255,255))]

            #Make a shader and a shader function
            rasterColourShader = QgsColorRampShader()
            rasterColourShader.setMinimumValue(-1)
            rasterColourShader.setMaximumValue(1)
            rasterColourShader.setColorRampItemList([QgsColorRampShader.ColorRampItem(value, colour) for value, colour in colourStops])
            rasterColourShader.setColorRampType(Qgis.ShaderInterpolationMethod.Linear)  
            rasterShaderFunction = QgsRasterShader()
            rasterShaderFunction.setRasterShaderFunction(rasterColourShader)

            #Apply the shading renderer to the actual layer
            pseudoColourRenderer = QgsSingleBandPseudoColorRenderer(finalRasterLayer.dataProvider(), 1, rasterShaderFunction)
            finalRasterLayer.setRenderer(pseudoColourRenderer)
            finalRasterLayer.triggerRepaint()
        
            """
            ############################################################################################
            Final stuff
            """
        
        except BaseException as e:
            feedback.raiseError(str(e))
            
        #Return nothing because you need to return something
        return {}

    #Required bs
    def name(self): return 'tas_dry_aspect_calc'
    def displayName(self): return 'Tas Dry Aspect Calc'
    def group(self): return 'NB Custom Scripts'
    def groupId(self): return 'nbcustomscripts'
    def createInstance(self): return TasDryAspectCalc()
