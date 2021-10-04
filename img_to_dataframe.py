import cv2
import numpy as np
import pytesseract as pt
import pandas as pd

# from: https://medium.com/analytics-vidhya/how-to-detect-tables-in-images-using-opencv-and-python-6a0f15e560c3


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
    input_img = cv2.resize(input_img, (part_width * 10, part_height * 10))
    input_img = cv2.threshold(input_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    cv2.imwrite('D:/Dokumente/Programmieren/Python/testTableDetection/test.jpg', input_img)
    # convert image to text
    recongnized_text = pt.image_to_string(input_img, lang='deu')
    if recongnized_text == "\x0c":
        recongnized_text = pt.image_to_string(input_img, lang='deu', config="--psm 7")

    # remove "\n", "\x0c", " "
    recongnized_text = recongnized_text.strip("\n\x0c ")
    recongnized_text = recongnized_text.replace("\n", " ")

    # tesseract always recognizes T. instead of 7.
    # should be fixed later
    if recongnized_text == "T.":
        recongnized_text = "7."

    return recongnized_text


def convert_table_img_to_list(img: np.ndarray):
    # define Path to pytesseract
    pt.pytesseract.tesseract_cmd = r'Tesseract-OCR\tesseract.exe'

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
        if 30 < h < 100:
            x -= 2
            y -= 2
            w += 2
            h += 2

            # select one table cell from image
            part_img = img_gray[y:y + h, x:x + w]
            cell_text = img_to_text(part_img)  # extract text from image
            # text to exclude from output table
            if cell_text in ["Vertretungsplan", "BGy", "/", "|", "I", "[", "DuBAS"]:
                date_upper_pos = y + h
                continue

            if y_before == y or y_before == 0:  # same line as cell before
                table_row.insert(0, cell_text)
            else:  # next line
                table.insert(0, table_row)
                table_row = [cell_text]
            y_before = y

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

    # cv2.imwrite("lol.png", img_gray[table_upper_pos:table_lower_pos, table_left_pos:table_right_pos])
    # get img area where date can be
    part_img = img_gray[date_upper_pos:table_upper_pos-30, table_left_pos:table_right_pos-150]
    date = img_to_text(part_img)  # get date from image
    # cv2 doesn't recognize Heading of Table because background is orange
    # date+"\nKlasse" is intented because of compatibility to camelot
    table.insert(0, [date+"\nKlasse", "Stunde", "Fach", "Raum", "Lehrkraft: +Vertretung / (fehlt)", "Mitteilung"])
    
    data_frame = pd.DataFrame(table)
    data_frame = data_frame.fillna(value="")

    return data_frame
