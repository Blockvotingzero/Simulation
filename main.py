from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# Enable CORS to allow frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Allow necessary HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# In-memory blockchain structure for elections
elections = []

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
    election_id: int
    candidate_index: int  # Voting by candidate index instead of name

@app.post("/api/election/create")
async def create_election(election: Election):
    # Ensure election times are valid
    if election.start_time >= election.end_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Create election ID (sequential blockchain structure)
    election_id = len(elections)
    
    # Store the election
    elections.append({
        "id": election_id,
        "title": election.title,
        "start_time": election.start_time,
        "end_time": election.end_time,
        "candidates": election.candidates,
        "budget": election.budget,
        "votes": {}  # Dictionary to store votes
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

    # Ensure candidate index is valid
    if vote.candidate_index < 0 or vote.candidate_index >= len(election["candidates"]):
        raise HTTPException(status_code=400, detail="Invalid candidate index")

    # Record the vote (using the index of the candidate)
    candidate_name = election["candidates"][vote.candidate_index].name
    if candidate_name not in election["votes"]:
        election["votes"][candidate_name] = 0
    election["votes"][candidate_name] += 1

    return {"message": "Vote cast successfully", "voted_for": candidate_name}

@app.get("/api/election/{election_id}/results")
async def get_results(election_id: int):
    if election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[election_id]

    # Count votes per candidate
    results = {c.name: 0 for c in election["candidates"]}
    for candidate, count in election["votes"].items():
        results[candidate] += count

    return {"election_id": election_id, "title": election["title"], "results": results}
