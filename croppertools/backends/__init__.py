import jpegtrans, magickwand, imagemagick, pil, gtkpixbuf

MODULES = [jpegtrans, magickwand, imagemagick, pil, gtkpixbuf]

class CropManager(object):
	"""
	Abstracts away the process of selecting backends based on file type, crop 
	sizes, what's installed, phases of the moon, etc.
	
	Attempts to use the highest-quality backend first, and will move to lower 
	ones if it's unavailable/unable.
	"""
	def __init__(self, gfile, pb, data):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Initializes the backend, including loading the file.
		
		Raises a NotImplementedException if this backend can't work on this 
		kind of file.
		"""
	
	def do_crop(self, rect, dest):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> (TODO: Some kind of object to notify of progress)
		Start performing the crop. The hard work should be done in a back end.
		
		Returns an object that's used for syncronization.
		"""
		dest.replace('', False).write('')
