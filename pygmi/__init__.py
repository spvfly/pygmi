"""
PyGMI stands for Python Geophysical Modelling and Interpretation. It is a
modelling and interpretation suite aimed at magnetic, gravity and other
datasets. It includes:

 * Magnetic and Gravity 3D forward modelling
 * Cluster Analysis
 * Routines for cutting, reprojecting and doing simple modifications to data
 * Convenient display of data using pseudo-color, ternary and sunshaded representation

It is released under the Gnu General Public License version 3.0
"""
__all__ = ["raster", "clust", "pfmod", "vector", "test", "seis"]
from . import raster
from . import clust
from . import pfmod
from . import vector
from . import test
from . import seis
from .main import main