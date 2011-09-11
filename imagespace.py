#-*- coding: utf-8 -*-
"""
The ImageSpace control. Handles the image and the selection boxes on top.

Ignore the errant red outline when not running in optimized mode, it's just our 
change-rect debugger.
"""
from __future__ import with_statement, division, absolute_import
import gtk, gobject, sys, cairo
#from glade import CustomWidget
from rectutils import *
from box import Box
#from gobject.propertyhelper import property as gprop
from usefulgprop import property as gprop

__all__ = 'ImageSpace',

#class ImageSpaceModes(gobject.GEnum):
#	__enum_values__ = {
#		# int : GEnum
#		0: 'SELECT',
#		1: 'INSERT',
#		}
#	#def __new__(cls, value); value must be int
#	# Note that this requires calling some C-level functions and allocating a new GType

def new_adj():
	# Blatently ripped from http://git.gnome.org/browse/pygtk/tree/examples/gtk/scrollable.py
	return gtk.Adjustment(0.0, 0.0, 0.0,
	                      0.0, 0.0, 0.0)

class ImageSpace(gtk.Widget):
	"""
	Displays an image and allows the user to draw boxes over it.
	"""
	
# *****************
# *** CONSTANTS ***
# *****************
	
	SELECT, INSERT = MODES = range(2) #map(ImageSpaceModes, xrange(2))
	
# ******************
# *** PROPERTIES ***
# ******************
	
	__gsignals__ = {
		'box-added'    : (gobject.SIGNAL_RUN_LAST, None, (Box,)),
		'insert-box-changed': (gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, None, (Box,)),
		'realize'      : 'override',
		'expose-event' : 'override',
		'size-allocate': 'override',
		'size-request' : 'override',
		'set-scroll-adjustments': (gobject.SIGNAL_RUN_LAST, None, (gtk.Adjustment, gtk.Adjustment)),
#		'query-tooltip': 'override',
		}
	def _set_zoom(self, value):
		type(self).zoom._default_setter(self, value)
		self._changed_size()
		if self.flags() & gtk.REALIZED: self.queue_draw_area(*self.allocation)
	zoom = gprop(
		type=gobject.TYPE_DOUBLE,
		getter=Ellipsis,
		setter=_set_zoom,
		nick='view zoom',
		blurb='the amount of zoom. 1.0 is normal. Larger numbers mean bigger image.',
		minimum=0.0,
		maximum=10.0, # A really big number
		default=1.0,
		flags=gobject.PARAM_READWRITE
		)
	def _set_image(self, value):
		type(self).image._default_setter(self, value)
		self._changed_size()
	image = gprop(
		type=gtk.gdk.Pixbuf,
		getter=Ellipsis,
		setter=_set_image,
		nick='the image to draw',
		blurb='the background image',
		flags=gobject.PARAM_CONSTRUCT|gobject.PARAM_READWRITE
		)
#	overlap = gprop(
#		type=gobject.TYPE_BOOLEAN,
#		nick='allow overlapping boxes',
#		blurb='Should boxes be allowed to overlap?',
#		flags=gobject.PARAM_CONSTRUCT|gobject.PARAM_READWRITE
#		)
	mode = gprop(
		type=gobject.TYPE_UINT,
		nick='current mode',
		blurb='The current user interaction mode. either selecting or inserting.',
		minimum=min(MODES),
		maximum=max(MODES),
		default=SELECT,
		flags=gobject.PARAM_READWRITE
		)
	# This is a style property
	alpha = gprop(
		type=gobject.TYPE_UINT,
		nick='alpha',
		blurb='The alpha used when drawing the interrior of boxes.',
		minimum=0,
		maximum=255,
		default=64,
		flags=gobject.PARAM_READWRITE
		)
	def _set_model(self, value):
			if self.model is not None:
				self._disconnect_model(self.model)
			type(self).model._default_setter(self, value)
			if value is not None:
				self._connect_model(value)
			if self.flags() & gtk.REALIZED:
				self.queue_draw()
	model = gprop(
		type=gobject.TYPE_OBJECT, #gtk.TreeModel,
		getter=Ellipsis,
		setter=_set_model,
		nick='data model',
		blurb='The model where boxes are pulled from.',
		flags=gobject.PARAM_CONSTRUCT|gobject.PARAM_READWRITE
		)
	def _set_selection(self, value):
			if self.selection is not None:
				self._disconnect_selection(self.selection)
			type(self).selection._default_setter(self, value)
			if value is not None:
				self._connect_selection(value)
			if self.flags() & gtk.REALIZED:
				self.queue_draw()
	selection = gprop(
		type=gobject.TYPE_OBJECT, #gtk.TreeSelection,
		getter=Ellipsis,
		setter=_set_selection,
		nick='tree selection',
		blurb='Selection from a TreeView. If None, manage selection ourselves.',
		flags=gobject.PARAM_READWRITE
		)
	box_col = gprop(
		type=gobject.TYPE_UINT,
		nick='color column',
		blurb='The column to pull colors from.',
#		minimum=0,
#		maximum=sys.maxint,
		default=1,
		flags=gobject.PARAM_CONSTRUCT|gobject.PARAM_READWRITE
		)
	next_color = gprop(
		type=gtk.gdk.Color,
		nick='next color',
		blurb='The color the next box will be. I suggest setting this in the box-added signal.',
		flags=gobject.PARAM_READWRITE
		)
	
