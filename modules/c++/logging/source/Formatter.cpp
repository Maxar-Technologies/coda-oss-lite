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
//  Formatter.cpp
///////////////////////////////////////////////////////////

#include <sstream>
#include <iostream>
#include <import/str.h>
#include "logging/Formatter.h"

const static std::string THREAD_ID = "%t";
const static std::string LOG_NAME = "%c";
const static std::string LOG_LEVEL = "%p";
const static std::string TIMESTAMP = "%d";
const static std::string FILE_NAME = "%F";
const static std::string LINE_NUM = "%L";
const static std::string MESSAGE = "%m";
const static std::string FUNCTION = "%M";

logging::Formatter::~Formatter()
{
}

void logging::Formatter::replace(std::string& str, const std::string& search, const std::string& replace) const
{
    int index = str.find(search);
    if (index >= 0)
        str.replace(index, search.length(), replace);
}

std::string logging::Formatter::format(logging::LogRecord* record) const
{
    //std::ostringstream s;
    std::string name = (record->getName().empty()) ? ("DEFAULT") : record->getName();
    /*if (record->getLineNum() >= 0)
        s << "[" << name << "] " << record->getLevelName() << "  " << record->getTimeStamp() << "  " <<
            record->getFile() << " " << record->getLineNum() << " ==> " << record->getMessage();
    else
        s << record->getLevelName() << "  " << record->getTimeStamp() << " ==> " << record->getMessage();
    */
    // t = thread, p = level, m = message, F = filename, L = line num, M = method, d = date, c = name

    std::string format = mFmt;
    //replace(format, "%t", record->);
    replace(format, "%c", name);
    replace(format, "%p", record->getLevelName());
    replace(format, "%d", record->getTimeStamp());
    if (record->getLineNum() >= 0)
    {
        replace(format, "%F", record->getFile());
        replace(format, "%L", str::toString<int>(record->getLineNum()));
    }
    else
    {
        replace(format, "%F", " ");
        replace(format, "%L", " ");
    }
    replace(format, "%M", record->getFunction());
    replace(format, "%m", record->getMessage());

    return format;
}

