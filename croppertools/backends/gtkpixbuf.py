# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Implements cropping using the GTK Pixbuf. I consider this module to have the 
lowest quality, but always available.
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker
import os.path

def module_available():
	"""module_available() -> boolean
	Always returns true, since GTK is always available.
	"""
	return True

class Module(object):
	"""
	Manages the cropping process. One will be instantiated for each image to 
	crop.
	
	Implements the context manager interface so we know when we can free stuff up.
	"""
	
	def __init__(self, _, pb, _):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Just stores the pixbuf for later use.
		"""
		self.origin = pb
	
	def do_crop(self, rect, dest):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> ProgressTracker
		Start performing the crop. The hard work should be done in a back end.
		
		Immediately raises NotImplementedError if this module can't do this 
		particular crop.
		
		Returns an object that's used for syncronization.
		"""
		with ProgressTracker(False) as rv:
			img = self.origin.subpixbuf(rect.x, rect.y, rect.width, rect.height)
		
			ext = os.path.splitext(dest.get_basename())[1].lower()
			if ext.lower() in ('jpg', 'jpeg') and not self.origin.get_property('has-alpha'):
				typ = 'jpeg'
			else:
				typ = 'png'
		
			def write(buf):
				with rv:
					try:
						dest.replace('', False).write(buf)
					else:
						rv.finish()
		
			img.save_to_callback(write, typ)
		
		return rv
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		We're done with this cropping business. Clean up.
		"""
		del self.origin
