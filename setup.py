#!/usr/bin/env python

import sys
from distutils.core import setup
import croppertools.cropper

# Application registration
if sys.platform == 'linux2':
	morefiles = [
		('/usr/share/applications', [
			'share/cropper.desktop', 
			]
		),
		]
else:
	morefiles = []

setup(
	name='cropper',
	version=croppertools.cropper.__version__,
	description='Simple image slicing program',
	long_description=open('README.rst').read(),
	author='James Bliss',
	author_email='james.bliss@astro73.com',
	url='https://astronouth7303.github.com/cropper',
	packages=['croppertools'],
	requires=['pygtk', 'PIL'],
	scripts=['cropper'],
	data_files=[
		('share/cropper', [
			'share/cropper.ui', 
			'share/drag-resize.png', 
			'share/logo.svg',
			]
		),
	]+morefiles,
	download_url='https://github.com/astronouth7303/cropper/tarball/v'+croppertools.cropper.__version__,
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Environment :: X11 Applications :: GTK',
		'Intended Audience :: End Users/Desktop',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Topic :: Artistic Software',
		'Topic :: Multimedia :: Graphics',
		'Topic :: Multimedia :: Graphics :: Editors',
		'Topic :: Utilities',
		],
	)
