# -----------------------------------------------------------------------------
# Name:        iodefs.py (part of PyGMI)
#
# Author:      Patrick Cole
# E-Mail:      pcole@geoscience.org.za
#
# Copyright:   (c) 2013 Council for Geoscience
# Licence:     GPL-3.0
#
# This file is part of PyGMI
#
# PyGMI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyGMI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
""" Import Data """

import sys
import os
import re
import zipfile
from PyQt5 import QtWidgets, QtCore
import numpy as np
from osgeo import osr, gdal
from osgeo import ogr
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pygmi.pfmod.datatypes import Data, LithModel
import pygmi.pfmod.grvmag3d as grvmag3d
import pygmi.pfmod.tensor3d as tensor3d
import pygmi.pfmod.cubes as mvis3d
import pygmi.menu_default as menu_default
import pygmi.raster.dataprep as dp
# This is necessary for loading npz files, since I moved the location of
# datatypes.
from pygmi.pfmod import datatypes
sys.modules['datatypes'] = datatypes


class ImportMod3D(object):
    """ Import Data """
    def __init__(self, parent):
        self.parent = parent
        self.lmod = LithModel()

        self.ifile = ""
        self.name = "Import 3D Model: "
        self.ext = ""
        self.indata = {}
        self.outdata = {}

        if parent is not None:
            self.pbars = parent.pbar

    def settings(self):
        """ Settings """
        ext = ('npz (*.npz);;'
               'Leapfrog Block Model (*.csv);;'
               'x,y,z,label (*.csv);;'
               'x,y,z,label (*.txt)')

        filename, filt = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, 'Open File', '.', ext)

        if filename == '':
            return False
        os.chdir(filename.rpartition('/')[0])
        self.ifile = str(filename)
        self.parent.modelfilename = filename.rpartition('.')[0]

# Reset Variables
        self.lmod.griddata.clear()
        self.lmod.lith_list.clear()

        if filt == 'Leapfrog Block Model (*.csv)':
            self.import_leapfrog_csv(filename)
        elif filt == 'x,y,z,label (*.csv)' or filt == 'x,y,z,label (*.txt)':
            self.import_ascii_xyz_model(filename)
        else:
            indict = np.load(filename)
            self.dict2lmod(indict)

        self.outdata['Model3D'] = [self.lmod]
        self.lmod.name = filename.rpartition('/')[-1]

        for i in self.lmod.griddata:
            if self.lmod.griddata[i].dataid == '':
                self.lmod.griddata[i].dataid = i

        tmp = [i for i in set(self.lmod.griddata.values())]
        self.outdata['Raster'] = tmp

        return True

    def import_leapfrog_csv(self, filename):
        """ Imports leapfrog csv block models """

        piter = self.pbars.iter

        with open(filename) as fno:
            tmp = fno.readlines()

        while tmp[0][0] == '#':
            tmp.pop(0)

        if not tmp:
            return

        header = tmp.pop(0).split(',')
        header = header[7:]

        mtmp = MessageCombo(header)
        mtmp.exec_()
        datindx = mtmp.master.currentIndex()

        x = []
        y = []
        z = []
        label = []
        xcell = float(tmp[0].split(',')[3])
        ycell = float(tmp[0].split(',')[4])
        zcell = float(tmp[0].split(',')[5])

        for i in piter(tmp):
            i2 = i.split(',')
            x.append(float(i2[0]))
            y.append(float(i2[1]))
            z.append(float(i2[2]))
            label.append(i2[7+datindx])

        x = np.array(x)
        y = np.array(y)
        z = np.array(z)

        x_u = np.unique(x)
        y_u = np.unique(y)
        z_u = np.unique(z)
        labelu = np.unique(label)
        labelu[labelu == 'blank'] = 'Background'

        lmod = self.lmod

        lmod.numx = x_u.shape[0]
        lmod.numy = y_u.shape[0]
        lmod.numz = z_u.shape[0]
        lmod.dxy = max(xcell, ycell)
        lmod.d_z = zcell
        lmod.curprof = 0
        lmod.curlayer = 0
        lmod.xrange = [x_u.min()-lmod.dxy/2., x_u.max()+lmod.dxy/2.]
        lmod.yrange = [y_u.min()-lmod.dxy/2., y_u.max()+lmod.dxy/2.]
        lmod.zrange = [z_u.min()-lmod.d_z/2., z_u.max()+lmod.d_z/2.]

        lindx = 0
        for itxt in labelu:
            lindx += 1
            if itxt == 'Background':
                lmod.lith_list[itxt] = grvmag3d.GeoData(
                    self.parent, ncols=lmod.numx, nrows=lmod.numy,
                    numz=lmod.numz, dxy=lmod.dxy, d_z=lmod.d_z)
                lmod.lith_list[itxt].lith_index = 0
                lmod.mlut[0] = [np.random.randint(0, 255),
                                np.random.randint(0, 255),
                                np.random.randint(0, 255)]
            else:
                lmod.lith_list[itxt] = grvmag3d.GeoData(
                    self.parent, ncols=lmod.numx, nrows=lmod.numy,
                    numz=lmod.numz, dxy=lmod.dxy, d_z=lmod.d_z)
                lmod.lith_list[itxt].lith_index = lindx
                lmod.mlut[lindx] = [np.random.randint(0, 255),
                                    np.random.randint(0, 255),
                                    np.random.randint(0, 255)]

            lmod.lith_list[itxt].modified = True
            lmod.lith_list[itxt].set_xyz12()

        lmod.lith_index = None
        lmod.update(lmod.numx, lmod.numy, lmod.numz, lmod.xrange[0],
                    lmod.yrange[1], lmod.zrange[1], lmod.dxy, lmod.d_z,
                    usedtm=True)
        lmod.update_lith_list_reverse()

        for i in piter(range(len(x))):
            xi = x[i]
            col = int((xi-lmod.xrange[0])/lmod.dxy)
            row = int((lmod.yrange[1]-y[i])/lmod.dxy)
            layer = int((lmod.zrange[1]-z[i])/lmod.d_z)
            if label[i] == 'blank':
                lmod.lith_index[col, row, layer] = \
                    lmod.lith_list['Background'].lith_index
            else:
                lmod.lith_index[col, row, layer] = \
                    lmod.lith_list[label[i]].lith_index

    def import_ascii_xyz_model(self, filename):
        """ Used to import ASCII XYZ Models of the form x,y,z,label"""

        if filename.find('.csv') > -1:
            tmp = np.genfromtxt(filename, delimiter=',', dtype=np.str)
        else:
            tmp = np.genfromtxt(filename, dtype=np.str)

        x = tmp[:, 0].astype(np.float)
        y = tmp[:, 1].astype(np.float)
        z = tmp[:, 2].astype(np.float)
        label = tmp[:, 3]
        labelu = np.unique(label)

        idx = np.unique(x, return_index=True)[1]
        x_u = x[np.sort(idx)]
        dx_u = np.diff(x_u)
        idx = np.unique(y, return_index=True)[1]
        y_u = y[np.sort(idx)]
        dy_u = np.diff(y_u)
        idx = np.unique(z, return_index=True)[1]
        z_u = z[np.sort(idx)]
        dz_u = np.diff(z_u)

        if dx_u[0] < 0:
            dx_u *= -1
        if dy_u[0] < 0:
            dy_u *= -1
        if dz_u[0] < 0:
            dz_u *= -1

        xcell = np.max(dx_u)
        ycell = np.max(dy_u)
        zcell = np.max(dz_u)

        lmod = self.lmod

        lmod.dxy = min(xcell, ycell)
        lmod.d_z = zcell
        lmod.curprof = 0
        lmod.curlayer = 0
        lmod.xrange = [x_u.min()-lmod.dxy/2., x_u.max()+lmod.dxy/2.]
        lmod.yrange = [y_u.min()-lmod.dxy/2., y_u.max()+lmod.dxy/2.]
        lmod.zrange = [z_u.min()-lmod.d_z/2., z_u.max()+lmod.d_z/2.]
        lmod.numx = int(np.ptp(lmod.xrange)/lmod.dxy+1)
        lmod.numy = int(np.ptp(lmod.yrange)/lmod.dxy+1)
        lmod.numz = int(np.ptp(lmod.zrange)/lmod.d_z+1)


