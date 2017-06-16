#!/usr/bin/env python

from random    import seed as set_seed
from random    import sample
from itertools import product
from itertools import combinations

"""
Notes on data representation:

Boolean circuits are represented by a connections list, for example:

[
    [(0, 3), (4, 0), (3, 2), (1, 0)],
    [(4, 0), (2, 0), (3, 2), (0, 0)]
]

The first item is a list of connections between layers 0 and 1, and the second
between layers 1 and 2. Between layers 0 and 1 there are connections between
gate pairs (0, 3), (4, 0) etc. meaning that gate 0 in layer 0 is connected to
gate 3 in layer 1 and so on.

Connection lists come in two varieties; id and position-based. Numbers in
id-based lists are gate ids while those in position-based are gate positions in
their respective layers.

Position-based lists (referred to as po_cons in code) can be generated from
id-based lists (id_cons) using an "arrangement list" in the form:

[
    [0, 1, 2],
    [2, 1, 0],
    [0, 1, 2],
]

In the above arrangement, for example, layers 0 and 2 contain gates sorted by id
while layer 1 contain gate 2, 1 then 0.

Arrangement lists can be used to explore the quality of ordering algorithms. The
basic steps for evaluating a given algorithm algo1() are:

1. Generate N connection lists (of given layers and cons. per layer)

2. Use algo1() to produce corresponding arrangements

3. Compared crossed connection counts for the id-based and positional connection
lists (pos lists are obtained using the arrangements in 2).
"""

def count_cross(cons):
    # Return the number of crossed connections in `cons`
    cross_count = 0
    is_oppo = lambda a, b : a>0 and b<0
    for layer_cons in cons:
        for (con1, con2) in combinations(layer_cons, 2):
            dx = con1[0] - con2[0]
            dy = con1[1] - con2[1]
            crossed = is_oppo(dx, dy) or is_oppo(dy, dx)
            cross_count += 1 if crossed else 0
    return cross_count

def print_cons(cons, label=None):
    # Pretty-print `cons` with an optional label
    if label:
        print "%s:\n" % label
    for key, val in enumerate(cons):
        print "%d : %s" % (key, val)
    print ""

def get_rand_id_cons(layers, connections, seed=1):
    # Generate random connectivity
    n = len(layers)
    id_cons = [None] * (n-1)
    set_seed(seed)
    for index, con_count in enumerate(connections):
        i = layers[index]     # number of gates in layer index
        j = layers[index + 1] # number of gates in layer index + 1
        all_cons = list(product(range(i), range(j)))
        id_cons[index] = sample(all_cons, con_count)
    return id_cons

def get_po_cons(id_cons, arrangement):
    # Generated positional (i.e. ordered) connectivity for id_cons given an
    # arrangement
    po_cons = []
    for layer, layer_cons in enumerate(id_cons):
        po_layer_cons = []
        for (id1, id2) in layer_cons:
            pos1 = arrangement[layer].index(id1)
            pos2 = arrangement[layer+1].index(id2)
            po_layer_cons.append((pos1, pos2))
        po_cons.append(po_layer_cons)
    return po_cons

def rand_arrange(layers, id_cons):
    return [range(x) for x in layers]

def get_distrib(layers, connections, arrange_fun, samples=1000):
    # Generate list of crossed connection counts, sampled from
    # randomly-generated id_cons
    def get_sample(seed):
        id_cons = get_rand_id_cons(layers, connections, seed)
        arrangement = arrange_fun(layers, id_cons)
        po_cons = get_po_cons(id_cons, arrangement)
        return count_cross(po_cons)
    return [get_sample(seed) for seed in range(samples)]

def print_test(layers, connections):
    # Perform basic function tests and print results
    arrangement = [range(x) for x in layers]
    id_cons = get_rand_id_cons(layers, connections)
    po_cons = get_po_cons(id_cons, arrangement)
    print_cons(id_cons, "id_cons")
    print_cons(po_cons, "po_cons")
    print "Crossed (id_cons) = %d" % count_cross(id_cons)
    print "Crossed (po_cons) = %d" % count_cross(po_cons)
    print ""

def main():

    layers = [5, 5, 5] # gates in each layer
    connections = [10, 10] # connections between adjacent layers

    # id_cons stores connections between gate ids
    # po_cons stores connections between gate positions

    print_test(layers, connections)
    print "samples_rand = %s;" % get_distrib(layers, connections, rand_arrange)

if __name__ == "__main__":
    main()
