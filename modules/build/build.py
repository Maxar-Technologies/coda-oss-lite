import sys, os, types, re, fnmatch, subprocess
from os.path import split, isdir, isfile, exists, splitext

import Options, Utils, Logs
from Configure import conf
from Build import BuildContext
from TaskGen import taskgen, feature, after, before


# provide a partial function if we don't have one
try:
    from functools import partial
except:
    def partial(fn, *cargs, **ckwargs):
        def call_fn(*fargs, **fkwargs):
            d = ckwargs.copy()
            d.update(fkwargs)
            return fn(*(cargs + fargs), **d)
        return call_fn


class CPPBuildContext(BuildContext):
    """
    Create a custom context for building C/C++ modules/plugins
    """
    def __init__(self):
        BuildContext.__init__(self)
    
    def safeVersion(self, version):
        return re.sub(r'[^\w]', '.', version)
    
    def __getDefines(self, env):
        defines = []
        for k, v in env.defines.iteritems():
            if v is not None and v != ():
                if k.startswith('HAVE_') or k.startswith('USE_'):
                    defines.append(k)
                else:
                    defines.append('%s=%s' % (k, v))
        return defines

    def pprint(self, *strs, **kw):
        colors = kw.get('colors', 'blue')
        if type(colors) == str:
            colors = colors.split()
        colors = map(str.upper, colors)
        for i, s in enumerate(strs):
            sys.stderr.write("%s%s " % (Logs.colors(colors[i % len(colors)]), s))
        sys.stderr.write("%s%s" % (Logs.colors.NORMAL, os.linesep))
    
    def runUnitTests(self, tests, path):
        path = path or self.path.abspath()
        
        def _isTest(x):
            isTest = os.path.isfile(x) and os.access(x, os.X_OK) and \
                           splitext(split(x)[1])[0] in tests
            if isTest and sys.platform.startswith('win'):
                isTest = x.endswith('.exe')
            elif isTest:
                isTest = split(x)[1] in tests
            return isTest
        
        exes = filter(_isTest, map(lambda x: os.path.join(path, x),
                                  os.listdir(path)))
        
        if exes:
            self.pprint('Running Unit Tests:', path, colors='blue pink')
            passed, failed = [], []
            for test in exes:
                stdout = stderr = subprocess.PIPE
                p = subprocess.Popen([test], shell=True, stdout=stdout, stderr=stderr)
                stdout, stderr = p.communicate()
                rc = p.returncode
                passed.extend(map(lambda x: (split(test)[1], x),
                                  filter(lambda x: x.find('PASSED') >= 0, stderr.split('\n'))))
                if rc != 0:
                    fails = map(lambda x: (split(test)[1], x),
                                filter(lambda x: x.find('FAILED') >= 0, stderr.split('\n')))
                    if fails:
                        failed.extend(fails)
                    else:
                        failed.append((split(test)[1],
                                       'FAILURE: %d : %s' % (p.returncode, stderr.strip())))
            
            num = len(passed) + len(failed)
            if num > 0:
                passPct = 100.0 * len(passed) / num
                self.pprint('Results:', '%d of %d Test(s) Passed (%.2f%%)' % (len(passed), num, passPct),
                           colors='blue pink')
                for test, err in failed:
                    self.pprint(test, '-->', err, colors='blue normal red')
            else:
                self.pprint('No tests found', colors='red')
    
    
    def module(self, **modArgs):
        """
        Builds a module, along with optional tests.
        It makes assumptions, but most can be overridden by passing in args.
        """
        bld = self
        if 'env' in modArgs:
            env = modArgs['env']
        else:
            variant = modArgs.get('variant', bld.env['VARIANT'] or 'default')
            env = bld.env_of_name(variant)
            env.set_variant(variant)
    
        modArgs = dict((k.lower(), v) for k, v in modArgs.iteritems())
        lang = modArgs.get('lang', 'c++')
        libExeType = {'c++':'cxx', 'c':'cc'}.get(lang, 'cxx')
        libName = '%s-%s' % (modArgs['name'], lang)
        path = modArgs.get('path',
                           'dir' in modArgs and bld.path.find_dir(modArgs['dir']) or bld.path)

        module_deps = map(lambda x: '%s-%s' % (x, lang), modArgs.get('module_deps', '').split())
        defines = self.__getDefines(env) + modArgs.get('defines', '').split()
        uselib_local = module_deps + modArgs.get('uselib_local', '').split()
        uselib = modArgs.get('uselib', '').split() + ['CSTD', 'CRUN']
        includes = modArgs.get('includes', 'include').split()
        exportIncludes = modArgs.get('export_includes', 'include').split()
        libVersion = modArgs.get('version', None)
        
        if libVersion is not None and sys.platform != 'win32':
            targetName = '%s.%s' % (libName, self.safeVersion(libVersion))
        else:
            targetName = libName
        
        
        headersOnly = modArgs.get('headersonly', False)
        if not headersOnly:
            #build the lib
            lib = bld.new_task_gen(libExeType, env['LIB_TYPE'] or 'staticlib', includes=includes,
                    target=targetName, name=libName, export_incdirs=exportIncludes,
                    uselib_local=uselib_local, uselib=uselib, env=env.copy(),
                    defines=defines, path=path, install_path='${PREFIX}/lib')
            lib.find_sources_in_dirs(modArgs.get('source_dir', modArgs.get('sourcedir', 'source')))
            lib.source = filter(modArgs.get('source_filter', None), lib.source)
            
            if libVersion is not None and sys.platform != 'win32' and Options.options.symlinks:
                symlinkLoc = '%s/%s' % (lib.install_path, env['staticlib_PATTERN'] % libName)
