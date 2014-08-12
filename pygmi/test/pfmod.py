# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Name:        pfmod.py (part of PyGMI)
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
""" These are pfmod tests. Run this file from within this directory to do the
tests """

import numpy as np
from pygmi.pfmod.grvmag3d import quick_model
from pygmi.pfmod.grvmag3d import calc_field
import matplotlib.pyplot as plt


def main():
    """ Main test function """
    print('Testing modelling of gravity and potential field data')

    # First initialise variables
    x = []
    z = []
    xpos = []
    g2dc = []
    m2dc = []

    # start to load in gravity data
    gfile = open('Grav2dc_grav.txt')
    tmp = gfile.read()
    tmp2 = tmp.splitlines()

    numx = get_int(tmp2, 2, 2)
    cnrs = get_int(tmp2, 6, 4)
    dens = get_float(tmp2, 6, 8) + 2.67
    strike = get_float(tmp2, 7, 3)

    for i in range(cnrs):
        x.append(get_float(tmp2, 9+i, 0))
        z.append(get_float(tmp2, 9+i, 1))

    for i in range(numx):
        xpos.append(get_float(tmp2, 11+cnrs+i, 0))
        g2dc.append(get_float(tmp2, 11+cnrs+i, 1))

    gfile.close()

    # Convert to numpy and correct orientation of depths.
    x = np.array(x)
    z = -np.array(z)
    xpos = np.array(xpos)
    g2dc = np.array(g2dc)

    # Start to load in magnetic data
    mfile = open('Mag2dc_mag.txt')
    tmp = mfile.read()
    tmp2 = tmp.splitlines()

    finc = get_float(tmp2, 4, 5)
    fdec = get_float(tmp2, 4, 8)
    mht = get_float(tmp2, 7, 5)
    susc = get_float(tmp2, 12, 7)
    minc = get_float(tmp2, 14, 9)
    mdec = get_float(tmp2, 14, 12)
    mstrength = get_float(tmp2, 14, 5)/(400*np.pi)

    for i in range(numx):
        m2dc.append(get_float(tmp2, 18+cnrs+i, 1))

    mfile.close()

    # Convert to numpy
    m2dc = np.array(m2dc)

    # for testing purposes the cube being modelled should have dxy = d_z to
    # keep things simple
    dxy = xpos[1]-xpos[0]
    d_z = dxy
    ypos = np.arange(-strike, strike, dxy)
    zpos = np.arange(z.min(), 0, d_z)
    numy = ypos.size
    numz = zpos.size
    tlx = xpos.min()
    tly = ypos.max()
    tlz = zpos.max()

    # quick model initialises a model with all the variables we have defined.
    lmod = quick_model(['Generic'], numx, numy, numz, dxy, d_z, tlx, tly, tlz,
                       0, 0, finc, fdec, [susc], [dens], [minc], [mdec],
                       [mstrength])

    # Create the actual model. It is a 3 dimensional vector with '1' where the
    # body lies
    for i in np.arange(x.min(), x.max(), dxy):
        for j in np.arange(0, 2*strike, dxy):
            for k in np.arange(1, numz):
                i2 = int(i/dxy)
                j2 = int(j/dxy)
                k2 = int(k)
                lmod.lith_index[i2, j2, k2] = 1

    # Calculate the gravity
    calc_field(lmod)
    gdata = lmod.griddata['Calculated Gravity'].data[20].copy()

    # Change to observation height to 100 meters and calculate magnetics
    lmod.mht = mht
    calc_field(lmod, altcalc=True)

    mdata = lmod.griddata['Calculated Magnetics'].data[20]

    # Display results
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('Distance (m)')
    ax1.plot(xpos+dxy/2, gdata, 'r', label='PyGMI')
    ax1.plot(xpos, g2dc, 'r.', label='Grav2DC')
    ax1.set_ylabel('mGal')
    ax1.legend(loc='upper left', shadow=True)

    ax2 = ax1.twinx()
    ax2.plot(xpos+dxy/2, mdata, 'b', label='PyGMI')
    ax2.plot(xpos, m2dc, 'b.', label='Mag2DC')
    ax2.set_ylabel('nT')
    ax2.legend(loc='upper right', shadow=True)
    plt.show()


def get_int(tmp, row, word):
    """ gets an int from a list of strings. First row or word is zero """
    return int(tmp[row].split()[word])


def get_float(tmp, row, word):
    """ gets a float from a list of strings. First row or word is zero """
    return float(tmp[row].split()[word])


if __name__ == "__main__":
    main()