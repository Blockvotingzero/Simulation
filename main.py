from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import uuid

app = FastAPI()

# In-memory storage for elections and votes
elections: Dict[str, Dict] = {}
votes: Dict[str, Dict] = {}

class Candidate(BaseModel):
    name: str
    party_name: str
    party_abbreviation: str
    party_slogan: str

class Election(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    candidates: List[Candidate]
    budget: float

class Vote(BaseModel):
    election_id: str
    nin: str
    secret_code: str
    candidate_name: str

@app.post("/api/election/create")
async def create_election(election: Election):
    election_id = str(uuid.uuid4())
    if election.start_time >= election.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time.")
    elections[election_id] = {
        "id": election_id,
        "title": election.title,
        "start_time": election.start_time,
        "end_time": election.end_time,
        "candidates": {candidate.name: candidate for candidate in election.candidates},
        "budget": election.budget,
        "votes": {}
    }
    return {"message": "Election created successfully", "election_id": election_id}

@app.get("/api/election/all")
async def get_all_elections():
    return elections

@app.get("/api/election/{election_id}")
async def get_election(election_id: str):
    election = elections.get(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return election

@app.post("/api/vote")
async def cast_vote(vote: Vote):
    election = elections.get(vote.election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    current_time = datetime.utcnow()
    if not (election["start_time"] <= current_time <= election["end_time"]):
        raise HTTPException(status_code=400, detail="Election is not active")
    wallet_address = f"{vote.nin}_{vote.secret_code}"
    if wallet_address in election["votes"]:
        raise HTTPException(status_code=400, detail="User has already voted")
    if vote.candidate_name not in election["candidates"]:
        raise HTTPException(status_code=404, detail="Candidate not found in this election")
    election["votes"][wallet_address] = vote.candidate_name
    return {"message": "Vote cast successfully"}

@app.get("/api/election/{election_id}/results")
async def get_election_results(election_id: str):
    election = elections.get(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    results = {candidate: 0 for candidate in election["candidates"]}
    for candidate in election["votes"].values():
        results[candidate] += 1
    return results
