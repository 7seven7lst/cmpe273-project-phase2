import mmh3
import math

def int_to_float(value):
    fifty_three_ones = 0xFFFFFFFFFFFFFFFF >> (64 - 53)
    fifty_three_zeros = float(1 << 53)
    return (value & fifty_three_ones) / fifty_three_zeros

class Node(object):
    def __init__(self, node, seed):
        self.node, self.seed = node, seed

    def compute_score(self, key):
        hash_1, hash_2 = mmh3.hash64(str(key), 0xFFFFFFFF & self.seed)
        hash_f = int_to_float(hash_2)
        score = 1.0 / -math.log(hash_f)
        return score

def determine_responsible_node(nodes, key):
    highest_score, champion = -1, None
    for node in nodes:
        score = node.compute_score(key)
        if score > highest_score:
            champion, highest_score = node, score
    return champion
