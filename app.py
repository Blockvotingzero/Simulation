from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI()

# Simulated blockchain storage (JSON file)
BLOCKCHAIN_FILE = "blockchain.json"

# Ensure blockchain file exists
if not os.path.exists(BLOCKCHAIN_FILE):
    with open(BLOCKCHAIN_FILE, "w") as f:
        json.dump([], f)

# Models
class Candidate(BaseModel):
    name: str
    party: str
    abbreviation: str
    slogan: str

class Election(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    budget: float
    candidates: list[Candidate]

class Vote(BaseModel):
    election_id: int
    nin: str
    secret_code: str
    candidate: str

# Load blockchain
def load_blockchain():
    with open(BLOCKCHAIN_FILE, "r") as f:
        return json.load(f)

# Save blockchain
def save_blockchain(data):
    with open(BLOCKCHAIN_FILE, "w") as f:
        json.dump(data, f, indent=4)

# API Routes

@app.post("/api/election/create")
def create_election(election: Election):
    blockchain = load_blockchain()

    # Create new election
    new_election = {
        "id": len(blockchain) + 1,
        "title": election.title,
        "start_time": election.start_time.isoformat(),
        "end_time": election.end_time.isoformat(),
        "budget": election.budget,
        "candidates": [c.dict() for c in election.candidates],
        "votes": []
    }

    blockchain.append(new_election)
    save_blockchain(blockchain)

    return {"message": "Election created", "election": new_election}

@app.get("/api/election/all")
def get_all_elections():
    return load_blockchain()

@app.post("/api/vote")
def cast_vote(vote: Vote):
    blockchain = load_blockchain()

    # Find election
    for election in blockchain:
        if election["id"] == vote.election_id:
            # Check if voting time is valid
            now = datetime.utcnow().isoformat()
            if not (election["start_time"] <= now <= election["end_time"]):
                raise HTTPException(status_code=400, detail="Voting period is over or not started")

            # Prevent duplicate votes (basic check)
            for v in election["votes"]:
                if v["nin"] == vote.nin:
                    raise HTTPException(status_code=400, detail="You have already voted")

            # Add vote
            election["votes"].append({"nin": vote.nin, "candidate": vote.candidate})
            save_blockchain(blockchain)
            return {"message": "Vote casted"}

    raise HTTPException(status_code=404, detail="Election not found")

@app.get("/api/election/{election_id}/results")
def get_election_results(election_id: int):
    blockchain = load_blockchain()

    for election in blockchain:
        if election["id"] == election_id:
            # Count votes per candidate
            results = {}
            for vote in election["votes"]:
                results[vote["candidate"]] = results.get(vote["candidate"], 0) + 1
            return {"election": election["title"], "results": results}

    raise HTTPException(status_code=404, detail="Election not found")
