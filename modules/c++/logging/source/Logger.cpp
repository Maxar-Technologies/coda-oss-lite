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
//  Logger.cpp
///////////////////////////////////////////////////////////

#include "logging/Logger.h"
#include <deque>

void logging::Logger::log(logging::LogLevel level, const std::string& msg)
{
    logging::LogRecord *rec = new logging::LogRecord(mName, msg, level);
    handle(rec);
    delete rec;
}

void logging::Logger::log(LogLevel level, const except::Context& ctxt)
{
    logging::LogRecord *rec = new logging::LogRecord(mName, ctxt.getMessage(),
                              level, ctxt.getFile(), ctxt.getFunction(), ctxt.getLine(), ctxt.getTime());
    handle(rec);
    delete rec;
}

void logging::Logger::log(LogLevel level, except::Throwable& t)
{
    std::deque<except::Context> savedContexts;
    except::Trace& trace = t.getTrace();
    size_t size = trace.getSize();
    if(size > 0)
    {
        for (unsigned int i = 0; i < size; ++i)
        {
            except::Context ctxt = trace.getContext();
            savedContexts.push_front(ctxt);
            //log(level, ctxt);
            trace.popContext();
        }
        // Do this so we print the original context first
        for (unsigned int i = 0; i < savedContexts.size(); ++i)
        {
            except::Context ctxt = savedContexts[i];
            // Put it back on the trace in case someone else wants it
            trace.pushContext(ctxt);

            log(level, ctxt);
        }
    }
    else
    {
        // Just log the message
        log(level, t.getMessage());
    }
}

void logging::Logger::debug(const std::string& msg){ log(LOG_DEBUG, msg); };
void logging::Logger::info(const std::string& msg){ log(LOG_INFO, msg); };
void logging::Logger::warn(const std::string& msg){ log(LOG_WARNING, msg); };
void logging::Logger::error(const std::string& msg){ log(LOG_ERROR, msg); };
void logging::Logger::critical(const std::string& msg){ log(LOG_CRITICAL, msg); };

void logging::Logger::debug(const except::Context& ctxt){ log(LOG_DEBUG, ctxt); };
void logging::Logger::info(const except::Context& ctxt){ log(LOG_INFO, ctxt); };
void logging::Logger::warn(const except::Context& ctxt){ log(LOG_WARNING, ctxt); };
void logging::Logger::error(const except::Context& ctxt){ log(LOG_ERROR, ctxt); };
void logging::Logger::critical(const except::Context& ctxt){ log(LOG_CRITICAL, ctxt); };

void logging::Logger::debug(except::Throwable& t){ log(LOG_DEBUG, t); };
void logging::Logger::info(except::Throwable& t){ log(LOG_INFO, t); };
void logging::Logger::warn(except::Throwable& t){ log(LOG_WARNING, t); };
void logging::Logger::error(except::Throwable& t){ log(LOG_ERROR, t); };
void logging::Logger::critical(except::Throwable& t){ log(LOG_CRITICAL, t); };

void logging::Logger::handle(logging::LogRecord* record)
{
    if (filter(record))
    {
        for (std::vector<logging::Handler* >::iterator p = handlers.begin();
                p != handlers.end(); ++p)
        {
            //std::cout << (int)(*p)->getLevel() << std::endl;
            //only handle if it is above/equal to threshold
            if ((*p)->getLevel() <= record->getLevel())

                (*p)->handle(record);
        }
    }
}

void logging::Logger::addHandler(logging::Handler* handler)
{
    //only add the handler if it isn't added already
    bool found = false;
    for (std::vector<logging::Handler* >::iterator p = handlers.begin();
            p != handlers.end() && !found; ++p)
    {
        if ((*p) == handler)
            found = true;
    }
    if (!found)
        handlers.push_back(handler);
}

void logging::Logger::removeHandler(logging::Handler* handler)
{
    //find and remove, if it exists
    for (std::vector<logging::Handler* >::iterator p = handlers.begin();
            p != handlers.end(); ++p)
    {
        if ((*p) == handler)
        {
            handlers.erase(p);
            break;
        }
    }
}


void logging::Logger::setLevel(LogLevel level)
{
    for (std::vector<logging::Handler* >::iterator p = handlers.begin();
            p != handlers.end(); ++p)
    {
        //set the level
        (*p)->setLevel(level);
    }
}