#                bld.add_group()
                bld.symlink_as(symlinkLoc, env['staticlib_PATTERN'] % lib.target, env=env)
            

        for f in path.find_dir('include').find_iter():
            relpath = f.relpath_gen(path)
            bld.install_files('${PREFIX}/%s' % os.path.dirname(relpath),
                              f.abspath())
        
        testNode = path.find_dir('tests')
        if testNode and not Options.options.libs_only:
            test_deps = modArgs.get('test_deps', modArgs.get('module_deps', '')).split()
            
            if not headersOnly:
                test_deps.append(modArgs['name'])
            
            sourceExt = {'c++':'.cpp', 'c':'.c'}.get(lang, 'cxx')
            for test in filter(modArgs.get('test_filter', None),
                               testNode.find_iter(in_pat=['*%s' % sourceExt],
                                                  maxdepth=1, flat=True).split()):
                
                self.program(env=env, name=splitext(test)[0], source=test,
                             module_deps=' '.join(test_deps),
                             uselib_local=modArgs.get('test_uselib_local', ''),
                             uselib=modArgs.get('test_uselib', modArgs.get('uselib', '')),
                             lang=lang, path=testNode,
                             install_path='${PREFIX}/share/%s/test' % modArgs['name'])

        testNode = path.find_dir('unittests')
        if testNode:
            test_deps = modArgs.get('module_deps', '').split()
            test_uselib = modArgs.get('uselib', '').split()
            #add to the UNITTEST var in other places to define what it means
            test_uselib.append('UNITTEST')
            
            if not headersOnly:
                test_deps.append(modArgs['name'])
            
            sourceExt = {'c++':'.cpp', 'c':'.c'}.get(lang, 'cxx')
            tests = []
            for test in filter(modArgs.get('unittest_filter', None),
                               testNode.find_iter(in_pat=['*%s' % sourceExt],
                                                  maxdepth=1, flat=True).split()):
                
                exe = self.unittest(env=env, test=test, module_deps=' '.join(test_deps),
                             uselib=' '.join(test_uselib),
                             lang=lang, path=testNode, disabled=True)
                tests.append(splitext(test)[0])
                
            # add a post-build hook to run the unit tests
            # I use partial so I can pass arguments to a post build hook
            if Options.options.unittests:
                bld.add_post_fun(partial(CPPBuildContext.runUnitTests,
                                         tests=tests,
                                         path=self.getBuildDir(testNode)))
                

        return env
    
    
    def unittest(self, **modArgs):
        bld = self
        if 'env' in modArgs:
            env = modArgs['env']
        else:
            variant = modArgs.get('variant', bld.env['VARIANT'] or 'default')
            env = bld.env_of_name(variant)
            env.set_variant(variant)
        
        test_deps = modArgs.get('module_deps', '').split()
        test_uselib = modArgs.get('uselib', '').split()
        #add to the UNITTEST var in other places to define what it means
        test_uselib.append('UNITTEST')
        test = modArgs['test']
        path = modArgs.get('path',
                           'dir' in modArgs and bld.path.find_dir(modArgs['dir']) or bld.path)

        exe = self.program(env=env, name=splitext(test)[0], source=test,
                     module_deps=' '.join(test_deps),
                     uselib=' '.join(test_uselib),
                     lang=modArgs.get('lang', 'c++'), path=path,
                     install_path=None)

        if 'disabled' not in modArgs:
            # add a post-build hook to run the unit tests
            # I use partial so I can pass arguments to a post build hook
            if Options.options.unittests:
                bld.add_post_fun(partial(CPPBuildContext.runUnitTests,
                                         tests=[splitext(test)[0]],
                                         path=self.getBuildDir(path)))
        return exe
    
    
    def plugin(self, **modArgs):
        """
        Builds a plugin (.so) and sets the install path based on the type of
        plugin (via the plugin kwarg).
        """
        bld = self
        if 'env' in modArgs:
            env = modArgs['env']
        else:
            variant = modArgs.get('variant', bld.env['VARIANT'] or 'default')
            env = bld.env_of_name(variant)
            env.set_variant(variant)
        
        modArgs = dict((k.lower(), v) for k, v in modArgs.iteritems())
        lang = modArgs.get('lang', 'c++')
        libExeType = {'c++':'cxx', 'c':'cc'}.get(lang, 'cxx')
        libName = '%s-%s' % (modArgs['name'], lang)
        plugin = modArgs.get('plugin', '')
        path = modArgs.get('path',
                           'dir' in modArgs and bld.path.find_dir(modArgs['dir']) or bld.path)

        module_deps = map(lambda x: '%s-%s' % (x, lang), modArgs.get('module_deps', '').split())
        defines = self.__getDefines(env) + modArgs.get('defines', '').split() + ['PLUGIN_MODULE_EXPORTS']
        uselib_local = module_deps + modArgs.get('uselib_local', '').split()
        uselib = modArgs.get('uselib', '').split() + ['CSTD', 'CRUN']
        includes = modArgs.get('includes', 'include').split()
        exportIncludes = modArgs.get('export_includes', 'include').split()
        source = modArgs.get('source', '').split() or None
        
        lib = bld.new_task_gen(libExeType, 'shlib', includes=includes, source=source,
                target=libName, name=libName, export_incdirs=exportIncludes,
                uselib_local=uselib_local, uselib=uselib, env=env.copy(),
                defines=defines, path=path,
                install_path='${PREFIX}/share/%s/plugins' % plugin)
        if not source:
            lib.find_sources_in_dirs(modArgs.get('source_dir', modArgs.get('sourcedir', 'source')))
            lib.source = filter(modArgs.get('source_filter', None), lib.source)
        
        confDir = path.find_dir('conf')
        if confDir:
            for f in confDir.find_iter():
                relpath = f.relpath_gen(path)
                bld.install_files('${PREFIX}/share/%s/conf' % plugin, f.abspath())
    
    
    def program(self, **modArgs):
        """
        Builds a program (exe)
        """
        bld = self
        if 'env' in modArgs:
            env = modArgs['env']
        else:
            variant = modArgs.get('variant', bld.env['VARIANT'] or 'default')
            env = bld.env_of_name(variant)
            env.set_variant(variant)
        
        modArgs = dict((k.lower(), v) for k, v in modArgs.iteritems())
        lang = modArgs.get('lang', 'c++')
        libExeType = {'c++':'cxx', 'c':'cc'}.get(lang, 'cxx')
        progName = modArgs['name']
        path = modArgs.get('path',
                           'dir' in modArgs and bld.path.find_dir(modArgs['dir']) or bld.path)

        module_deps = map(lambda x: '%s-%s' % (x, lang), modArgs.get('module_deps', '').split())
        defines = self.__getDefines(env) + modArgs.get('defines', '').split()
        uselib_local = module_deps + modArgs.get('uselib_local', '').split()
        uselib = modArgs.get('uselib', '').split() + ['CSTD', 'CRUN']
        includes = modArgs.get('includes', 'include').split()
        source = modArgs.get('source', '').split() or None
        install_path = modArgs.get('install_path', '${PREFIX}/bin')
        
        exe = bld.new_task_gen(libExeType, 'program', source=source,
                               includes=includes, defines=defines,
                               uselib_local=uselib_local, uselib=uselib,
                               env=env.copy(), target=progName, path=path,
                               install_path=install_path)
        if not source:
            exe.find_sources_in_dirs(modArgs.get('source_dir', modArgs.get('sourcedir', 'source')))
            exe.source = filter(modArgs.get('source_filter', None), exe.source)
        return exe

    def getBuildDir(self, path=None):
        """
        Returns the build dir, relative to where you currently are (bld.path)
        """
        cwd = path and path.abspath() or self.path.abspath()
        bldDir = self.srcnode.abspath(self.env)
        for i in range(len(cwd)):
            if not bldDir.startswith(cwd[:i]):
                bldDir = os.path.join(bldDir, cwd[i - 1:])
                break
        return bldDir


