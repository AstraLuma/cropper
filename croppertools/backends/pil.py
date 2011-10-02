# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Uses the Python Imaging Library. I consider PIL to be decent quality, but lacks 
in certain areas.
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker

try:
	import PIL.Image
except ImportError:
	PIL = None

def module_available():
	return PIL is not None

"""
		origin = PIL.Image.open(StringIO(self.imagedata))
		
		
			print "fn:", fn,
			r = box.rect
			img = origin.crop((r.x, r.y, r.x+r.width, r.y+r.height))
			
			ext = os.path.splitext(dest.get_basename())[1].lower()
			img.save(dest.replace('', False), PIL.Image.EXTENSION.get(ext, origin.format))
"""

