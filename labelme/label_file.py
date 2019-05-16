import base64
import io
import json
import os.path as osp

import PIL.Image

from labelme._version import __version__
from labelme.logger import logger
from labelme import PY2
from labelme import QT4
from labelme import utils
from labelme.shape import Shape

from qtpy import QtCore
from qtpy import QtGui

#annotations=
#[
#    {
#        "name": "",
#        "type": "", #label, guide, and user configurable types, used to set default attrubutes
#        "shapes": #optional
#        [
#            {
#                "type": "", #polygon, circle, ...
#                "line_color": [], #optional
#                "fill_color": [], #optional
#                "points": []
#            },...
#        ],
#        "attributes"
#        {
#            "value": "",
#            etc...
#        },
#        "children": [] #allow labels to be nested
#    }
#]

#annotation_types=
# sting
# float
#
#annotation_types
#{
#    "car_label":
#    {
#        "make":
#        {
#            "type": "enum_string",
#            "enum": ["Chevy", "Ford", etc...]
#            "default": 0
#        },
#        "model":
#        {
#            "type": "string",
#            "default": ""
#        },
#        "color"
#        {
#            "type": "color"
#            "default": [255, 255, 255, 255]
#        }
#    },
#    "person_label":
#    {
#        "mood"
#        {
#            "type": "enum_string",
#            "enum": ["happy", "sad", etc...],
#            "default": 0
#        },
#        "action":
#        {
#            "type": "enum_string",
#            "enum": ["standing", "walking", "eating", etc...],
#            "allow_multiple": true,
#            "default": 0
#        },
#        "visibility":
#        {
#            "type": "enum_string",
#            "enum": ["clear", "occuluded", etc...]
#            "default": 0
#        }
#    }
#}

class LabelFileError(Exception):
    pass


class LabelFile(object):

    suffix = '.json'

    def __init__(self, filename=None):
#        self.shapes = ()
        self.imagePath = None
        self.imageData = None
        self.annotations = []
        if filename is not None:
            self.load(filename)
        self.filename = filename

    @staticmethod
    def load_image_file(filename):
        try:
            image_pil = PIL.Image.open(filename)
        except IOError:
            logger.error('Failed opening image file: {}'.format(filename))
            return

        # apply orientation to image according to exif
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()
            if PY2 and QT4:
                format = 'PNG'
            elif ext in ['.jpg', '.jpeg']:
                format = 'JPEG'
            else:
                format = 'PNG'
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()

    def __convert_format(self, shapes):
        annotations=[]

        for s in shapes:
            annotation={}
            
            annotation['name'] = s['label']
            annotation['type'] = 'label'
            annotation['shapes'] = []
            annotation['attributes'] = []
            annotation['children'] = []

            shape=Shape(annotation=annotation, shape_type=s.get('shape_type', 'polygon'))

            for x, y in s['points']:
                shape.addPoint(QtCore.QPoint(x, y))
            shape.close()
            if 'line_color' in s and s['line_color'] is not None:
                shape.line_color = QtGui.QColor(s['line_color'])
            if 'fill_color' in s and s['fill_color'] is not None:
                shape.fill_color = QtGui.QColor(s['fill_color'])

            annotation['shapes'].append(shape)
            annotations.append(annotation)
        return annotations

    def load(self, filename):
        keys = [
            'imageData',
            'imagePath',
            'lineColor',
            'fillColor',
#            'shapes',  # polygonal annotations
            'annotations',
            'labels',
            'flags',   # image level flags
            'imageHeight',
            'imageWidth',
        ]
        try:
            with open(filename, 'rb' if PY2 else 'r') as f:
                data = json.load(f)
            if data['imageData'] is not None:
                imageData = base64.b64decode(data['imageData'])
                if PY2 and QT4:
                    imageData = utils.img_data_to_png_data(imageData)
            else:
                # relative path from label file to relative path from cwd
                imagePath = osp.join(osp.dirname(filename), data['imagePath'])
                imageData = self.load_image_file(imagePath)
            flags = data.get('flags')
            imagePath = data['imagePath']
            self._check_image_height_and_width(
                base64.b64encode(imageData).decode('utf-8'),
                data.get('imageHeight'),
                data.get('imageWidth'),
            )
            lineColor = data['lineColor']
            fillColor = data['fillColor']

            if 'shapes' in data:
                annotations = self.__convert_format(data['shapes'])
            else:
                annotations = data['annotations']

        except Exception as e:
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # Only replace data after everything is loaded.
        self.flags = flags
        self.annotations = annotations
#        self.labels = labels
        self.imagePath = imagePath
        self.imageData = imageData
        self.lineColor = lineColor
        self.fillColor = fillColor
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        img_arr = utils.img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            logger.error(
                'imageHeight does not match with imageData or imagePath, '
                'so getting imageHeight from actual image.'
            )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            logger.error(
                'imageWidth does not match with imageData or imagePath, '
                'so getting imageWidth from actual image.'
            )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    def save(
        self,
        filename,
        shapes,
        imagePath,
        imageHeight,
        imageWidth,
        imageData=None,
        lineColor=None,
        fillColor=None,
        otherData=None,
        flags=None,
    ):
        if imageData is not None:
            imageData = base64.b64encode(imageData).decode('utf-8')
            imageHeight, imageWidth = self._check_image_height_and_width(
                imageData, imageHeight, imageWidth
            )
        if otherData is None:
            otherData = {}
        if flags is None:
            flags = {}
        data = dict(
            version=__version__,
            flags=flags,
            shapes=shapes,
            lineColor=lineColor,
            fillColor=fillColor,
            imagePath=imagePath,
            imageData=imageData,
            imageHeight=imageHeight,
            imageWidth=imageWidth,
        )
        for key, value in otherData.items():
            data[key] = value
        try:
            with open(filename, 'wb' if PY2 else 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    @staticmethod
    def is_label_file(filename):
        return osp.splitext(filename)[1].lower() == LabelFile.suffix
