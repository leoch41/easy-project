# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 15:58:35 2025

@author: franc

"""
from functools import partial
import gurobipy as gp
from gurobipy import GRB
import time


class CallbackData:
    def __init__(self):
        self.last_gap_change_time = -GRB.INFINITY  # Dernier temps où le MIPGap a changé significativement
        self.last_gap = GRB.INFINITY              # Dernier MIPGap enregistré


def callback(model, where, *, cbdata):
    if where == GRB.Callback.MIP:
        # Récupérer le nombre de solutions trouvées
        solution_count = model.cbGet(GRB.Callback.MIP_SOLCNT)
        if solution_count == 0:
            return

        # Obtenir le MIPGap actuel
        mip_gap = model.cbGet(GRB.Callback.MIP_GAP)

        # Temps écoulé depuis le début de l'optimisation
        runtime = model.cbGet(GRB.Callback.RUNTIME)

        # Si c'est la première solution, initialiser le suivi
        if cbdata.last_gap == GRB.INFINITY:
            cbdata.last_gap = mip_gap
            cbdata.last_gap_change_time = runtime
            return

        # Vérifier si le MIPGap a changé significativement
        if abs(cbdata.last_gap - mip_gap) > epsilon_to_compare_gap:
            cbdata.last_gap = mip_gap
            cbdata.last_gap_change_time = runtime
        else:
            # Vérifier si le temps écoulé depuis le dernier changement est supérieur à 50 secondes
            if runtime - cbdata.last_gap_change_time > time_from_best:
                print(f"Terminating optimization: No significant MIPGap improvement in {time_from_best} seconds.")
                model.terminate()


# Charger le modèle depuis le fichier MPS
with gp.read("data/mkp.mps.bz2") as model:
    # Paramètres pour la fonction de rappel
    time_from_best = 50  # Temps (en secondes) avant de terminer si le MIPGap ne s'améliore pas
    epsilon_to_compare_gap = 1e-4  # Seuil de changement significatif pour le MIPGap

    # Initialiser les données pour le callback
    callback_data = CallbackData()

    # Créer une fonction partielle pour passer les données au callback
    callback_func = partial(callback, cbdata=callback_data)

    # Optimiser avec la fonction de rappel
    model.optimize(callback_func)

    # Vérifier le statut final de l'optimisation
    if model.Status == GRB.OPTIMAL:
        print("Optimal solution found.")
    elif model.Status == GRB.TIME_LIMIT:
        print("Optimization stopped due to time limit.")
    elif model.Status == GRB.INTERRUPTED:
        print("Optimization interrupted.")
    else:
        print("Optimization ended with status:", model.Status)