class GlobDirectoryWalker:
    """ recursively walk a directory, matching filenames """
    def __init__(self, directory, patterns=["*"]):
        self.stack = [directory]
        self.patterns = patterns
        self.files = []
        self.index = 0
        
    def __iter__(self):
        return self.next()
    
    def next(self):
        while True:
            try:
                file = self.files[self.index]
                self.index = self.index + 1
            except IndexError:
                # pop next directory from stack
                if len(self.stack) == 0:
                    raise StopIteration
                self.directory = self.stack.pop()
                if isdir(self.directory):
                    self.files = os.listdir(self.directory)
                else:
                    self.files, self.directory = [self.directory], ''
                self.index = 0
            else:
                # got a filename
                fullname = os.path.join(self.directory, file)
                if isdir(fullname):# and not os.path.islink(fullname):
                    self.stack.append(fullname)
                for p in self.patterns:
                    if fnmatch.fnmatch(file, p):
                        yield fullname

def recursiveGlob(directory, patterns=["*"]):
    return GlobDirectoryWalker(directory, patterns)


def getPlatform(pwd=None, default=None):
    """ returns the platform name """
    platform = default or sys.platform
    
    if platform != 'win32':
        if not pwd:
            pwd = os.getcwd()
            
        locs = recursiveGlob(pwd, patterns=['config.guess'])
        for loc in locs:
            if not exists(loc): continue
            try:
                out = os.popen('chmod +x %s' % loc)
                out.close()
            except:{}
            try:
                out = os.popen(loc, 'r')
                platform = out.readline()
                platform = platform.strip('\n')
                out.close()
            except:{}
            else:
                break
    return platform



