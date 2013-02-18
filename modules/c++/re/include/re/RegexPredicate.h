#ifndef __RE_REGEX_FILE_PREDICATE_H__
#define __RE_REGEX_FILE_PREDICATE_H__

#include "sys/FileFinder.h"
#include "re/PCRE.h"

namespace re
{

struct RegexPredicate : sys::FilePredicate
{
public:
    RegexPredicate(const std::string& match)
    {
        mRegex.compile(match);
    }
    
    bool operator()(const std::string& filename)
    {
        return mRegex.matches(filename);
    }

private:
    re::PCRE mRegex;

};

}
#endif