# Section to load lithologies.
        if 'Generic 1' in lmod.lith_list:
            lmod.lith_list.pop('Generic 1')

        lindx = 0
        for itxt in labelu:
            lindx += 1
            lmod.mlut[lindx] = [np.random.randint(0, 255),
                                np.random.randint(0, 255),
                                np.random.randint(0, 255)]
            lmod.lith_list[itxt] = grvmag3d.GeoData(
                self.parent, ncols=lmod.numx, nrows=lmod.numy, numz=lmod.numz,
                dxy=lmod.dxy, d_z=lmod.d_z)

            lmod.lith_list[itxt].lith_index = lindx
            lmod.lith_list[itxt].modified = True
            lmod.lith_list[itxt].set_xyz12()

        lmod.lith_index = None
        lmod.update(lmod.numx, lmod.numy, lmod.numz, lmod.xrange[0],
                    lmod.yrange[1], lmod.zrange[1], lmod.dxy, lmod.d_z)
        lmod.update_lith_list_reverse()

        for i, xi in enumerate(x):
            col = int((xi-lmod.xrange[0])/lmod.dxy)
            row = int((lmod.yrange[1]-y[i])/lmod.dxy)
            layer = int((lmod.zrange[1]-z[i])/lmod.d_z)
            try:
                lmod.lith_index[col, row, layer] = \
                    lmod.lith_list[label[i]].lith_index
            except:
                import pdb
                pdb.set_trace()

    def dict2lmod(self, indict, pre=''):
        """ routine to convert a dictionary to an lmod """
        lithkeys = indict[pre+'lithkeys']

        lmod = self.lmod

        lmod.gregional = indict[pre+'gregional']
        lmod.ght = indict[pre+'ght']
        lmod.mht = indict[pre+'mht']
        lmod.numx = indict[pre+'numx']
        lmod.numy = indict[pre+'numy']
        lmod.numz = indict[pre+'numz']
        lmod.dxy = indict[pre+'dxy']
        lmod.d_z = indict[pre+'d_z']
        lmod.lith_index = indict[pre+'lith_index']
        lmod.curprof = 0
        lmod.curlayer = 0
        lmod.xrange = np.array(indict[pre+'xrange']).tolist()
        lmod.yrange = np.array(indict[pre+'yrange']).tolist()
        lmod.zrange = np.array(indict[pre+'zrange']).tolist()
        if pre+'custprofx' in indict:
            lmod.custprofx = np.asscalar(indict[pre+'custprofx'])
        else:
            lmod.custprofx = {0: (lmod.xrange[0], lmod.xrange[1])}
        if pre+'custprofy' in indict:
            lmod.custprofy = np.asscalar(indict[pre+'custprofy'])
        else:
            lmod.custprofy = {0: (lmod.yrange[0], lmod.yrange[0])}

        lmod.mlut = np.asscalar(indict[pre+'mlut'])
        lmod.init_calc_grids()

        lmod.griddata = np.asscalar(indict[pre+'griddata'])

        for i in lmod.griddata:
            lmod.griddata[i].data = np.ma.array(lmod.griddata[i].data)

        # This gets rid of a legacy variable name
        for i in lmod.griddata:
            if not hasattr(lmod.griddata[i], 'dataid'):
                lmod.griddata[i].dataid = ''
            if hasattr(lmod.griddata[i], 'bandid'):
                if lmod.griddata[i].dataid == '':
                    lmod.griddata[i].dataid = lmod.griddata[i].bandid
                del lmod.griddata[i].bandid

        wktfin = None
        for i in lmod.griddata:
            wkt = lmod.griddata[i].wkt
            if wkt != '' and wkt is not None:
                wktfin = wkt

        if wktfin is not None:
            for i in lmod.griddata:
                wkt = lmod.griddata[i].wkt
                if wkt == '' or wkt is None:
                    lmod.griddata[i].wkt = wktfin

# Section to load lithologies.
        lmod.lith_list['Background'] = grvmag3d.GeoData(self.parent)

        for itxt in lithkeys:
            if itxt != 'Background':
                lmod.lith_list[itxt] = grvmag3d.GeoData(self.parent)

            lmod.lith_list[itxt].hintn = np.asscalar(indict[pre+itxt+'_hintn'])
            lmod.lith_list[itxt].finc = np.asscalar(indict[pre+itxt+'_finc'])
            lmod.lith_list[itxt].fdec = np.asscalar(indict[pre+itxt+'_fdec'])
            lmod.lith_list[itxt].zobsm = np.asscalar(indict[pre+itxt+'_zobsm'])
            lmod.lith_list[itxt].susc = np.asscalar(indict[pre+itxt+'_susc'])
            lmod.lith_list[itxt].mstrength = np.asscalar(
                indict[pre+itxt+'_mstrength'])
            lmod.lith_list[itxt].qratio = np.asscalar(
                indict[pre+itxt+'_qratio'])
            lmod.lith_list[itxt].minc = np.asscalar(indict[pre+itxt+'_minc'])
            lmod.lith_list[itxt].mdec = np.asscalar(indict[pre+itxt+'_mdec'])
            lmod.lith_list[itxt].density = np.asscalar(
                indict[pre+itxt+'_density'])
            lmod.lith_list[itxt].bdensity = np.asscalar(
                indict[pre+itxt+'_bdensity'])
            lmod.lith_list[itxt].lith_index = np.asscalar(
                indict[pre+itxt+'_lith_index'])
            lmod.lith_list[itxt].g_cols = np.asscalar(indict[pre+itxt+'_numx'])
            lmod.lith_list[itxt].g_rows = np.asscalar(indict[pre+itxt+'_numy'])
            lmod.lith_list[itxt].numz = np.asscalar(indict[pre+itxt+'_numz'])
            lmod.lith_list[itxt].g_dxy = np.asscalar(indict[pre+itxt+'_dxy'])
            lmod.lith_list[itxt].dxy = np.asscalar(indict[pre+itxt+'_dxy'])
            lmod.lith_list[itxt].d_z = np.asscalar(indict[pre+itxt+'_d_z'])
            lmod.lith_list[itxt].zobsm = np.asscalar(indict[pre+itxt+'_zobsm'])
            lmod.lith_list[itxt].zobsg = np.asscalar(indict[pre+itxt+'_zobsg'])
            lmod.lith_list[itxt].modified = True
            lmod.lith_list[itxt].set_xyz12()


