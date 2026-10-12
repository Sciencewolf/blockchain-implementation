"""
Blockchain.

It relies on the properties of cryptographic hash functions:
  - collision resistance: hard to find two inputs with the same hash,
    so a record cannot be swapped for another one with a matching hash
  - avalanche effect: changing one bit changes about half the output bits
  - preimage resistance: what makes proof-of-work require actual search

Run:  python main.py
"""

import hashlib
import json
import time

DIFFICULTY = 4          # required number of leading zeros in a block hash
GENESIS_PREV = "0" * 64
MAX_FUTURE = 2 * 60 * 60   # a block may not be dated more than 2 hours ahead
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
    def __init__(self, index, records, previous_hash, timestamp=None, difficulty=DIFFICULTY):
        self.index = index
        self.difficulty = difficulty
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
                "difficulty": self.difficulty,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )

    def compute_hash(self):
        return sha256_hex(self.header())

    def mine(self, difficulty=None):
        if difficulty is not None:
            self.difficulty = difficulty
        target = "0" * self.difficulty
        self.nonce = 0
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.nonce

    def __repr__(self):
        return f"Block(index={self.index}, records={len(self.records)}, hash={self.hash})"


class Blockchain:
    def __init__(self, difficulty=DIFFICULTY):
        self.difficulty = difficulty
        self.chain = []
        self.pending = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(0, ["genesis block"], GENESIS_PREV, difficulty=self.difficulty)
        genesis.mine()
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
            timestamp=max(time.time(), self.last_block.timestamp),
            difficulty=self.difficulty,
        )
        attempts = block.mine()
        self.chain.append(block)
        self.pending = []
        return block, attempts

    def is_valid(self):
        """
        Check the whole chain. Returns (True, "") or (False, reason).

        Checked for every block:
          1. the stored hash really is the hash of the header
          2. the block uses the chain's difficulty and its hash meets it
          3. the Merkle root matches the records actually stored
          4. the index equals the block's position in the chain
          5. previous_hash matches the actual hash of the preceding block
             (the genesis block must have previous_hash = 64 zeros)
          6. the timestamp is not earlier than the previous block's and
             not unreasonably far in the future
        """
        target = "0" * self.difficulty
        now = time.time()

        for i, block in enumerate(self.chain):
            if block.hash != block.compute_hash():
                return False, f"block {i}: stored hash does not match its contents"

            if block.difficulty != self.difficulty or not block.hash.startswith(target):
                return False, f"block {i}: proof of work is invalid"

            if merkle_root(block.records) != block.merkle_root:
                return False, f"block {i}: records do not match the Merkle root"

            if block.index != i:
                return False, f"block {i}: index is {block.index}, expected {i}"

            if i == 0:
                if block.previous_hash != GENESIS_PREV:
                    return False, "block 0: genesis block has a wrong previous_hash"
            else:
                if block.previous_hash != self.chain[i - 1].hash:
                    return False, f"block {i}: link to block {i - 1} is broken"

                if block.timestamp < self.chain[i - 1].timestamp:
                    return False, f"block {i}: timestamp is earlier than block {i - 1}"

            if block.timestamp > now + MAX_FUTURE:
                return False, f"block {i}: timestamp is too far in the future"

        return True, ""

    def __len__(self):
        return len(self.chain)


def print_chain(chain):
    for block in chain.chain:
        print(f"  Block {block.index}")
        print(f"    previous hash : {block.previous_hash}")
        print(f"    merkle root   : {block.merkle_root}")
        print(f"    nonce         : {block.nonce}")
        print(f"    hash          : {block.hash}")
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

    print()
    print("=" * 68)
    print("More attacks (each attacker re-mines the affected blocks)")
    print("=" * 68)

    def remine_from(i):
        for j in range(i, len(chain.chain)):
            if j > 0:
                chain.chain[j].previous_hash = chain.chain[j - 1].hash
            chain.chain[j].mine()

    b2 = chain.chain[2]

    old_ts = b2.timestamp
    b2.timestamp = 0
    remine_from(2)
    valid, reason = chain.is_valid()
    print(f"  block 2 backdated to 1970  -> valid: {valid} ({reason})")
    b2.timestamp = old_ts
    remine_from(2)

    b2.index = 99
    remine_from(2)
    valid, reason = chain.is_valid()
    print(f"  block 2 index set to 99    -> valid: {valid} ({reason})")
    b2.index = 2
    remine_from(2)

    genesis = chain.chain[0]
    genesis.previous_hash = "1" * 64
    remine_from(0)
    valid, reason = chain.is_valid()
    print(f"  genesis previous_hash edit -> valid: {valid} ({reason})")
    genesis.previous_hash = GENESIS_PREV
    remine_from(0)

    valid, _ = chain.is_valid()
    print(f"\nAfter restoring everything, chain is valid : {valid}")


if __name__ == "__main__":
    main()