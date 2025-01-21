import numpy as np
import gurobipy as gp
from gurobipy import GRB

def generate_knapsack(num_items):
    # Fix seed value
    rng = np.random.default_rng(seed=0)
    # Item values, weights
    values = rng.uniform(low=1, high=25, size=num_items)
    weights = rng.uniform(low=5, high=100, size=num_items)
    # Knapsack capacity
    capacity = 0.7 * weights.sum()

    return values, weights, capacity


def solve_knapsack_model(values, weights, capacity):
    num_items = len(values)
    # Turn values and weights numpy arrays to dict
    values_dict = {i: values[i] for i in range(num_items)}
    weights_dict = {i: weights[i] for i in range(num_items)}

    with gp.Env() as env:
        with gp.Model(name="knapsack", env=env) as model:
            # Define decision variables (binary variables for each item)
            x = model.addVars(num_items, vtype=GRB.BINARY, name="x")

            # Define the objective function: maximize the total value
            model.setObjective(
                gp.quicksum(values_dict[i] * x[i] for i in range(num_items)),
                GRB.MAXIMIZE
            )

            # Define the capacity constraint
            model.addConstr(
                gp.quicksum(weights_dict[i] * x[i] for i in range(num_items)) <= capacity,
                name="capacity"
            )

            # Optimize the model
            model.optimize()

            # Check and return the solution
            if model.Status == GRB.OPTIMAL:
                selected_items = [i for i in range(num_items) if x[i].X > 0.5]
                total_value = model.ObjVal
                total_weight = sum(weights_dict[i] for i in selected_items)
                print(f"Optimal value: {total_value}")
                print(f"Total weight: {total_weight}")
                print(f"Selected items: {selected_items}")
            else:
                print("No optimal solution found.")


# Generate data and solve the problem
data = generate_knapsack(10000)
solve_knapsack_model(*data)
