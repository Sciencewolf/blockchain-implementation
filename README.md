# Blockchain

A blockchain implemented from scratch in Python, with no cryptocurrency layer.
There are no coins, wallets, balances, transactions or mining rewards — only
the data structure itself: hash-linked blocks, a Merkle tree over the records
in each block, proof of work, and chain validation.

A block stores arbitrary text records. In the demonstration these are document
events, but they could equally be log entries, file fingerprints or sensor
readings.

Hash function: **SHA-256**

---

## Requirements

Python 3.7 or newer. Nothing to install — the code uses only the standard
library (`hashlib`, `json`, `time`).

---

## Running it

```
python blockchain.py
```

The program builds a four-block chain, prints it, validates it, then tampers
with a record and shows the validation failing. Example output, abbreviated:

```
Block 1 mined after 45889 attempts
Block 2 mined after 38585 attempts
Block 3 mined after 19730 attempts

  Block 1
    previous hash : 00003fd1e56e7c78058516117bee3d09...
    merkle root   : c89b4b76e359e6e6852190c7e9b8271a...
    nonce         : 45889
    hash          : 000029c47c215effb04a36aff4f6f586...
    records       : ['document A submitted by Alice', 'document B submitted by Bob']

Chain of 4 blocks is valid : True
```

The number of mining attempts varies between runs because the timestamp in
each block header differs.

---

`add_record` queues a record; `mine_block` puts every queued record into a new
block and appends it to the chain. `is_valid` returns a pair: a boolean and, on
failure, a description of which block broke and why.

The mining difficulty is set by the `DIFFICULTY` constant at the top of the
file. It is the number of leading zeros a block hash must have. Each extra zero
multiplies the expected work by sixteen, so raising it much above 5 makes the
demo slow.

---

## How it works

### Hash linking

Every block stores the hash of the block before it. Because the previous hash
is part of what gets hashed, editing an old record changes that block's hash,
which invalidates the link held by the next block, and so on to the end of the
chain. A single edit therefore cannot be hidden without redoing every block
that follows it.

The first block, the genesis block, has no predecessor, so its `previous_hash`
field is set to sixty-four zeros.

### Merkle tree

`merkle_root` hashes the records of a block pairwise, level by level, until a
single value remains. That value goes in the block header, so the header stays
a fixed size regardless of how many records the block holds, while still
committing to every one of them: change any record and the root changes.

When a level has an odd number of nodes, the last node is paired with itself.

### Block header

The hash of a block is the SHA-256 of its header, which contains the index,
timestamp, previous hash, Merkle root and nonce, serialised as JSON with sorted
keys so the encoding is deterministic. The records themselves are not in the
header — they enter through the Merkle root.

### Proof of work

`Block.mine` increments the nonce until the block hash begins with the required
number of zeros. Because the hash function is preimage resistant there is no
way to compute a suitable nonce directly; the only method is trial and error.
Verifying someone else's result, by contrast, costs a single hash. That
asymmetry is the point: appending a block is deliberately expensive, checking
one is cheap.

### Validation

`is_valid` walks the chain and checks four things for every block:

1. the stored hash really is the hash of the header;
2. the hash satisfies the difficulty requirement;
3. the Merkle root matches the records actually stored in the block;
4. `previous_hash` matches the real hash of the preceding block.

---

## The tampering demonstration

The final part of the demo shows why the structure is tamper-evident, in three
stages.

First a record in block 1 is edited. Validation fails immediately, because the
records in the block no longer hash to the stored Merkle root.

Then the attacker is allowed to do the obvious repair: recompute the Merkle
root and re-mine block 1 so that its proof of work is valid again. Validation
still fails, but now at block 2, whose stored `previous_hash` points at the old
hash of block 1.

To complete the forgery the attacker would have to re-mine every subsequent
block as well. With one honest participant continuing to extend the real chain,
that is a race the attacker has to win from behind.

---

## References

- Course material on cryptographic hash functions and digital signatures
- R. Merkle, *A Digital Signature Based on a Conventional Encryption Function*
  (1987) — the origin of the hash tree
- S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System* (2008) —
  sections 3 to 5 describe the chain, proof of work and Merkle trees used here,
  independently of the currency