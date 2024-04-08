import sys
import cv2
import pytesseract
import re

if sys.platform == "win32":
    print("changing path")
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'


class TesseractProcessor:
    def __init__(self, ranks, config):
        self.ranks = ranks
        self.config = config
        
    def scrape_names(self, img, psm=11):
        valid_names = []
        try:
            text = pytesseract.image_to_string(img, config =f'--oem 1 --psm {psm} -c load_system_dawg=false -c load_freq_dawg=false')
            reg = "|".join([re.escape(f"{r}") for r in self.ranks])
            res = re.finditer(reg,text)
            split_points = [0] + [t.end() for t in res]
            split_on_rank = []
            for x in range(1,len(split_points)):
                split_on_rank.append(text[split_points[x-1]:split_points[x]])
            valid_names = [l.split("\n")[-1].split("]")[-1].split("(")[0].strip() for l in split_on_rank]
            return valid_names
        except:
            # sometimes tesseract fails for odd reasons so just pass this frame
            return valid_names
        
    def mask_to_bounding_boxes(mask, min_width=150, max_width=700, min_height=20, max_height=500):
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for contour in contours:
            x,y,w,h = cv2.boundingRect(contour)
            if (w > min_width) and (w < max_width) and (h>min_height) and (h<max_height):
                boxes.append({"y1": y,
                            "y2": y+h,
                            "x1": x,
                            "x2": x+w})
        return boxes
    
    def get_rectangles_from_image(self, img, mask):
        boxes = self.mask_to_bounding_boxes(mask)
        rectangles = []
        for box in boxes:
            rectangles.append(img[box["y1"]:box["y2"], box["x1"]:box["x2"]])
        return rectangles

    def scrape_names_via_contours(self, img, mask):
        rects = self, self.get_rectangles_from_image(img, mask)
        words = []
        for r in rects: 
            words = words + self.scrape_names(r)
        return words
    
    def apply_filters(self, img):
        mask = img
        for f in self.config:
            if f.get("values"):
                img, mask = f["function"](img, mask, **f["values"])
            else:
                img, mask = f["function"](img, mask)
        return img, mask