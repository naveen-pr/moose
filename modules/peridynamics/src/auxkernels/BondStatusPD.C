//* This file is part of the MOOSE framework
//* https://www.mooseframework.org
//*
//* All rights reserved, see COPYRIGHT for full restrictions
//* https://github.com/idaholab/moose/blob/master/COPYRIGHT
//*
//* Licensed under LGPL 2.1, please see LICENSE for details
//* https://www.gnu.org/licenses/lgpl-2.1.html

#include "BondStatusPD.h"
#include "MeshBasePD.h"
#include "AuxiliarySystem.h"
#include "MooseVariable.h"

registerMooseObject("PeridynamicsApp", BondStatusPD);

template <>
InputParameters
validParams<BondStatusPD>()
{
  InputParameters params = validParams<AuxKernelBasePD>();
  params.addClassDescription("Class for updating the bond status based on different failure "
                             "criteria: critical stretch and "
                             "maximum principal stress");
  MooseEnum FailureCriteriaType("CriticalStretch MaximumPrincipalStress", "CriticalStretch");
  params.addParam<MooseEnum>(
      "failure_criterion", FailureCriteriaType, "Which failure criterion to be used");
  params.addRequiredCoupledVar("critical_variable", "Name of critical AuxVariable");
  params.addCoupledVar("additional_damage_criterion", "Name of additional criteria for damage");
  params.addCoupledVar("damage_index", "Damage_index");
  params.addParam<bool>("surface_correction", false, "True for surface correction based on volumeSum");
  params.addParam<bool>("limit_damage", false, "True if you want to limit damage index to > 0");
  params.set<ExecFlagEnum>("execute_on") = EXEC_TIMESTEP_END;

  return params;
}

BondStatusPD::BondStatusPD(const InputParameters & parameters)
  : AuxKernelBasePD(parameters),
    _failure_criterion(getParam<MooseEnum>("failure_criterion").getEnum<FailureCriterion>()),
    _bond_status_var(_subproblem.getVariable(_tid, "bond_status")),
    _critical_val(coupledValue("critical_variable")),
    _mechanical_stretch(getMaterialProperty<Real>("mechanical_stretch")),
    _stress(NULL),
    _additional_damage_criterion(getVar("additional_damage_criterion", 0)),
    _damage_index(getVar("damage_index", 0)),
    _surface_correction(getParam<bool>("surface_correction")),
    _limit_damage(getParam<bool>("limit_damage")),
    _serialized_solution(_aux_sys.serializedSolution())
{
  switch (_failure_criterion)
  {
    case FailureCriterion::CriticalStretch:
      break;

    case FailureCriterion::MaximumPrincipalStress:
    {
      if (hasMaterialProperty<RankTwoTensor>("stress"))
        _stress = &getMaterialProperty<RankTwoTensor>("stress");
      else
        mooseError("Material property stress is not available for current model!");

      break;
    }

    default:
      paramError("failure_criterion",
                 "Unsupported PD failure criterion. Choose from: CriticalStretch and "
                 "MaximumPrincipalStress");
  }
}

Real
BondStatusPD::computeValue()
{

  if (_t > 0.04)
    throw MooseException("Moose exception from BondStatusPD");

  bool insufficient_bonds = false;

    if ( _limit_damage == true){

    unsigned int node_id_i = _current_elem->get_node(0)->id();
    unsigned int node_id_j = _current_elem->get_node(1)->id();

    dof_id_type dof_i =
    _current_elem->get_node(0)->dof_number(_aux_sys.number(), _additional_damage_criterion->number(), 0);

    dof_id_type dof_j =
    _current_elem->get_node(1)->dof_number(_aux_sys.number(), _additional_damage_criterion->number(), 0);

    // Get intact bonds of nodes i and j
    unsigned int intact_bonds_i = _serialized_solution(dof_i);
    unsigned int intact_bonds_j = _serialized_solution(dof_j);

    if ( (intact_bonds_i <= _dim) || (intact_bonds_j <= _dim ) )
      insufficient_bonds = true;

  }

  Real avg_surf_corr_factor = 1.0;

  if (_surface_correction == true){

    unsigned int node_id_i = _current_elem->get_node(0)->id();
    unsigned int node_id_j = _current_elem->get_node(1)->id();

    // Surface correction factor
    Real surf_corr_factor_i = _pdmesh.avgVolumeSum() / _pdmesh.volumeSum(node_id_i);
    Real surf_corr_factor_j = _pdmesh.avgVolumeSum() / _pdmesh.volumeSum(node_id_j);

    avg_surf_corr_factor = 0.5 * (surf_corr_factor_i + surf_corr_factor_j);
  }

  Real val = 0.0;

  switch (_failure_criterion)
  {
    case FailureCriterion::CriticalStretch:
      val = _mechanical_stretch[0];
      break;

    case FailureCriterion::MaximumPrincipalStress:
    {
      RankTwoTensor avg_stress = 0.5 * ((*_stress)[0] + (*_stress)[1]);
      std::vector<Real> eigvals(LIBMESH_DIM, 0.0);

      if (_bond_status_var.getElementalValue(_current_elem) > 0.5)
        avg_stress.symmetricEigenvalues(eigvals);

      val = eigvals[LIBMESH_DIM - 1];

      break;
    }

    default:
      paramError("failure_criterion",
                 "Unsupported PD failure criterion. Choose from: CriticalStretch and "
                 "MaximumPrincipalStress");
  }

  if (_bond_status_var.getElementalValue(_current_elem) > 0.5 &&
      val < _critical_val[0] * avg_surf_corr_factor)
    return 1.0; // unbroken and does not meet the failure criterion, bond is still unbroken
  else if (_bond_status_var.getElementalValue(_current_elem) > 0.5 &&
          insufficient_bonds == true)
    return 1.0; // bond is still unbroken if there are too few bonds regardless of if it satifies failure criterion
  else
    return 0.0; // meet the failure criterion, bond is taken as broken



}
