# -*- tab-width: 4; use-tabs: 1; coding: utf-8 -*-
# vim:tabstop=4:noexpandtab:
"""
Uses the external ImageMagick program. Must install ImageMagick seperately.
"""
from __future__ import division, absolute_import, with_statement
from ..backends import ProgressTracker

def module_available():
	return False
