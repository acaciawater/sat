from .modis import MOD13
from datetime import date

DATA = r'/media/GONWKS2/GIS_bestanden/Africa/modis/mod13c2.006'
EXTENT = (-20.0, -36.0, 55.0, 38.0)

DATASET='NDVI'

modis = MOD13()
modis.extract(DATASET, DATA, EXTENT)
