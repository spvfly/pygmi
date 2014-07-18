# -----------------------------------------------------------------------------
# Name:        ptimer.py (part of PyGMI)
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
""" ptimer is a routine to simplify checking how much time has passed in a
    program. It also outputs a message at the point when called """

# pylint: disable=E1101, C0103
import time


class PTime(object):
    """ Main PTime class"""
    def __init__(self):
        self.tchk = [time.clock()]

    def since_first_call(self, msg='since first call'):
        """ This function prints out a message and lets you know the time
        passed since the first call"""
        self.tchk.append(time.clock())
        print(msg, 'at time (s):', self.tchk[-1] - self.tchk[0])

    def since_last_call(self, msg='since last call'):
        """ This function prints out a message and lets you know the time
        pass since the last call """
        self.tchk.append(time.clock())
        print(msg, 'time(s):', self.tchk[-1] - self.tchk[-2],
              'since last call')
