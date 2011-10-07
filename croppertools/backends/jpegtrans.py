# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Implements loseless JPEG cropping in limited cases.

Note: This is VERY limited. It only works if the box is along compression block 
borders (8x8 px).
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker

def module_available():
	return False

