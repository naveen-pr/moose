//* This file is part of the MOOSE framework
//* https://www.mooseframework.org
//*
//* All rights reserved, see COPYRIGHT for full restrictions
//* https://github.com/idaholab/moose/blob/master/COPYRIGHT
//*
//* Licensed under LGPL 2.1, please see LICENSE for details
//* https://www.gnu.org/licenses/lgpl-2.1.html

#include "gtest/gtest.h"

#include "RankTwoTensor.h"
#include "RankFourTensor.h"

TEST(RankTwoEigenRoutines, symmetricEigenvalues)
{
  RankTwoTensor m0(0, 0, 0, 0, 0, 0, 0, 0, 0);
  RankTwoTensor m2(1, 0, 0, 0, 2, 0, 0, 0, 3);
  RankTwoTensor m3(1, 2, 3, 2, -5, -6, 3, -6, 9);
  std::vector<Real> eigvals;

  m0.symmetricEigenvalues(eigvals);
  EXPECT_NEAR(0, eigvals[0], 0.0001);
  EXPECT_NEAR(0, eigvals[1], 0.0001);
  EXPECT_NEAR(0, eigvals[2], 0.0001);

  m2.symmetricEigenvalues(eigvals);
  EXPECT_NEAR(1, eigvals[0], 0.0001);
  EXPECT_NEAR(2, eigvals[1], 0.0001);
  EXPECT_NEAR(3, eigvals[2], 0.0001);

  m3.symmetricEigenvalues(eigvals);
  EXPECT_NEAR(-8.17113, eigvals[0], 0.0001);
  EXPECT_NEAR(1.51145, eigvals[1], 0.0001);
  EXPECT_NEAR(11.6597, eigvals[2], 0.0001);
}

TEST(RankTwoEigenRoutines, dsymmetricEigenvalues)
{
  RankTwoTensor m2(1, 0, 0, 0, 2, 0, 0, 0, 3);
  RankTwoTensor m3(1, 2, 3, 2, -5, -6, 3, -6, 9);
  RankTwoTensor m5(1, 0, 0, 0, 1, 0, 0, 0, 2);
  RankTwoTensor m6(1, 0, 0, 0, 2, 0, 0, 0, 1);
  RankTwoTensor m7(1, 0, 0, 0, 2, 0, 0, 0, 2);
  RankTwoTensor m8(1, 1, 0, 1, 1, 0, 0, 0, 2); // has eigenvalues 0, 2 and 2

  // this derivative is less trivial than dtrace and dsecondInvariant,
  // so let's check with a finite-difference approximation
  Real ep = 1E-5; // small finite-difference parameter

  std::vector<Real> eigvals;        // eigenvalues in ascending order provided by RankTwoTensor
  std::vector<RankTwoTensor> deriv; // derivatives of these eigenvalues provided by RankTwoTensor

  RankTwoTensor mep;                 // the RankTwoTensor with successive entries shifted by ep
  std::vector<Real> eigvalsep;       // eigenvalues of mep in ascending order
  std::vector<Real> eigvalsep_minus; // for equal-eigenvalue cases, i take a central difference

  m2.dsymmetricEigenvalues(eigvals, deriv);
  mep = m2;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      mep(i, j) += ep;
      mep.symmetricEigenvalues(eigvalsep);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvals[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) -= ep;
    }

  m3.dsymmetricEigenvalues(eigvals, deriv);
  mep = m3;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      mep(i, j) += ep;
      mep.symmetricEigenvalues(eigvalsep);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvals[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) -= ep;
    }

  // the equal-eigenvalue cases follow:

  m5.dsymmetricEigenvalues(eigvals, deriv);
  mep = m5;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      // here i use a central difference to define the
      // discontinuous derivative
      mep(i, j) += ep / 2.0;
      mep.symmetricEigenvalues(eigvalsep);
      mep(i, j) -= ep;
      mep.symmetricEigenvalues(eigvalsep_minus);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvalsep_minus[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) += ep / 2.0;
    }

  m6.dsymmetricEigenvalues(eigvals, deriv);
  mep = m6;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      // here i use a central difference to define the
      // discontinuous derivative
      mep(i, j) += ep / 2.0;
      mep.symmetricEigenvalues(eigvalsep);
      mep(i, j) -= ep;
      mep.symmetricEigenvalues(eigvalsep_minus);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvalsep_minus[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) += ep / 2.0;
    }

  m7.dsymmetricEigenvalues(eigvals, deriv);
  mep = m7;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      // here i use a central difference to define the
      // discontinuous derivative
      mep(i, j) += ep / 2.0;
      mep.symmetricEigenvalues(eigvalsep);
      mep(i, j) -= ep;
      mep.symmetricEigenvalues(eigvalsep_minus);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvalsep_minus[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) += ep / 2.0;
    }

  m8.dsymmetricEigenvalues(eigvals, deriv);
  mep = m8;
  for (unsigned i = 0; i < 3; ++i)
    for (unsigned j = 0; j < 3; ++j)
    {
      // here i use a central difference to define the
      // discontinuous derivative
      mep(i, j) += ep / 2.0;
      mep.symmetricEigenvalues(eigvalsep);
      mep(i, j) -= ep;
      mep.symmetricEigenvalues(eigvalsep_minus);
      for (unsigned k = 0; k < 3; ++k)
        EXPECT_NEAR((eigvalsep[k] - eigvalsep_minus[k]) / ep, deriv[k](i, j), ep);
      mep(i, j) += ep / 2.0;
    }
}

