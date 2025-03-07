from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# ✅ CORS Setup - Allow frontend to access the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for testing)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# In-memory storage for elections (simulating blockchain stacking)
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
    budget: float

class Vote(BaseModel):
    election_id: int
    candidate_index: int

@app.post("/api/election/create")
async def create_election(election: Election):
    """ Creates a new election and stores it in memory. """
    if election.start_time >= election.end_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    election_id = len(elections)

    # Store as dictionary to avoid serialization issues
    elections.append({
        "id": election_id,
        "title": election.title,
        "start_time": election.start_time.isoformat(),
        "end_time": election.end_time.isoformat(),
        "candidates": [candidate.dict() for candidate in election.candidates],  # Store as list of dicts
        "budget": election.budget,
        "votes": {}  # Store votes
    })

    return {"message": "Election created", "election_id": election_id}

@app.get("/api/elections")
async def get_elections():
    """ Fetches all elections. """
    return {"elections": elections}

@app.post("/api/vote")
async def cast_vote(vote: Vote):
    """ Allows a user to cast a vote using election ID and candidate index. """
    if vote.election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[vote.election_id]

    current_time = datetime.utcnow()
    if not (election["start_time"] <= current_time.isoformat() <= election["end_time"]):
        raise HTTPException(status_code=400, detail="Voting is not allowed at this time")

    if vote.candidate_index < 0 or vote.candidate_index >= len(election["candidates"]):
        raise HTTPException(status_code=400, detail="Invalid candidate index")

    candidate_name = election["candidates"][vote.candidate_index]["name"]

    # Store votes
    if candidate_name not in election["votes"]:
        election["votes"][candidate_name] = 0
    election["votes"][candidate_name] += 1

    return {"message": "Vote cast successfully", "voted_for": candidate_name}

@app.get("/api/election/{election_id}/results")
async def get_results(election_id: int):
    """ Retrieves the results of an election. """
    if election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[election_id]

    # Count votes per candidate
    results = {c["name"]: 0 for c in election["candidates"]}
    for candidate, count in election["votes"].items():
        results[candidate] += count

    return {"election_id": election_id, "title": election["title"], "results": results}