class ImportTMod3D(object):
    """ Import Data """
    def __init__(self, parent):
        self.parent = parent
        self.lmod = LithModel()

        self.ifile = ""
        self.name = "Import 3D Model: "
        self.ext = ""
        self.indata = {}
        self.outdata = {}

        if parent is not None:
            self.pbars = parent.pbar

    def settings(self):
        """ Settings """
        ext = ('npz (*.npz)')

        filename, filt = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, 'Open File', '.', ext)

        if filename == '':
            return False
        os.chdir(filename.rpartition('/')[0])
        self.ifile = str(filename)
        self.parent.modelfilename = filename.rpartition('.')[0]

# Reset Variables
        self.lmod.griddata.clear()
        self.lmod.lith_list.clear()

        indict = np.load(filename)
        self.dict2lmod(indict)

        self.outdata['Model3D'] = [self.lmod]
        self.lmod.name = filename.rpartition('/')[-1]

        for i in self.lmod.griddata:
            if self.lmod.griddata[i].dataid == '':
                self.lmod.griddata[i].dataid = i

        tmp = [i for i in set(self.lmod.griddata.values())]
        self.outdata['Raster'] = tmp

        return True

    def dict2lmod(self, indict, pre=''):
        """ routine to convert a dictionary to an lmod """
        lithkeys = indict[pre+'lithkeys']

        lmod = self.lmod

        lmod.gregional = indict[pre+'gregional']
        lmod.ght = indict[pre+'ght']
        lmod.mht = indict[pre+'mht']
        lmod.numx = indict[pre+'numx']
        lmod.numy = indict[pre+'numy']
        lmod.numz = indict[pre+'numz']
        lmod.dxy = indict[pre+'dxy']
        lmod.d_z = indict[pre+'d_z']
        lmod.lith_index = indict[pre+'lith_index']
        lmod.curprof = 0
        lmod.curlayer = 0
        lmod.xrange = np.array(indict[pre+'xrange']).tolist()
        lmod.yrange = np.array(indict[pre+'yrange']).tolist()
        lmod.zrange = np.array(indict[pre+'zrange']).tolist()
        if pre+'custprofx' in indict:
            lmod.custprofx = np.asscalar(indict[pre+'custprofx'])
        else:
            lmod.custprofx = {0: (lmod.xrange[0], lmod.xrange[1])}
        if pre+'custprofy' in indict:
            lmod.custprofy = np.asscalar(indict[pre+'custprofy'])
        else:
            lmod.custprofy = {0: (lmod.yrange[0], lmod.yrange[0])}

        lmod.mlut = np.asscalar(indict[pre+'mlut'])
        lmod.init_calc_grids()

        lmod.griddata = np.asscalar(indict[pre+'griddata'])

        for i in lmod.griddata:
            lmod.griddata[i].data = np.ma.array(lmod.griddata[i].data)

        # This gets rid of a legacy variable name
        for i in lmod.griddata:
            if not hasattr(lmod.griddata[i], 'dataid'):
                lmod.griddata[i].dataid = ''
            if hasattr(lmod.griddata[i], 'bandid'):
                if lmod.griddata[i].dataid == '':
                    lmod.griddata[i].dataid = lmod.griddata[i].bandid
                del lmod.griddata[i].bandid

        wktfin = None
        for i in lmod.griddata:
            wkt = lmod.griddata[i].wkt
            if wkt != '' and wkt is not None:
                wktfin = wkt

        if wktfin is not None:
            for i in lmod.griddata:
                wkt = lmod.griddata[i].wkt
                if wkt == '' or wkt is None:
                    lmod.griddata[i].wkt = wktfin

# Section to load lithologies.
        lmod.lith_list['Background'] = tensor3d.GeoData(self.parent)

        for itxt in lithkeys:
            if itxt != 'Background':
                lmod.lith_list[itxt] = tensor3d.GeoData(self.parent)

            lmod.lith_list[itxt].hintn = np.asscalar(indict[pre+itxt+'_hintn'])
            lmod.lith_list[itxt].finc = np.asscalar(indict[pre+itxt+'_finc'])
            lmod.lith_list[itxt].fdec = np.asscalar(indict[pre+itxt+'_fdec'])
            lmod.lith_list[itxt].zobsm = np.asscalar(indict[pre+itxt+'_zobsm'])
            lmod.lith_list[itxt].susc = np.asscalar(indict[pre+itxt+'_susc'])
            lmod.lith_list[itxt].mstrength = np.asscalar(
                indict[pre+itxt+'_mstrength'])
            lmod.lith_list[itxt].qratio = np.asscalar(
                indict[pre+itxt+'_qratio'])
            lmod.lith_list[itxt].minc = np.asscalar(indict[pre+itxt+'_minc'])
            lmod.lith_list[itxt].mdec = np.asscalar(indict[pre+itxt+'_mdec'])
            lmod.lith_list[itxt].density = np.asscalar(
                indict[pre+itxt+'_density'])
            lmod.lith_list[itxt].bdensity = np.asscalar(
                indict[pre+itxt+'_bdensity'])
            lmod.lith_list[itxt].lith_index = np.asscalar(
                indict[pre+itxt+'_lith_index'])
            lmod.lith_list[itxt].g_cols = np.asscalar(indict[pre+itxt+'_numx'])
            lmod.lith_list[itxt].g_rows = np.asscalar(indict[pre+itxt+'_numy'])
            lmod.lith_list[itxt].numz = np.asscalar(indict[pre+itxt+'_numz'])
            lmod.lith_list[itxt].g_dxy = np.asscalar(indict[pre+itxt+'_dxy'])
            lmod.lith_list[itxt].dxy = np.asscalar(indict[pre+itxt+'_dxy'])
            lmod.lith_list[itxt].d_z = np.asscalar(indict[pre+itxt+'_d_z'])
            lmod.lith_list[itxt].zobsm = np.asscalar(indict[pre+itxt+'_zobsm'])
            lmod.lith_list[itxt].zobsg = np.asscalar(indict[pre+itxt+'_zobsg'])
            lmod.lith_list[itxt].modified = True
            lmod.lith_list[itxt].set_xyz12()


