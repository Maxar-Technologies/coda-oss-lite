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
//  MemoryHandler.cpp
///////////////////////////////////////////////////////////

#include "logging/MemoryHandler.h"

using namespace logging;


MemoryHandler::MemoryHandler(LogLevel level) : Handler(level)
{
    //might as well setup the map -- we could let emit take care of it,
    //but this would allow for less chance of an exception getting thrown
    mLogMap[LogLevel::LOG_NOTSET] = std::list<std::string>();
    mLogMap[LogLevel::LOG_DEBUG] = std::list<std::string>();
    mLogMap[LogLevel::LOG_INFO] = std::list<std::string>();
    mLogMap[LogLevel::LOG_WARNING] = std::list<std::string>();
    mLogMap[LogLevel::LOG_ERROR] = std::list<std::string>();
    mLogMap[LogLevel::LOG_CRITICAL] = std::list<std::string>();
}
MemoryHandler::~MemoryHandler() {}

std::list<std::string>& MemoryHandler::getLogs(LogLevel level)
{
    if (mLogMap.find(level) == mLogMap.end())
        throw except::NoSuchKeyException(Ctxt(FmtX("LogLevel: %d", level.toString().c_str())));
    return mLogMap[level];
}

void MemoryHandler::emitRecord(const LogRecord* record)
{
    // TODO: The base handler no longer has a function
    //       to format to a string, so we will need to 
    //       update this to send a buffered output 
    //       stream to emit, and then read this into the
    //       log map when it get returned.

    //LogLevel level = record->getLevel();
    //if (mLogMap.find(level) == mLogMap.end())
    //    mLogMap[level] = std::list<std::string>();
    //std::string formatted = format(record);
    //mLogMap[level].push_back(formatted);
    //if (level != LogLevel::LOG_NOTSET)
    //{
    //    if (mLogMap.find(LogLevel::LOG_NOTSET) == mLogMap.end())
    //        mLogMap[LogLevel::LOG_NOTSET] = std::list<std::string>();
    //    mLogMap[LogLevel::LOG_NOTSET].push_back(formatted);
    //}
}
