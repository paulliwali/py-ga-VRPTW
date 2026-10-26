# -*- coding: utf-8 -*-

import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

from . import mvcore
mvCore = mvcore

__all__ = ['BASE_DIR', 'mvcore', 'mvCore']