class ExportMod3D(object):
    """ Export Data """
    def __init__(self, parent):
        self.ifile = ""
        self.name = "Import Data: "
        self.ext = ""
        self.pbar = None
        self.parent = parent
        self.indata = {}
        self.outdata = {}
        self.lmod = None
        if parent is not None:
            self.showtext = self.parent.showprocesslog
        else:
            self.showtext = print

    def run(self):
        """ Show Info """
        if 'Model3D' not in self.indata:
            self.parent.showprocesslog(
                'Error: You need to have a model first!')
            return

        for self.lmod in self.indata['Model3D']:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.parent, 'Save File', '.',
                'npz (*.npz);;shapefile (*.shp);;kmz (*.kmz);;csv (*.csv)')

            if filename == '':
                return

            os.chdir(filename.rpartition('/')[0])
            self.ifile = str(filename)
            self.ext = filename[-3:]

            self.showtext('Saving '+self.ifile+'...')

        # Pop up save dialog box
            if self.ext == 'npz':
                self.savemodel()
            if self.ext == 'kmz':
                self.mod3dtokmz()
            if self.ext == 'shp':
                self.mod3dtoshp()
            if self.ext == 'csv':
                self.mod3dtocsv()

    def savemodel(self):
        """ Save model """
# Open file
        filename = self.ifile

# Construct output dictionary
        outdict = {}
        outdict = self.lmod2dict(outdict)

# Save data
        try:
            np.savez_compressed(filename, **outdict)
            self.showtext('Model save complete!')
        except:
            self.showtext('ERROR! Model save failed!')

    def lmod2dict(self, outdict, pre=''):
        """ place lmod in dictionary """

        outdict[pre+"gregional"] = self.lmod.gregional
        outdict[pre+"ght"] = self.lmod.ght
        outdict[pre+"mht"] = self.lmod.mht
        outdict[pre+"numx"] = self.lmod.numx
        outdict[pre+"numy"] = self.lmod.numy
        outdict[pre+"numz"] = self.lmod.numz
        outdict[pre+"dxy"] = self.lmod.dxy
        outdict[pre+"d_z"] = self.lmod.d_z
        outdict[pre+"lith_index"] = self.lmod.lith_index
        outdict[pre+"xrange"] = self.lmod.xrange
        outdict[pre+"yrange"] = self.lmod.yrange
        outdict[pre+"zrange"] = self.lmod.zrange
        outdict[pre+"mlut"] = self.lmod.mlut
        outdict[pre+"griddata"] = self.lmod.griddata
        outdict[pre+"custprofx"] = self.lmod.custprofx
        outdict[pre+"custprofy"] = self.lmod.custprofy

# Section to save lithologies.
        outdict[pre+"lithkeys"] = list(self.lmod.lith_list.keys())

        for i in self.lmod.lith_list.items():
            curkey = i[0]
            outdict[pre+curkey+"_hintn"] = i[1].hintn
            outdict[pre+curkey+"_finc"] = i[1].finc
            outdict[pre+curkey+"_fdec"] = i[1].fdec
            outdict[pre+curkey+"_zobsm"] = i[1].zobsm
            outdict[pre+curkey+"_susc"] = i[1].susc
            outdict[pre+curkey+"_mstrength"] = i[1].mstrength
            outdict[pre+curkey+"_qratio"] = i[1].qratio
            outdict[pre+curkey+"_minc"] = i[1].minc
            outdict[pre+curkey+"_mdec"] = i[1].mdec
            outdict[pre+curkey+"_density"] = i[1].density
            outdict[pre+curkey+"_bdensity"] = i[1].bdensity
            outdict[pre+curkey+"_lith_index"] = i[1].lith_index
            outdict[pre+curkey+"_numx"] = i[1].g_cols
            outdict[pre+curkey+"_numy"] = i[1].g_rows
            outdict[pre+curkey+"_numz"] = i[1].numz
            outdict[pre+curkey+"_dxy"] = i[1].g_dxy
            outdict[pre+curkey+"_d_z"] = i[1].d_z
            outdict[pre+curkey+"_zobsm"] = i[1].zobsm
            outdict[pre+curkey+"_zobsg"] = i[1].zobsg
            outdict[pre+curkey+"_x12"] = i[1].x12
            outdict[pre+curkey+"_y12"] = i[1].y12
            outdict[pre+curkey+"_z12"] = i[1].z12

        return outdict

    def mod3dtocsv(self):
        """ Saves the 3D model in a csv file. """
        self.showtext('csv export starting...')

        self.lmod.update_lith_list_reverse()
        lithname = self.lmod.lith_list_reverse.copy()
        lithlist = self.lmod.lith_list.copy()

        tmp = []
        ltmp = []
        for i in range(self.lmod.numx):
            x = self.lmod.xrange[0]+i*self.lmod.dxy
            for j in range(self.lmod.numy):
                y = self.lmod.yrange[0]+j*self.lmod.dxy
                for k in range(self.lmod.numz):
                    z = self.lmod.zrange[1]-k*self.lmod.d_z
                    lith = self.lmod.lith_index[i, j, k]
                    if lith > -1:
                        name = lithname[lith]
                        dens = lithlist[name].density
                        susc = lithlist[name].susc
                        tmp.append([x, y, z, dens, susc, lith])
                        ltmp.append(lithname[lith])

        tmp = np.array(tmp)
        ltmp = np.array(ltmp)
        stmp = np.zeros(len(tmp), dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
                                         ('dens', 'f4'), ('susc', 'f4'),
                                         ('lith', 'i4'), ('lithname', 'a24')])

        stmp['x'] = tmp[:, 0]
        stmp['y'] = tmp[:, 1]
        stmp['z'] = tmp[:, 2]
        stmp['dens'] = tmp[:, 3]
        stmp['susc'] = tmp[:, 4]
        stmp['lith'] = tmp[:, 5]
        stmp['lithname'] = ltmp

        head = 'X, Y, Z, Density, Susceptibility, Lithology Code, Lithology'
        np.savetxt(self.ifile, stmp, fmt="%f, %f, %f, %f, %f, %i, %s",
                   header=head)

        self.showtext('csv export complete!')

    def mod3dtokmz(self):
        """ Saves the 3D model and grids in a kmz file.
        Note:
        Only the boundary of the area is in degrees. The actual coordinates
        are still in meters.
        """

        mvis_3d = mvis3d.Mod3dDisplay()
        mvis_3d.lmod1 = self.lmod

        rev = 1  # should be 1 normally

        xrng = np.array(self.lmod.xrange, dtype=float)
        yrng = np.array(self.lmod.yrange, dtype=float)
        zrng = np.array(self.lmod.zrange, dtype=float)

        if 'Raster' in self.indata:
            wkt = self.indata['Raster'][0].wkt
        else:
            wkt = ''
        prjkmz = Exportkmz(wkt)
        tmp = prjkmz.exec_()

        if tmp == 0:
            return

        if prjkmz.proj.wkt == '':
            QtWidgets.QMessageBox.warning(QtWidgets.QMessageBox(), 'Warning',
                                          ' You need a projection!',
                                          QtWidgets.QMessageBox.Ok,
                                          QtWidgets.QMessageBox.Ok)
            return

        smooth = prjkmz.checkbox_smooth.isChecked()

        orig_wkt = prjkmz.proj.wkt
        orig = osr.SpatialReference()
        orig.ImportFromWkt(orig_wkt)

        targ = osr.SpatialReference()
        targ.SetWellKnownGeogCS('WGS84')
        prj = osr.CoordinateTransformation(orig, targ)

        res = prj.TransformPoint(xrng[0], yrng[0])
        lonwest, latsouth = res[0], res[1]
        res = prj.TransformPoint(xrng[1], yrng[1])
        loneast, latnorth = res[0], res[1]

