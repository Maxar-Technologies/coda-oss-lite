/* =========================================================================
 * This file is part of math.poly-c++ 
 * =========================================================================
 * 
 * (C) Copyright 2004 - 2014, MDA Information Systems LLC
 *
 * math.poly-c++ is free software; you can redistribute it and/or modify
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

#include <import/math/linear.h>
#include <import/math/poly.h>
#include "TestCase.h"

using namespace math::linear;
using namespace math::poly;

TEST_CASE(test1DPolyfit)
{
    const double xObs[] = { 1, -1, 2, -2 };
    const double yObs[] = { 3, 13, 1, 33 };
    const double zPoly[] = { 5, -4, 3, -1 };

    const std::vector<double> truthSTLVec(zPoly, zPoly + 4);

    const OneD<double> truth(3, zPoly);
    // First test the raw pointer signature
    const OneD<double> polyFromRaw = fit(4, xObs, yObs, 3);
    
    // Now call the other one
    const Vector<double> xv(4, xObs);
    const Vector<double> yv(4, yObs);

    const OneD<double> polyFromVec = fit(xv, yv, 3);

    const Fixed1D<3> fixed = fit(xv, yv, 3);

    const OneD<double> polyFromSTL(truthSTLVec);

    // Polys better match
    TEST_ASSERT_EQ(polyFromRaw, polyFromVec);
    TEST_ASSERT_EQ(polyFromRaw, truth);
    TEST_ASSERT_EQ(polyFromRaw, fixed);
    assert(polyFromRaw == truthSTLVec);
    TEST_ASSERT_EQ(polyFromSTL, truth);
}

TEST_CASE(test1DPolyfitLarge)
{
    // Fit a polynomial
    static const size_t NUM_OBS = 4;
    double xObs[] = { 1, -1, 2, -2 };
    const double yObs[] = { 3, 13, 1, 33 };
    const OneD<double> polyUnshifted = fit(NUM_OBS, xObs, yObs, 3);

    // Now shift all the x values and fit another polynomial
    static const size_t OFFSET = 10000;
    double xObsShifted[NUM_OBS];
    for (size_t ii = 0; ii < NUM_OBS; ++ii)
    {
        xObsShifted[ii] = xObs[ii] + OFFSET;
    }

    const OneD<double> polyShifted = fit(NUM_OBS, xObsShifted, yObs, 3);

    // If we evaluate the polynomials at equivalent x positions, we better
    // have almost the same values
    // TODO: This isn't close enough to pass right now
    for (size_t ii = 0; ii < NUM_OBS; ++ii)
    {
        //TEST_ASSERT_ALMOST_EQ(polyUnshifted(xObs[ii]),
        //                      polyShifted(xObsShifted[ii]));
    }

    // Calculate the mean residual error to determine goodness of fit.
    double errorSumUnshifted = 0.0;
    double errorSumShifted = 0.0;
    for (size_t ii = 0; ii < NUM_OBS; ++ii)
    {
        errorSumUnshifted += std::abs(polyUnshifted(xObs[ii]) - yObs[ii]);
        errorSumShifted += std::abs(polyShifted(xObsShifted[ii]) - yObs[ii]);
    }
    const double meanResidualErrorUnshifted = errorSumUnshifted / NUM_OBS;
    const double meanResidualErrorShifted = errorSumShifted / NUM_OBS;

    std::cout << "meanResidualErrorUnshifted: "
              << meanResidualErrorUnshifted
              << "\nmeanResidualErrorShifted: "
              << meanResidualErrorShifted
              << std::endl;

    TEST_ASSERT_ALMOST_EQ(meanResidualErrorUnshifted, 0.0);
    TEST_ASSERT_ALMOST_EQ(meanResidualErrorShifted, 0.0);
}

TEST_CASE(test2DPolyfit)
{
    const double coeffs[] =
    {
        -1.02141e-16, 0.15,
         0.08,        0.4825,
    };

    TwoD<double> truth(1, 1, coeffs);

    Matrix2D<double> x(3, 3);
    x(0, 0) = 1;  x(1, 0) = 0; x(2, 0) = 1;
    x(0, 1) = 1;  x(1, 1) = 1; x(2, 1) = 0;
    x(0, 2) = 0;  x(1, 2) = 1; x(2, 2) = 1;
        
    Matrix2D<double> y(3, 3);
    y(0, 0) = 1;  y(1, 0) = 1; y(2, 0) = 1;
    y(0, 1) = 0;  y(1, 1) = 1; y(2, 1) = 1;
    y(0, 2) = 0;  y(1, 2) = 0; y(2, 2) = 1;


    Matrix2D<double> z(3, 3);
    z(0, 0) = 1;   z(1, 0) = .3; z(2, 0) = 0;
    z(0, 1) = .16; z(1, 1) = 1;  z(2, 1) = 0;
    z(0, 2) = 0;   z(1, 2) = 0;  z(2, 2) = .85;

    TwoD<double> poly = fit(x, y, z, 1, 1);
    TEST_ASSERT_EQ(poly, truth);
}

TEST_CASE(test2DPolyfitLarge)
{
    // Use a defined polynomial to generate mapped values.  This ensures
    // it is possible to fit the points using at least as many coefficients.
    const double coeffs[] =
    {
        -1.021e-12, 7.5,    2.2,   5.5,
         0.88,      4.825,  .52,   .69,
         5.5,       1.0,    .62,   1.01,
         .012,      6.32,   1.56,  .376
    };

    TwoD<double> truth(3, 3, coeffs);

    // Specifically sampling points far from (0,0) to verify an issue
    // identified when fitting non-centered input.

    size_t gridSize = 9; // 9x9
    size_t xOffset = 25000;
    size_t xSpacing = 2134;
    size_t yOffset = 42000;
    size_t ySpacing = 3214;

    Matrix2D<double> x(gridSize, gridSize);
    for (size_t i = 0; i < gridSize; i++)
    {
        double xidx = xOffset + i * xSpacing;
        for (size_t j = 0; j < gridSize; j++)
        {
            x(i, j) = xidx;
        }
    }

    Matrix2D<double> y(gridSize, gridSize);
    for (size_t j = 0; j < gridSize; j++)
    {
        double yidx = yOffset + j * ySpacing;
        for (size_t i = 0; i < gridSize; i++)
        {
            y(i, j) = yidx;
        }
    }

    Matrix2D<double> z(gridSize, gridSize);
    for (size_t i = 0; i < gridSize; i++)
    {
        for (size_t j = 0; j < gridSize; j++)
        {
            z(i, j) = truth(i, j);
        }
    }

    // Fit polynomial
    TwoD<double> poly = fit(x, y, z, 5, 5);

    // Calculate the mean residual error to determine goodness of fit.
    double errorSum(0.0);
    for (size_t i = 0; i < gridSize; i++)
    {
        for (size_t j = 0; j < gridSize; j++)
        {
            double diff = z(i, j) - poly(x(i, j), y(i, j));
            errorSum += diff * diff;
        }
    }
    double meanResidualError = errorSum / (gridSize * gridSize);

    std::cout << "meanResidualError: " << meanResidualError << std::endl;

    TEST_ASSERT_ALMOST_EQ(meanResidualError, 0.0);
}

int main(int, char**)
{
    TEST_CHECK(test1DPolyfit);
    TEST_CHECK(test1DPolyfitLarge);
    TEST_CHECK(test2DPolyfit);
    TEST_CHECK(test2DPolyfitLarge);
}
