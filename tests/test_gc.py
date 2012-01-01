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

    if greenlet.GREENLET_USE_GC_FULL:
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

        def test_finalizer_ref(self):
            class object_with_finalizer(object):
                def __del__(self):
                    pass
            def greenlet_body():
                g = greenlet.getcurrent()
                o = object_with_finalizer()
                try:
                    g.parent.switch(g)
                finally:
                    pass
            o = weakref.ref(greenlet.greenlet(greenlet_body).switch())
            gc.collect()
            self.assertTrue(o() is None)
            self.assertFalse(gc.garbage, gc.garbage)

        def test_finalizer_indirect_ref(self):
            # Why does this crash:
            # - order of object creation is important
            # - array is created first, so it is moved to unreachable first
            # - we create a cycle between a greenlet and this array
            # - we create an object that participates in gc is only
            #   referenced by the greenlet, and would corrupt gc
            #   lists on destruction, the easiest is to use
            #   an object with a finalizer
            # - because array is the first object in unreachable it is
            #   cleared first, which causes all references to greenlet
            #   to disappear and causes greenlet to be destroyed, but since
            #   it is still live it causes a switch during gc, which causes
            #   an object with finalizer to be destroyed, which causes stack
            #   corruption and thus a crash
            # - because greenlet's tp_clear is never called there's no
            #   chance to insert safeguard sentinels before switching (also
            #   no way to know whether destruction is due to gc or not,
            #   whether greenlet itself is on gc lists or not, so no way
            #   to reliably find unreachable/finalizer gc list heads on stack)
            class object_with_finalizer(object):
                def __del__(self):
                    pass
            array = []
            parent = greenlet.getcurrent()
            def greenlet_body():
                a = array
                o = object_with_finalizer()
                try:
                    parent.switch()
                finally:
                    pass
            g = greenlet.greenlet(greenlet_body)
            array.append(g)
            g.switch()
            array = None
            g = weakref.ref(g)
            gc.collect()
            self.assertTrue(g() is None)
            self.assertFalse(gc.garbage, gc.garbage)
