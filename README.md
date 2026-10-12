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
python main.py
```

The program builds a four-block chain, prints it, validates it, then tampers
with it in several ways and shows the validation failing each time. Example output, abbreviated:

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
field is set to sixty-four zeros. Validation insists on this value, so the
start of the chain cannot be rewritten either.

### Merkle tree

`merkle_root` hashes the records of a block pairwise, level by level, until a
single value remains. That value goes in the block header, so the header stays
a fixed size regardless of how many records the block holds, while still
committing to every one of them: change any record and the root changes.

When a level has an odd number of nodes, the last node is paired with itself.

### Block header

The hash of a block is the SHA-256 of its header, which contains the index,
timestamp, previous hash, Merkle root, difficulty and nonce, serialised as JSON with sorted
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

`is_valid` walks the chain and checks six things for every block:

1. the stored hash really is the hash of the header;
2. the block uses the chain's difficulty and its hash satisfies it;
3. the Merkle root matches the records actually stored in the block;
4. the `index` equals the block's position in the chain;
5. `previous_hash` matches the real hash of the preceding block (for the
   genesis block: sixty-four zeros);
6. the timestamp is not earlier than the previous block's and not more than two
   hours in the future. This is what gives the chain its ordering in time.

Mining sets a new block's timestamp to at least the previous block's, so honest
blocks always pass check 6.

---

## Requirements mapping

| Requirement | Where |
| --- | --- |
| Cryptographic hash function (SHA-256) | `HASH = hashlib.sha256`, `sha256_hex`, `Block.compute_hash` |
| Every block contains the hash of the previous block's header (`previous_hash`) | `Block.previous_hash`, set in `Blockchain.mine_block`, checked in `is_valid` (check 5) |
| Modifying any earlier data invalidates the whole chain after it | Merkle root (check 3) + hash linking (check 5); see the demo below |
| History and timing are guaranteed | index and timestamp checks (checks 4 and 6) |

---

## The tampering demonstration

The demo shows why the structure is tamper-evident.

**Stage 1 - edit a record.** A record in block 1 is changed. Validation fails
immediately, because the records no longer hash to the stored Merkle root.

**Stage 2 - edit and repair.** The attacker recomputes the Merkle root and
re-mines block 1 so its proof of work is valid again. Validation still fails,
now at block 2, whose `previous_hash` points at the old hash of block 1.

**Stage 3 - more attacks.** In each case the attacker re-mines the affected
blocks so the hashes and links are consistent, and validation still fails:

| Attack | Detected by |
| --- | --- |
| Backdating block 2 to 1970 | timestamp earlier than the previous block |
| Changing block 2's index to 99 | index does not match position |
| Editing the genesis block's `previous_hash` | genesis must be sixty-four zeros |

To hide a change the attacker would have to re-mine every later block as well,
while the honest participants keep extending the real chain. That is the
protection the proof of work provides.

---

## How to present it

1. **Idea (30 s).** Each block carries the hash of the previous block's header.
   Change anything old and every later link breaks.
2. **Run it.** `python main.py` takes a few seconds. Point at the output:
   - "Block N mined after X attempts" - this is proof of work, the nonce search.
   - In the printed chain, each block's `previous hash` equals the `hash` of the
     block above it.
3. **Validation.** Show `Chain of 4 blocks is valid : True`.
4. **Tampering, stage 1.** "Mallory" replaces Bob's record: invalid, Merkle root
   mismatch.
5. **Tampering, stage 2.** Even after re-mining block 1, block 2's link breaks.
   Say: the attacker would have to redo the work for all following blocks.
6. **Stage 3.** Backdating, wrong index and a rewritten genesis are all rejected.
7. **Optional live demo** in a Python shell:

```python
from main import *
c = Blockchain(difficulty=3)
c.add_record("Alice pays Bob 10"); c.mine_block()
c.add_record("Bob pays Carol 5");  c.mine_block()
print(c.is_valid())              # (True, '')
c.chain[1].records[0] = "Alice pays Bob 1000"
print(c.is_valid())              # (False, 'block 1: records do not match the Merkle root')
```

Likely questions:

- *Why can the attacker not simply re-mine everything?* They can, but it costs
  the full proof of work for every block, and they must outpace the honest chain.
- *What does the Merkle tree add?* A fixed-size header that still commits to
  every record in the block.
- *Why is the timestamp checked?* Without it, blocks could be backdated and the
  history's ordering would mean nothing.
- *What is not covered?* There are no digital signatures on the records and no
  network of nodes; see the `ECC-digital-signature` project for signatures.

---

## References

- Course material on cryptographic hash functions and digital signatures
- R. Merkle, *A Digital Signature Based on a Conventional Encryption Function*
  (1987) — the origin of the hash tree
- S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System* (2008) —
  sections 3 to 5 describe the chain, proof of work and Merkle trees used here,
  independently of the currency