"""
Blockchain.

It relies on the properties of cryptographic hash functions:
  - collision resistance: hard to find two inputs with the same hash,
    so a record cannot be swapped for another one with a matching hash
  - avalanche effect: changing one bit changes about half the output bits
  - preimage resistance: what makes proof-of-work require actual search

Run:  python blockchain.py
"""

import hashlib
import json
import time

DIFFICULTY = 4          # required number of leading zeros in a block hash
HASH = hashlib.sha256


def sha256_hex(data: str) -> str:
    return HASH(data.encode("utf-8")).hexdigest()


def merkle_root(records):
    if not records:
        return sha256_hex("")

    level = [sha256_hex(record) for record in records]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [sha256_hex(level[i] + level[i + 1]) for i in range(0, len(level), 2)]

    return level[0]


class Block:
    def __init__(self, index, records, previous_hash, timestamp=None):
        self.index = index
        self.records = list(records)
        self.previous_hash = previous_hash
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.merkle_root = merkle_root(self.records)
        self.nonce = 0
        self.hash = self.compute_hash()

    def header(self):
        return json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "previous_hash": self.previous_hash,
                "merkle_root": self.merkle_root,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )

    def compute_hash(self):
        return sha256_hex(self.header())

    def mine(self, difficulty=DIFFICULTY):
        target = "0" * difficulty
        self.nonce = 0
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.nonce

    def __repr__(self):
        return f"Block(index={self.index}, records={len(self.records)}, hash={self.hash[:16]}...)"


class Blockchain:
    def __init__(self, difficulty=DIFFICULTY):
        self.difficulty = difficulty
        self.chain = []
        self.pending = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(0, ["genesis block"], "0" * 64)
        genesis.mine(self.difficulty)
        self.chain.append(genesis)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_record(self, record):
        self.pending.append(record)

    def mine_block(self):
        if not self.pending:
            raise ValueError("no pending records to put in a block")

        block = Block(
            index=len(self.chain),
            records=self.pending,
            previous_hash=self.last_block.hash,
        )
        attempts = block.mine(self.difficulty)
        self.chain.append(block)
        self.pending = []
        return block, attempts

    def is_valid(self):
        """
        Check the whole chain. Returns (True, "") or (False, reason).

        Four things are checked for every block:
          1. the stored hash really is the hash of the header
          2. the hash satisfies the proof-of-work difficulty
          3. previous_hash matches the actual hash of the preceding block
          4. the Merkle root matches the records actually stored
        """
        target = "0" * self.difficulty

        for i, block in enumerate(self.chain):
            if block.hash != block.compute_hash():
                return False, f"block {i}: stored hash does not match its contents"

            if not block.hash.startswith(target):
                return False, f"block {i}: proof of work is invalid"

            if merkle_root(block.records) != block.merkle_root:
                return False, f"block {i}: records do not match the Merkle root"

            if i > 0 and block.previous_hash != self.chain[i - 1].hash:
                return False, f"block {i}: link to block {i - 1} is broken"

        return True, ""

    def __len__(self):
        return len(self.chain)


def print_chain(chain):
    for block in chain.chain:
        print(f"  Block {block.index}")
        print(f"    previous hash : {block.previous_hash[:32]}...")
        print(f"    merkle root   : {block.merkle_root[:32]}...")
        print(f"    nonce         : {block.nonce}")
        print(f"    hash          : {block.hash[:32]}...")
        print(f"    records       : {block.records}")


def main():
    print("=" * 68)
    print(f"Building a chain (difficulty = {DIFFICULTY} leading zeros)")
    print("=" * 68)

    chain = Blockchain()

    chain.add_record("document A submitted by Alice")
    chain.add_record("document B submitted by Bob")
    _, attempts = chain.mine_block()
    print(f"Block 1 mined after {attempts} attempts")

    chain.add_record("document A approved")
    _, attempts = chain.mine_block()
    print(f"Block 2 mined after {attempts} attempts")

    chain.add_record("document C submitted by Carol")
    chain.add_record("document B rejected")
    _, attempts = chain.mine_block()
    print(f"Block 3 mined after {attempts} attempts")

    print()
    print_chain(chain)

    print()
    print("=" * 68)
    print("Validation")
    print("=" * 68)
    valid, reason = chain.is_valid()
    print(f"Chain of {len(chain)} blocks is valid : {valid}")

    print()
    print("=" * 68)
    print("Tampering with block 1")
    print("=" * 68)
    original = chain.chain[1].records[1]
    print(f"  original record : {original}")
    chain.chain[1].records[1] = "document B submitted by Mallory"
    print(f"  altered record  : {chain.chain[1].records[1]}")

    valid, reason = chain.is_valid()
    print(f"\nChain is valid : {valid}")
    print(f"Reason         : {reason}")

    print()
    print("Even if the attacker recomputes the Merkle root and re-mines block 1,")
    print("its hash changes, so block 2 no longer points at it:")
    b1 = chain.chain[1]
    b1.merkle_root = merkle_root(b1.records)
    b1.mine(chain.difficulty)
    valid, reason = chain.is_valid()
    print(f"  chain is valid : {valid}")
    print(f"  reason         : {reason}")
    print("\nTo hide the change, every later block would have to be re-mined.")

    chain.chain[1].records[1] = original
    b1.merkle_root = merkle_root(b1.records)
    b1.mine(chain.difficulty)
    valid, _ = chain.is_valid()
    print(f"\nAfter restoring the original record, chain is valid : {valid}")


if __name__ == "__main__":
    main()