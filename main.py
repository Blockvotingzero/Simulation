from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST"],  
    allow_headers=["*"],  
)

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
    election_id = len(elections)
    elections.append({
        "id": election_id,
        "title": election.title,
        "start_time": election.start_time,
        "end_time": election.end_time,
        "candidates": [candidate.dict() for candidate in election.candidates],
        "budget": election.budget,
        "votes": {}
    })
    return {"message": "Election created", "election_id": election_id}

@app.get("/api/elections")
async def get_elections():
    return {"elections": elections}

@app.post("/api/vote")
async def cast_vote(vote: Vote):
    if vote.election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[vote.election_id]
    candidate_name = election["candidates"][vote.candidate_index]["name"]

    election["votes"][candidate_name] = election["votes"].get(candidate_name, 0) + 1

    return {"message": "Vote cast successfully", "voted_for": candidate_name}

@app.get("/api/election/{election_id}/results")
async def get_results(election_id: int):
    if election_id >= len(elections):
        raise HTTPException(status_code=404, detail="Election not found")

    election = elections[election_id]
    return {"election_id": election_id, "title": election["title"], "results": election["votes"]}
