# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
This is an example cropping module to demonstrate the API.

DON'T USE THIS! This is merely an example.
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker

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
	
	Implements the context manager interface so we know when we can free stuff up.
	"""
	
	def __init__(self, gfile, pb, data):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Initializes the backend, including loading the file.
		
		Raises a NotImplementedError if this backend can't work on this kind of 
		file.
		"""
	
	def do_crop(self, rect, dest):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> ProgressTracker
		Start performing the crop. The hard work should be done in a back end.
		
		Immediately raises NotImplementedError if this module can't do this 
		particular crop.
		
		Returns an object that's used for syncronization.
		"""
		with ProgressTracker() as rv:
			dest.replace('', False).write('') # Just so that the box model thinks we did something
		return rv
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		We're done with this cropping business. Clean up.
		"""