/**
 * Validity of the second derivatives has been tested by splitting a 3x3 matrix into 2x2 matrices
 * Ex: 3x3 symmetric matrix
 *       a00 a01 a02
 *   A = a10 a11 a12
 *       a20 a21 a22
 * Upper left four elements and lower right four elements can be given by 2x2 matrices
 *       a10 a01   and  a11 a12
 *       a10 a11        a21 a22
 *
 * Now eigen values of the above 2x2 matrixes can be written as:
 *    lamda = 0.5*[(a00+a11) + or - sqrt[(a00+a11)^2-4(a00.a11-((a01+a10)/2)^2)]
 * By differentiating lamda with respect to a00, a01, a11, a12, a22
 * some elements of rank four tensor ie. a0000, a0001, a1100, a0101, a1111, a1112, a2211, a1212
 * (second derivatives) can be verified
 * Furthermore the validity of all the elements of rank four tensor has been tested in
 * "d2symmetricEigenvaluesTest2" method using finite difference method.
 */
TEST(RankTwoEigenRoutines, d2symmetricEigenvaluesTest1)
{
  RankTwoTensor m2(1, 0, 0, 0, 2, 0, 0, 0, 3);
  RankTwoTensor m4(1, 0, 0, 0, 3, 0, 0, 0, 2);

  std::vector<RankFourTensor> second_deriv;
  m4.d2symmetricEigenvalues(second_deriv);

  EXPECT_NEAR(0, second_deriv[0](0, 0, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](0, 0, 0, 1), 0.000001);
  EXPECT_NEAR(-0.25, second_deriv[0](0, 1, 0, 1), 0.000001);
  EXPECT_NEAR(-0.25, second_deriv[0](0, 1, 1, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](1, 1, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](2, 2, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](1, 1, 1, 0), 0.000001);

  m2.d2symmetricEigenvalues(second_deriv);
  EXPECT_NEAR(0, second_deriv[0](0, 0, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](0, 0, 0, 1), 0.000001);
  EXPECT_NEAR(-0.5, second_deriv[0](0, 1, 0, 1), 0.000001);
  EXPECT_NEAR(-0.5, second_deriv[0](0, 1, 1, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](1, 1, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](2, 2, 0, 0), 0.000001);
  EXPECT_NEAR(0, second_deriv[0](1, 1, 1, 0), 0.000001);
}

/**
 * Second derivative of Eginvalues are compared with finite difference method
 * This method checks all the elements in RankFourTensor
 **/
TEST(RankTwoEigenRoutines, d2symmetricEigenvaluesTest2)
{
  RankTwoTensor m2(1, 0, 0, 0, 2, 0, 0, 0, 3);
  RankTwoTensor m3(1, 2, 3, 2, -5, -6, 3, -6, 9);

  Real ep = 1E-5; // small finite-difference parameter
  std::vector<Real> eigvals, eigvalsep,
      eigvalsep_minus; // eigenvalues in ascending order provided by RankTwoTensor
  std::vector<RankTwoTensor> deriv, derivep,
      derivep_minus; // derivatives of these eigenvalues provided by RankTwoTensor
  std::vector<RankFourTensor> second_deriv;

  RankTwoTensor mep; // the RankTwoTensor with successive entries shifted by ep

  m2.d2symmetricEigenvalues(second_deriv);
  m2.dsymmetricEigenvalues(eigvals, deriv);
  mep = m2;
  for (unsigned int m = 0; m < 3; m++)
    for (unsigned i = 0; i < 3; i++)
      for (unsigned j = 0; j < 3; j++)
      {
        for (unsigned int k = 0; k < 3; k++)
          for (unsigned int l = 0; l < 3; l++)
          {
            mep(k, l) += ep;
            mep.dsymmetricEigenvalues(eigvalsep, derivep);
            EXPECT_NEAR((derivep[m](i, j) - deriv[m](i, j)) / ep, second_deriv[m](i, j, k, l), ep);
            mep(k, l) -= ep;
          }
      }

  m3.d2symmetricEigenvalues(second_deriv);
  m3.dsymmetricEigenvalues(eigvals, deriv);
  mep = m3;
  for (unsigned int m = 0; m < 3; m++)
    for (unsigned i = 0; i < 3; i++)
      for (unsigned j = 0; j < 3; j++)
      {
        for (unsigned int k = 0; k < 3; k++)
          for (unsigned int l = 0; l < 3; l++)
          {
            mep(k, l) += ep;
            mep.dsymmetricEigenvalues(eigvalsep, derivep);
            EXPECT_NEAR((derivep[m](i, j) - deriv[m](i, j)) / ep, second_deriv[m](i, j, k, l), ep);
            mep(k, l) -= ep;
          }
      }
}

TEST(RankTwoEigenRoutines, someIdentities)
{
  RankTwoTensor m3(1, 2, 3, 2, -5, -6, 3, -6, 9);

  // checks identities that should hold if eigenvalues
  // and invariants are correctly calculated
  std::vector<Real> eigvals;
  m3.symmetricEigenvalues(eigvals);

  Real mean = m3.tr() / 3.0;
  Real secondInvariant = m3.secondInvariant();
  Real shear = std::sqrt(secondInvariant);
  m3.thirdInvariant();

  Real lode = std::asin(m3.sin3Lode(0, 0) / 3.0);

  Real two_pi_over_3 = 2.09439510239;
  EXPECT_NEAR(
      eigvals[0], 2 * shear * std::sin(lode - two_pi_over_3) / std::sqrt(3.0) + mean, 0.0001);
  EXPECT_NEAR(eigvals[1], 2 * shear * std::sin(lode) / std::sqrt(3.0) + mean, 0.0001);
  EXPECT_NEAR(
      eigvals[2], 2 * shear * std::sin(lode + two_pi_over_3) / std::sqrt(3.0) + mean, 0.0001);
}
