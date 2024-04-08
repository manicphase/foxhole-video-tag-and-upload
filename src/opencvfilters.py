from functools import wraps, WRAPPER_ASSIGNMENTS
import inspect
import itertools

import cv2
import numpy as np


class OpenCVFilters():
    def __init__(self, config=None):
        function_list = [self.adjust_red,
                         self.adjust_blue,
                         self.adjust_green,
                         self.adjust_hue,
                         self.adjust_saturation,
                         self.adjust_lightness,
                         self.make_edge_mask,
                         self.blur_mask,
                         self.make_mask_from_colour,
                         self.resize_image_and_mask,
                         self.threshold_mask_from_mask
                        ]
        function_list_no_params = [self.apply_mask,
                                   self.invert_image_colours]
        self.functions = {}
        for f in function_list:
            self.functions[f.__name__] = {"name": f.__name__,
                                    "function": f,
                                    "defaults": dict(zip(list(inspect.signature(f) \
                                                .parameters.keys())[2:], f.__defaults__)),
                                    "values": dict(zip(list(inspect.signature(f) \
                                                .parameters.keys())[2:], f.__defaults__))}
        for f in function_list_no_params:
            self.functions[f.__name__] = {"name": f.__name__,
                                    "function": f}
        if config:
            self.config = config
            self.populate_config_functions(config)

    def run_filters(self, img):
        if not self.config:
            raise "No config loaded"
        mask = img
        for f in self.config:
            if f.get("values"):
                img, mask = f["function"](img, mask, **f["values"])
            else:
                img, mask = f["function"](img, mask)
        return img

    def _get_functions(self):
        return self
    
    def _adjust_channel_value(self, channel, brightness=128, contrast=50):
        # Apply brightness adjustment
        adjusted_channel = cv2.add(channel.astype(np.uint16), brightness)
        brightness = int(brightness-128)

        contrast = contrast / 50 # default contrast value = 1.0 multiplier

        # move middle of range to zero
        signed_channel = channel.astype(np.float32) - 128
        
        # multiply pixel values relative to middle
        adjusted_signed_channel = cv2.multiply(signed_channel, contrast)

        # set back to unsigned int range
        contrasted_channel = adjusted_signed_channel + 128

        # Apply contrast adjustment
        adjusted_channel = np.clip(contrasted_channel, 0, 255)
        adjusted_channel = adjusted_channel.astype(np.uint8)

        return adjusted_channel

    def adjust_red(self, img, mask, brightness=128, contrast = 128):
        red, green, blue = cv2.split(img)
        red = self._adjust_channel_value(red, brightness, contrast)
        return cv2.merge([red, green, blue]), mask

    def adjust_green(self, img, mask, brightness=128, contrast = 128):
        red, green, blue = cv2.split(img)
        green = self._adjust_channel_value(green, brightness, contrast)
        return cv2.merge([red, green, blue]), mask    

    def adjust_blue(self, img, mask, brightness=128, contrast = 128):
        red, green, blue = cv2.split(img)
        blue = self._adjust_channel_value(blue, brightness, contrast)
        return cv2.merge([red, green, blue]), mask

    def _as_hsv(func):
        @wraps(func, assigned=WRAPPER_ASSIGNMENTS + ('__defaults__', '__kwdefaults__'))
        def wrapper(*args, **kwargs):
            args = list(args)
            args[1] = cv2.cvtColor(args[1], cv2.COLOR_RGB2HSV)            
            img, mask = func(*args, **kwargs)
            img = cv2.cvtColor(img, cv2.COLOR_HSV2RGB)
            return img, mask
        return wrapper

    @_as_hsv
    def adjust_hue(self, img, mask, brightness=128, contrast=128):
        hue, saturation, lightness = cv2.split(img)
        hue = self._adjust_channel_value(hue, brightness, contrast)
        return cv2.merge([hue, saturation, lightness]), mask

    @_as_hsv
    def adjust_saturation(self, img, mask, brightness=128, contrast=128):
        hue, saturation, lightness = cv2.split(img)
        saturation = self._adjust_channel_value(saturation, brightness, contrast)
        return cv2.merge([hue, saturation, lightness]), mask

    @_as_hsv
    def adjust_lightness(self, img, mask, brightness=128, contrast=128):
        hue, saturation, lightness = cv2.split(img)
        lightness = self._adjust_channel_value(lightness, brightness, contrast)
        return cv2.merge([hue, saturation, lightness]), mask

    def resize_image_and_mask(self, img, mask, scale=100, aspect_ratio=100, scale_method=1):
        height_factor = scale/50
        width_factor = height_factor*(aspect_ratio/100)

        height_factor = np.clip(height_factor, 1, 255)
        width_factor = np.clip(width_factor, 1, 255)
        
        up_width = int(len(img[0])*width_factor)
        up_height = int(len(img)*height_factor)
        up_points = (up_width, up_height)
        
    
        scale_methods = [cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_AREA,
                         cv2.INTER_CUBIC, cv2.INTER_LANCZOS4]
    
        img = cv2.resize(img, up_points, interpolation=scale_methods[scale_method%5])
        #if mask:
        mask = cv2.resize(mask, up_points, interpolation=scale_methods[scale_method%5])
        return img, mask

    def make_edge_mask(self, img, mask, threshold1=50, threshold2=200):
        mask = cv2.Canny(img,threshold1*4,threshold2*4)
        return img, mask
    
    def blur_mask(self, img, mask, kernal_height=30, kernal_width=30):
        kernal_height = np.clip(kernal_height, 1, 255)
        kernal_width = np.clip(kernal_width, 1, 255)

        mask = cv2.blur(mask,(kernal_height, kernal_width))
        return img, mask
    
    def threshold_mask_from_mask(self, img, mask, lower=10, upper=255):
        mask = cv2.inRange(mask, lower, upper)
        return img, mask

    def make_mask_from_colour(self, img, mask, blue_low=0, blue_high=255, green_low=0, green_high=255, red_low=0, red_high=255):
        lower = np.array([blue_low, green_low, red_low])
        upper = np.array([blue_high, green_high, red_high])
        mask = cv2.inRange(img, lower, upper)
        return img, mask
    
    def apply_mask(self, img, mask):
        img = cv2.bitwise_and(img,img,mask=mask)
        return img, mask
    
    def invert_image_colours(self, img, mask):
        return 255-img, mask

    def map_config_to_list(self, config):
        value_array = [list(d["values"].values()) for d in config if d.get("values")]
        return list(itertools.chain.from_iterable(value_array))

    def map_list_to_config(self, config, values):
        new_config = config.copy()
        values_copy = values[:]
        for function in new_config:
            if function.get("values"):
                for k, v in function["values"].items():
                    function["values"][k] = int(values_copy.pop(0))
        return new_config

    def create_default_config(self, funcs):
        return [self.functions[f] for f in funcs]

    def populate_config_functions(self, config):
        for func in config:
            func["function"] = self.functions[func["name"]]["function"]
        return config

    def get_config_json(self, config):
        new_config = [func.copy() for func in config]
        for func in new_config:
            if func.get("function"):
                del func["function"]
        return new_config
        