# *********************************
# *** BASIC WIDGET HOUSEKEEPING ***
# *********************************
	
	def __init__(self, image=None, model=None, box=1):
#		if __debug__: print "__init__", self, image, model, color, rect
		gtk.Widget.__init__(self)
		# Properties
		self.image = image
		self.model = model
		self.box_col = box
		self.next_color = gtk.gdk.color_parse('#0f0')
		# Other attributes
		self._hadj = self._vadj = None
	
	def do_realize(self):
		# The do_realize method is responsible for creating GDK (windowing system)
		# resources. In this example we will create a new gdk.Window which we
		# then draw on
		
		# First set an internal flag telling that we're realized
		self.set_flags(self.flags() | gtk.REALIZED)
		
		# Create a new gdk.Window which we can draw on.
		# Also say that we want to receive exposure events by setting
		# the event_mask
		self.window = gtk.gdk.Window(
			self.get_parent_window(),
			width=self.allocation.width,
			height=self.allocation.height,
			window_type=gtk.gdk.WINDOW_CHILD,
			wclass=gtk.gdk.INPUT_OUTPUT,
			event_mask=self.get_events() | gtk.gdk.EXPOSURE_MASK
			         | gtk.gdk.BUTTON1_MOTION_MASK
			         | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK
			         | gtk.gdk.POINTER_MOTION_MASK
			         | gtk.gdk.POINTER_MOTION_HINT_MASK)
		
		# Associate the gdk.Window with ourselves, Gtk+ needs a reference
		# between the widget and the gdk window
		self.window.set_user_data(self)
		
		# Attach the style to the gdk.Window, a style contains colors and
		# GC contextes used for drawing
		self.style.attach(self.window)

		# The default color of the background should be what
		# the style (theme engine) tells us.
		self.style.set_background(self.window, gtk.STATE_NORMAL)
		self.window.move_resize(*self.allocation)
		
		# Some extra stuff
		self.gc = self.style.fg_gc[gtk.STATE_NORMAL]
		#self.connect("motion_notify_event", self.do_motion_notify_event)
#		self.connect("query-tooltip", self.do_query_tooltip_event)
		#self.set_tooltip_text('spam&eggs')
	
	def do_unrealize(self):
        # The do_unrealized method is responsible for freeing the GDK resources

        # De-associate the window we created in do_realize with ourselves
		self.window.set_user_data(None)
		#self.window.destroy()
	
	def do_size_request(self, requisition):
		# The do_size_request method Gtk+ is calling on a widget to ask
		# it the widget how large it wishes to be. It's not guaranteed
		# that gtk+ will actually give this size to the widget
		
		if self.image is not None:
			requisition.width = self.image.get_width() * self.zoom
			requisition.height = self.image.get_height() * self.zoom
	
	def do_size_allocate(self, allocation):
		# The do_size_allocate is called by when the actual size is known
		# and the widget is told how much space could actually be allocated
		
		#Save the allocated space
		self.allocation = allocation
		
		self._clear_matrix()
		
		# If we're realized, move and resize the window to the
		# requested coordinates/positions
		if self.flags() & gtk.REALIZED:
			self.window.move_resize(*allocation)
	
	def _changed_size(self):
		"""
		Updates the states related to widget size, image size, zoom, and other 
		metrics.
		
		The tasks performed are:
		* Clear the transformation matrices
		* Update scrollbars
		* queue a resize for ourselves and parent
		"""
		self._clear_matrix()
		
		self._recalc_adjustments()
		
		if self.flags() & gtk.REALIZED:
			self.parent.queue_resize()
			self.queue_resize()
	
