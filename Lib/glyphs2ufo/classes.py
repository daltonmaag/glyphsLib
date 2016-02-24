#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2016 Georg Seifert. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re, traceback

from casting import num, transform, point, glyphs_datetime, CUSTOM_INT_PARAMS, CUSTOM_FLOAT_PARAMS, CUSTOM_TRUTHY_PARAMS, CUSTOM_INTLIST_PARAMS, floatToString, truthy

__all__ = [
	"GSFont", "GSCustomParameter", "GSInstance", 
]

def color(line):
	if line[0] == "(":
		line = line[1:-1]
		color = line.split(",")
		color = tuple([int(c) for c in color])
	else:
		color = int(line)
	return color


def hint_target(line):
	if line[0] == "{":
		return point(line)
	else:
		return line

class GSBase(object):
	def __repr__(self):
		content = ""
		if hasattr(self, "_dict"):
			content = str(self._dict)
		return "<%s %s>" % (self.__class__.__name__, content)
	
	def classForName(self, name):
		return self._classesForName.get(name, str)
	
	def __setitem__(self, key, value):
		try:
			if type(value) is str and key in self._classesForName:
				new_type = self._classesForName[key]
				if new_type is unicode:
					# print "__set", key
					value = value.decode('utf-8')
				else:
					value = new_type(value)
			setattr(self, key, value)
		except:
			print traceback.format_exc()

class GSCustomParameter(GSBase):
	_classesForName = {
		"name": str,
		"value": str,  # TODO: check 'name' to determine proper class
	}
	
	def __repr__(self):
		return "<%s %s: %s>" % (self.__class__.__name__, self.name, self._value)
	
	def getValue(self):
		return self._value
	
	def setValue(self, value):
		"""Cast some known data in custom parameters."""
		if self.name in CUSTOM_INT_PARAMS:
			value = int(value)
		if self.name in CUSTOM_FLOAT_PARAMS:
			value = float(value)
		if self.name in CUSTOM_TRUTHY_PARAMS:
			value = truthy(value)
		if self.name in CUSTOM_INTLIST_PARAMS:
			value = intlist(value)
		elif self.name == 'DisableAllAutomaticBehaviour':
			value = truthy(value)
		self._value = value
	
	value = property(getValue, setValue)


class GSAlignmentZone(GSBase):
	_classesForName = {}
	
	def __init__(self, line = None):
		if line is not None:
			self.position, self.size = point(line)
	
	def __repr__(self):
		return "<%s pos:%g size:%g>" % (self.__class__.__name__, self.position, self.size)
		
	def plistValue(self):
		return "\"{%s, %s}\"" % (floatToString(self.position), floatToString(self.size))

class GSGuideLine(GSBase):
	_classesForName = {
		"alignment": str,
		"angle": float,
		"locked": truthy,
		"position": point,
		"showMeasurement": truthy,
	}


class GSFontMaster(GSBase):
	_classesForName = {
		"alignmentZones": GSAlignmentZone,
		"ascender": float,
		"capHeight": float,
		"custom": str,
		"customParameter": GSCustomParameter,
		"customValue": float,
		"descender": float,
		"guideLines": GSGuideLine,
		"horizontalStems": int,
		"id": str,
		"italicAngle": float,
		"userData": dict,
		"verticalStems": int,
		"visible": truthy,
		"weight": str,
		"weightValue": float,
		"width": str,
		"widthValue": float,
		"xHeight": float,
	}


class GSNode(GSBase):
	_classesForName = { }
	
	def __init__(self, line = None):
		if line is not None:
			rx = '([-.e\d]+) ([-.e\d]+) (LINE|CURVE|OFFCURVE|n/a)(?: (SMOOTH))?'
			m = re.match(rx, line).groups()
			self.position = (num(m[0]), num(m[1]))
			self.type = m[2].lower()
			self.smooth = bool(m[3])
		else:
			self.position = (0, 0)
			self.type = 'line'
			self.smooth = False
	
	def __repr__(self):
		content = self.type
		if self.smooth:
			content += " smooth"
		return "<%s %g %g %s>" % (self.__class__.__name__, self.position[0], self.position[1], content)
	
	def plistValue(self):
		content = self.type.upper()
		if self.smooth:
			content += " SMOOTH"
		return "\"%s %s %s\"" % (floatToString(self.position[0]), floatToString(self.position[1]), content)

class GSPath(GSBase):
	_classesForName = {
		"nodes": GSNode,
		"closed": truthy
	}


class GSComponent(GSBase):
	_classesForName = {
		"alignment": int,
		"anchor": str,
		"locked": truthy,
		"name": str,
		"piece": dict,
		"transform": transform,
	}


class GSAnchor(GSBase):
	_classesForName = {
		"name": str,
		"position": point,
	}


class GSHint(GSBase):
	_classesForName = {
		"horizontal": truthy,
		"options": int, # bitfield
		"origin": point, # Index path to node
		"other1": point, # Index path to node for third node
		"other2": point, # Index path to node for fourth node
		"place": point, # (position, width)
		"scale": point, # for corners
		"stem": int, # index of stem
		"target": hint_target,  # Index path to node or 'up'/'down'
		"type": str,
	}


