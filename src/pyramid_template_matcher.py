import cv2
import numpy as np

from cv2img import Rect

class FindResult:
    def __init__(self, x=0, y=0, w=0, h=0, score=-1):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.score = score

    def __str__(self):
        return "x:{x}, y:{y}, w:{w}, h:{h}, score:{score}".format(
            x=self.x,
            y=self.y,
            w=self.w,
            h=self.h,
            score=self.score
        )


class PyramidTemplateMatcher:
    def __init__(self, source_img, target_img, level, factor):
        self.source_img = source_img
        self.target_img = target_img
        self.factor = factor
        self.level = level
        self.lower_pyramid = None
        self.cache_result = None

        if self.source_img < self.target_img:
            return

        if level > 0:
            self.lower_pyramid = self._create_small_matcher()

    def _create_small_matcher(self):
        return PyramidTemplateMatcher(
            self.source_img.resize(self.factor),
            self.target_img.resize(self.factor),
            self.level - 1,
            self.factor
        )

    def find_best(self, roi=None):
        source_img = self.source_img
        target_img = self.target_img

        if roi:
            source_img = source_img.crop(roi)

        if target_img.is_same_color():
            if target_img.is_black():
                source_img = source_img.invert()
                target_img = target_img.invert()

            result = cv2.matchTemplate(source_img.source,
                                       target_img.source,
                                       cv2.TM_SQDIFF_NORMED)

            result = np.ones(result.size(), np.float32) - result
        else:
            result = cv2.matchTemplate(source_img.source,
                                       target_img.source,
                                       cv2.TM_CCOEFF_NORMED)

        self.cache_result = result
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(self.cache_result)

        return maxVal, maxLoc

    def erase_result(self, x, y, x_margin, y_margin):
        x0 = max(x - x_margin, 0)
        y0 = max(y - y_margin, 0)

        rows, cols = self.cache_result.shape
        x1 = min(x + x_margin, cols)
        y1 = min(y + y_margin, rows)

        self.cache_result[y0:y1, x0:x1] = 0

    def next(self):

        if self.source_img < self.target_img:
            return FindResult(0, 0, 0, 0, -1)

        if self.lower_pyramid != None:
            return self._next_from_lower_pyramid()

        detection_score = -1
        detection_loc = None

        if self.cache_result is None:
            detection_score, detection_loc = self.find_best()
        else:
            _, detection_score, _, detection_loc = cv2.minMaxLoc(self.cache_result)

        x_margin = int(self.target_img.cols / 3)
        y_margin = int(self.target_img.rows / 3)
        detection_x, detection_y = detection_loc

        self.erase_result(detection_x,
                          detection_y,
                          x_margin,
                          y_margin)

        return FindResult(detection_x,
                          detection_y,
                          self.target_img.cols,
                          self.target_img.rows,
                          detection_score)

    def _next_from_lower_pyramid(self):
        match = self.lower_pyramid.next()

        x = int(match.x * self.factor)
        y = int(match.y * self.factor)

        # Convert factor from float to int
        factor = int(self.factor)

        # Compute the parameter to define the neighborhood rectangle
        x0 = max(x - factor, 0)
        y0 = max(y - factor, 0)

        x1 = min(x + self.target_img.cols + factor, self.source_img.cols)
        y1 = min(y + self.target_img.rows + factor, self.source_img.rows)

        roi = Rect(x0, y0, x1-x0, y1-y0)

        detection_score, detection_loc = self.find_best(roi)

        detection_x, detection_y = detection_loc
        detection_x += roi.x
        detection_y += roi.y

        return FindResult(
            detection_x,
            detection_y,
            self.target_img.cols,
            self.target_img.rows,
            detection_score)



