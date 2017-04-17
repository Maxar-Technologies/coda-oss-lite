/* =========================================================================
 * This file is part of math-c++
 * =========================================================================
 *
 * (C) Copyright 2004 - 2016, MDA Information Systems LLC
 *
 * math-c++ is free software; you can redistribute it and/or modify
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

#ifndef __MATH_UTILITIES_H__
#define __MATH_UTILITIES_H__

#include <stdlib.h>
#include <sys/Conf.h>
namespace math
{
/*!
 * Find sign of input, expressed as -1, 0, or 1
 * \param val A signed number
 * \return 1 if val is positive, -1 if negative, 0 otherwise
 */
template <typename T>
int sign(T val)
{
    if (val < 0)
    {
        return -1;
    }
    if (val > 0)
    {
        return 1;
    }
    return 0;
}

inline double square(double val)
{
    return val * val;
}

/*!
 * Return true if argument is NaN
 *
 * \param value Argument to be checked for NaN
 * \return true if value is NaN
 */
inline bool isNaN(double value)
{
#ifdef HAVE_ISNAN
    return isnan(value);
#else
    // This will fail if g++ is compiled with -ffast-math
    // But in that case, we ought to have C99, so shouldn't even be here
    return value != value;
#endif
}


/*
 * Calculate the binomial coefficient
 * Be wary of the possibility of overflow from integer arithmetic.
 *
 * \param n number of possibilities
 * \param k number of outcomes
 * \return n choose k
 */
sys::Uint64_T nChooseK(size_t n, size_t k);
}

#endif

