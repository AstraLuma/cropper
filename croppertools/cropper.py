#!/usr/bin/python -O
#-*- coding: utf-8 -*-
"""
cropper [file]

An app to easily crop an image into multiple pieces.
"""
from __future__ import with_statement, division, absolute_import
import gtk
gtk.gdk.threads_init()
#gobject.threads_init()
import gio, gobject, glib
from optparse import OptionParser
import sys, os, subprocess
import PIL.Image
from cStringIO import StringIO

from .gbuilder import BuilderWindow, resource
from .box import Box
from .boxmodel import BoxListStore, make_absolute
from .imagespace import ImageSpace
from .backends import CropManager

__version__ = 'dev'

BUFSIZE = 8*1024 #8K # Amount to read in one go

parser = OptionParser()
#parser.add_option("-f", "--file", dest="filename",
#                  help="write report to FILE", metavar="FILE")
#parser.add_option("-q", "--quiet",
#                  action="store_false", dest="verbose", default=True,
#                  help="don't print status messages to stdout")

def permIter(seq):
	"""
	Given some sequence 'seq', returns an iterator that gives
	all permutations of that sequence.
	"""
	# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/105962
	## Base case
	if len(seq) == 1:
		yield seq[0]
	else:
		## Inductive case
		for i in range(len(seq)):
			element_slice = seq[i:i+1]
			rest_iter = permIter(seq[:i] + seq[i+1:])
			for rest in rest_iter:
				yield element_slice + rest

def find_pictures_dir():
	"""find_pictures_dir() -> gio.File
	Returns the user's pictures folder.
	"""
	return gio.File(path=glib.get_user_special_dir(glib.USER_DIRECTORY_PICTURES))

class Cropper(BuilderWindow):
	__glade_file__ = 'cropper.ui'
	
	window = property(lambda self: self.wCropper)
	#TODO: Change this to directory and pattern, so we can do non-file sources.
	filename = None
	crop_dir = None
	crop_pattern = '%i'
	def __init__(self, options, args, *pargs, **kwargs):
		if __debug__: print 'Cropper.__init__()'
		
		#FIXME: Do this in the XML, from the factory
		self.wCropper.set_icon_from_file(resource('logo.svg'))
		
		self.crop_dir = find_pictures_dir()
		self.fcbCropDir.set_current_folder_file(self.crop_dir)
		self.crop_pattern = '%i'
		
		#TODO: Put all of this into GtkBuilder
		self.model = BoxListStore()
		self.model.exist_image = 'filesave'
		self.model.no_exist_image = 'filenew'
		
		self.tvAreas.set_model(self.model)
		self.tvAreas.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		self.tvAreas.get_selection().connect('changed', self.on_selection_changed)
		
		self.isImage = ImageSpace(model=self.model, box=1)
		self.isImage.selection = self.tvAreas.get_selection()
		self.isImage.mode = ImageSpace.INSERT
		self.isImage.next_color = gtk.gdk.color_parse('#A0F')
		self.isImage.connect('box-added', self.on_box_added)
#		self.isImage.connect('insert-box-changed', self.on_insert_box_changed)
		self.swImage.add(self.isImage)
		
		self.crpExists = gtk.CellRendererPixbuf()
		self.crtFilename = gtk.CellRendererText()
		self.crtFilename.set_property('editable', True)
		self.crtFilename.connect('edited', self.on_cell_edited, self.model)
		self.crtColor = gtk.CellRendererText()
		self.crtColor.set_property('background-set', True)
		self.crtColor.set_property('text', ' ')
		
		self.tvcFile = gtk.TreeViewColumn()
		self.tvcFile.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
		self.tvcFile.pack_start(self.crpExists, False)
		self.tvcFile.set_attributes(self.crpExists, icon_name=10)
		self.tvcFile.pack_start(self.crtFilename, True)
		self.tvcFile.set_attributes(self.crtFilename, text=2)
		self.tvcColor = gtk.TreeViewColumn()
		self.tvcColor.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
		self.tvcColor.pack_start(self.crtColor, True)
		self.tvcColor.set_attributes(self.crtColor, background_gdk=8)
		
		self.tvAreas.append_column(self.tvcFile)
		self.tvAreas.append_column(self.tvcColor)
		self.tvAreas.set_headers_visible(False)
		self.tvAreas.set_tooltip_column(11)
		
		self.isImage.connect("drag-data-received", self.on_drag_data_received)
		self.isImage.drag_dest_set(
			gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_HIGHLIGHT | gtk.DEST_DEFAULT_DROP,
			[ ( "text/uri-list", 0, 0 ) ],
			gtk.gdk.ACTION_COPY)
		
		if len(args):
			if __debug__: print "args: %r" % args
			self.Open(file=make_absolute(args[0]))