# *******************************
# *** TRANSFORMATION MATRICES ***
# *******************************
	
	_w2i_matrix = _i2w_matrix = None
	
	def _clear_matrix(self):
		"""
		Clears the transformation matrices.
		"""
		self._w2i_matrix = self._i2w_matrix = None
	
	def _calc_matrix(self):
		"""
		Calculates the transformation matrices.
		"""
		i2w = cairo.Matrix()
		# Change to centered-origin
		if self.image is not None:
			i2w.translate(-self.image.get_width()/2, -self.image.get_height()/2)
		# Scale
		i2w.scale(self.zoom, self.zoom)
		# Change to Widget's origin
		i2w.translate(self.allocation.width/2, self.allocation.height/2)
		
		self._i2w_matrix = i2w
		
		w2i = cairo.Matrix(*i2w) #copy
		w2i.invert()
		self._w2i_matrix = w2i
	
	def img2widgetcoords(self, x,y):
		"""is.img2widgetcoords(num,num) -> (num, num)
		Converts the given (x,y) from image coordinates to widget coordinates 
		(suitable for using with GTK).
		
		Inverse of widget2imgcoords().
		"""
		if self._i2w_matrix is None: self._calc_matrix()
		return self._i2w_matrix.transform_point(x,y)
	
	def widget2imgcoords(self, x,y):
		"""is.img2widgetcoords(num,num) -> (num, num)
		Converts the given (x,y) from widget coordinates (suitable for using 
		with GTK) to image coordinates.
		
		Inverse of img2widgetcoords().
		"""
		if self._w2i_matrix is None: self._calc_matrix()
		return self._w2i_matrix.transform_point(x,y)
	
	def rect2widget(self, rect):
		x,y = self.img2widgetcoords(rect.x, rect.y)
		# Doesn't check _i2w_matrix since img2widgetcoords() does that
		w,h = self._i2w_matrix.transform_distance(rect.width, rect.height)
		return frect(x,y,w,h)
	
	def rect2img(self, rect):
		# Doesn't check _w2i_matrix since widget2imgcoords() does that
		x,y = self.widget2imgcoords(rect.x, rect.y)
		w,h = self._w2i_matrix.transform_distance(rect.width, rect.height)
		return frect(x,y,w,h)
	
	def alloc2img(self):
		"""is.alloc2img() -> Rectangle
		Translates allocation to the images coordinates.
		"""
		return self.rect2img(self.allocation)
	
# *******************************
# *** BOX TRACKING & HANDLING ***
# *******************************
	
	_temporary_box = None # Used for adding boxes
	_current_box = None # The box we're hovering over, possibly chosen arbitrarily
	_boxes_under_cursor = None
	_changed_rect = None
	
	def find_boxes_under_coord(self,x,y):
		"""is.find_boxes_under_coord(num,num) -> [Box]
		Returns all of the boxes underneath image location (x,y).
		"""
		return tuple(r[self.box_col] for r in self.model if rect_contains(r[self.box_col].rect,x,y))
	
	RESIZE_RANGE = 5
	def find_boxes_coord_near(self, x,y, range=None):
		"""is.find_boxes_coord_near(num,num) -> (Box, dir), ...
		Returns all of the boxes which:
		* are underneath image location (x,y)
		* have an edge near image location (x,y)
		
		If given, range is how close to the edge we need to be (in widget 
		pixels).
		
		dir is intern()'d 'N'orth, 'S'outh, 'E'ast, 'W'est, 'NE', 'NW', 'SW', 
		'SE'.
		
		If the location given is within range of two opposite sides (ie skinny 
		boxes), then the closer of the two is returned
		"""
		if range is None: range = self.RESIZE_RANGE
		range /= self.zoom
		
		
		for box in self.find_boxes_under_coord(x,y):
			dir = ''
			if box.height < range*2:
				# Skinny!
				dir += 'N' if y - box.y < box.y+box.height - y else 'S'
			elif y - box.y <= range:
				dir += 'N'
			elif box.y+box.height - y <= range:
				dir += 'S'
			if box.width < range*2:
				# Skinny!
				dir += 'W' if x - box.x < box.x+box.width - x else 'E'
			elif x - box.x <= range:
				dir += 'W'
			elif box.x+box.width - x <= range:
				dir += 'E'