# Get Save Name
        filename = self.ifile

        self.showtext('kmz export starting...')

# Move to 3d model tab to update the model stuff
        self.showtext('updating 3d model...')

        mvis_3d.spacing = [self.lmod.dxy, self.lmod.dxy, self.lmod.d_z]
        mvis_3d.origin = [xrng[0], yrng[0], zrng[0]]
        mvis_3d.gdata = self.lmod.lith_index[::1, ::1, ::-1]
        itmp = np.sort(np.unique(self.lmod.lith_index))
        itmp = itmp[itmp > 0]
        tmp = np.ones((255, 4))*255
        for i in itmp:
            tmp[i, :3] = self.lmod.mlut[i]
        mvis_3d.lut = tmp
        mvis_3d.update_model(smooth)

        self.showtext('creating kmz file')
        heading = str(0.)
        tilt = str(45.)  # angle from vertical
        lat = str(np.mean([latsouth, latnorth]))  # coord of object
        lon = str(np.mean([lonwest, loneast]))  # coord of object
        rng = str(max(xrng.ptp(), yrng.ptp(), zrng.ptp()))  # range to object
        alt = str(0)  # alt of object eye is looking at (meters)
        lato = str(latsouth)
        lono = str(lonwest)

# update colors
        self.lmod.update_lith_list_reverse()

        dockml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\r\n'
            '<kml xmlns="http://www.opengis.net/kml/2.2" '
            'xmlns:gx="http://www.google.com/kml/ext/2.2">\r\n'
            '\r\n'
            '  <Folder>\r\n'
            '    <name>Lithological Model</name>\r\n'
            '    <description>Created with PyGMI</description>\r\n'
            '    <visibility>1</visibility>\r\n'
            '    <LookAt>\r\n'
            '      <heading>' + heading + '</heading>\r\n'
            '      <tilt>' + tilt + '</tilt>\r\n'
            '      <latitude>' + lat + '</latitude>\r\n'
            '      <longitude>' + lon + '</longitude>\r\n'
            '      <range>' + rng + '</range>\r\n'
            '      <altitude>' + alt + '</altitude>\r\n'
            '    </LookAt>\r\n')

        mvis_3d.update_for_kmz()

        modeldae = []
        lkey = list(mvis_3d.faces.keys())
        lkey.pop(lkey.index(0))
        lithcnt = -1

        alt = str(0)
        for lith in lkey:
            faces = np.array(mvis_3d.gfaces[lith])
            # Google wants the model to have origin (0,0)

            points = mvis_3d.gpoints[lith]

            if points == []:
                continue

            points -= mvis_3d.origin

            x = points[:, 0]
            y = points[:, 1]
            earthrad = 6378137.
            z = earthrad-np.sqrt(earthrad**2-(x**2+y**2))
            points[:, 2] -= z

            if rev == -1:
                points += [xrng.ptp(), yrng.ptp(), 0]

            norm = np.abs(mvis_3d.gnorms[lith])
            clrtmp = np.array(self.lmod.mlut[lith])/255.
            curmod = self.lmod.lith_list_reverse[lith]

            if len(points) > 60000:
                self.showtext(curmod + ' has too many points (' +
                              str(len(points))+'). Not exported')
                points = points[:60000]
                norm = norm[:60000]
                faces = faces[faces.max(1) < 60000]

            lithcnt += 1

            dockml += (
                '    <Placemark>\r\n'
                '      <name>' + curmod + '</name>\r\n'
                '      <description></description>\r\n'
                '      <Style id="default"/>\r\n'
                '      <Model>\r\n'
                '        <altitudeMode>absolute</altitudeMode>\r\n'
                '        <Location>\r\n'
                '          <latitude>' + lato + '</latitude>\r\n'
                '          <longitude>' + lono + '</longitude>\r\n'
                '          <altitude>' + str(alt) + '</altitude>\r\n'
                '        </Location>\r\n'
                '        <Orientation>\r\n'
                '          <heading>0</heading>\r\n'
                '          <tilt>0</tilt>\r\n'
                '          <roll>0</roll>\r\n'
                '        </Orientation>\r\n'
                '        <Scale>\r\n'
                '          <x>1</x>\r\n'
                '          <y>1</y>\r\n'
                '          <z>1</z>\r\n'
                '        </Scale>\r\n'
                '        <Link>\r\n'
                '          <href>models/mod3d' + str(lithcnt) +
                '.dae</href>\r\n'
                '        </Link>\r\n'
                '      </Model>\r\n'
                '    </Placemark>\r\n')

            position = str(points.flatten().tolist())
            position = position.replace('[', '')
            position = position.replace(']', '')
            position = position.replace(',', '')
            vertex = str(faces.flatten().tolist())
            vertex = vertex.replace('[', '')
            vertex = vertex.replace(']', '')
            vertex = vertex.replace(',', '')
            normal = str(norm.flatten().tolist())
            normal = normal.replace('[', '')
            normal = normal.replace(']', '')
            normal = normal.replace(',', '')
            color = str(clrtmp.flatten().tolist())
            color = color.replace('[', '')
            color = color.replace(']', '')
            color = color.replace(',', '')

            modeldae.append(
                '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\r\n'
                '<COLLADA xmlns="http://www.collada.org/2005'
                '/11/COLLADASchema" '
                'version="1.4.1">\r\n'
                '  <asset>\r\n'
                '    <contributor>\r\n'
                '      <authoring_tool>PyGMI</authoring_tool>\r\n'
                '    </contributor>\r\n'
                '    <created>2012-03-01T10:36:38Z</created>\r\n'
                '    <modified>2012-03-01T10:36:38Z</modified>\r\n'
                '    <up_axis>Z_UP</up_axis>\r\n'
                '  </asset>\r\n'
                '  <library_visual_scenes>\r\n'
                '    <visual_scene id="ID1">\r\n'
                '      <node name="SketchUp">\r\n'
                '        <node id="ID2" name="instance_0">\r\n'
                '          <matrix>    1 0 0 0 \r\n'
                '                      0 1 0 0 \r\n'
                '                      0 0 1 0 \r\n'
                '                      0 0 0 1 \r\n'
                '          </matrix>\r\n'
                '          <instance_node url="#ID3" />\r\n'
                '        </node>\r\n'
                '      </node>\r\n'
                '    </visual_scene>\r\n'
                '  </library_visual_scenes>\r\n'
                '  <library_nodes>\r\n'
                '    <node id="ID3" name="skp489E">\r\n'
                '      <instance_geometry url="#ID4">\r\n'
                '        <bind_material>\r\n'
                '          <technique_common>\r\n'
                '            <instance_material symbol="Material2"'
                ' target="#ID5">\r\n'
                '              <bind_vertex_input semantic="UVSET0" '
                'input_semantic="TEXCOORD" input_set="0" />\r\n'
                '            </instance_material>\r\n'
                '          </technique_common>\r\n'
                '        </bind_material>\r\n'
                '      </instance_geometry>\r\n'
                '    </node>\r\n'
                '  </library_nodes>\r\n'
                '  <library_geometries>\r\n'
                '    <geometry id="ID4">\r\n'
                '      <mesh>\r\n'
                '        <source id="ID7">\r\n'
                '          <float_array id="ID10" count="' +
                str(points.size) + '">' + position +
                '          </float_array>\r\n'
                '          <technique_common>\r\n'
                '            <accessor count="' + str(points.shape[0]) +
                '" source="#ID10" stride="3">\r\n'
                '              <param name="X" type="float" />\r\n'
                '              <param name="Y" type="float" />\r\n'
                '              <param name="Z" type="float" />\r\n'
                '            </accessor>\r\n'
                '          </technique_common>\r\n'
                '        </source>\r\n'
                '        <source id="ID8">\r\n'
                '          <float_array id="ID11" count="' + str(norm.size) +
                '">' + normal +
                '          </float_array>\r\n'
                '          <technique_common>\r\n'
                '            <accessor count="' + str(norm.shape[0]) +
                '" source="#ID11" stride="3">\r\n'
                '              <param name="X" type="float" />\r\n'
                '              <param name="Y" type="float" />\r\n'
                '              <param name="Z" type="float" />\r\n'
                '            </accessor>\r\n'
                '          </technique_common>\r\n'
                '        </source>\r\n'
                '        <vertices id="ID9">\r\n'
                '          <input semantic="POSITION" source="#ID7" />\r\n'
                '          <input semantic="NORMAL" source="#ID8" />\r\n'
                '        </vertices>\r\n'
                '        <triangles count="' + str(faces.shape[0]) +
                '" material="Material2">\r\n'
                '          <input offset="0" semantic="VERTEX" '
                'source="#ID9" />\r\n'
                '          <p>' + vertex + '</p>\r\n'
                '        </triangles>\r\n'
                '      </mesh>\r\n'
                '    </geometry>\r\n'
                '  </library_geometries>\r\n'
                '  <library_materials>\r\n'
                '    <material id="ID5" name="__auto_">\r\n'
                '      <instance_effect url="#ID6" />\r\n'
                '    </material>\r\n'
                '  </library_materials>\r\n'
                '  <library_effects>\r\n'
                '    <effect id="ID6">\r\n'
                '      <profile_COMMON>\r\n'
                '        <technique sid="COMMON">\r\n'
                '          <lambert>\r\n'
                '            <diffuse>\r\n'
                '              <color>' + color + '</color>\r\n'
                '            </diffuse>\r\n'
                '          </lambert>\r\n'
                '        </technique>\r\n'
                '        <extra> />\r\n'
                '          <technique profile="GOOGLEEARTH"> />\r\n'
                '            <double_sided>1</double_sided> />\r\n'
                '          </technique> />\r\n'
                '        </extra> />\r\n'
                '      </profile_COMMON>\r\n'
                '    </effect>\r\n'
                '  </library_effects>\r\n'
                '  <scene>\r\n'
                '    <instance_visual_scene url="#ID1" />\r\n'
                '  </scene>\r\n'
                '</COLLADA>')

        zfile = zipfile.ZipFile(filename, 'w')
        for i, _ in enumerate(modeldae):
            zfile.writestr('models\\mod3d'+str(i)+'.dae', modeldae[i])

        for i in self.lmod.griddata:
            x_1 = self.lmod.griddata[i].tlx
            x_2 = x_1 + self.lmod.griddata[i].xdim*self.lmod.griddata[i].cols
            y_2 = self.lmod.griddata[i].tly
            y_1 = y_2 - self.lmod.griddata[i].ydim*self.lmod.griddata[i].rows

            res = prj.TransformPoint(x_1, y_1)
            lonwest, latsouth = res[0], res[1]
            res = prj.TransformPoint(x_2, y_2)
            loneast, latnorth = res[0], res[1]

            dockml += (
                '    <GroundOverlay>\r\n'
                '        <name>' + i + '</name>\r\n'
                '        <description></description>\r\n'
                '        <Icon>\r\n'
                '            <href>models/' + i + '.png</href>\r\n'
                '        </Icon>\r\n'
                '        <LatLonBox>\r\n'
                '            <north>' + str(latnorth) + '</north>\r\n'
                '            <south>' + str(latsouth) + '</south>\r\n'
                '            <east>' + str(loneast) + '</east>\r\n'
                '            <west>' + str(lonwest) + '</west>\r\n'
                '            <rotation>0.0</rotation>\r\n'
                '        </LatLonBox>\r\n'
                '    </GroundOverlay>\r\n')

            fig = plt.figure('tmp930', frameon=False)
            ax1 = plt.Axes(fig, [0., 0., 1., 1.])
            ax1.set_axis_off()
            fig.add_axes(ax1)

            plt.imshow(self.lmod.griddata[i].data,
                       extent=(lonwest, loneast, latsouth, latnorth),
                       aspect='auto',
                       interpolation='nearest')
            plt.savefig('tmp930.png')

            zfile.write('tmp930.png', 'models\\'+i+'.png')
            os.remove('tmp930.png')

        dockml += (
            '  </Folder>\r\n'
            '  \r\n'
            '  </kml>')

        zfile.writestr('doc.kml', dockml)

        zfile.close()
        self.showtext('kmz export complete!')

    def mod3dtoshp(self):
        """ Saves the 3D model and grids in a shapefile file.
        Note:
        Only the boundary of the area is in degrees. The actual coordinates
        are still in meters.
        """

        mvis_3d = mvis3d.Mod3dDisplay()
        mvis_3d.lmod1 = self.lmod

        xrng = np.array(self.lmod.xrange, dtype=float)
        yrng = np.array(self.lmod.yrange, dtype=float)
        zrng = np.array(self.lmod.zrange, dtype=float)

        if 'Raster' in self.indata:
            wkt = self.indata['Raster'][0].wkt
        else:
            wkt = ''
        prjkmz = Exportkmz(wkt)
        tmp = prjkmz.exec_()

        if tmp == 0:
            return

        smooth = prjkmz.checkbox_smooth.isChecked()

        self.showtext('shapefile export starting...')

