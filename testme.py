import gc
from greenlet import greenlet, getcurrent

ntests = 0

class myobject(object):
    pass

class mygreenlet(greenlet):
    pass

def crashme(n=7):
    if n > 0:
        #greenlet(crashme).switch(n-1)
        crashme(n-1)
    main = getcurrent()
    finished = [False]
    def victim(*args):
        try:
            main.switch()
        finally:
            print 'finished'
            finished[0] = True
    g = mygreenlet(victim)
    g.switch()
    print '<myobject 0x%x>' % id(g)
    d = {'g': g}
    print '<dict 0x%x>' % id(d)
    a = []
    a.append(a)
    o = myobject()
    o.__dict__ = d
    del d
    a.append(o)
    del o
    del g
    del a
    assert not finished[0]
    gc.set_debug(gc.DEBUG_COLLECTABLE|gc.DEBUG_UNCOLLECTABLE|gc.DEBUG_OBJECTS)
    gc.collect()
    assert not gc.garbage
    assert finished[0]
    global ntests
    ntests += 1

crashme()
print ntests, 'tests'
gc.collect()
