# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Uses the Python Imaging Library. I consider PIL to be decent quality, but lacks 
in certain areas.
"""
from __future__ import division, absolute_import, with_statement
import os.path
from StringIO import StringIO
from ..backends import ProgressTracker

try:
	import PIL.Image, PIL.ImageFile
except ImportError:
	PIL = None

def module_available():
	return PIL is not None

#TODO: Cache the PIL Image for particular files.

def decode(pbl):
	"""decode(PixbufLoader)
	Pretty much just passes the image data to the PixbufLoader.
	"""
	#FIXME: Fails with alpha channel
	#KLUDGE: If this turns out to be an RGBA image, ignore the parse we just did.
	fullimg = ''
	try:
		parser = PIL.ImageFile.Parser()
		imgdata = yield 
		fullimg += imgdata
		while True:
			parser.feed(imgdata)
			imgdata = yield
			fullimg += imgdata
	except GeneratorExit:
		img = parser.close()
		
		#KLUDGE
		if img.mode == 'RGBA':
			pbl.write(fullimg) # Don't use our parser
		else:
			sio = StringIO()
			img.save(sio, 'ppm')
			pbl.write(sio.getvalue())
			sio.close()

class CropManager(object):
	"""
	Manages the cropping process. One will be instantiated for each image to 
	crop.
	
	Implements the context manager interface so we know when we can free stuff up.
	"""
	
	def __init__(self, gf, pb, img):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Just stores the pixbuf for later use.
		"""
		self.origin = PIL.Image.open(StringIO(img))
	
	def do_crop(self, rect, dest):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> ProgressTracker
		Start performing the crop. The hard work should be done in a back end.
		
		Immediately raises NotImplementedError if this module can't do this 
		particular crop.
		
		Returns an object that's used for syncronization.
		"""
		if __debug__: print "PIL: Do Crop", rect, dest
		
		with ProgressTracker() as rv:
			img = self.origin.crop((rect.x, rect.y, rect.x+rect.width, rect.y+rect.height))
			
			ext = os.path.splitext(dest.get_basename())[1].lower()
			img.save(dest.replace('', False), PIL.Image.EXTENSION.get(ext, self.origin.format))
		return rv
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		We're done with this cropping business. Clean up.
		"""
		del self.origin

