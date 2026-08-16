# VeriRAG — Healthcare — Run Guide

This is the healthcare-domain build of VeriRAG: Ganache blockchain + Merkle-verified
ChromaDB retrieval + local Ollama LLM + Flask UI, built on your uploaded
`healthcare_dataset.csv` (55,500 records, 15 columns, no unique patient-ID column).

**This has been tested against your actual 55,500-row file** in this environment:
record-ID uniqueness, Merkle tree construction, proof verification for a spread of
records, and tamper detection all passed. You still need to run the blockchain/LLM
steps yourself on your own machine (this sandbox has no network/GPU access to run
Ganache or Ollama).

The steps below are identical in structure to the education-domain run guide you
already used — same tools, same order. Only the dataset-specific parts differ.

---

## Important note on this dataset

1. **No unique ID column.** Unlike the OULAD dataset, this file has no
   `patient_id` column, and it contains ~5,500 exact duplicate rows (a known
   property of this dataset, confirmed in testing). To guarantee every record
   gets its own tamper-proof hash even across duplicates, `record_id` is built
   from the patient name + admission date + the record's row position in the
   file (e.g. `BobbyJacksOn_31012024_000000`). This is already implemented for
   you in `hashing/healthcare_hashing.py` — you don't need to do anything.
2. **This looks like PHI-shaped data (patient names, conditions, billing) but
   is a public synthetic/demo dataset**, not real patient records. If you ever
   swap in real clinical data, treat that as a different risk category
   entirely (HIPAA, IRB approval, de-identification) — this project's
   verification layer proves data integrity, not regulatory compliance.

---

## Before you start: what you need installed

| Tool | Why | Check you have it |
|---|---|---|
| Python 3.10+ | Runs everything | `python --version` |
| Node.js (for Ganache) | Runs the local blockchain | `node --version` |
| Ganache CLI | Local blockchain | see Step 2 |
| Ollama | Runs the local LLM | `ollama --version` |

---

## STEP 1 — Set up Python

```powershell
cd path\to\VeriRAG_Healthcare
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Wait for it to finish. Your prompt should show `(venv)`.

---

## STEP 2 — Start Ganache

```powershell
ganache --database.dbPath ./ganache_data
```
Leave this terminal open. Copy the **first private key** it prints — you need it
in Step 3.

If you get `EADDRINUSE: address already in use 127.0.0.1:8545`, something is
already using that port — see the Troubleshooting table below.

---

## STEP 3 — Configure your `.env`

```powershell
copy .env.example .env
```
Open `.env`, paste your Ganache private key:
```
PRIVATE_KEY=0xabc123...
GANACHE_RPC_URL=http://127.0.0.1:8545
```
For your **first test run**, also uncomment this line so you test against the
small 10-row sample before running the full 55,500-row file:
```
DATASET_CSV_PATH=dataset/healthcare/healthcare_dataset_sample.csv
```
Save and close.

*(The full `healthcare_dataset.csv` — your actual uploaded file — is already
placed at `dataset/healthcare/healthcare_dataset.csv`; you don't need to add it
yourself.)*

---

## STEP 4 — Start Ollama

```powershell
ollama serve
```
In another terminal, one-time only:
```powershell
ollama pull llama3.2:3b
```

---

## STEP 5 — Build everything (once, in this exact order)

In your main project terminal (`(venv)` active):

```powershell
python hashing/healthcare_hashing.py
python merkle/build_merkle_tree.py
python blockchain/deploy_contract.py
python blockchain/deploy_merkle_contract.py
python merkle/store_merkle_root.py
python vector_db/build_healthcare_db.py
```

Run each one, wait for it to finish, then run the next. Expected output for
the sample dataset (10 rows):

```
[build_merkle_tree] 10 leaves
[build_merkle_tree] Merkle root: 0x...
[deploy_contract] HashRegistry deployed at 0x...
[deploy_contract] Registered 10 hashes (10/10). Block 1
[deploy_merkle_contract] MerkleRegistry deployed at 0x...
[store_merkle_root] Root 0x... stored for 10 records.
[build_healthcare_db] Done. Collection 'healthcare_records' has 10 documents.
```

---

## STEP 6 — Test the pipeline

```powershell
python retrieval/retrieve_healthcare.py patients diagnosed with diabetes
python verification/verify_retrieved_record.py patients diagnosed with diabetes
python llm/verirag_healthcare.py Which patients were diagnosed with diabetes?
```

The last command should print `VERIFIED ✓` for each record and a real answer
at the end. Other good test queries for this dataset (matching its actual
values):
```
python llm/verirag_healthcare.py Which patients had abnormal test results?
python llm/verirag_healthcare.py Which patients were admitted as an emergency?
python llm/verirag_healthcare.py Which patients are covered by Medicare?
```

---

## STEP 7 — Launch the web UI

```powershell
python app.py
```
Open **http://localhost:5000**, type a question, click **Ask Question**.

---

## STEP 8 — Switch to the full 55,500-row dataset

1. In `.env`, comment out or delete the `DATASET_CSV_PATH=...sample.csv` line
   (the full file is already in place at `dataset/healthcare/healthcare_dataset.csv`).
2. Re-run **Step 5, all six commands, in order** — everything must be rebuilt
   against the full file.
3. This will take longer on a laptop CPU: embedding ~55,500 records is roughly
   1.7x the OULAD dataset's 32,593 rows, so budget extra time and avoid
   running other heavy programs at the same time (see your earlier RAM notes
   — 8 GB total is workable but tight with Ganache + Ollama + Chroma all
   running together).
4. `deploy_contract.py` only individually registers `HASH_REGISTRY_SAMPLE_SIZE`
   records on HashRegistry (200 by default) — this is intentional; the Merkle
   root is what actually covers all 55,500 records with one on-chain value.
   See `config.py` to change the sample size if you want.

---

## Everyday restart routine

```powershell
# Terminal 1
ganache --database.dbPath ./ganache_data