class GSFeature(GSBase):
	_classesForName = {
		"automatic": truthy,
		"code": unicode,
		"name": str,
		"notes": unicode,
	}
	def getCode(self):
		return self._code
		
	def setCode(self, code):
		replacements = (
			('\\012', '\n'), ('\\011', '\t'), ('\\U2018', "'"), ('\\U2019', "'"),
			('\\U201C', '"'), ('\\U201D', '"'))
		for escaped, unescaped in replacements:
			code = code.replace(escaped, unescaped)
		self._code = code
	code = property(getCode, setCode)

class GSClass(GSFeature):
	_classesForName = {
		"automatic": truthy,
		"code": unicode,
		"name": str,
		"notes": unicode,
	}


class GSAnnotation(GSBase):
	_classesForName = {
		"angle": float,
		"position": point,
		"text": str,
		"type": str,
		"width": float, # the width of the text field or size of the cicle
	}


class GSInstance(GSBase):
	_classesForName = {
		"customParameters": GSCustomParameter,
		"exports": truthy,
		"instanceInterpolations": dict,
		"interpolationCustom": float,
		"interpolationWeight": float,
		"interpolationWidth": float,
		"isBold": truthy,
		"isItalic": truthy,
		"linkStyle": str,
		"manualInterpolation": truthy,
		"name": str,
		"weightClass": str,
		"widthClass": str,
	}
	
	def __init__(self):
		self.exports = True
		self.name = "Regular"
		self.name = "Regular"
		self.linkStyle = ""
		self.interpolationWeight = 100
		self.interpolationWidth = 100
		self.interpolationCustom = 0
		self.visible = True
		self.isBold = False
		self.isItalic = False
		self.widthClass = "Medium (normal)"
		self.weightClass = "Regular"


class GSBackgroundLayer(GSBase):
	_classesForName = {
		"anchors": GSAnchor,
		"annotations": GSAnnotation,
		"backgroundImage": dict, # TODO
		"components": GSComponent,
		"guideLines": GSGuideLine,
		"hints": GSHint,
		"paths": GSPath,
		"visible": truthy,
	}


class GSLayer(GSBase):
	_classesForName = {
		"anchors": GSAnchor,
		"annotations": GSAnnotation,
		"associatedMasterId": str,
		"background": GSBackgroundLayer, 
		"backgroundImage": dict, # TODO
		"color": color,
		"components": GSComponent,
		"guideLines": GSGuideLine,
		"hints": GSHint,
		"layerId": str,
		"leftMetricsKey": str,
		"name": unicode,
		"paths": GSPath,
		"rightMetricsKey": str,
		"userData": dict,
		"vertWidth": float,
		"visible": truthy,
		"width": float,
		"widthMetricsKey": str,
	}


class GSGlyph(GSBase):
	_classesForName = {
		"bottomKerningGroup": str,
		"bottomMetricsKey": str,
		"category": str,
		"color": color,
		"export":truthy,
		"glyphname": str,
		"lastChange": glyphs_datetime,
		"layers": GSLayer,
		"leftKerningGroup": str,
		"leftMetricsKey": str,
		"note": unicode,
		"partsSettings": dict,
		"production": str,
		"rightKerningGroup": str,
		"rightMetricsKey": str,
		"script": str,
		"subCategory": str,
		"topKerningGroup": str,
		"topMetricsKey": str,
		"unicode": str,
		"userData": dict,
		"vertWidthMetricsKey": str,
		"widthMetricsKey": str,
	}


class GSFont(GSBase):
	_classesForName = {
		".appVersion": str,
		"DisplayStrings": [str],
		"classes": GSClass,
		"copyright": unicode,
		"customParameters": GSCustomParameter,
		"date": glyphs_datetime,
		"designer": unicode,
		"designerURL": unicode,
		"disablesAutomaticAlignment": truthy,
		"disablesNiceNames": truthy,
		"familyName": str,
		"featurePrefixes": GSClass,
		"features": GSFeature,
		"fontMaster": GSFontMaster,
		"glyphs": GSGlyph,
		"gridLength": int,
		"gridSubDivision": int,
		"instances": GSInstance,
		"keepAlternatesTogether": truthy,
		"kerning": dict,
		"manufacturer": unicode,
		"manufacturerURL": str,
		"unitsPerEm": int,
		"userData": dict,
		"versionMajor": int,
		"versionMinor": int,
	}
	
	def __init__(self):
		self.familyName = "Unnamed font"
		self._versionMinor = 0
		self.versionMajor = 1
	
	def __repr__(self):
		return "<%s \"%s\">" % (self.__class__.__name__, self.familyName)
	
	def getVersionMinor(self):
		return self._versionMinor
	
	def setVersionMinor(self, value):
		"""Ensure that the minor version number is between 0 and 999."""
		assert value >= 0 and value <= 999
		self._versionMinor = value
	
	versionMinor = property(getVersionMinor, setVersionMinor)

