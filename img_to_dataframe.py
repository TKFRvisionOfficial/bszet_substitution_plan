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

import re
from math import isclose

import cv2
import numpy as np
import pandas as pd
from easyocr import Reader

# from: https://medium.com/analytics-vidhya/how-to-detect-tables-in-images-using-opencv-and-python-6a0f15e560c3
langs = ["de", "en"]
reader = Reader(langs, gpu=False)


def find_contours(img_gray):
    # separate light from dark picture elements
    ret, thresh_value = cv2.threshold(img_gray, 190, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((8, 8), np.uint8)
    dilated_value = cv2.dilate(thresh_value, kernel, iterations=1)

    # recognize contours
    contours = cv2.findContours(dilated_value, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]

    return contours


def sort_and_join_texts(easyocr_result):
    # sort recognized text by coordinates for right text order
    sorted_by_xaxes = sorted(easyocr_result, key=lambda k: k[0][0][0])
    # get all y-coordinates of texts
    all_y_coordinates = [coordinate[0][0][1] for coordinate in sorted_by_xaxes]
    # list for coordinates of lines, smallest coordinate is given
    line_coordinates = [min(all_y_coordinates)]
    # filter y-coordinates by close values (get all lines)
    for y in all_y_coordinates:
        close_to_existing_value = False
        for line in line_coordinates:
            if isclose(y, line, abs_tol=15):
                close_to_existing_value = True
                break
        if not close_to_existing_value:
            line_coordinates.append(y)
    # sort lines
    line_coordinates = sorted(line_coordinates)

    # sort texts into 2D-list
    sorted_text = [[] for _ in range(len(line_coordinates))]
    for i, y in enumerate(all_y_coordinates):  # iterate all recognized texts
        for line, line_coordinate in enumerate(line_coordinates):  # iterate all text-lines
            if isclose(y, line_coordinate, abs_tol=15):  # match text to line
                sorted_text[line].append(sorted_by_xaxes[i][1])  # insert text into list

    recognized_text = " ".join(item for line in sorted_text for item in line)

    return recognized_text


def img_to_text(input_img):
    (part_height, part_width) = input_img.shape[:2]
    # preprocess image
    ret, img_bin = cv2.threshold(input_img, 150, 255, cv2.THRESH_BINARY)
    img_bin = cv2.resize(img_bin, (part_width * 10, part_height * 10))
    img_blurry_dark = cv2.resize(cv2.blur(255 - img_bin, (5, 5)), (part_width * 2, part_height * 2))

    # recognize inverted image
    results_dark = reader.readtext(img_blurry_dark)

    if results_dark:
        recognized_text = sort_and_join_texts(results_dark)  # sort texts
    else:  # no text recognized
        recognized_text = ""

    return recognized_text


def handle_parsing_mistakes(recognized_text, column):
    # be sure that lessons are enumerations with dot (must start with one number)
    if (search := re.search("^\d", recognized_text)) and column == 4:  # not expecting 10
        revised_text = search.group(0)[0] + "."
    # lesson ends with I -> (Gruppe-1)
    # or lesson starts with 1 -> I (e.g. IS)
    elif column == 3:
        rev = re.sub("^1", "I", recognized_text)
        revised_text = re.sub("I$", "1", rev)
    # replace 8 with B (for room)
    elif column == 2:
        rev = re.sub("^8", "B", recognized_text)
        rev = re.sub("^\+8", "+B", rev)
        revised_text = re.sub("\(8", "(B", rev)
    elif column == 1:
        rev = re.sub("Dr(_|-|\s)", "Dr.", recognized_text)
        rev = re.sub("Dr\.", "Dr. ", rev)
        revised_text = re.sub("\s+", " ", rev)
    elif column == 0:
        rev = re.sub("Std(_|-)", "Std.", recognized_text)
        revised_text = re.sub("(-|_)\sStd", ". Std", rev)
    else:
        revised_text = recognized_text
    return revised_text


def convert_table_img_to_list(img: np.ndarray):
    img_color = img
    # convert image to gray
    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

    contours = find_contours(img_gray)

    table = []
    table_row = []
    y_before = 0
    # position/coordinates of table
    table_left_pos = 99999
    table_upper_pos = 99999
    table_right_pos = 0
    table_lower_pos = 0
    date_upper_pos = 0

    for cnt in contours:
        # get rects from contours
        x, y, w, h = cv2.boundingRect(cnt)
        if 60 < h < 150:
            x -= 2
            y -= 2
            w += 2
            h += 2

            # select one table cell from image
            part_img = img_gray[y:y + h, x:x + w]
            cell_text = img_to_text(part_img)  # extract text from image
            col = len(table_row) % 6
            cell_text = handle_parsing_mistakes(cell_text, col)
            # text to exclude from output table
            excluded_from_table = ["bszet", "vertretungsplan", "bgy", "/", "|", "i", "[", "dubas"]
            exclude = False
            for ex in excluded_from_table:  # iterate all strings to be excluded
                if cell_text.lower() in ex and cell_text:  # text must contain anything
                    date_upper_pos = y + h  # set top position of date-area
                    exclude = True
                    break  # leave this for-loop
            if exclude:
                continue  # continue to next cell

            if y_before == y or y_before == 0:  # same line as cell before
                table_row.insert(0, cell_text)
            else:  # next line
                table.insert(0, table_row)
                table_row = [cell_text]
            y_before = y

            # empty table cells are not allowed to affect the determination of the table size
            if cell_text != "":
                # get min/max value of y and x (table)
                if x < table_left_pos:
                    table_left_pos = x
                if y < table_upper_pos:
                    table_upper_pos = y
                if x + w > table_right_pos:
                    table_right_pos = x + w
                if y + h > table_lower_pos:
                    table_lower_pos = y + h
    table.insert(0, table_row)  # insert last row

    # get img area where date can be
    part_img = img_gray[date_upper_pos:table_upper_pos - 60, table_left_pos:table_right_pos - 300]
    date = img_to_text(part_img)  # get date from image
    # ToDo:
    # cv2 doesn't recognize Heading of Table because background is orange
    # date+"\nKlasse" is intended because of compatibility to camelot
    table.insert(0, [date + "\nKlasse", "Stunde", "Fach", "Raum", "Lehrkraft: +Vertretung / (fehlt)", "Mitteilung"])

    data_frame = pd.DataFrame(table)
    data_frame = data_frame.fillna(value="")
    # print(data_frame)

    return data_frame
