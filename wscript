import os
from build import CPPOptionsContext, enableWafUnitTests
from waflib import Scripting, Options, Context

VERSION = '3.0-dev'
APPNAME = 'CODA-OSS-LITE'
Context.APPNAME = APPNAME
top  = '.'
out  = 'target'

DIRS = 'modules'

TOOLS = 'build'

def options(opt):
    opt.load(TOOLS, tooldir='./build/')
    # always set_options on all
    opt.recurse(DIRS)

def configure(conf):
    conf.options.swigver = '3.0.12'
    conf.load(TOOLS, tooldir='./build/')
    conf.recurse(DIRS)

def build(bld):
    bld.recurse(DIRS)
    enableWafUnitTests(bld)

def distclean(ctxt):
    ctxt.recurse(DIRS)
    Scripting.distclean(ctxt)
