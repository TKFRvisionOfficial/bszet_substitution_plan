import cv2
import numpy as np
from easyocr import Reader
import pandas as pd

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


def img_to_text(input_img):
    (part_height, part_width) = input_img.shape[:2]
    # preprocess image
    ret, img_bin = cv2.threshold(input_img, 150, 255, cv2.THRESH_BINARY)
    img_bin = cv2.resize(img_bin, (part_width*10, part_height*10))
    img_blurry_dark = cv2.resize(cv2.blur(255-img_bin, (5, 5)), (part_width*2, part_height*2))

    # recognize inverted image
    results_dark = reader.readtext(img_blurry_dark, detail=0)
    recognized_text = "".join(results_dark)

    # be sure that lessons are enumerations with dot
    if recognized_text.isdigit():
        recognized_text += "."
    # print(recognized_text)

    return recognized_text


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
            # text to exclude from output table
            # ToDo: not good to check for "Vertretu" or "ngsplan"
            if cell_text in ["Vertretu", "ngsplan", "ET", "BSZET", "Vertretungsplan", "BGy", "/", "|", "I", "[", "DuBAS"]:
                date_upper_pos = y + h
                continue

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
    part_img = img_gray[date_upper_pos:table_upper_pos-60, table_left_pos:table_right_pos-300]
    date = img_to_text(part_img)  # get date from image
    # ToDo:
    # cv2 doesn't recognize Heading of Table because background is orange
    # date+"\nKlasse" is intented because of compatibility to camelot
    table.insert(0, [date+"\nKlasse", "Stunde", "Fach", "Raum", "Lehrkraft: +Vertretung / (fehlt)", "Mitteilung"])
    
    data_frame = pd.DataFrame(table)
    data_frame = data_frame.fillna(value="")
    # print(data_frame)

    return data_frame
