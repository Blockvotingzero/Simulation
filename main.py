from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import hashlib

app = FastAPI()

# Enable CORS to allow frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (frontend access)
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly allow GET, POST, OPTIONS
    allow_headers=["*"],  # Allow all headers
)

# In-memory blockchain structure for elections
elections = []
votes = {}

class Candidate(BaseModel):
    name: str
    party: str
    abbreviation: str
    slogan: str

class Election(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    candidates: list[Candidate]
    budget: float  # Amount to be spent on blockchain

class Vote(BaseModel):
    nin: str
    secret_code: str
    election_id: int
    candidate_name: str

@app.post("/api/election/create")
async def create_election(election: Election):
    # Ensure election times are valid
    if election.start_time >= election.end_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Create election ID (sequential blockchain structure)
    election_id = len(elections)
    
    # Store the election (immutable after creation)
    elections.append({
        "id": election_id,
        "title": election.title,
        "start_time": election.start_time,
        "end_time": election.end_time,
        "candidates": election.candidates,
        "budget": election.budget,
        "votes": {}
    })

    return {"message": "Election created", "election_id": election_id}

@app.get("/api/elections")
async def get_elections():
    return {"elections": elections}

@app.post("/api/vote")
async def cast_vote(vote: Vote):
    # Check if election exists
    if vote.election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[vote.election_id]

    # Ensure voting is within the election period
    current_time = datetime.utcnow()
    if not (election["start_time"] <= current_time <= election["end_time"]):
        raise HTTPException(status_code=400, detail="Voting is not allowed at this time")

    # Generate unique voter ID using NIN + secret code
    voter_hash = hashlib.sha256(f"{vote.nin}-{vote.secret_code}".encode()).hexdigest()

    # Check if voter has already voted
    if voter_hash in election["votes"]:
        raise HTTPException(status_code=403, detail="Voter has already voted")

    # Ensure candidate exists
    candidate_names = [c.name for c in election["candidates"]]
    if vote.candidate_name not in candidate_names:
        raise HTTPException(status_code=400, detail="Invalid candidate")

    # Record the vote (permanently stored)
    election["votes"][voter_hash] = vote.candidate_name

    return {"message": "Vote casted successfully", "hash": voter_hash}

@app.get("/api/election/{election_id}/results")
async def get_results(election_id: int):
    if election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[election_id]

    # Count votes per candidate
    results = {c.name: 0 for c in election["candidates"]}
    for candidate in election["votes"].values():
        results[candidate] += 1

    return {"election_id": election_id, "title": election["title"], "results": results}
