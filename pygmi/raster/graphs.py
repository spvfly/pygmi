# -----------------------------------------------------------------------------
# Name:        raster/graphs.py (part of PyGMI)
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
"""
Plot Raster Data

This module provides a variety of methods to plot raster data via the context
menu. The following are supported:

 * Correlation coefficients
 * Images
 * Surfaces
 * Histograms
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore
import matplotlib.cm as cm
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as \
    NavigationToolbar
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import axes3d


class MyMplCanvas(FigureCanvas):
    """
    Canvas for the actual plot

    Attributes
    ----------
    axes : matplotlib subplot
    parent : parent
        reference to the parent routine
    """
    def __init__(self, parent=None):
        fig = Figure()
        self.axes = fig.add_subplot(111)
        self.parent = parent

        FigureCanvas.__init__(self, fig)

    def update_pcolor(self, data1, dmat):
        """
        Update the correlation coefficient plot

        Parameters
        ----------
        data1 : PyGMI raster Data
            raster dataset to be used in contouring
        dmat : numpy array
            dummy matrix of numbers to be plotted using pcolor
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.pcolor(dmat)
        self.axes.axis('scaled')
        self.axes.set_title('Correlation Coefficients')
        for i in range(len(data1)):
            for j in range(len(data1)):
                self.axes.text(i + .1, j + .4, format(float(dmat[i, j]),
                                                      '4.2f'))
        dat_mat = [i.dataid for i in data1]
        self.axes.set_xticks(np.array(list(range(len(data1)))) + .5)

        self.axes.set_xticklabels(dat_mat, rotation='vertical')
        self.axes.set_yticks(np.array(list(range(len(data1)))) + .5)

        self.axes.set_yticklabels(dat_mat, rotation='horizontal')
        self.axes.set_xlim(0, len(data1))
        self.axes.set_ylim(0, len(data1))

        self.figure.tight_layout()
        self.figure.canvas.draw()

    def update_raster(self, data1, data2=None):
        """
        Update the raster plot

        Parameters
        ----------
        data1 : PyGMI raster Data
            raster dataset to be used in contouring
        data2 : PyGMI point PData
            points to be plotted over raster image
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)

        extent = (data1.tlx, data1.tlx + data1.cols * data1.xdim,
                  data1.tly - data1.rows * data1.ydim, data1.tly)

        rdata = self.axes.imshow(data1.data, extent=extent,
                                 interpolation='nearest')

        cbar = self.figure.colorbar(rdata)
        try:
            cbar.set_label(data1.units)
        except AttributeError:
            pass
        self.axes.set_xlabel("Eastings")
        self.axes.set_ylabel("Northings")

        tmp = self.axes.get_yticks()
        self.axes.set_yticklabels(tmp, rotation='horizontal')
        tmp = self.axes.get_xticks()
        self.axes.set_xticklabels(tmp, rotation='vertical')

        self.figure.tight_layout()
        self.figure.canvas.draw()

    def update_rgb(self, data1):
        """
        Update the RGB plot

        Parameters
        ----------
        data1 : PyGMI raster Data
            raster dataset to be used
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)

        self.axes.imshow(data1.data)

        self.figure.tight_layout()
        self.figure.canvas.draw()

    def update_hexbin(self, data1, data2):
        """
        Update the hexbin plot

        Parameters
        ----------
        data1 : PyGMI raster Data
            raster dataset to be used
        data2 : PyGMI raster Data
            raster dataset to be used
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        x = data1.copy()
        y = data2.copy()
        msk = np.logical_or(x.mask, y.mask)
        x.mask = msk
        y.mask = msk
        x = x.compressed()
        y = y.compressed()

        xmin = x.min()
        xmax = x.max()
        ymin = y.min()
        ymax = y.max()

        hbin = self.axes.hexbin(x, y, bins='log')
        self.axes.axis([xmin, xmax, ymin, ymax])
        self.axes.set_title('Hexbin Plot')
        cbar = self.figure.colorbar(hbin)
        cbar.set_label('log10(N)')

        self.figure.tight_layout()
        self.figure.canvas.draw()

    def update_wireframe(self, data):
        """
        Update the surface wireframe plot

        Parameters
        ----------
        data : PyGMI raster Data
            raster dataset to be used
        """

        x = data.tlx+np.arange(data.cols)*data.xdim+data.xdim/2
        y = data.tly-np.arange(data.rows)*data.ydim-data.ydim/2
        x, y = np.meshgrid(x, y)
        z = data.data.copy()
        if not np.ma.is_masked(z):
            z = np.ma.array(z)

        x = np.ma.array(x, mask=z.mask)
        y = np.ma.array(y, mask=z.mask)

        cmap = cm.jet

        norml = mcolors.Normalize(vmin=z.min(), vmax=z.max())

        z.set_fill_value(np.nan)
        z = z.filled()

        self.figure.clear()
        self.axes = self.figure.add_subplot(111, projection='3d')
        ax1 = self.axes

        surf = ax1.plot_surface(x, y, z, cmap=cmap, linewidth=0.1, norm=norml,
                                vmin=z.min(), vmax=z.max(), shade=False,
                                antialiased=False)
        self.figure.colorbar(surf)

        ax1.set_title('')
        ax1.set_xlabel("X")
        ax1.set_ylabel("Y")
        ax1.set_zlabel("Z")

        self.figure.canvas.draw()

    def update_hist(self, data1):
        """
        Update the hiostogram plot

        Parameters
        ----------
        data1 : PyGMI raster Data
            raster dataset to be used
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)

        dattmp = data1.data[data1.data.mask == 0].flatten()
        self.axes.hist(dattmp, 50)
        self.axes.set_title(data1.dataid, fontsize=12)
        self.axes.set_xlabel("Data Value", fontsize=8)
        self.axes.set_ylabel("Counts", fontsize=8)

        self.figure.tight_layout()
        self.figure.canvas.draw()


