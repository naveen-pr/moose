//* This file is part of the MOOSE framework
//* https://www.mooseframework.org
//*
//* All rights reserved, see COPYRIGHT for full restrictions
//* https://github.com/idaholab/moose/blob/master/COPYRIGHT
//*
//* Licensed under LGPL 2.1, please see LICENSE for details
//* https://www.gnu.org/licenses/lgpl-2.1.html

#ifndef GENERALIZEDPLANESTRAINPD_H
#define GENERALIZEDPLANESTRAINPD_H

#include "ScalarKernel.h"

class GeneralizedPlaneStrainPD;
class GeneralizedPlaneStrainUserObjectBasePD;

template <>
InputParameters validParams<GeneralizedPlaneStrainPD>();

/**
 * ScalarKernel class to assemble residual and diagonal jacobian fetched from userobject
 */
class GeneralizedPlaneStrainPD : public ScalarKernel
{
public:
  GeneralizedPlaneStrainPD(const InputParameters & parameters);

  virtual void reinit() override {}

  virtual void computeResidual() override;
  virtual void computeJacobian() override;

protected:
  /// Userobject to calculate the residual and jacobian
  const GeneralizedPlaneStrainUserObjectBasePD & _gpsuo;
};
#endif // GENERALIZEDPLANESTRAINPD_H