import zipfile
def unzipper(inFile, outDir):
    if not outDir.endswith(':') and not exists(outDir):
        os.mkdir(outDir)
    
    zf = zipfile.ZipFile(inFile)
    
    dirs = filter(lambda x: x.endswith('/'), zf.namelist())
    dirs.sort()
    
    for d in filter(lambda x: not exists(x),
                    map(lambda x: os.path.join(outDir, x), dirs)):
        os.mkdir(d)

    for i, name in enumerate(filter(lambda x: not x.endswith('/'), zf.namelist())):
        outFile = open(os.path.join(outDir, name), 'wb')
        outFile.write(zf.read(name))
        outFile.flush()
        outFile.close()


def set_options(opt):
    opt.tool_options('compiler_cc')
    opt.tool_options('compiler_cxx')
    opt.tool_options('misc')
    
    if Options.platform == 'win32':
        opt.tool_options('msvc')
        opt.add_option('--with-crt', action='store', choices=['MD', 'MT'],
                       dest='crt', default='MT', help='Specify Windows CRT library - MT (default) or MD')
    
    opt.add_option('--enable-warnings', action='store_true', dest='warnings',
                   help='Enable warnings')
    opt.add_option('--enable-debugging', action='store_true', dest='debugging',
                   help='Enable debugging')
    #TODO - get rid of enable64 - it's useless now
    opt.add_option('--enable-64bit', action='store_true', dest='enable64',
                   help='Enable 64bit builds')
    opt.add_option('--enable-32bit', action='store_true', dest='enable32',
                   help='Enable 32bit builds')
    opt.add_option('--enable-doxygen', action='store_true', dest='doxygen',
                   help='Enable running doxygen')
    opt.add_option('--with-cflags', action='store', nargs=1, dest='cflags',
                   help='Set non-standard CFLAGS', metavar='FLAGS')
    opt.add_option('--with-cxxflags', action='store', nargs=1, dest='cxxflags',
                   help='Set non-standard CXXFLAGS (C++)', metavar='FLAGS')
    opt.add_option('--with-linkflags', action='store', nargs=1, dest='linkflags',
                   help='Set non-standard LINKFLAGS (C/C++)', metavar='FLAGS')
    opt.add_option('--with-defs', action='store', nargs=1, dest='_defs',
                   help='Use DEFS as macro definitions', metavar='DEFS')
    opt.add_option('--with-optz', action='store',
                   choices=['med', 'fast', 'fastest'],
                   default='fastest', metavar='OPTZ',
                   help='Specify the optimization level for optimized/release builds')
    opt.add_option('--libs-only', action='store_true', dest='libs_only',
                   help='Only build the libs (skip building the tests, etc.)')
    opt.add_option('--shared', action='store_true', dest='shared_libs',
                   help='Build all libs as shared libs')
    opt.add_option('--disable-symlinks', action='store_false', dest='symlinks',
                   default=True, help='Disable creating symlinks for libs')
    opt.add_option('--unittests', action='store_true', dest='unittests',
                   help='Build-time option to run unit tests after the build has completed')
    

    

types_str = '''
#include <stdio.h>
int isBigEndian()
{
    long one = 1;
    return !(*((char *)(&one)));
}
int main()
{
    if (isBigEndian()) printf("bigendian=True\\n");
    else printf("bigendian=False\\n");
    printf("sizeof_int=%d\\n", sizeof(int));
    printf("sizeof_short=%d\\n", sizeof(short));
    printf("sizeof_long=%d\\n", sizeof(long));
    printf("sizeof_long_long=%d\\n", sizeof(long long));
    printf("sizeof_float=%d\\n", sizeof(float));
    printf("sizeof_double=%d\\n", sizeof(double));
    return 0;
}
'''