#			if __debug__: print "find_boxes_coord_near: box, dir: (%r,%r) %r, %r    \r" % (x,y,box, dir),
			sys.stdout.flush()
			if len(dir):
				yield box, (dir)
	
	def _update_boxes(self, x,y):
		"""
		Handles the fairly complex algorithm used to cache-and-calculate the 
		boxes that are underneath the cursor.
		
		Current Caching: A rectangle for which the current state is true.
		"""
		alloc = self.alloc2img()
		
		if not rect_contains(alloc, x,y):
			# The mouse has left the widget
			self._changed_rect = None
			self._boxes_under_cursor = []
			return True
		
		if self._changed_rect is None or not rect_contains(self._changed_rect, x, y):
			if len(self.model) == 0: return False
			# The mouse left the common area
#			if __debug__: print '(%i,%i)' % (x,y),
			
#			if __debug__: print "Old rect:", tuple(self._changed_rect) if self._changed_rect is not None else self._changed_rect,
			self._changed_rect = None
				
			
			# Calculate new boxes
			newboxes = self.find_boxes_under_coord(x,y)
			self._boxes_under_cursor = newboxes
#			if __debug__: print "newboxes:", newboxes,
			
			# Update the caching rectangle
			if len(newboxes):
				changed = newboxes[0].rect
			else: # Outside of any boxes, use allocation
				changed = alloc
			for b in newboxes[1:]:
				changed = changed.intersect(b.rect)
			for r in self.model:
				b = r[self.box_col]
				if b not in newboxes:
					changed = rect_diff(changed, b.rect, (x,y))
			if changed == alloc: # This is so extrodinarily BAD that we should test for it.
				from warnings import warn
				warn("The chosen change rect was the allocation. THIS SHOULD'T HAPPEN.")
				changed = None
#			if __debug__: print "Change rect:", tuple(changed)
			self._changed_rect = changed
			if __debug__: # If debugging, redraw every time the box changes
				self.queue_draw_area(*self.allocation)
			assert changed is None or rect_contains(changed, x,y)
			return True
		else:
			return False
	
	def get_boxes_under_cursor(self,x=None,y=None):
		"""is.get_boxes_under_cursor() -> (Box, ...)
		Return the list of boxes currently under the cursor, in some order
		"""
		if not self._boxes_under_cursor or not self._changed_rect or (x is not None and y is not None):
			# It doesn't matter if these are way off: if the mouse is outside 
			# the cache box, it'll be recalculated.
			if x is None or y is None:
				x,y,_ = self.window.get_pointer()
			x,y = self.widget2imgcoords(x,y)
			self._update_boxes(x,y)
		return self._boxes_under_cursor[:]
	
	def do_box_added(self, box):
		if __debug__: print "box-added", self, box
	
