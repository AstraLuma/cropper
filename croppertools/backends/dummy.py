# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
This is an example cropping module to demonstrate the API.

DON'T USE THIS! This is merely a demo.
"""
from __future__ import division, absolute_import, with_statement

def module_available():
	"""module_available() -> boolean
	Returns True if the utilities/libraries/oracle that this module uses is 
	available. This is used as a fast filter.
	"""
	return True

class Module(object):
	"""
	Manages the cropping process. One will be instantiated for each image to 
	crop.
	"""
	
	def __init__(self, gfile, pb, data):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Initializes the backend, including loading the file.
		
		Raises a NotImplementedException if this backend can't work on this 
		kind of file.
		"""
	
	def do_crop(self, rect, gfile):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> (TODO: Some kind of object to notify of progress)
		Start performing the crop. The hard work should be done in a back end.
		
		Returns an object that's used for syncronization.
		"""
		gfile.