def detect(self):
    
    if self.env['DETECTED_BUILD_PY']:
        return
    
    platform = getPlatform(default=Options.platform)
    
    self.check_message_custom('platform', '', platform, color='GREEN')
    self.check_tool('compiler_cc')
    self.check_tool('compiler_cxx')

    cxxCompiler = self.env["COMPILER_CXX"]
    ccCompiler = self.env["COMPILER_CC"]
    
    if ccCompiler == 'msvc':
        cxxCompiler = ccCompiler
        
    if not cxxCompiler or not ccCompiler:
        self.fatal('Unable to find C/C++ compiler')

    self.check_tool('misc')
    if Options.options.doxygen:
        self.find_program('doxygen', var='DOXYGEN')
    
    #Look for a ton of headers
    self.check_cc(header_name="inttypes.h")
    self.check_cc(header_name="unistd.h")
    self.check_cc(header_name="getopt.h")
    self.check_cc(header_name="malloc.h")
    self.check_cc(header_name="sys/time.h")
    self.check_cc(header_name="dlfcn.h")
    self.check_cc(header_name="fcntl.h")
    self.check_cc(header_name="check.h")
    self.check_cc(header_name="memory.h")
    self.check_cc(header_name="string.h")
    self.check_cc(header_name="strings.h")
    self.check_cc(header_name="stdbool.h")
    self.check_cc(header_name="stdlib.h")
    self.check_cc(header_name="stddef.h")
    self.check_cc(function_name='mmap', header_name="sys/mman.h")
    self.check_cc(function_name='memmove', header_name="string.h")
    self.check_cc(function_name='strerror', header_name="string.h")
    self.check_cc(function_name='bcopy', header_name="strings.h")
    self.check_cc(type_name='size_t', header_name='stddef.h')
    self.check_cc(fragment='int main(){const int i = 0; return 0;}',
                  define_name='HAVE_CONST', msg='Checking for const keyword')
    self.check_cc(fragment='int main(){unsigned short; return 0;}',
                  define_name='HAVE_UNSIGNED_SHORT', msg='Checking for unsigned short')
    self.check_cc(fragment='int main(){unsigned char i; return 0;}',
                  define_name='HAVE_UNSIGNED_CHAR', msg='Checking for unsigned char')
    self.check_cc(lib="m", mandatory=False, uselib_store='MATH')
    self.check_cc(lib="rt", mandatory=False, uselib_store='RT')
    self.check_cc(lib="sqrt", mandatory=False, uselib_store='SQRT')
    
    self.check_cc(function_name='gettimeofday', header_name='sys/time.h')
    if self.check_cc(lib='rt', function_name='clock_gettime', header_name='time.h'):
        self.env.defines['USE_CLOCK_GETTIME']= 1
    self.check_cc(function_name='BSDgettimeofday', header_name='sys/time.h')
    self.check_cc(function_name='gethrtime', header_name='sys/time.h')
    self.check_cc(function_name='getpagesize', header_name='unistd.h')
    self.check_cc(function_name='getopt', header_name='unistd.h')
    self.check_cc(function_name='getopt_long', header_name='getopt.h')
    
    self.check_cc(fragment='#include <math.h>\nint main(){if (!isnan(3.14159)) isnan(2.7183);}',
                  define_name='HAVE_ISNAN', msg='Checking for function isnan',
                  errmsg='not found')
    
    # Check for hrtime_t data type; some systems (AIX) seem to have
    # a function called gethrtime but no hrtime_t!
    frag = '''
    #ifdef HAVE_SYS_TIME_H
    #include <sys/time.h>
    int main(){hrtime_t foobar;}
    #endif
    '''
    self.check_cc(fragment=frag, define_name='HAVE_HRTIME_T',
                  msg='Checking for type hrtime_t', errmsg='not found')
    
    
    #find out the size of some types, etc.
    output = self.check(fragment=types_str, execute=1, msg='Checking system type sizes')
    t = Utils.to_hashtable(output or '')
    for k, v in t.iteritems():
        try:
            v = int(v)
        except:
            v = v.strip()
            if v == 'True':
                v = True
            elif v == 'False':
                v = False
        #v = eval(v)
        self.check_message_custom(k.replace('_', ' '), '', v)
        self.define(k.upper(), v)
    
    env = self.env
    env['PLATFORM'] = platform
    
    env['LIB_TYPE'] = Options.options.shared_libs and 'shlib' or 'staticlib'
    
    env.append_unique('CXXFLAGS', Options.options.cxxflags or '')
    env.append_unique('CCFLAGS', Options.options.cflags or '')
    env.append_unique('LINKFLAGS', Options.options.linkflags or '')
    if Options.options._defs:
        env.append_unique('CCDEFINES', Options.options._defs.split(','))
        env.append_unique('CXXDEFINES', Options.options._defs.split(','))

    appleRegex = r'i.86-apple-.*'
    linuxRegex = r'.*-.*-linux-.*|i686-pc-.*|linux'
    sparcRegex = r'sparc-sun.*'
    winRegex = r'win32'
    
    config = {'cxx':{}, 'cc':{}}

    #apple
    if re.match(appleRegex, platform):
        env.append_value('LIB_DL', 'dl')
        env.append_value('LIB_NSL', 'nsl')
        env.append_value('LIB_THREAD', 'pthread')
        self.check_cc(lib='pthread', mandatory=True)

        config['cxx']['debug']          = '-g'
        config['cxx']['warn']           = '-Wall'
        config['cxx']['verbose']        = '-v'
        config['cxx']['64']             = '-m64'
        config['cxx']['32']             = '-m32'
        config['cxx']['optz_med']       = '-O1'
        config['cxx']['optz_fast']      = '-O2'
        config['cxx']['optz_fastest']   = '-O3'

        env.append_value('CXXDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE __POSIX'.split())
        env.append_value('LINKFLAGS', '-fPIC -dynamiclib'.split())
        env.append_value('CXXFLAGS', '-fPIC')
        env.append_value('CXXFLAGS_THREAD', '-D_REENTRANT')

        config['cc']['debug']          = config['cxx']['debug']
        config['cc']['warn']           = config['cxx']['warn']
        config['cc']['verbose']        = config['cxx']['verbose']
        config['cc']['64']             = config['cxx']['64']
        config['cc']['optz_med']       = config['cxx']['optz_med']
        config['cc']['optz_fast']      = config['cxx']['optz_fast']
        config['cc']['optz_fastest']   = config['cxx']['optz_fastest']

        env.append_value('CCDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE __POSIX'.split())
        env.append_value('CCFLAGS', '-fPIC -dynamiclib'.split())
        env.append_value('CCFLAGS_THREAD', '-D_REENTRANT')

    #linux
    elif re.match(linuxRegex, platform):
        env.append_value('LIB_DL', 'dl')
        env.append_value('LIB_NSL', 'nsl')
        env.append_value('LIB_THREAD', 'pthread')
        env.append_value('LIB_MATH', 'm')

        self.check_cc(lib='pthread', mandatory=True)

        if cxxCompiler == 'g++':
            config['cxx']['debug']          = '-g'
            config['cxx']['warn']           = '-Wall'
            config['cxx']['verbose']        = '-v'
            config['cxx']['64']             = '-m64'
            config['cxx']['32']             = '-m32'
            config['cxx']['optz_med']       = '-O1'
            config['cxx']['optz_fast']      = '-O2'
            config['cxx']['optz_fastest']   = '-O3'
            
            env.append_value('CXXDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE __POSIX'.split())
            env.append_value('LINKFLAGS', '-Wl,-E -fPIC'.split())
            env.append_value('CXXFLAGS', '-fPIC')
            
            #for some reason using CXXDEFINES_THREAD won't work w/uselib... so using FLAGS instead
            env.append_value('CXXFLAGS_THREAD', '-D_REENTRANT')
        
        if ccCompiler == 'gcc':
            config['cc']['debug']          = '-g'
            config['cc']['warn']           = '-Wall'
            config['cc']['verbose']        = '-v'
            config['cc']['64']             = '-m64'
            config['cc']['32']             = '-m32'
            config['cc']['optz_med']       = '-O1'
            config['cc']['optz_fast']      = '-O2'
            config['cc']['optz_fastest']   = '-O3'
            
            env.append_value('CCDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE __POSIX'.split())
            env.append_value('CCFLAGS', '-fPIC'.split())
            
            #for some reason using CXXDEFINES_THREAD won't work w/uselib... so using FLAGS instead
            env.append_value('CCFLAGS_THREAD', '-D_REENTRANT')
    
    #Solaris
    elif re.match(sparcRegex, platform):
        env.append_value('LIB_DL', 'dl')
        env.append_value('LIB_NSL', 'nsl')
        env.append_value('LIB_SOCKET', 'socket')
        env.append_value('LIB_THREAD', 'thread')
        env.append_value('LIB_MATH', 'm')
        env.append_value('LIB_CRUN', 'Crun')
        env.append_value('LIB_CSTD', 'Cstd')
        self.check_cc(lib='thread', mandatory=True)

        if cxxCompiler == 'sunc++':
            config['cxx']['debug']          = '-g'
            config['cxx']['warn']           = ''
            config['cxx']['verbose']        = '-v'
            config['cxx']['64']             = '-xtarget=generic64'
            config['cxx']['32']             = '-xtarget=generic'
            config['cxx']['linkflags_32'] = '-xtarget=generic'
            config['cxx']['linkflags_64'] = '-xtarget=generic64'
            config['cxx']['optz_med']       = '-xO3'
            config['cxx']['optz_fast']      = '-xO4'
            config['cxx']['optz_fastest']   = '-fast'
            env['shlib_CXXFLAGS']            = ['-KPIC', '-DPIC']

            env.append_value('CXXDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE'.split())
            env.append_value('CXXFLAGS', '-KPIC -instances=global'.split())
            env.append_value('CXXFLAGS_THREAD', '-mt')
            
        if ccCompiler == 'suncc':
            config['cc']['debug']          = '-g'
            config['cc']['warn']           = ''
            config['cc']['verbose']        = '-v'
            config['cc']['64']             = '-xtarget=generic64'
            config['cc']['linkflags_64'] = '-xtarget=generic64'
            config['cc']['linkflags_32'] = '-xtarget=generic'
            config['cc']['32']             = '-xtarget=generic'
            config['cc']['optz_med']       = '-xO2'
            config['cc']['optz_fast']      = '-xO3'
            config['cc']['optz_fastest']   = '-fast'
            env['shlib_CCFLAGS']            = ['-KPIC', '-DPIC']

            env.append_value('CCDEFINES', '_FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE'.split())
            env.append_value('CCFLAGS', '-KPIC'.split())
            env.append_value('CCFLAGS_THREAD', '-mt')

    elif re.match(winRegex, platform):
