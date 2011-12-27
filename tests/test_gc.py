import gc
import sys
import unittest
import weakref

import greenlet

def _live_greenlet_body():
    g = greenlet.getcurrent()
    try:
        g.parent.switch(g)
    finally:
        pass

def _switch_to_parent():
    g = greenlet.getcurrent()
    g.parent.switch(g)

def _live_subframe_body():
    g = greenlet.getcurrent()
    try:
        _switch_to_parent()
    finally:
        pass

def _live_stub_body(g):
    try:
        g.parent.switch(g)
    finally:
        pass

class _live_throw_exc(Exception):
    def __init__(self, g):
        self.greenlet = g

def _live_throw_body(g):
    try:
        g.parent.throw(_live_throw_exc(g))
    finally:
        pass

def _live_cluster_body(g):
    o = weakref.ref(greenlet.greenlet(_live_greenlet_body).switch())
    gc.collect()
    try:
        g.parent.switch(g)
    finally:
        pass

def _make_green_weakref(body, kw=False):
    g = greenlet.greenlet(body)
    try:
        if kw:
            g = g.switch(g=g)
        else:
            g = g.switch(g)
    except _live_throw_exc:
        pass
    return weakref.ref(g)

class GCTests(unittest.TestCase):
    def test_circular_greenlet(self):
        class circular_greenlet(greenlet.greenlet):
            pass
        o = circular_greenlet()
        o.self = o
        o = weakref.ref(o)
        gc.collect()
        self.assertTrue(o() is None)
        self.assertFalse(gc.garbage, gc.garbage)

    def test_dead_circular_ref(self):
        o = weakref.ref(greenlet.greenlet(greenlet.getcurrent).switch())
        gc.collect()
        self.assertTrue(o() is None)
        self.assertFalse(gc.garbage, gc.garbage)

    if greenlet.GREENLET_USE_GC:
        # These only work with greenlet gc support

        def test_inactive_ref(self):
            class inactive_greenlet(greenlet.greenlet):
                def __init__(self):
                    greenlet.greenlet.__init__(self, run=self.run)
                def run(self):
                    pass
            o = inactive_greenlet()
            o = weakref.ref(o)
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

    if greenlet.GREENLET_USE_GC and greenlet.GREENLET_USE_GC_FULL:
        # These only work with greenlet full gc support

        def test_live_circular_ref(self):
            o = weakref.ref(greenlet.greenlet(_live_greenlet_body).switch())
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def test_live_subframe_ref(self):
            o = weakref.ref(greenlet.greenlet(_live_subframe_body).switch())
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def test_stub_circular_ref(self):
            o = _make_green_weakref(_live_stub_body)
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def _disabled_test_stub_circular_kw_ref(self):
            # Unfortunately keyword arguments cannot be traversed
            o = _make_green_weakref(_live_stub_body, kw=True)
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def test_stub_throw_ref(self):
            o = _make_green_weakref(_live_throw_body)
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def test_stub_cluster_ref(self):
            o = _make_green_weakref(_live_cluster_body)
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)
