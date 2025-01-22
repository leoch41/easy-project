# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 11:43:21 2025

@author: franc
"""

import gurobipy as gp
from gurobipy import GRB

# 24-hour Load Forecast (MW)
load_forecast = [
    4, 4, 4, 4, 4, 4, 6, 6, 12, 12, 12, 12, 12, 4, 4, 4, 4, 16, 16, 16, 16, 6.5, 6.5, 6.5,
]

# Solar energy forecast (MW)
solar_forecast = [
    0, 0, 0, 0, 0, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5, 3.5, 2.5, 2.0, 1.5, 1.0, 0.5, 0, 0, 0, 0, 0, 0,
]

# Global number of time intervals
nTimeIntervals = len(load_forecast)

# Thermal units
thermal_units = ["gen1", "gen2", "gen3"]

# Thermal units' costs (a + b*p + c*p^2), (startup and shutdown costs)
thermal_units_cost, a, b, c, sup_cost, sdn_cost = gp.multidict(
    {"gen1": [5.0, 0.5, 1.0, 2, 1], "gen2": [5.0, 0.5, 0.5, 2, 1], "gen3": [5.0, 3.0, 2.0, 2, 1]}
)

# Thermal units operating limits
thermal_units_limits, pmin, pmax = gp.multidict(
    {"gen1": [1.5, 5.0], "gen2": [2.5, 10.0], "gen3": [1.0, 3.0]}
)

# Thermal units dynamic data (initial commitment status)
thermal_units_dyn_data, init_status = gp.multidict(
    {"gen1": [0], "gen2": [0], "gen3": [0]}
)

def show_results(model, thermal_units_out_power, solar_forecast, load_forecast):
    obj_val = model.ObjVal
    print(f"Overall Cost = {round(obj_val, 2)}")
    print("\n%5s" % "Time", end=" ")
    for t in range(nTimeIntervals):
        print(f"{t:4}", end=" ")
    print("\n")

    for g in thermal_units:
        print(f"{g:5}", end=" ")
        for t in range(nTimeIntervals):
            print(f"{thermal_units_out_power[g, t].X:4.1f}", end=" ")
        print("\n")

    print("%5s" % "Solar", end=" ")
    for t in range(nTimeIntervals):
        print(f"{solar_forecast[t]:4.1f}", end=" ")
    print("\n")

    print("%5s" % "Load", end=" ")
    for t in range(nTimeIntervals):
        print(f"{load_forecast[t]:4.1f}", end=" ")
    print("\n")

with gp.Env() as env, gp.Model(env=env) as model:
    # Add decision variables
    thermal_units_out_power = model.addVars(
        thermal_units, range(nTimeIntervals), lb=0, name="thermal_out_power"
    )
    thermal_units_comm_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="thermal_comm_status"
    )
    thermal_units_startup_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="startup_status"
    )
    thermal_units_shutdown_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="shutdown_status"
    )

    # Define objective function
    obj_fun_expr = gp.QuadExpr()
    for t in range(nTimeIntervals):
        for g in thermal_units:
            obj_fun_expr += (
                a[g] * thermal_units_comm_status[g, t]
                + b[g] * thermal_units_out_power[g, t]
                + c[g] * thermal_units_out_power[g, t] * thermal_units_out_power[g, t]
                + sup_cost[g] * thermal_units_startup_status[g, t]
                + sdn_cost[g] * thermal_units_shutdown_status[g, t]
            )
    model.setObjective(obj_fun_expr, GRB.MINIMIZE)

    # Power balance constraints
    for t in range(nTimeIntervals):
        model.addConstr(
            gp.quicksum(thermal_units_out_power[g, t] for g in thermal_units) + solar_forecast[t]
            == load_forecast[t],
            name=f"power_balance_{t}",
        )

    # Logical constraints
    for t in range(nTimeIntervals):
        for g in thermal_units:
            if t == 0:
                model.addConstr(
                    thermal_units_comm_status[g, t] - init_status[g]
                    == thermal_units_startup_status[g, t] - thermal_units_shutdown_status[g, t],
                    name=f"logical_initial_{g}_{t}",
                )
            else:
                model.addConstr(
                    thermal_units_comm_status[g, t] - thermal_units_comm_status[g, t - 1]
                    == thermal_units_startup_status[g, t] - thermal_units_shutdown_status[g, t],
                    name=f"logical_{g}_{t}",
                )
            model.addConstr(
                thermal_units_startup_status[g, t] + thermal_units_shutdown_status[g, t] <= 1,
                name=f"startup_shutdown_{g}_{t}",
            )

    # Physical constraints using indicator constraints
    for t in range(nTimeIntervals):
        for g in thermal_units:
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t], True, 
                thermal_units_out_power[g, t] >= pmin[g], 
                name=f"min_output_{g}_{t}"
            )
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t], True, 
                thermal_units_out_power[g, t] <= pmax[g], 
                name=f"max_output_{g}_{t}"
            )
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t], False, 
                thermal_units_out_power[g, t] == 0, 
                name=f"zero_output_{g}_{t}"
            )

    # Optimize the model
    model.optimize()

    # Show results
    if model.SolCount > 0:
        show_results(model, thermal_units_out_power, solar_forecast, load_forecast)
