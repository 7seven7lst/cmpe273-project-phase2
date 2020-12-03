import bisect
import hashlib
import collections

class Node(object):
    def __init__(self, node, name):
        self.node = node
        self.name = name

class ConsistentHashRing(object):
    def __init__(self, nodes):
        self.ring = dict() # hashed-key: node
        for node in nodes:
            hashed_key = self.hash(node.name)
            self.ring[hashed_key] = node
        self.ring = dict(sorted(self.ring.items()))
    def hash(self, name):
        key = str(name).encode('utf-8')
        return int(hashlib.md5(key).hexdigest(), 16) % (2**32)

    def add_node(self, node):
        print("self.ring>>>", self.ring)
        hashed_key = self.hash(node.name)
        print("hashed_key>>>", hashed_key)
        self.ring[hashed_key] = node
        self.ring = dict(sorted(self.ring.items()))

    def remove_node(self, node):
        hashed_key = self.hash(node.name)
        self.ring.pop(hashed_key, None)
        self.ring = dict(sorted(self.ring.items()))

    def get_node(self, key):
        hashed_key = self.hash(key)
        last_key = int(list(self.ring.keys())[-1])
        first_key = int(list(self.ring.keys())[0])
        values = list(self.ring.values())
        if (hashed_key > last_key):
            return values[0], values[1]
        elif (hashed_key <= first_key):
            return values[0], values[1]
        else:
            v1 = None
            v2 = None
            for k, v in self.ring.items():
                if (hashed_key > k):
                    continue
                else:
                    v1 = v
                    my_list = list(self.ring)
                    last_index = len(my_list) -1
                    index = my_list.index(k)
                    if (index < last_index):
                        v2 = values[index+1]
                    else:
                        v2 = values[0]
                    return v1, v2

    def get_next_node(self, node):
        print("node.name is >>>", node.name)
        hashed_key = self.hash(node.name)
        key_list = list(self.ring)
        node_index = key_list.index(hashed_key)
        if node_index < len(key_list) -1:
            next_node_hash_key = key_list[node_index+1]
            return self.ring[next_node_hash_key]
        else:
            next_node_hash_key = key_list[0]
            return self.ring[next_node_hash_key]