# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 15:58:35 2025

@author: franc

"""

import json
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Charger les données à partir du fichier JSON
with open("data/portfolio-example.json", "r") as f:
    data = json.load(f)

# Extraction des paramètres
n = data["num_assets"]  # Nombre d'actifs
sigma = np.array(data["covariance"])  # Matrice de covariance
mu = np.array(data["expected_return"])  # Rendements attendus
mu_0 = data["target_return"]  # Rendement cible
k = data["portfolio_max_size"]  # Nombre maximal d'actifs à inclure

# Création du modèle
with gp.Model("portfolio") as model:
    # Variables de décision
    x = model.addVars(n, lb=0, ub=1, name="x")  # Fraction investie dans chaque actif
    y = model.addVars(n, vtype=GRB.BINARY, name="y")  # Indicateur binaire pour inclure un actif

    # Objectif : minimiser le risque (variance pondérée)
    risk_expr = gp.quicksum(
        sigma[i, j] * x[i] * x[j] for i in range(n) for j in range(n)
    )
    model.setObjective(risk_expr, GRB.MINIMIZE)

    # Contraintes
    # 1. Rendement attendu >= rendement cible
    model.addConstr(
        gp.quicksum(mu[i] * x[i] for i in range(n)) >= mu_0, name="return"
    )

    # 2. Investissement total = 1 (100 % du portefeuille)
    model.addConstr(gp.quicksum(x[i] for i in range(n)) == 1, name="budget")

    # 3. Actifs inclus dans le portefeuille limité à k
    model.addConstr(gp.quicksum(y[i] for i in range(n)) <= k, name="max_assets")

    # 4. Relation entre x et y : si un actif n'est pas sélectionné (y[i] = 0), x[i] = 0
    for i in range(n):
        model.addConstr(x[i] <= y[i], name=f"x_to_y_{i}")

    # Résolution du modèle
    model.optimize()

    # Extraction des résultats
    if model.Status == GRB.OPTIMAL:
        # Variables de portefeuille
        portfolio = [x[i].X for i in range(n)]
        # Risque optimisé
        risk = model.ObjVal
        # Rendement obtenu
        expected_return = sum(mu[i] * portfolio[i] for i in range(n))

        # Stockage des résultats dans un DataFrame
        df = pd.DataFrame(
            data=portfolio + [risk, expected_return],
            index=[f"asset_{i}" for i in range(n)] + ["risk", "return"],
            columns=["Portfolio"],
        )
        print(df)
    else:
        print("Aucune solution optimale trouvée.")
