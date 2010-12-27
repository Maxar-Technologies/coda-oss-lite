/* =========================================================================
 * This file is part of logging-c++ 
 * =========================================================================
 * 
 * (C) Copyright 2004 - 2009, General Dynamics - Advanced Information Systems
 *
 * logging-c++ is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public 
 * License along with this program; If not, 
 * see <http://www.gnu.org/licenses/>.
 *
 */

///////////////////////////////////////////////////////////
//  StandardFormatter.cpp
///////////////////////////////////////////////////////////

#include <sstream>
#include <iostream>
#include <import/sys.h>
#include <import/str.h>
#include "logging/StandardFormatter.h"

using namespace logging;

const char StandardFormatter::DEFAULT_FORMAT[] = "[%c] %p [%t] %d ==> %m";

StandardFormatter::StandardFormatter(const std::string& fmt, 
                                     const std::string& prologue,
                                     const std::string& epilogue) :
    Formatter((fmt.empty()) ? DEFAULT_FORMAT : fmt, prologue, epilogue)
{
}

void StandardFormatter::format(const LogRecord* record, io::OutputStream& os) const
{
    std::string name = (record->getName().empty()) ? ("DEFAULT") : record->getName();

    // populate log
    long threadId = sys::getThreadID();
    std::string format = mFmt;
    replace(format, THREAD_ID, str::toString(threadId));
    replace(format, LOG_NAME,  name);
    replace(format, LOG_LEVEL, record->getLevelName());
    replace(format, TIMESTAMP, record->getTimeStamp());
    if (record->getLineNum() >= 0)
    {
        replace(format, FILE_NAME, record->getFile());
        replace(format, LINE_NUM,  
                str::toString<int>(record->getLineNum()));
    }
    else
    {
        replace(format, FILE_NAME, "");
        replace(format, LINE_NUM,  "");
    }
    replace(format, FUNCTION, record->getFunction());
    replace(format, MESSAGE,  record->getMessage());

    // write to stream
    os.write(format + "\n");
}