class GraphWindow(QtWidgets.QDialog):
    """
    Graph Window - The QDialog window which will contain our image

    Attributes
    ----------
    parent : parent
        reference to the parent routine
    """
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent=None)
        self.parent = parent

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Graph Window")

        vbl = QtWidgets.QVBoxLayout(self)  # self is where layout is assigned
        self.hbl = QtWidgets.QHBoxLayout()
        self.mmc = MyMplCanvas(self)
        mpl_toolbar = NavigationToolbar(self.mmc, self.parent)

        self.combobox1 = QtWidgets.QComboBox()
        self.combobox2 = QtWidgets.QComboBox()
        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        self.label1.setText('Bands:')
        self.label2.setText('Bands:')
        self.hbl.addWidget(self.label1)
        self.hbl.addWidget(self.combobox1)
        self.hbl.addWidget(self.label2)
        self.hbl.addWidget(self.combobox2)

        vbl.addWidget(self.mmc)
        vbl.addWidget(mpl_toolbar)
        vbl.addLayout(self.hbl)

        self.setFocus()

        self.combobox1.currentIndexChanged.connect(self.change_band)
        self.combobox2.currentIndexChanged.connect(self.change_band)

    def change_band(self):
        """ Combo box to choose band """
        pass


class PlotCCoef(GraphWindow):
    """
    Plot 2D Correlation Coeffiecients

    Attributes
    ----------
    label1 : QLabel
        reference to GraphWindow's label1
    combobox1 : QComboBox
        reference to GraphWindow's combobox1
    label2 : QLabel
        reference to GraphWindow's label2
    combobox2 : QComboBox
        reference to GraphWindow's combobox2
    parent : parent
        reference to the parent routine
    indata : dictionary
        dictionary of input datasets
    """
    def __init__(self, parent):
        GraphWindow.__init__(self, parent)
        self.label1.hide()
        self.combobox1.hide()
        self.label2.hide()
        self.combobox2.hide()
        self.indata = {}
        self.parent = parent

    def change_band(self):
        """ Combo box to choose band """
        pass

    def run(self):
        """ Run """
        self.show()
        data = self.indata['Raster']

        dummy_mat = [[corr2d(i.data, j.data) for j in data] for i in data]
        dummy_mat = np.array(dummy_mat)

        self.mmc.update_pcolor(data, dummy_mat)


def corr2d(dat1, dat2):
    """
    Calculate the 2D correlation

    Parameters
    ----------
    dat1 : numpy array
        dataset 1 for use in correlation calculation
    dat2 : numpy array
        dataset 2 for use in correlation calculation

    Returns
    -------
    out : numpy array
        array of correlation coefficients
    """

    out = None
    if dat1.shape == dat2.shape:
        mdat1 = dat1 - dat1.mean()
        mdat2 = dat2 - dat2.mean()
        numerator = (mdat1 * mdat2).sum()
        denominator = np.sqrt((mdat1 ** 2).sum() * (mdat2 ** 2).sum())
        out = numerator / denominator

    return out


