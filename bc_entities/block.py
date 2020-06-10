import time


class Block:

    def __init__(self, index, transactions, previous_hash, nonce=0):
        self.index = index
        self.transaction = transactions
        self.timestamp = time.time()
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = None
