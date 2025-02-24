# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 08:36:18 2025

@author: franc
"""

import sys
import gurobipy as gp
from gurobipy import GRB

def parse_input(filename):
    
    with open(filename, 'r') as file:
        N = int(file.readline().strip())  # nb de photos
        photos = []

        for i in range(N):
            data = file.readline().strip().split()
            orientation = data[0]  # 'H' ou 'V'
            tags = set(data[2:])  #liste de tags
            photos.append((i, orientation, tags))

    return photos

def pair_vertical_photos(photos):
    
    vertical_photos = [p for p in photos if p[1] == 'V'] #selectionne photo vertical
    used = set()
    paired_slides = []

    for i, (id1, _, tags1) in enumerate(vertical_photos):
        
        if id1 in used:
            continue # on passe si photo deja utiliser
            
        best_match = None
        max_unique_tags = -1

        for j, (id2, _, tags2) in enumerate(vertical_photos):
            if i != j and id2 not in used:
                combined_tags = tags1 | tags2
                if len(combined_tags) > max_unique_tags:
                    best_match = (id1, id2, combined_tags)
                    max_unique_tags = len(combined_tags)

        if best_match:
            paired_slides.append((best_match[0], best_match[1], best_match[2]))
            used.add(best_match[0])
            used.add(best_match[1])

    return paired_slides

def calcul_score(tags1, tags2): # calcul de l'interet
    common = len(tags1 & tags2)
    only_in_1 = len(tags1 - tags2)
    only_in_2 = len(tags2 - tags1)
    return min(common, only_in_1, only_in_2)

def optimize_slideshow(slides):
    model = gp.Model("slideshow")

    S = len(slides)
    vars_x = model.addVars(S, S, vtype=GRB.BINARY)

    #contrainte chaque slide a exactement un prédécesseur et un successeur
    model.addConstrs(vars_x.sum(i, '*') == 1 for i in range(S))
    model.addConstrs(vars_x.sum('*', j) == 1 for j in range(S))

    # fonction objectif 
    objective = gp.quicksum(
        calcul_score(slides[i][1], slides[j][1]) * vars_x[i, j]
        for i in range(S) for j in range(S) if i != j
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    model.optimize()

    # calcul ordre optimal
    ordered_slides = []
    for i in range(S):
        for j in range(S):
            if vars_x[i, j].x > 0.5:
                ordered_slides.append(slides[i])
                break

    return ordered_slides

def generate_slideshow(photos):
    
    slides = []
    
    #ajoute les photos horizontales
    for id, orientation, tags in photos:
        if orientation == 'H':
            slides.append(([id], tags))

    #ajoute photos verticales
    vertical_pairs = pair_vertical_photos(photos)
    for id1, id2, tags in vertical_pairs:
        slides.append(([id1, id2], tags))

    ordered_slides = optimize_slideshow(slides)
    
    return ordered_slides

def write_output(slideshow, output_file="slideshow.sol"):
    with open(output_file, 'w') as file:
        file.write(f"{len(slideshow)}\n")
        for slide in slideshow:
            file.write(" ".join(map(str, slide[0])) + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slideshow.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    #input_file = "data/trivial.txt"
    photos = parse_input(input_file)
    slideshow = generate_slideshow(photos)
    write_output(slideshow)
    print(f"Slideshow généré : {len(slideshow)} solution enregistrés dans slideshow.sol")