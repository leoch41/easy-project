# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 11:45:15 2025

@author: franc
"""

import gurobipy as gp
from gurobipy import GRB
import numpy as np

# 24-hour Load Forecast (MW)
load_forecast = np.array(
    [4, 4, 4, 4, 4, 4, 6, 6, 12, 12, 12, 12, 12, 4, 4, 4, 4, 16, 16, 16, 16, 6.5, 6.5, 6.5]
)

# Solar energy forecast (MW)
solar_forecast = np.array(
    [0, 0, 0, 0, 0, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5, 3.5, 2.5, 2.0, 1.5, 1.0, 0.5, 0, 0, 0, 0, 0, 0]
)

# Global number of time intervals
nTimeIntervals = len(load_forecast)

# Thermal units
thermal_units = ["gen1", "gen2", "gen3"]
nUnits = len(thermal_units)

# Thermal units' costs (a + b*p + c*p^2), (startup and shutdown costs)
a = np.array([5.0, 5.0, 5.0])
b = np.array([0.5, 0.5, 3.0])
c = np.array([1.0, 0.5, 2.0])
sup_cost = np.array([2, 2, 2])
sdn_cost = np.array([1, 1, 1])

# Thermal units operating limits
pmin = np.array([1.5, 2.5, 1.0])
pmax = np.array([5.0, 10.0, 3.0])

# Thermal units dynamic data (initial commitment status)
init_status = np.array([0, 0, 0])

with gp.Env() as env, gp.Model(env=env) as model:
    # Variables
    thermal_out_power = model.addMVar((nUnits, nTimeIntervals), lb=0, name="thermal_out_power")
    comm_status = model.addMVar((nUnits, nTimeIntervals), vtype=GRB.BINARY, name="comm_status")
    startup_status = model.addMVar((nUnits, nTimeIntervals), vtype=GRB.BINARY, name="startup_status")
    shutdown_status = model.addMVar((nUnits, nTimeIntervals), vtype=GRB.BINARY, name="shutdown_status")

    # Objective function
    fixed_cost = a @ comm_status.sum(axis=1)
    linear_cost = b @ thermal_out_power.sum(axis=1)
    quadratic_cost = c @ (thermal_out_power ** 2).sum(axis=1)
    startup_cost = sup_cost @ startup_status.sum(axis=1)
    shutdown_cost = sdn_cost @ shutdown_status.sum(axis=1)

    model.setObjective(fixed_cost + linear_cost + quadratic_cost + startup_cost + shutdown_cost, GRB.MINIMIZE)

    # Power balance constraints
    model.addConstr(
        thermal_out_power.sum(axis=0) + solar_forecast == load_forecast,
        name="power_balance"
    )

    # Logical constraints
    initial_diff = comm_status[:, 0] - init_status
    model.addConstr(initial_diff == startup_status[:, 0] - shutdown_status[:, 0], name="initial_logic")
    diff_comm_status = comm_status[:, 1:] - comm_status[:, :-1]
    model.addConstr(
        diff_comm_status == startup_status[:, 1:] - shutdown_status[:, 1:],
        name="logical_constraints"
    )
    model.addConstr(
        startup_status + shutdown_status <= 1,
        name="startup_shutdown_exclusive"
    )

    # Physical constraints using indicator constraints
    for g in range(nUnits):
        for t in range(nTimeIntervals):
            model.addGenConstrIndicator(
                comm_status[g, t], True, thermal_out_power[g, t] >= pmin[g], 
                name=f"min_output_{g}_{t}"
            )
            model.addGenConstrIndicator(
                comm_status[g, t], True, thermal_out_power[g, t] <= pmax[g], 
                name=f"max_output_{g}_{t}"
            )
            model.addGenConstrIndicator(
                comm_status[g, t], False, thermal_out_power[g, t] == 0, 
                name=f"zero_output_{g}_{t}"
            )

    # Optimize the model
    model.optimize()

    # Display results
    if model.SolCount > 0:
        print(f"Overall Cost: {model.ObjVal:.2f}")
        print("Thermal Power Output:")
        for g, unit in enumerate(thermal_units):
            print(f"{unit}: {thermal_out_power.X[g, :]}")
        print("Commitment Status:")
        print(comm_status.X)