#		self.window.connect('key-press-event', self._keypress)
	
#	def _keypress(self, window, event):
#		if __debug__: print "Keypress: %r %r" % (event.keyval, event.state)
#		return False
	
	def present(self):
#		self.preshow()
		self.wCropper.show_all()
		self.wCropper.present()
	
	def add_box(self, fn, box, color=None):
		if color is not None:
			if isinstance(color, basestring):
				color = gtk.gdk.color_parse(color)
			if not isinstance(box, gtk.gdk.Rectangle):
				box = gtk.gdk.Rectangle(*box)
			box = Box(box, color)
		self.model.append([fn, box])
	
	def get_next_filename(self):
		if self.filename is None:
			return ''
		return self.crop_pattern % len(self.model)
	
	_color_iter = None
	def get_next_color(self, color):
		if self._color_iter is None:
			self._color_iter = (gtk.gdk.color_parse('#'+p) for p in permIter('F0A'))
		try:
			return self._color_iter.next()
		except StopIteration:
			self._color_iter = None
			return self.get_next_color(color)
	
	def show_error_dialog(self, msg, sec_msg):
		"""
		Displays an error dialog. We don't care what the user clicks on.
		"""
		dlg = gtk.MessageDialog(self.wCropper, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
		dlg.format_secondary_text(sec_msg)
		dlg.connect('response', lambda *_: dlg.destroy())
		dlg.show_all()
	
	# Event handlers
	def on_delete_event(self, widget, event):
		gtk.main_quit()
	
	def on_box_added(self, widget, box):
		self.model.append([self.get_next_filename(), box])
		self.isImage.next_color = self.get_next_color(self.isImage.next_color)
	
	def on_selection_changed(self, selection):
		self.aDelete.set_sensitive(bool(selection.count_selected_rows()))
	
	def on_drag_data_received(self, widget, context, x, y, selection, targetType, time):
		print widget, context, x, y, selection, targetType, time
		print selection.selection, selection.target, selection.type, selection.format
		print repr(selection.get_uris())
		uri = selection.get_uris()[0]
		self.Open(file=gio.File(uri=uri))
		context.finish(True, False, time)
	
	def on_cropdir_set(self, widget):
		if __debug__: 
			print "on_cropdir_set", widget, self.fcbCropDir.get_file()
		self.crop_dir = self.fcbCropDir.get_file()
	
	def on_cell_edited(self, cell, path, new_text, model):
		i = model.get_iter(path)
		#FIXME: On windows, add extension if it's not there.
		model.set_value(i, 0, new_text)
	
#########
# ACTIONS
#########
	
	def Open(self, action=None, **kwargs):
		if __debug__: print 'Open'
		
		if 'file' in kwargs:
			filename = kwargs['file']
		else:
			dlg = gtk.FileChooserDialog(parent=self.wCropper,
				action=gtk.FILE_CHOOSER_ACTION_OPEN, 
				buttons=(
					gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
					gtk.STOCK_OPEN, gtk.RESPONSE_OK,
					)
				)
			if self.filename:
				dlg.set_file(self.filename)
			else:
				dlg.set_current_folder_file(self.crop_dir)
			dlg.set_use_preview_label(True)
			dlg.set_select_multiple(False)
			if dlg.run() in (gtk.RESPONSE_CANCEL, gtk.RESPONSE_NONE):
				dlg.destroy()
				return
			filename = dlg.get_file()
			dlg.destroy()
		
		self.filename = filename
		
		# Open image
		self.model.clear()
		#Use gtk.gdk.PixbufLoader
		# open the file
		pbl = gtk.gdk.PixbufLoader()
		self.isImage.loadfrompixbuf(pbl)
		self._loadfromgio(pbl, filename)
		
		self.crop_dir = filename.get_parent()
		self.fcbCropDir.set_current_folder_file(self.crop_dir)
		def qia(cd, result):
			fi = cd.query_info_finish(result)
			cdi = fi.get_attribute_as_string(gio.FILE_ATTRIBUTE_ACCESS_CAN_WRITE)
			if cdi is None or cdi is False:
				# Can't write to the same directory, prompt later.
				self.crop_dir = find_pictures_dir()
				self.fcbCropDir.set_current_folder_file(self.crop_dir)
		self.crop_dir.query_info_async(gio.FILE_ATTRIBUTE_ACCESS_CAN_WRITE, qia)
		before, after = os.path.splitext(filename.get_basename())
		self.crop_pattern = before+'.%i'+after
	
	imagedata = None
	
	def _loadfromgio(self, pbl, fil):
		#TODO: Reimplement progressive reading
		def _open(f, result):
			try:
				s = fil.read_finish(result)
#			except (gio.Error), err:
			except Exception, err:
				self.show_error_dialog("Error loading image", err.message)
			else:
				data = s.read()
				self.imagedata += data
				try:
					pbl.write(data)
				except Exception, err:
					self.show_error_dialog("Error loading image", err.message)
			finally:
				try:
					pbl.close()
				except Exception, err:
					if self.imagedata:
						self.show_error_dialog("Error loading image", err.message)
					else:
						pass # Not really an error
		self.imagedata = ''
		fil.read_async(_open)
	
	def Crop(self, action):
		if __debug__: print 'Crop'
		if self.crop_dir is None:
			#Ask the user
			dlg = gtk.FileChooserDialog(parent=self.wCropper,
				action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, 
				buttons=(
					gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
					gtk.STOCK_OPEN, gtk.RESPONSE_OK,
					)
				)
			dlg.set_file(self.filename)
			dlg.set_use_preview_label(True)
			dlg.set_select_multiple(False)
			if dlg.run() in (gtk.RESPONSE_CANCEL, gtk.RESPONSE_NONE):
				dlg.destroy()
				return
			filename = dlg.get_file()
			dlg.destroy()
		
		#TODO: Check for conflicts, and ask user (make use of gio etags?)
		cm = CropManager(None, self.image, self.imagedata)
		for r in self.model:
			fn, box = r[0],r[1]
			dest = self.crop_dir.get_child(fn)
			print self.crop_dir, dest
			sync = cm.do_crop(box.rect, fn)
			sync.connect('done', self.crop_done, row)
	
	def crop_done(self, row):
		self.model.row_changed(row)
	
	def Quit(self, action):
		self.wCropper.destroy()
	
	def Clear(self, action):
		if __debug__: print 'Clear'
		self.model.clear()
	
	def Cut(self, action):
		if __debug__: print 'Cut'
		pass
	
	def Copy(self, action):
		if __debug__: print 'Copy'
		pass
	
	def Paste(self, action):
		if __debug__: print 'Paste'
		pass
	
	def Delete(self, action):
		if __debug__: print 'Delete'
		model, rows = self.tvAreas.get_selection().get_selected_rows()
		rows = map(model.get_iter, rows)
		for row in rows:
			model.remove(row)
	
	def SelectAll(self, action):
		self.tvAreas.get_selection().select_all()
	
	def ZoomIn(self, action):
		self.isImage.zoom *= 1.1
	
	def ZoomOut(self, action):
		self.isImage.zoom /= 1.1
	
	def ZoomNormal(self, action):
		self.isImage.zoom = 1.0
	
	def ZoomFit(self, action):
		if __debug__: print "ZoomFit"
		self.isImage.zoom_to_size()
	
	def FlipHorizontal(self, action):
		pass
	
	def FlipVertical(self, action):
		pass
	
	def RotateCW(self, action):
		pass
	
	def RotateCCW(self, action):
		pass
	
	def EditPreferences(self, action):
		pass
	
	def AutoShrink(self, action):
		# Shrink boxes to image size
		pass
	
	def About(self, action):
		dlg = gtk.AboutDialog()
		props = {
			'version': __version__,
			'name': 'cropper',
			'authors': ['James Bliss <james.bliss@astro73.com>'],
			'copyright': u'\N{COPYRIGHT SIGN} 2011 James Bliss',
			'website': 'https://astro73.com/cropper'
			}
		if self.wCropper.get_property('icon-name'):
			props['logo-icon-name'] = self.wCropper.get_property('icon-name')
		elif self.wCropper.get_property('icon'):
			props['logo'] = self.wCropper.get_property('icon')
		for k,v in props.iteritems():
			dlg.set_property(k,v)
		dlg.run()
		dlg.destroy()
	
	def Add(self, action, value):
		if action == value:
			if __debug__: print "Add"
			self.isImage.mode = ImageSpace.INSERT
	
	def Select(self, action, value):
		if action == value:
			if __debug__: print "Select"
			self.isImage.mode = ImageSpace.SELECT

def main():
	options, args = parser.parse_args(sys.argv[1:])
	app = Cropper(options=options, args=args)
	
#	app.add_box('test1.gif', ( 75,131,354,547), '#F0A')
#	app.add_box('test2.gif', ( 15, 22,467,191), '#AF0')
#	app.add_box('test3.gif', (273, 37,204,712), '#0AF')
#	app.add_box('test4.gif', ( 18,622,470,124), '#0F0')
#	app.add_box('test5.gif', ( 11, 20,178,722), '#00F')
#	app.isImage.image = gtk.gdk.pixbuf_new_from_file('test.gif')
#	app.isImage.mode = ImageSpace.INSERT
	
#	app.wCropper.set_default_size(700, 1000)
	
	# Run
	app.present()
	if __debug__: print "Model data:", map(tuple, app.model)
	if __debug__: gtk.gdk.set_show_events(True)
	gtk.main()