#        if Options.options.enable64:
#            platform = 'win'

        env.append_value('LIB_RPC', 'rpcrt4')
        env.append_value('LIB_SOCKET', 'Ws2_32')
        
        winRegex
        crtFlag = '/%s' % Options.options.crt
        crtDebug = '%sd' % crtFlag

        vars = {}
        vars['debug']          = ['/Zi', crtDebug]
        vars['warn']           = '/Wall'
        vars['nowarn']         = '/W3 /wd4290'.split()
        vars['verbose']        = ''
        vars['64']             = '/MACHINE:X64 '
        vars['optz_med']       = ['-O2', crtFlag]
        vars['optz_fast']      = ['-O2', crtFlag]
        vars['optz_fastest']   = ['-Ox', crtFlag]
        vars['linkflags_32'] = vars['linkflags_64'] = '/STACK:80000000'

        # choose the runtime to link against
        # [/MD /MDd /MT /MTd]
        
        config['cxx'].update(vars)
        config['cc'].update(vars)

        defines = '_CRT_SECURE_NO_WARNINGS _FILE_OFFSET_BITS=64 _LARGEFILE_SOURCE WIN32 _USE_MATH_DEFINES'.split()
        flags = '/UUNICODE /U_UNICODE /EHs /GR'.split()
        threadFlags = '/D_REENTRANT'
        
        env.append_value('CXXDEFINES', defines)
        env.append_value('CXXFLAGS', flags)
        env.append_value('CXXFLAGS_THREAD', threadFlags)
        
        env.append_value('CCDEFINES', defines)
        env.append_value('CCFLAGS', flags)
        env.append_value('CCFLAGS_THREAD', threadFlags)
    
    else:
        self.fatal('OS/platform currently unsupported: %s' % platform)
    
    #CXX
    if Options.options.warnings:
        env.append_value('CXXFLAGS', config['cxx'].get('warn', ''))
        env.append_value('CCFLAGS', config['cc'].get('warn', ''))
    else:
        env.append_value('CXXFLAGS', config['cxx'].get('nowarn', ''))
        env.append_value('CCFLAGS', config['cc'].get('nowarn', ''))
    if Options.options.verbose:
        env.append_value('CXXFLAGS', config['cxx'].get('verbose', ''))
        env.append_value('CCFLAGS', config['cc'].get('verbose', ''))
    
    
    variant = env.copy() 
    if Options.options.debugging:
        variantName = '%s-debug' % platform
        variant.append_value('CXXFLAGS', config['cxx'].get('debug', ''))
        variant.append_value('CCFLAGS', config['cc'].get('debug', ''))
    else:
        variantName = '%s-release' % platform
        optz = Options.options.with_optz
        variant.append_value('CXXFLAGS', config['cxx'].get('optz_%s' % optz, ''))
        variant.append_value('CCFLAGS', config['cc'].get('optz_%s' % optz, ''))
    
    is64Bit = False
    #check if the system is 64-bit capable
    if re.match(winRegex, platform):
        is64Bit = Options.options.enable64
    elif not Options.options.enable32:
        if '64' in config['cxx']:
            if self.check_cxx(cxxflags=config['cxx']['64'], linkflags=config['cc'].get('linkflags_64', ''), mandatory=False):
                is64Bit = self.check_cc(cflags=config['cc']['64'], linkflags=config['cc'].get('linkflags_64', ''), mandatory=False)

    if is64Bit:
        if not re.match(winRegex, platform):
            variantName = '%s-64' % variantName
        variant.append_value('CXXFLAGS', config['cxx'].get('64', ''))
        variant.append_value('CCFLAGS', config['cc'].get('64', ''))
        variant.append_value('LINKFLAGS', config['cc'].get('linkflags_64', ''))
    else:
        variant.append_value('CXXFLAGS', config['cxx'].get('32', ''))
        variant.append_value('CCFLAGS', config['cc'].get('32', ''))
        variant.append_value('LINKFLAGS', config['cc'].get('linkflags_32', ''))
    
    self.set_env_name(variantName, variant)
    variant.set_variant(variantName)
    env.set_variant(variantName)
    self.setenv(variantName)
    
    env['VARIANT'] = variant['VARIANT'] = variantName
    
    #flag that we already detected
    self.env['DETECTED_BUILD_PY'] = True


