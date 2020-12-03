import bisect
import hashlib
import collections

class Node(object):
    def __init__(self, node, name):
        self.node = node
        self.name = name #tcp://127.0.0.1:{server_port}

class ConsistentHashRing(object):
    def __init__(self, nodes):
        self.ring = dict() # hashed-key => node
        for node in nodes:
            hashed_key = self.hash(node.name)
            self.ring[hashed_key] = node
        self.ring = dict(sorted(self.ring.items()))

    def hash(self, name):
        key = str(name).encode('utf-8')
        return int(hashlib.md5(key).hexdigest(), 16) % (2**32)

    def add_node(self, node):
        hashed_key = self.hash(node.name)
        self.ring[hashed_key] = node
        self.ring = dict(sorted(self.ring.items()))

    def remove_node(self, node):
        hashed_key = self.hash(node.name)
        self.ring.pop(hashed_key, None)
        self.ring = dict(sorted(self.ring.items()))

    def get_node(self, key):
        # return current node, and next node
        hashed_key = self.hash(key)
        key_list = list(self.ring.keys())
        last_key = int(key_list[-1])
        first_key = int(key_list[0])
        nodes = list(self.ring.values())
        if (hashed_key > last_key):
            return nodes[0], nodes[1]
        elif (hashed_key <= first_key):
            return nodes[0], nodes[1]
        else:
            n1 = None
            n2 = None
            for k, v in self.ring.items():
                if (hashed_key > k):
                    # starting from smallest key, skip if
                    # hashed key is greater
                    continue
                else:
                    n1 = v # identify the target node
                    ring_list = list(self.ring)
                    last_index = len(ring_list) -1
                    target_node_index = ring_list.index(k)
                    if (target_node_index < last_index):
                        # next node will be the one next to target_node_index
                        n2 = nodes[target_node_index+1]
                    else:
                        # next node will be looped back to starting one
                        n2 = nodes[0]
                    return n1, n2

    def get_next_node(self, node):
        hashed_key = self.hash(node.name)
        key_list = list(self.ring)
        node_index = key_list.index(hashed_key)
        if node_index < len(key_list) -1:
            next_node_hash_key = key_list[node_index+1]
            return self.ring[next_node_hash_key]
        else:
            next_node_hash_key = key_list[0]
            return self.ring[next_node_hash_key]