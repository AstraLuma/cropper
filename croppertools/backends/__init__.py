import gobject
from ..usefulgprop import property as gprop

MODULES = []

def decode(pbl):
	"""decode(PixbufLoader)
	Decodes an image. A coroutine, though.
	Takes image data on send(). Call close() when there is no more data.
	"""
	#TODO: Recover on error and attempt other backends
	for m in MODULES:
		if hasattr(m, 'decode'): break
	if __debug__: print m
	dec = m.decode(pbl)
	dec.next()
	try:
		imgdata = yield
		while imgdata is not None:
			dec.send(imgdata)
			imgdata = yield
	except GeneratorExit:
		dec.close()

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
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> ProgressTracker
		Start performing the crop. The hard work should be done in a back end.
		
		Returns an object that's used for syncronization.
		"""
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		We're done with this cropping business. Clean up.
		"""

#class ProgressTracker(gobject.GObject):
class ProgressTracker(object):
	"""
	Helps syncronize the backends and the UI.
	"""
#	__gtype_name__ = None
	__gsignals__ = {
		'finished': (gobject.SIGNAL_RUN_FIRST, None, ()),
		'error': (gobject.SIGNAL_RUN_FIRST, None, (type, Exception, object)), #exc_type, exc_val, exc_tb
		}
	value = gprop(
		type=gobject.TYPE_DOUBLE,
		nick='percent finished',
		blurb='how done this task is, as a fraction (0 is nothing done, 1 is completely done)',
		minimum=0.0,
		maximum=1.0,
		default=0.0,
		flags=gobject.PARAM_READWRITE
		)
	has_value = gprop(
		type=gobject.TYPE_BOOLEAN,
		nick='barber pole',
		blurb='Do we have a value at all? If this is false, a ProgressBar should be set to barber pole mode.',
		default=False,
		flags=gobject.PARAM_READWRITE
		)
	
	_finished = None
	_err = None
	_autofinish = True
	
	def __init__(self, autofinish=True):
		super(ProgressTracker, self).__init__()
		self._autofinish = autofinish
	
	def finish(self):
		if self._err is not None:
			raise RuntimeError("Can call only finish() or error(), never both!")
		self._finished = True
		self.emit('finished')
	
	def error(self, exc_type, exc_val, exc_tb):
		if self._finished is not None:
			raise RuntimeError("Can call only finish() or error(), never both!")
		self._err = exc_type, exc_val, exc_tb
		self.emit('error', exc_type, exc_val, exc_tb)
	
	def connect(self, signal, handler):
		if signal == 'finished' and self._finished is not None: handler(self)
		elif signal == 'error' and self._err is not None: handler(self, *self._err)
		super(ProgressTracker, self).connect(signal, handler)
	
	def connect_after(self, signal, handler):
		if signal == 'finished' and self._finished is not None: handler(self)
		elif signal == 'error' and self._err is not None: handler(self, *self._err)
		super(ProgressTracker, self).connect_after(signal, handler)
	
	def connect_object(self, signal, handler, gobj):
		if signal == 'finished' and self._finished is not None: handler(gobj)
		elif signal == 'error' and self._err is not None: handler(gobj, *self._err)
		super(ProgressTracker, self).connect_object(signal, handler, gobj)
		
	def connect_object_after(self, signal, handler, gobj):
		if signal == 'finished' and self._finished is not None: handler(gobj)
		elif signal == 'error' and self._err is not None: handler(gobj, *self._err)
		super(ProgressTracker, self).connect_object_after(signal, handler, gobj)
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		Shortcut to handle setting up the props and to call things.
		
		NOTE: This swallows errors! Be careful when mixing with and try.
		"""
		if exc_type is None:
			if self._autofinish: self.finish()
		else:
			self.emit('error', exc_type, exc_val, exc_tb)
		return True

import jpegtrans, magickwand, imagemagick, pil, gtkpixbuf
MODULES = filter((lambda m: m.module_available()), [jpegtrans, magickwand, imagemagick, pil, gtkpixbuf])

print MODULES