@taskgen
@feature('untar')
def untar(tsk):
    import tarfile
    f = tsk.path.find_or_declare(tsk.fname)
    tf = tarfile.open(f.abspath(), 'r')
    p = tsk.path.abspath()
    for x in tf:
        tf.extract(x, p)
    tf.close()


@taskgen
@feature('unzip')
def unzip(tsk):
    f = tsk.path.find_or_declare(tsk.fname)
    unzipper(f.abspath(), tsk.path.abspath())


@taskgen
@feature('m4subst')
def m4subst(tsk):
    import re
    #similar to the subst in misc.py - but outputs to the src directory
    m4_re = re.compile('@(\w+)@', re.M)

    env = tsk.env
    infile = os.path.join(tsk.path.abspath(), tsk.input)
    outfile = os.path.join(tsk.path.abspath(), tsk.output)
    
    file = open(infile, 'r')
    code = file.read()
    file.close()

    # replace all % by %% to prevent errors by % signs in the input file while string formatting
    code = code.replace('%', '%%')

    s = m4_re.sub(r'%(\1)s', code)

    di = tsk.dict or {}
    if not di:
        names = m4_re.findall(code)
        for i in names:
            di[i] = env.get_flat(i) or env.get_flat(i.upper())
    
    file = open(outfile, 'w')
    file.write(s % di)
    file.close()
    if tsk.chmod: os.chmod(outfile, tsk.chmod)