# **************************
# *** DRAWING & EXPOSURE ***
# **************************
	
	SELECTSIZE = 2.0
	TEMP_IS_SELECTED = False
	def do_expose_event(self, event):
		# The do_expose_event is called when the widget is asked to draw itself
		# Remember that this will be called a lot of times, so it's usually
		# a good idea to write this code as optimized as it can be, don't
		# create any resources in here.
		
		# For w/e reason, this has to be created every time
		cr = self.window.cairo_create()
		alloc = self.allocation
		img = self.image
		z = self.zoom
		
		# Do some translation
		if img is not None:
			# Center
			dx = (alloc.width/z - img.get_width()) / 2
			dy = (alloc.height/z - img.get_height()) / 2
		else:
			dx = alloc.width / 2
			dy = alloc.height / 2
		if __debug__:
			print "dx,dy=", (dx, dy)
			if img is not None:
				print "img=", (img.get_width(), img.get_height())
		if self._i2w_matrix is None: self._calc_matrix()
		cr.set_matrix(self._i2w_matrix)
		linewidth = 1.0/z
		
		# Draw image
		if img is not None:
			cr.set_source_pixbuf(img, 0, 0) # set_source_surface()
			cr.rectangle((0,0,img.get_width(), img.get_height()))
			cr.fill()
		
		# Draw boxes on top of it
		# This all works
		cr.set_line_width(linewidth)
		cr.set_line_join(cairo.LINE_JOIN_MITER)
		def draw_box_border(self, c, r, s):
			if s:
				cr.set_line_width(linewidth*self.SELECTSIZE)
			else:
				cr.set_line_width(linewidth)
			# draw border
			cr.set_source_rgba(c.red/0xFFFF, c.green/0xFFFF, c.blue/0xFFFF, 1.0)
			cr.rectangle(r)
			cr.stroke()
		def draw_box_fill(self, c, r, s):
			# draw fill
			if self.alpha > 0:
				cr.set_source_rgba(c.red/0xFFFF, c.green/0xFFFF, c.blue/0xFFFF, self.alpha/0xFF)
				cr.rectangle(r)
				cr.fill()
		
		boxes = []
		def draw_box_row(model, path, row, self):
			box, = model.get(row, int(self.box_col))
			c = box.color
			r = box.rect
			r = gtk.gdk.Rectangle(*r)
			r.width += 1
			r.height += 1
			s = False
			if self.selection is not None:
				s = self.selection.iter_is_selected(row)
			boxes.append((c,r,s))
		
		# Draw the fills
		if self.model is not None:
			self.model.foreach(draw_box_row, self)
			for c,r,s in boxes:
				draw_box_fill(self,c,r,s)
		if self._temporary_box is not None:
			draw_box_fill(self, self._temporary_box.color, self._temporary_box.rect, self.TEMP_IS_SELECTED)
		
		# Draw the strokes
		# We do this second so the fills don't obscure the strokes
		for c,r,s in boxes:
			draw_box_border(self,c,r,s)
		if self._temporary_box is not None:
			draw_box_border(self, self._temporary_box.color, self._temporary_box.rect, self.TEMP_IS_SELECTED)
		
		# Do this last, so that it appears on top of everything
		if __debug__:
			if self._changed_rect is not None:
				draw_box_border(self, gtk.gdk.color_parse('#F00'), self._changed_rect, False)
	
# **********************************
# *** CURSOR TRACKING & HANDLING ***
# **********************************
	
	RESIZE_CURSORS = {
		'N' :gtk.gdk.TOP_SIDE,
		'S' :gtk.gdk.BOTTOM_SIDE,
		'E' :gtk.gdk.RIGHT_SIDE,
		'W' :gtk.gdk.LEFT_SIDE,
		'NE':gtk.gdk.TOP_RIGHT_CORNER,
		'NW':gtk.gdk.TOP_LEFT_CORNER,
		'SE':gtk.gdk.BOTTOM_RIGHT_CORNER,
		'SW':gtk.gdk.BOTTOM_LEFT_CORNER,
		}
	
	_insert_start_coords = None
	
	_rubber_band_start = None
	_box_may_resize = None
	_box_is_resizing = None
	_box_may_resize_dir = None
	_box_is_resizing_dir = None
	def do_motion_notify_event(self, event):
		"""
		Handles updating all the cached info dealing with the mouse (eg, boxes, 
		tooltips).
		"""
		# if this is a hint, then let's get all the necessary 
		# information, if not it's all we need.
		if event.is_hint:
			x, y, state = event.window.get_pointer()
		else:
			x = event.x
			y = event.y
			state = event.state
		
		# Update box underneath cursor, for tooltip
		ix, iy = icoords = self.widget2imgcoords(x,y)
		if __debug__: 
			sys.stdout.write(repr(icoords)+'\r')
			sys.stdout.flush()
		if self._update_boxes(*icoords):
			self.set_tooltip_text(self.get_tooltip_text(self._boxes_under_cursor))
			self.trigger_tooltip_query()
		
		if self.mode == self.INSERT and self._insert_start_coords is not None and state & gtk.gdk.BUTTON1_MASK:
			# Adjust temporary box
			nr = pt2rect(icoords, self._insert_start_coords)
			redraw = nr.union(self._temporary_box.rect)
			self._temporary_box.rect = nr
			#self.queue_draw_area(*redraw)
			self.queue_draw()
			self.emit('insert-box-changed', self._temporary_box)
		elif self._box_is_resizing is not None and state & gtk.gdk.BUTTON1_MASK:
			d = self._box_is_resizing_dir
			b = self._box_is_resizing
			r = frect(*b.rect)
			obox = frect(*b.rect)
			if 'W' in d:
				r.x, r.width = round(ix), round(r.x + r.width - ix)
			elif 'E' in d:
				r.width = round(ix - r.x)
			if 'N' in d:
				r.y, r.height = round(iy), round(r.y + r.height - iy)
			elif 'S' in d:
				r.height = round(iy - r.y)
			b.rect = r
