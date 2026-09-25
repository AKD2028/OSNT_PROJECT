## -*- coding: utf-8 -*-
##
## analyse-flows.py
##
## Author:   Toke Høiland-Jørgensen (toke@toke.dk)
## Date:      5 juni 2014
## Copyright (c) 2014, Toke Høiland-Jørgensen
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, subprocess, pprint, json

filenames = sys.argv[1:]
flownums = 2,4

for fn in filenames:
    data = {}
    for flow in flownums:
        output = subprocess.check_output("./run-captcp.sh %s throughput -f %d -r -t" % (fn, flow), shell=True)
        for line in output.strip().splitlines():
            line = line.decode("utf-8")
            if not line or line.startswith("#"):
                continue
            x,y = line.strip().split()
            if not x in data:
                data[x] = {flow: y}
            else:
                data[x][flow] = y
    with open("%s.json" % fn, "w") as fp:
        json.dump(data, fp)