@taskgen
@feature('commentUndefs')
def commentUndefs(tsk):
    import re
    env = tsk.env
    infile = os.path.join(tsk.path.abspath(), tsk.input)
    outfile = os.path.join(tsk.path.abspath(), tsk.output)
    
    file = open(infile, 'r')
    code = file.read()
    file.close()

    code = re.sub(r'(#undef[^\n]*)(\n)', r'/* \1 */\2', code)
    file = open(outfile, 'w')
    file.write(code)
    file.close()
    if tsk.chmod: os.chmod(outfile, tsk.chmod)


@taskgen
@feature('makeHeader')
def makeHeader(tsk):
    outfile = os.path.join(tsk.path.abspath(), tsk.output)
    dest = open(outfile, 'w')
    guard = '__CONFIG_H__'
    dest.write('#ifndef %s\n#define %s\n\n' % (guard, guard))

    for k in tsk.defs.keys():
        v = tsk.defs[k]
        if v is None:
            v = ''
        dest.write('\n#ifndef %s\n#define %s %s\n#endif\n' % (k, k, v))
    
    if hasattr(tsk, 'undefs'):
        for u in tsk.undefs:
            dest.write('\n#undef %s\n' % u)

    dest.write('\n#endif /* %s */\n' % guard)
    dest.close()
    if tsk.chmod: os.chmod(outfile, tsk.chmod)


@feature('cc', 'cxx')
@before('apply_obj_vars')
def fix_libs(self):
    """
    The apply_lib_vars task does not order the STATICLIBs based on dependencies,
    which is required for some OSes (Linux, Solaris)
    """
    env = self.env
    
    uselib = self.to_list(getattr(self, 'uselib', []))
    names = self.to_list(getattr(self, 'uselib_local', []))
    
    seen = {}
    tmp = names[:]
    while tmp:
        lib_name = tmp.pop(0)
        # visit dependencies only once
        if lib_name in seen:
            continue

        y = self.name_to_obj(lib_name)
        if not y: continue
        uselib_locals = y.to_list(getattr(y, 'uselib_local', []))
        
        if 'cshlib' in y.features or 'cprogram' in y.features:
            uselib_locals = filter(lambda x: 'cstaticlib' not in \
                                   self.name_to_obj(x).features, uselib_locals)
        
        seen[lib_name] = (y, uselib_locals)
        tmp.extend(uselib_locals)
        
    ordered = []
    allKeys = seen.keys()[:]
    while allKeys:
        for k in allKeys:
            found = False
            for ok in allKeys:
                if k == ok or found: continue
                found = k in seen[ok][1]
            if not found:
                ordered.append(k)
                allKeys.remove(k)
    
    env['STATICLIB'] = [seen[k][0].target for k in ordered]