# Move to 3d model tab to update the model stuff
        if smooth is True:
            self.showtext('updating and smoothing 3d model...')
        else:
            self.showtext('updating 3d model...')

        mvis_3d.spacing = [self.lmod.dxy, self.lmod.dxy, self.lmod.d_z]
        mvis_3d.origin = [xrng[0], yrng[0], zrng[0]]
        mvis_3d.gdata = self.lmod.lith_index[::1, ::1, ::-1]
        itmp = np.sort(np.unique(self.lmod.lith_index))
        itmp = itmp[itmp > 0]
        tmp = np.ones((255, 4))*255
        for i in itmp:
            tmp[i, :3] = self.lmod.mlut[i]
        mvis_3d.lut = tmp
        mvis_3d.update_model(smooth)

        self.showtext('creating shapefile file')

        driver = ogr.GetDriverByName('ESRI Shapefile')

# update colors
        self.lmod.update_lith_list_reverse()

        mvis_3d.update_for_kmz()

        lkey = list(mvis_3d.faces.keys())
        lkey.pop(lkey.index(0))

        for lith in lkey:
            lithtext = mvis_3d.lmod1.lith_list_reverse[lith]
            lithsusc = self.lmod.lith_list[lithtext].susc
            lithdens = self.lmod.lith_list[lithtext].density
            self.showtext(' '+lithtext)

            faces = np.array(mvis_3d.gfaces[lith])

            if faces.size == 0:
                continue

            ifile = self.ifile[:-4]+'_'+re.sub(r'[^A-Za-z]+', '_',
                                               lithtext)+'.shp'
            datasource = driver.CreateDataSource(ifile)
            layer = datasource.CreateLayer('Model',
                                           geom_type=ogr.wkbMultiPolygon25D)

            layer.CreateField(ogr.FieldDefn("Lithology", ogr.OFTString))
            layer.CreateField(ogr.FieldDefn("Susc", ogr.OFTReal))
            layer.CreateField(ogr.FieldDefn("Density", ogr.OFTReal))

            points = mvis_3d.gpoints[lith]

            for f in faces:
                multipolygon = ogr.Geometry(ogr.wkbMultiPolygon25D)
                tmp = points[f]

                ring1 = ogr.Geometry(ogr.wkbLinearRing)
                ring1.AddPoint(tmp[0, 0], tmp[0, 1], tmp[0, 2])
                ring1.AddPoint(tmp[1, 0], tmp[1, 1], tmp[1, 2])
                ring1.AddPoint(tmp[2, 0], tmp[2, 1], tmp[2, 2])
                ring1.AddPoint(tmp[0, 0], tmp[0, 1], tmp[0, 2])

            # Create polygon #1
                poly1 = ogr.Geometry(ogr.wkbPolygon25D)
                poly1.AddGeometry(ring1)
                multipolygon.AddGeometry(poly1)

                ring1 = None
                poly1 = None

                feature = ogr.Feature(layer.GetLayerDefn())
                feature.SetGeometry(multipolygon)
                feature.SetField("Lithology", lithtext)
                feature.SetField("Susc", lithsusc)
                feature.SetField("Density", lithdens)
                layer.CreateFeature(feature)

                multipolygon = None

            # flush memory
            layer = None
            feature = None
            datasource = None

        self.showtext('shapefile export complete!')


