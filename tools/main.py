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

