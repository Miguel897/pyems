# -*- coding: utf-8 -*-
"""
Created on Wed May 15 14:33:22 2019

@author: Miguel

Useful links:
    - https://pyomo.readthedocs.io/en/latest/developer_reference/expressions/design.html

"""

# Standard library imports
import weakref
import logging
from os.path import join

# Third party imports
from datetime import datetime
import numpy
import pandas
import pyomo.kernel as pk
from pyomo.core.util import quicksum
from pyomo.environ import SolverFactory
from pyomo.opt.results.solver import SolverStatus as SolSt, TerminationCondition as TermCond

# Local application imports
from pyems.core.entity.entity import Entity
from pyems.core.optimization.utils import combine_positive_negative_variables, readable_pyomo_model
from pyems.core.results.results import Results
from pyems.core.utils.time import timestep_conversion


class Optimizer(Entity):
    """This class translates a SystemModel class into a Pyomo optimization model and then solved by GLPK solver.
    The results are extracted and checked to ensure physical validity of the solution."""

    def __init__(self, name='Optimizer', solver='glpk', full_solver_info=False, display_solver_info=False,
                 write_solver_info=True, solver_factory_options=None, solve_options=None, info_path='',
                 solver_info_file_name='solver_info.txt', readable_model_file_name='optimization_model.txt'):

        super().__init__(name, entity_type='optimizer')

        # Referencing main objects

        self._system = None
        self.optimization_model = None

        # Solver options

        self.solver = None
        self.solver_name = solver
        self.solver_factory_options = solver_factory_options if solver_factory_options is not None else {}
        self.solve_options = solve_options if solve_options is not None else {}
        self.solver_output = None
        self.solver_status = None

        # Resolution process info

        self.full_solver_info = full_solver_info
        self.display_solver_info = display_solver_info
        self.write_solver_info = write_solver_info
        self.hourly_timestamp = datetime.now().strftime('%Hh')
        self.solver_info_file_name = solver_info_file_name
        self.readable_model_file_name = readable_model_file_name
        self.info_path = info_path
        self.logger = logging.getLogger("pyems.Optimizer")

        # Results

        self.results = None
        self.target_soc = None

    """
    To avoid memory leakage between object (redundancy in memory and other effects) that are cross-referenced
    (i.e. object1 has and attribute that point to object2 and object2 has an attribute that also points to
    object1) this objects are weak referenced. The attributes storing this objects are transformed into properties
    to automate the reading and writing process.  
    """

    @property
    def system(self):
        if not self._system:
            return self._system
        _system = self._system()
        if _system:
            return _system
        else:
            raise LookupError("Referenced system was deleted.")

    @system.setter
    def system(self, system):
        self._system = weakref.ref(system)

    def create_optimization_model(self, config):

        self.logger.info('Creating optimization model.')

        # Consider using context managers

        # limit_sell = False

        # GET COMPONENTS FROM SYSTEM

        if self.system.has_battery:
            battery = self.system.get_battery_object()

        if self.system.has_external_grid:
            supply = self.system.get_external_grid_object()

        # STARTING MODEL

        m = pk.block()
        
        # Track the default attributes of the model to be aware of which the user adds.
        default_attributes = set(m.__dict__.keys())
        default_attributes.add('default_attributes')

        # SETS

        m.periods = range(config['periods'])
        m.E_set = []

        # VARIABLES

        m.E = pk.variable_dict()

        if self.system.has_stochastic_generators and not self.system.has_external_grid:
            m.E_set.append('stochastic')

            m.E['stochastic'] = pk.variable_list()
            for t in m.periods:
                m.E['stochastic'].append(
                    pk.variable(domain_type=pk.RealSet, lb=0, ub=self.system.stochastic_electrical_gen[t]))

        if self.system.has_external_grid:
            m.E_set.append('buy')
            m.E_set.append('sell')

            m.E['buy'] = pk.variable_list()
            for _ in m.periods:
                m.E['buy'].append(pk.variable(domain=pk.NonNegativeReals))

            m.E['sell'] = pk.variable_list()
            for _ in m.periods:
                m.E['sell'].append(pk.variable(domain=pk.NonNegativeReals))

            m.y_grid = pk.variable_list()
            for _ in m.periods:
                m.y_grid.append(pk.variable(domain_type=pk.IntegerSet, lb=0, ub=1))

        if self.system.has_battery:
            m.E_set.append('batt_chrg')
            m.E_set.append('batt_dis')

            m.E['batt_chrg'] = pk.variable_list()
            for _ in m.periods:
                # The upper bound are impose in the constraints below
                m.E['batt_chrg'].append(pk.variable(domain_type=pk.RealSet, lb=0))
            m.E['batt_dis'] = pk.variable_list()
            for _ in m.periods:
                m.E['batt_dis'].append(pk.variable(domain_type=pk.RealSet, lb=0))

            m.y_bat = pk.variable_list()
            for _ in m.periods:
                m.y_bat.append(pk.variable(domain_type=pk.IntegerSet, lb=0, ub=1))

            m.soc = pk.variable_list()
            for _ in m.periods:
                m.soc.append(pk.variable(domain_type=pk.RealSet, lb=battery.soc_lb, ub=battery.soc_ub))
            # Extra soc variable for the last value of soc that should be >= soc_l
            m.soc.append(pk.variable(domain_type=pk.RealSet, lb=battery.soc_l, ub=battery.soc_ub))

        # PARAMETERS

        if self.system.has_external_grid:
            m.prices = {
                'buy': supply.electricity_purchase_prices.copy(),
                'sell': supply.electricity_selling_prices.copy(),
            }

        # OBJECTIVE FUNCTION

        obj_exp = 0
        obj_sense = pk.minimize

        if self.system.has_external_grid:
            obj_exp = quicksum((m.E['buy'][t] * m.prices['buy'][t] for t in m.periods), linear=True) \
                   - quicksum((m.E['sell'][t] * m.prices['sell'][t] for t in m.periods), linear=True)

        m.obj = pk.objective(obj_exp, sense=obj_sense)

        # CONSTRAINTS
        
        # Grid constraints
        
        # if limit_sell:
        #     m.c_limit_sell = pk.constraint(
        #             lb=0, body=system['selling_ratio']
        #             * sum(m.E['buy'][t] + system['E_pv'][t] for t in m.periods)
        #             - sum(m.E['sell'][t] for t in m.periods))

        grid_m = 1e5
        m.cl_y_buy = pk.constraint_list()
        for t in m.periods:
            m.cl_y_buy.append(pk.constraint(
                body=m.y_grid[t] * grid_m - m.E['buy'][t], lb=0
            ))

        m.cl_y_sell = pk.constraint_list()
        for t in m.periods:
            m.cl_y_sell.append(pk.constraint(
                body=(1 - m.y_grid[t]) * grid_m - m.E['sell'][t], lb=0
            ))

        # Balance constraints
        
        energy_balance_exp = [0 for _ in m.periods]
        
        if self.system.has_fix_loads:
            for t in m.periods:
                energy_balance_exp[t] = -1 * self.system.fix_electrical_load[t]
        
        if self.system.has_external_grid:
            for t in m.periods:
                energy_balance_exp[t] = energy_balance_exp[t] + m.E['buy'][t] - m.E['sell'][t]
        
        if self.system.has_battery:
            for t in m.periods:
                energy_balance_exp[t] = energy_balance_exp[t] + m.E['batt_dis'][t] - m.E['batt_chrg'][t]
        
        if self.system.has_stochastic_generators and not self.system.has_external_grid:
            for t in m.periods:
                energy_balance_exp[t] = energy_balance_exp[t] + m.E['stochastic'][t]
        else:
            for t in m.periods:
                energy_balance_exp[t] = energy_balance_exp[t] + self.system.stochastic_electrical_gen[t]
        
        m.cl_balance = pk.constraint_list()
        for t in m.periods:
            m.cl_balance.append(pk.constraint(body=energy_balance_exp[t], rhs=0))

        # Battery constraints and restrictions
        
        if self.system.has_battery:
            m.soc[0].fix(battery.soc_0)

            m.cl_soc = pk.constraint_list()
            for t in m.periods:
                m.cl_soc.append(pk.constraint(
                    body=battery.batt_C * (m.soc[t + 1] - m.soc[t])
                    + 1 / battery.batt_dis_per * m.E['batt_dis'][t]
                    - battery.batt_chrg_per * m.E['batt_chrg'][t], rhs=0))

            m.cl_y_char = pk.constraint_list()
            for t in m.periods:
                m.cl_y_char.append(pk.constraint(
                    body=m.y_bat[t] * battery.batt_chrg_speed - m.E['batt_chrg'][t], lb=0
                ))

            m.cl_y_dis = pk.constraint_list()
            for t in m.periods:
                m.cl_y_char.append(pk.constraint(
                    body=(1 - m.y_bat[t]) * battery.batt_dis_speed - m.E['batt_dis'][t], lb=0
                ))

        # FINISHING

        # Determine the user defined attributes (written in this source code) by subtracting the defaults one.
        all_attributes = set(m.__dict__.keys())
        m.user_defined_attributes = list(all_attributes - default_attributes)

        self.optimization_model = m

        return m

    def solve_optimization_model(self, config):

        self.logger.info('Solving optimization model.')

        # Optimization model pre-resolution. We save it in case of a failure solving the model
        readable_model = readable_pyomo_model(self.optimization_model)
        file_name = self.hourly_timestamp + '_' + self.readable_model_file_name
        if self.write_solver_info:
            with open(join(self.info_path, file_name), 'w') as f:
                f.write(readable_pyomo_model(self.optimization_model))
                # self.optimization_model.write('model.lp', _solver_capability=None, _called_by_solver=False)

        if self.display_solver_info:
            print(readable_model)

        self.solver = SolverFactory(self.solver_name, **self.solver_factory_options)
        solver_output = self.solver.solve(self.optimization_model, **self.solve_options)

        # Optimization model post-resolution. Override the previous file with this new model with more info.
        if self.write_solver_info:
            with open(join(self.info_path, file_name), 'w') as f:
                f.write(readable_pyomo_model(self.optimization_model))

        # Check solver status.
        
        solver_status = solver_output.solver.status
        solver_termination_condition = solver_output.solver.termination_condition
        
        if (solver_status == SolSt.ok) and (solver_termination_condition == TermCond.optimal):
            solver_summary = "optimal"
            self.logger.info("Optimal solution found.")
        elif solver_termination_condition == TermCond.infeasible:
            solver_summary = "infeasible"
            self.logger.error('Infeasible probelm.')
        else:
            solver_summary = "other"
            print(f"Error found different from infeasibility. Solver status: {solver_status}")
            self.logger.error(f'Error found different from infeasibility. Solver status: {solver_status}')

        # Display full model information through screen.

        if self.display_solver_info:
            solver_output.write()
            
        # Save full model information to a file.
        
        if self.write_solver_info:
            file_name = self.hourly_timestamp + '_' + self.solver_info_file_name
            with open(join(self.info_path, file_name), 'w') as f:
                f.write('Solver output:\n\n')
                solver_output.write(ostream=f)
                # Report status information.

        self.solver_output = solver_output
        self.solver_status = {"solver_summary": solver_summary, "solver_status": str(solver_status),
                              "solver_termination_condition": str(solver_termination_condition)}

    def extract_results_from_opt_model(self, config):

        self.logger.info('Extracting results from optimization model.')

        # Extract variables of interest from the model

        raw_results = {}
        for e in self.optimization_model.E_set:
            raw_results[e] = numpy.array([self.optimization_model.E[e][t].value for t in self.optimization_model.periods])

        if self.system.has_battery:
            raw_results['soc'] = numpy.array([self.optimization_model.soc[t].value for t in self.optimization_model.periods])

        # check_soc = numpy.array([self.optimization_model.soc[t].value for t in range(len(self.optimization_model.soc))])
        # print(f'Full SOC vector: {check_soc}')

        # Check the raw_results for undefined values in the solver output

        for key, values in raw_results.items():
            if None in values:
                raise ValueError('The solver was unable to find a solution for \
                                 some variables in at least: {}'.format(key))

        # Combine var also checks that the system do not charge and discharge or
        # buy and sell energy at the same time. Below are the error messages:

        results = {}

        if not (self.system.has_interruptable_loads or self.system.has_schedulable_loads):
            results['building_load'] = self.system.fix_electrical_load
        else:
            raise NotImplementedError('Flexible loads not implemented yet.')

        if self.system.has_stochastic_generators:
            results['stochastic_generation'] = self.system.stochastic_electrical_gen.copy()

        if self.system.has_external_grid:
            error_supply = 'Invalid solution. The system buys and sells \
                            electricity at the same time'
            results['power_supply_flow'] = combine_positive_negative_variables(raw_results['buy'], raw_results['sell'], error_supply)

        if self.system.has_battery:
            error_batt = 'Invalid solution. The system is charging and \
                         discharging the battery at the same time'
            results['battery_energy_flow'] = combine_positive_negative_variables(raw_results['batt_dis'], raw_results['batt_chrg'], error_batt)
            results['battery_soc'] = numpy.array(raw_results['soc'])

        if self.system.has_external_grid:
            results['prices_buy'] = numpy.array(self.optimization_model.prices['buy'])
            results['prices_sell'] = numpy.array(self.optimization_model.prices['sell'])

        timestep = timestep_conversion(config['timestep'], pd_units=True)
        results_index = pandas.date_range(
            start=config['start'], periods=config['periods'], freq=timestep
        )

        self.results = pandas.DataFrame(results, index=results_index)

        # We assume that the first SOC <results_index[0]> in the results is the initial SOC. Therefore, the target SOC
        # for the next period is the second one <results_index[1]>
        self.target_soc = float(self.results.at[results_index[1], 'battery_soc'])

        return results

    def check_solution_physical_validity(self, config, tolerance=1e-2):

        # Check that the solution has physical sense and therefore there is no
        # evident mistake in the optimization model.

        self.logger.info('Checking physical validity of results.')

        # Balance check.

        energy_balance = numpy.zeros(config['periods'])

        if self.system.has_fix_loads:
            energy_balance = energy_balance - self.results['building_load']

        if self.system.has_external_grid:
            energy_balance = energy_balance + self.results['power_supply_flow']

        if self.system.has_battery:
            energy_balance = energy_balance + self.results['battery_energy_flow']

        if self.system.has_stochastic_generators:
            energy_balance = energy_balance + self.results['stochastic_generation']

        if any([abs(e) > tolerance for e in energy_balance]):
            print(energy_balance)
            raise ValueError('Invalid solution. Energy balance violation in the system.')

        # Battery energy conservation check

        if self.system.has_battery:

            battery = self.system.get_battery_object()

            batt_dis = numpy.array([x if x > 0 else 0 for x in self.results['battery_energy_flow']])
            batt_charg = numpy.array([-1 * x if x < 0 else 0 for x in self.results['battery_energy_flow']])
            # In the results series doesn't appear the final SOC at the end of the last period.
            soc = numpy.append(self.results['battery_soc'], self.optimization_model.soc[-1].value)

            battery_balance = battery.batt_C * (soc[1:] - soc[:-1]) \
                              + 1 / battery.batt_dis_per * batt_dis \
                              - battery.batt_chrg_per * batt_charg

            if any([abs(e) > tolerance for e in battery_balance]):
                print(battery_balance)
                raise ValueError('Invalid solution. Energy balance violation in the battery.')
    
    def solve(self, system=None, config=None):

        if self.system is None and system is not None:
            self.system = system

        if self.system is None:
            raise ValueError("No system is assigned to the optimizer.")

        self.create_optimization_model(config)
        self.solve_optimization_model(config)
        self.extract_results_from_opt_model(config)
        self.check_solution_physical_validity(config)

        self.logger.info('Creating results object.')

        return Results(output_data=self.results, target_soc=self.target_soc, timestamp=config['start'])

    def clear(self):
        self.optimization_model = None
        self.results = None
        self.target_soc = None