class Exportkmz(QtWidgets.QDialog):
    """ Class to call up a dialog """
    def __init__(self, wkt, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.checkbox_smooth = QtWidgets.QCheckBox()
        self.proj = dp.GroupProj('Confirm Model Projection')
        self.proj.set_current(wkt)

        self.setupui()

    def setupui(self):
        """ Setup UI """

        gridlayout = QtWidgets.QGridLayout(self)
        buttonbox = QtWidgets.QDialogButtonBox()
        helpdocs = menu_default.HelpButton('pygmi.pfmod.iodefs.exportkmz')

        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setStandardButtons(buttonbox.Cancel | buttonbox.Ok)

        gridlayout.addWidget(self.proj, 0, 0, 1, 2)
        gridlayout.addWidget(self.checkbox_smooth, 1, 0, 1, 2)
        gridlayout.addWidget(helpdocs, 2, 0, 1, 1)
        gridlayout.addWidget(buttonbox, 2, 1, 1, 1)

        self.setWindowTitle("Google Earth kmz Export")
        self.checkbox_smooth.setText("Smooth Model")

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)


class ImportPicture(QtWidgets.QDialog):
    """ Class to call up a dialog """
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.parent = parent
        self.lmod = LithModel()

        self.ifile = ""
        self.name = "Import 3D Model: "
        self.ext = ""
        self.pbar = None
        self.indata = {}
        self.outdata = {}
        self.grid = None

        self.dsb_picimp_west = QtWidgets.QDoubleSpinBox()
        self.dsb_picimp_east = QtWidgets.QDoubleSpinBox()
        self.dsb_picimp_depth = QtWidgets.QDoubleSpinBox()
        self.rb_picimp_westeast = QtWidgets.QRadioButton()
        self.rb_picimp_southnorth = QtWidgets.QRadioButton()
        self.dsb_picimp_maxalt = QtWidgets.QDoubleSpinBox()

        self.setupui()

        self.min_coord = None
        self.max_coord = None
        self.max_alt = None
        self.min_alt = None
        self.is_eastwest = None

        self.lmod2var()

    def setupui(self):
        """ Setup UI """
        groupbox = QtWidgets.QGroupBox()
        gridlayout_2 = QtWidgets.QGridLayout(self)
        gridlayout_3 = QtWidgets.QGridLayout(groupbox)
        buttonbox = QtWidgets.QDialogButtonBox()
        helpdocs = menu_default.HelpButton('pygmi.pfmod.iodefs.importpicture')

        label = QtWidgets.QLabel()
        label_2 = QtWidgets.QLabel()
        label_3 = QtWidgets.QLabel()
        label_4 = QtWidgets.QLabel()
        label_5 = QtWidgets.QLabel()

        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setStandardButtons(buttonbox.Cancel | buttonbox.Ok)

        self.dsb_picimp_west.setDecimals(6)
        self.dsb_picimp_west.setMinimum(-999999999.0)
        self.dsb_picimp_west.setMaximum(999999999.0)
        self.dsb_picimp_west.setProperty("value", 0.0)
        self.dsb_picimp_east.setDecimals(6)
        self.dsb_picimp_east.setMinimum(-999999999.0)
        self.dsb_picimp_east.setMaximum(999999999.0)
        self.dsb_picimp_east.setProperty("value", 1000.0)
        self.dsb_picimp_depth.setDecimals(6)
        self.dsb_picimp_depth.setMinimum(0.0)
        self.dsb_picimp_depth.setMaximum(999999999.0)
        self.dsb_picimp_depth.setProperty("value", 1000.0)
        self.rb_picimp_westeast.setChecked(True)
        self.dsb_picimp_maxalt.setDecimals(6)
        self.dsb_picimp_maxalt.setMinimum(-999999999.0)
        self.dsb_picimp_maxalt.setMaximum(999999999.0)
        self.dsb_picimp_maxalt.setProperty("value", 1000.0)

        self.setWindowTitle("Profile Picture Importer")
        groupbox.setTitle("Profile Coordinates")
        self.rb_picimp_westeast.setText("Profile is from West to East")
        self.rb_picimp_southnorth.setText("Profile is from South to North")
        label.setText("West/South Coordinate")
        label_2.setText("East/North Coordinate")
        label_3.setText("Depth")
        label_4.setText("Maximum Altitude")
        label_5.setText('Press Cancel if you wish to connect profile '
                        'information from a 3D model')

        gridlayout_2.addWidget(groupbox, 0, 0, 1, 2)
        gridlayout_2.addWidget(label_5, 1, 0, 1, 2)
        gridlayout_2.addWidget(helpdocs, 2, 0, 1, 1)
        gridlayout_2.addWidget(buttonbox, 2, 1, 1, 1)

        gridlayout_3.addWidget(self.rb_picimp_westeast, 0, 0, 1, 1)
        gridlayout_3.addWidget(self.rb_picimp_southnorth, 1, 0, 1, 1)
        gridlayout_3.addWidget(label, 2, 0, 1, 1)
        gridlayout_3.addWidget(self.dsb_picimp_west, 2, 1, 1, 1)
        gridlayout_3.addWidget(label_2, 4, 0, 1, 1)
        gridlayout_3.addWidget(self.dsb_picimp_east, 4, 1, 1, 1)
        gridlayout_3.addWidget(label_4, 5, 0, 1, 1)
        gridlayout_3.addWidget(self.dsb_picimp_maxalt, 5, 1, 1, 1)
        gridlayout_3.addWidget(label_3, 6, 0, 1, 1)
        gridlayout_3.addWidget(self.dsb_picimp_depth, 6, 1, 1, 1)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.rb_picimp_westeast.clicked.connect(self.lmod2var)
        self.rb_picimp_southnorth.clicked.connect(self.lmod2var)

    def lmod2var(self):
        """ lmod 2 var """
        self.is_eastwest = self.rb_picimp_westeast.isChecked()
        self.min_alt, self.max_alt = self.lmod.zrange

        if self.is_eastwest:
            self.min_coord, self.max_coord = self.lmod.xrange
        else:
            self.min_coord, self.max_coord = self.lmod.yrange

        self.update_win()

    def update_var(self):
        """ Updates the values """
        self.min_coord = self.dsb_picimp_west.value()
        self.max_coord = self.dsb_picimp_east.value()
        self.max_alt = self.dsb_picimp_maxalt.value()
        self.min_alt = self.max_alt - self.dsb_picimp_depth.value()
        self.is_eastwest = self.rb_picimp_westeast.isChecked()

        if self.is_eastwest:
            self.grid.dataid = r'West to East'
        else:
            self.grid.dataid = r'South to North'

        self.grid.dataid = "Image"
        self.grid.rows = self.grid.data.shape[0]
        self.grid.cols = self.grid.data.shape[1]
        self.grid.nullvalue = 0

        self.grid.xdim = (self.max_coord-self.min_coord)/self.grid.cols
        self.grid.ydim = (self.max_alt-self.min_alt)/self.grid.rows
        self.grid.tlx = self.min_coord
        self.grid.tly = self.max_alt

    def update_win(self):
        """ Updates the window values """
        self.dsb_picimp_west.setValue(self.min_coord)
        self.dsb_picimp_east.setValue(self.max_coord)
        self.dsb_picimp_maxalt.setValue(self.max_alt)
        self.dsb_picimp_depth.setValue(self.max_alt-self.min_alt)

    def settings(self):
        """ Load GeoTiff """
        if 'Model3D' in self.indata:
            self.lmod = self.indata['Model3D'][0]
            self.lmod2var()

        temp = self.exec_()
        if temp == 0:
            return False

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, 'Open File', '.', '*.jpg *.tif *.bmp')

        if filename == '':
            return False
        os.chdir(filename.rpartition('/')[0])

        self.ifile = filename

        data = mpimg.imread(filename)

        self.grid = Data()
        self.grid.data = data

        if (self.dsb_picimp_west.value() >=
                self.dsb_picimp_east.value()):
            return
        if self.dsb_picimp_depth.value() == 0.0:
            return

        self.update_var()
        self.outdata['ProfPic'] = [self.grid]

        return True