#			if __debug__: print "Resizing: %r (%r,%r) (%r,%r) %r->%r" % (d, x,y, ix,iy, list(obox), list(b.rect))
			self.queue_draw_area(*self.rect2widget(union(obox, b.rect)))
		elif not state & (gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON2_MASK | 
				gtk.gdk.BUTTON3_MASK | gtk.gdk.BUTTON4_MASK | 
				gtk.gdk.BUTTON5_MASK): # Hover
			boxes = tuple(self.find_boxes_coord_near(*icoords)) #FIXME: Use cache
			if len(boxes):
				#if __debug__: print "Nearby Boxes: %r" % (boxes,)
				box, dir = boxes[0]
				self._box_may_resize = box
				self._box_may_resize_dir = dir
				self.window.set_cursor(gtk.gdk.Cursor(self.window.get_display(), self.RESIZE_CURSORS[dir]))
			else:
				self._box_may_resize = self._box_may_resize_dir = None
				self.window.set_cursor(None)
	
	def do_button_press_event(self, event):
		# make sure it was the first button
		if event.button == 1:
			if self._box_may_resize is not None:
				if __debug__: print "Start resize"
				# FIXME: Calculate offset
				self._box_is_resizing = self._box_may_resize
				self._box_is_resizing_dir = self._box_may_resize_dir
			elif self.mode == self.INSERT:
				# Begin new box
				self._insert_start_coords = self.widget2imgcoords(event.x, event.y)
				self._temporary_box = Box(frect(*self._insert_start_coords+(0,0)), self.next_color.copy())
				self.emit('insert-box-changed', self._temporary_box)
			elif self.mode == self.SELECT:
				# Change selection
				# TODO: Rubber banding
				if self.selection is None: return True
				boxes = self.get_boxes_under_cursor(event.x, event.y)
				rows = []
			return True
	
	def do_button_release_event(self, event):
		# make sure it was the first button
		if event.button == 1:
			if self._box_is_resizing is not None:
				if __debug__: print "Stop resize"
				self._box_is_resizing = self._box_may_resize = None
				self._box_is_resizing_dir = self._box_may_resize_dir = None
			elif self.mode == self.INSERT:
				# End new box
				nb = self._temporary_box
				self._insert_start_coords = self._temporary_box = None
				if nb.rect.width == 0 or nb.rect.height == 0: 
					return
				redraw = self.rect2widget(nb.rect)
				redraw.x -= 1
				redraw.y -= 1
				redraw.width += 2
				redraw.height += 2
				self.queue_draw_area(*redraw)
				self.emit('box-added', nb)
				self._changed_rect = None
			elif self.mode == self.SELECT:
				# Change selection
				# TODO: Rubber banding
				if self.selection is None: return True
				rows = []
				boxes = self.get_boxes_under_cursor(event.x, event.y)
				def check(model, path, iter, ua):
					boxes, rows = ua
					rbox, = model.get(iter, int(self.box_col))
					if rbox in boxes:
						rows.append(iter)
				if event.state & gtk.gdk.SHIFT_MASK:
					self.model.foreach(check, (boxes, rows))
					assert len(boxes) == len(rows)
				else:
					self.model.foreach(check, (boxes[0:1], rows))
				if __debug__: print "Boxes: %r" % (boxes,)
				if __debug__: print "Rows: %r" % rows
				selection = self.selection
				if event.state & gtk.gdk.CONTROL_MASK:
					for r in rows: 
						if selection.iter_is_selected(r):
							selection.unselect_iter(r)
						else:
							selection.select_iter(r)
				else:
					selection.unselect_all()
					for r in rows: 
						selection.select_iter(r)
	
