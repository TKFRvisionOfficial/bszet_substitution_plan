#  bszet_substitution_plan
#  Copyright (C) 2022 TKFRvision, PBahner, MarcelCoding
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
from datetime import datetime

import camelot

# print(int(round(time.mktime(datetime.strptime("07.06.2022", "%d.%m.%Y").timetuple()) / 60 / 60 / 24, 0)))

# https://frei.bszet.de/inhalt/Blockplaene/BGy/Schuljahresablauf%20BSZ%202021-2022.pdf
stuff = camelot.read_pdf("[PLAN]")
data_table = stuff[0].data.copy()
data_table.pop(0)
for thing in data_table:
    if thing[0] != "" and thing[2] != "":
        timestamp = time.mktime(datetime.strptime(thing[2], "%d.%m.%Y").timetuple())
        print(int(round(timestamp / 60 / 60 / 24, 0)))