class PlotRaster(GraphWindow):
    """
    Plot Raster Class

    Attributes
    ----------
    label2 : QLabel
        reference to GraphWindow's label2
    combobox2 : QComboBox
        reference to GraphWindow's combobox2
    parent : parent
        reference to the parent routine
    indata : dictionary
        dictionary of input datasets
    """
    def __init__(self, parent):
        GraphWindow.__init__(self, parent)
        self.label2.hide()
        self.combobox2.hide()
        self.indata = {}
        self.parent = parent

    def change_band(self):
        """ Combo box to choose band """
        i = self.combobox1.currentIndex()
        data2 = None
        if 'Point' in self.indata:
            data2 = self.indata['Point'][0]
        if 'Raster' in self.indata:
            data = self.indata['Raster']
            self.mmc.update_raster(data[i], data2)
        elif 'ProfPic' in self.indata:
            data = self.indata['ProfPic']
            self.mmc.update_rgb(data[i])

    def run(self):
        """ Run """
        self.show()
        if 'Raster' in self.indata:
            data = self.indata['Raster']
        elif 'Cluster' in self.indata:
            data = self.indata['Cluster']
        elif 'ProfPic' in self.indata:
            data = self.indata['ProfPic']

        for i in data:
            self.combobox1.addItem(i.dataid)
        self.change_band()


class PlotSurface(GraphWindow):
    """
    Plot Raster Class

    Attributes
    ----------
    label2 : QLabel
        reference to GraphWindow's label2
    combobox2 : QComboBox
        reference to GraphWindow's combobox2
    parent : parent
        reference to the parent routine
    indata : dictionary
        dictionary of input datasets
    """
    def __init__(self, parent):
        GraphWindow.__init__(self, parent)
        self.label2.hide()
        self.combobox2.hide()
        self.indata = {}
        self.parent = parent

    def change_band(self):
        """ Combo box to choose band """
        i = self.combobox1.currentIndex()
        if 'Raster' in self.indata:
            data = self.indata['Raster']
            self.mmc.update_wireframe(data[i])

    def run(self):
        """ Run """
        if 'Raster' in self.indata:
            self.show()
            data = self.indata['Raster']

            for i in data:
                self.combobox1.addItem(i.dataid)
            self.change_band()


class PlotScatter(GraphWindow):
    """
    Plot Hexbin Class. A Hexbin is a type of scatter plot which is raster.

    Attributes
    ----------
    parent : parent
        reference to the parent routine
    indata : dictionary
        dictionary of input datasets
    """
    def __init__(self, parent):
        GraphWindow.__init__(self, parent=None)
        self.indata = {}
        self.parent = parent

    def change_band(self):
        """ Combo box to choose band """
        data = self.indata['Raster']
        i = self.combobox1.currentIndex()
        j = self.combobox2.currentIndex()
        self.mmc.update_hexbin(data[i].data, data[j].data)

    def run(self):
        """ Run """
        self.show()
        data = self.indata['Raster']
        for i in data:
            self.combobox1.addItem(i.dataid)
            self.combobox2.addItem(i.dataid)

        self.label1.setText('X Band:')
        self.label2.setText('Y Band:')
        self.combobox1.setCurrentIndex(0)
        self.combobox2.setCurrentIndex(1)


class PlotHist(GraphWindow):
    """
    Plot Hist Class

    Attributes
    ----------
    label2 : QLabel
        reference to GraphWindow's label2
    combobox2 : QComboBox
        reference to GraphWindow's combobox2
    parent : parent
        reference to the parent routine
    indata : dictionary
        dictionary of input datasets
    """
    def __init__(self, parent):
        GraphWindow.__init__(self, parent)
        self.label2.hide()
        self.combobox2.hide()
        self.indata = {}
        self.parent = parent

    def change_band(self):
        """ Combo box to choose band """
        data = self.indata['Raster']
        i = self.combobox1.currentIndex()
        self.mmc.update_hist(data[i])

    def run(self):
        """ Run """
        self.show()
        data = self.indata['Raster']
        for i in data:
            self.combobox1.addItem(i.dataid)

        self.label1.setText('Band:')
        self.combobox1.setCurrentIndex(0)
        self.change_band()
