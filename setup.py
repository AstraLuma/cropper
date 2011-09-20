#!/usr/bin/env python

from distutils.core import setup
import croppertools.cropper

setup(
	name='Cropper',
	version=croppertools.cropper.__version__,
	description='Simple image slicing program',
	long_description=open('README.rst').read(),
	author='James Bliss',
	author_email='james.bliss@astro73.com',
	url='https://github.com/astronouth7303/cropper',
	packages=['croppertools'],
	requires=['pygtk', 'PIL'],
	scripts=['cropper'],
	data_files=[('share/cropper', ['share/cropper.ui', 'share/drag-resize.png'])],
     )
