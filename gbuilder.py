#-*- coding: utf-8 -*-
"""
Defines a class which allows for easy use of GtkBuilder. Based on SubIM.
"""
## (c) 2007 James Bliss <http://www.astro73.com/>
## This code is freely usable and modifiable for any purpose with these 
## conditions:
##  1. This notice remains here
##  2. You send me a note that you're using it. I just like to know.
import gtk
__all__ = 'BuilderWindow', 'resource'

class BuilderWindow(object):
	"""
	Inherit from this in order to get some cool GtkBuilder automagick.
	
	Class properties:
	* __roots__: a list of names of the root widgets to load. If unset, all 
	             widgets are loaded.
	* __glade_file__: The XML file containing the UI information.
	
	For all controls in the XML, a property matching their ID is assigned to it.
	ie, if you have a control with id="MyButton", then 
	MyApp("myui.xml").MyButton would be that button.
	
	Properties:
	 * _builder - The gtk.Builder instance from which our widgets were loaded.
	"""
	
	__roots__ = None
	__glade_file__ = None
	__slots__ = '_builder', '__dict__', '__weakref__'
	
	def __getattr__(self, name):
		val = None
		if self._builder:
			val = self._builder.get_object(name)
		if val is not None:
			setattr(self, name, val)
			return val
		else:
			raise AttributeError, "%r object has no attribute %r" % (type(self).__name__, name)
	
	def __new__(cls, domain=None, *pargs, **kwargs):
		"""BuilderWindow(fname, root="", domain="") -> BuilderWindow
		 * root : the widget node in fname to start building from
		 * domain : the translation domain for the XML file (or "" for default)
		
		Note that when possible, root is filled in automatically (ie, when 
		__roots__ is 1 item.)
		
		If you need to perform initialization, define an __init__() method. It
		will be called after the XML is loaded, events connected, etc.
		"""
		
		self = super(BuilderWindow, cls).__new__(cls, domain=domain, *pargs, **kwargs)
		
		# Get the XML
		fname = resource(cls.__glade_file__)
		self._builder = gtk.Builder()
		if domain:
			self._builder.set_translation_domain(domain)
		self._builder.add_from_file(fname)
		
		# Connect events
		self._builder.connect_signals(self)
		return self

class ResourceNotFoundWarning(Warning):
	"""
	Indicates that a resource could not be located.
	"""
	__slots__ = 'filename',
	def __init__(self, fn):
		super(ResourceNotFoundWarning, self).__init__()
		self.filename = fn
	def __unicode__(self):
		return u"Couldn't find resource %r" % self.filename
	def __str__(self):
		return str(unicode(self))

def resource(fn, sec="share", appname=None):
	"""resource(filename. section="share", appname=None) -> string
	Attempts to locate a file given a section in a cross-platform manner.
	
	It searches a list of common linux prefix paths, the same dir as the 
	started script (sys.argv[0]), etc.
	
	appname defaults to the script name.
	
	The list of searched directories is as follows:
	* <script dir>
	* <sys.prefix>/<section>/<appname>
	* /usr/local/<section>/<appname>
	* /usr/<section>/<appname>
	* /opt/<section>/<appname>
	* /<section>/<appname>
	* ~/.local/<section>/<appname>
	* <script dir>/../<section>/<appname>
	* <script dir>/<section>/<appname>
	* ../<section>/<appname>
	
	When everything fails, just returns the passed-in file name (ie the current 
	directory) and raises a warning.
	
	Some special sections:
	* $var - Adds /var/lib to the mix (dollar sign stripped before using the 
	  normal list)
	* doc - Adss the whole list using share/doc as the section
	
	This function is geared towards files that are installed with the script, 
	not files that are created by the app (eg in /var/run, /var/log, /tmp)
	"""
	script = sys.argv[0]
	if appname is None:
		appname = os.path.basename(script)
	def _resource_paths(fn,sec,appname):
		if sec[0] == '$':
			sec=sec[1:]
		return [
			os.path.dirname(os.path.abspath(script)), # For development and Win32
			os.path.join(sys.prefix, sec, appname), # Assuming a single, global prefix
			# And now for some common prefix's
			'/'+os.path.join('usr', 'local', sec, appname),
			'/'+os.path.join('usr', sec, appname),
			'/'+os.path.join('opt', sec, appname),
			'/'+os.path.join(sec, appname),
			os.path.join(os.path.expanduser('~'), '.local', sec, appname),
			# Relative to the script
			os.path.join(os.path.dirname(script), os.pardir, sec, appname),
			os.path.join(os.path.dirname(script), sec, appname),
			# Now we're getting desparate
			os.path.join(os.pardir, sec, appname),
			]
	paths = _resource_paths(fn,sec,appname)
	if sec == '$var':
		paths.append('/'+os.path.join('var', 'lib', appname))
	elif sec == 'doc':
		paths += _resource_paths(fn, 'share/doc', appname)
	for path in paths:
		try:
			f = os.path.join(path, fn)
			if os.path.exists(f):
				return f
		except:
			pass
	else:
		import warnings
		warnings.warn(ResourceNotFoundWarning(fn))
		return fn #Can't actually find it