# ****************
# *** TOOLTIPS ***
# ****************
	
	def get_tooltip_text(self, boxes):
		if len(boxes) == 0:
			return None
		return '\n'.join(b.dimensions_text() for b in boxes)
	
	def do_query_tooltip(self, x,y, keyboard_mode, tooltip, _=None):
		# If widget wasn't passed as self
		if _ is not None: x,y, keyboard_mode, tooltip = y, keyboard_mode, tooltip, _
		if __debug__: print 'do_query_tooltip',self, x,y, keyboard_mode, tooltip
		ix,iy = self.widget2imgcoords(x,y)
		boxes = self.find_boxes_under_coord(ix,iy)
		if len(boxes) == 0:
			return False
		tooltip.set_text(self.get_tooltip_text(boxes))
		return True
	
# *************************************
# *** MODEL & SELECTION MAINTENANCE ***
# *************************************
	
	_model_listeners = None
	_selection_listeners = None
	
	def _connect_model(self, model):
		self._model_listeners = (
			model.connect('row-changed', self._model_changed),
			model.connect('row-deleted', self._model_changed),
			model.connect('row-inserted', self._model_changed),
			)
	def _disconnect_model(self, model):
		for l in self._model_listeners:
			model.disconnect(l)
		self._model_listeners = ()
	
	def _connect_selection(self, sel):
		self._selection_listeners = (
			sel.connect('changed', self._selection_changed),
			)
	def _disconnect_selection(self, sel):
		for l in self._selection_listeners:
			selection.disconnect(l)
		self._selection_listeners = ()
	
	def _model_changed(self, model, path, iter=None):
		self._changed_rect = None
		if not self.flags() & gtk.REALIZED: return
		if iter is not None:
			self.queue_draw_area(*self.rect2widget(self.model.get(iter, int(self.box_col))[0].rect))
		else:
			self.queue_draw_area(*self.allocation)
	
	def _selection_changed(self, selection):
		if not self.flags() & gtk.REALIZED: return
		self.queue_draw_area(*self.allocation)
	
# ***********************************
# *** SCROLLED WINDOW INTERFACING ***
# ***********************************
	
	_hadj = _vadj = None
	
	def _recalc_adjustments(self):
		h,v = self._hadj, self._vadj
		alloc = self.allocation if self.flags() & gtk.REALIZED else None
		# XXX: Should this be using the transformation matrices as well?
		if h:
			if self.image is not None:
				h.upper = self.image.get_width()
				if alloc is not None:
					h.page_size = alloc.width / self.zoom
					if __debug__: print "h.page_size =", h.page_size
			else:
				h.upper = 0
		if v:
			if self.image is not None:
				v.upper = self.image.get_height()
				if alloc is not None:
					v.page_size = alloc.height / self.zoom
			else:
				v.upper = 0
	
	def do_set_scroll_adjustments(self, hadj, vadj):
		if __debug__: print "do_set_scroll_adjustments", hadj, vadj
		# Blatently ripped from http://git.gnome.org/browse/pygtk/tree/examples/gtk/scrollable.py
		if not hadj and self._hadj:
			hadj = new_adj()
		
		if not vadj and self._vadj:
			vadj = new_adj()
		
		if self._hadj and self._hadj != hadj:
			self._hadj.disconnect(self._hadj_changed_id)
		
		if self._vadj and self._vadj != vadj:
			self._vadj.disconnect(self._vadj_changed_id)
		
		hadj.lower = vadj.lower = 0
		
		need_adjust = False
		
		if self._hadj != hadj:
			self._hadj = hadj
			self._hadj_changed_id = hadj.connect(
				"value-changed",
				self._adjustment_changed)
			need_adjust = True
		
		if self._vadj != vadj:
			self._vadj = vadj
			self._vadj_changed_id = vadj.connect(
				"value-changed",
				self._adjustment_changed)
			need_adjust = True
		
		if need_adjust and vadj and hadj:
			self._changed_size()
			self._adjustment_changed()
	
	def _adjustment_changed(self, adj=None):
		# Blatently ripped from http://git.gnome.org/browse/pygtk/tree/examples/gtk/scrollable.py
		if self.flags() & gtk.REALIZED:
			# Update some variables and redraw
			pass
	
