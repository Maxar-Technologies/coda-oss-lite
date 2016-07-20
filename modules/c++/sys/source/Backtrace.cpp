#include <sys/Backtrace.h>

#include <sys/sys_config.h>
#include <sstream>

static const size_t MAX_STACK_ENTRIES = 62;

#ifdef HAVE_EXECINFO_H

#include <execinfo.h>
#include <cstdlib>

std::string sys::getBacktrace()
{
    void * stackBuffer[MAX_STACK_ENTRIES];
    int currentStackSize = backtrace(stackBuffer, MAX_STACK_ENTRIES);
    char ** stackSymbols = backtrace_symbols(stackBuffer, currentStackSize);

    std::stringstream ss;
    for (int ii = 0; ii < currentStackSize; ++ii)
    {
        ss << stackSymbols[ii] << std::endl;
    }
    std::free(stackSymbols);

    return ss.str();
}

#else

std::string sys::getBacktrace()
{
    return "sys::getBacktrace() is not supported " +
        "on the current platform and/or libc";
}

#endif