# Terminal 2
ollama serve

# Terminal 3
venv\Scripts\activate
python app.py
```
Then go to `http://localhost:5000`. Only redo Step 5 if the dataset changes or
if you deleted `./ganache_data` (which wipes the deployed contracts).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `EADDRINUSE: address already in use 127.0.0.1:8545` | Another Ganache process already running | `netstat -ano \| findstr :8545`, then `taskkill /PID <that number> /F`, then retry |
| `ConnectionError: Could not connect to Ganache` | Ganache isn't running, or wrong port | Confirm the Ganache terminal shows `RPC Listening on 127.0.0.1:8545` |
| `EnvironmentError: PRIVATE_KEY is not set` | `.env` missing or not filled in | Repeat Step 3 |
| `Contract artifact not found` | Skipped a deploy step, or Ganache was restarted without `--database.dbPath` (wiping old contracts) | Re-run Step 5, steps 3–5, in order |
| `record_id not found in Merkle index` | Dataset changed but tree wasn't rebuilt | Re-run Step 5, steps 2, 5, 6, in order |
| Everything shows `NOT VERIFIED` | On-chain root and local root are out of sync (usually after a Ganache restart) | Re-run Step 5, steps 2, 5, 6, in order |
| Ollama errors / no response | `ollama serve` not running, or model not pulled | Repeat Step 4 |
| Very slow on the full 55,500-row dataset | Normal on a laptop CPU | Use the sample dataset while developing; run the full dataset once, when you have time |

---

## Quick reference — full command sequence

```
# one-time setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env: paste PRIVATE_KEY from Ganache

# every session, in separate terminals
ganache --database.dbPath ./ganache_data
ollama serve

# in your main project terminal
python hashing/healthcare_hashing.py
python merkle/build_merkle_tree.py
python blockchain/deploy_contract.py
python blockchain/deploy_merkle_contract.py
python merkle/store_merkle_root.py
python vector_db/build_healthcare_db.py
python llm/verirag_healthcare.py Which patients were diagnosed with diabetes?
python app.py
# open http://localhost:5000
```