# ******************************
# *** ADVANCED IMAGE LOADING ***
# *** (namely PixbufLoader)  ***
# ******************************
	
	_pbl_handlers = None # signal handles for PixbufLoader
	
	def loadfrompixbuf(self, pbloader):
		"""is.loadfrompixbuf(PixbufLoader) -> None
		Prepares the ImageSpace to load an image from PixbufLoader. The caller 
		is expected to create the PixbufLoader and call its write() method.
		"""
		self.image = None
		self._pbl_handlers = (
			pbloader.connect('area-prepared', self.pbl_do_prepared),
			pbloader.connect('area-updated', self.pbl_do_updated),
			pbloader.connect('closed', self.pbl_do_closed),
			)
	
	def pbl_do_prepared(self, pbloader):
		self.image = pbloader.get_pixbuf()
	
	def pbl_do_updated(self, pbloader, x, y, width, height):
		if self.flags() & gtk.REALIZED:
			redraw = self.rect2widget(frect(x,y-1,width,height+1)) # Go back one row
			self.queue_draw_area(*redraw)
	
	def pbl_do_closed(self, pbloader):
		for h in self._pbl_handlers:
			pbloader.disconnect(h)
		self._pbl_handlers = None
	
# ****************************************
# *** PUBLIC UTILITIES & MISCELLANEOUS ***
# ****************************************
	
	def zoom_to_size(self, *p):
		"""is.zoome_to_size() -> None
		Adjusts the zoom so the image fills the allocation.
		"""
		if self.image is None or self.allocation is None:
			return
		if __debug__: print self.allocation.width, self.image.get_width()
		if __debug__: print self.allocation.width, self.image.get_width(), self.allocation.width/self.image.get_width()
		z = min(
			self.allocation.width/self.image.get_width(),
			self.allocation.height/self.image.get_height()
			)
		if __debug__: print "zoom_to_size", "z=", z
		self.zoom = z
		if self.flags() & gtk.REALIZED:
			self.queue_draw_area(*self.allocation)
	
	# This should probably be in the application, not the widget
	def do_scroll_event(self, event):
		"""
		Zooms in or out
		"""
		if event.state & gtk.gdk.CONTROL_MASK:
			if event.direction == gtk.gdk.SCROLL_UP:
				self.zoom *= 1.1
			elif event.direction == gtk.gdk.SCROLL_DOWN:
				self.zoom /= 1.1
	
	
#CustomWidget(ImageSpace)

if __name__ == "__main__":
	from box import Box
	from boxmodel import BoxListStore
	win = gtk.Window()
	win.set_border_width(5)
	win.set_title('Widget test')
	win.connect('delete_event', gtk.main_quit)
#	win.connect('size_allocate', lambda *p: w.zoom_to_size())
	
	frame = gtk.Frame("Example frame")
	win.add(frame)
	
	bls = BoxListStore()
	bls.append(['test.1.gif', Box(gtk.gdk.Rectangle(124,191,248,383), gtk.gdk.color_parse('#F0A'))])
	bls.append(['test.2.gif', Box(gtk.gdk.Rectangle(50,100,200,300), gtk.gdk.color_parse('#AF0'))])
	print "Model data:", map(tuple, bls)
	w = ImageSpace(model=bls)
	w.alpha = 0x55
	w.zoom = 0.5
	w.image=gtk.gdk.pixbuf_new_from_file('test.gif')
	frame.add(w)
	
	win.show_all()
	w.zoom_to_size()
	print 'Window:', w.window
	gtk.main()