class MessageCombo(QtWidgets.QDialog):
    """
    Message combo box.

    Attributes
    ----------
    parent : parent
        reference to the parent routine
    """
    def __init__(self, combotext, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.indata = {}
        self.outdata = {}
        self.parent = parent

        self.master = QtWidgets.QComboBox()
        self.master.addItems(combotext)

        self.setupui()

    def setupui(self):
        """ Setup UI """
        gridlayout_main = QtWidgets.QGridLayout(self)
        buttonbox = QtWidgets.QDialogButtonBox()
        label_master = QtWidgets.QLabel()

        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setCenterButtons(True)
        buttonbox.setStandardButtons(buttonbox.Ok)

        self.setWindowTitle("Model Choice")
        label_master.setText("Choose Model:")

        gridlayout_main.addWidget(label_master, 0, 0, 1, 1)
        gridlayout_main.addWidget(self.master, 0, 1, 1, 1)
        gridlayout_main.addWidget(buttonbox, 3, 1, 1, 3)

        buttonbox.accepted.connect(self.accept)

    def acceptall(self):
        """ accept """
        return self.master.currentText()


def gtiff(filename):
    """ Utility to import geotiffs """

    dataset = gdal.Open(filename, gdal.GA_ReadOnly)
    nred = dataset.GetRasterBand(1).ReadAsArray()
    ngreen = dataset.GetRasterBand(2).ReadAsArray()
    nblue = dataset.GetRasterBand(3).ReadAsArray()
    itmp = np.uint32(nred*65536+ngreen*256+nblue+int('FF000000', 16))

    gtr = dataset.GetGeoTransform()
    dat = [Data()]

    dat[0].tlx = gtr[0]
    dat[0].tly = gtr[3]
    dat[0].dataid = "Image"
    dat[0].rows = dataset.RasterYSize
    dat[0].cols = dataset.RasterXSize
    dat[0].xdim = abs(gtr[1])
    dat[0].ydim = abs(gtr[5])
    dat[0].data = np.ma.array(itmp)
    dat[0].nullvalue = np.nan  # This was erread.nullvalue, is changed above

    return dat
