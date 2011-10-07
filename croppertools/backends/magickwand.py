# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Uses ImageMagick's MagickWand library, using the library at
<http://www.assembla.com/wiki/show/pythonmagickwand>.
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker

try:
	import pythonmagickwand.image
except ImportError:
	pythonmagickwand = None

def module_available():
	return pythonmagickwand is not None

