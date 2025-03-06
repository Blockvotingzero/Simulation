from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import hashlib
import json
import os
from functools import wraps

app = Flask(__name__)
CORS(app)

# Simulating blockchain storage with a simple JSON file
BLOCKCHAIN_FILE = "blockchain_data.json"

# Initialize blockchain data structure if it doesn't exist
def initialize_blockchain():
    if not os.path.exists(BLOCKCHAIN_FILE):
        data = {
            "elections": {},
            "electionCount": 0,
            "admin": hashlib.sha256("admin".encode()).hexdigest()  # Simple admin authentication
        }
        with open(BLOCKCHAIN_FILE, 'w') as f:
            json.dump(data, f)
    return load_blockchain()

# Load blockchain data
def load_blockchain():
    with open(BLOCKCHAIN_FILE, 'r') as f:
        return json.load(f)

# Save blockchain data
def save_blockchain(data):
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump(data, f)

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        blockchain = load_blockchain()
        admin_key = request.headers.get('Admin-Key', '')
        admin_hash = hashlib.sha256(admin_key.encode()).hexdigest()
        
        if admin_hash != blockchain["admin"]:
            return jsonify({"error": "Only admin can perform this action"}), 403
        return f(*args, **kwargs)
    return decorated_function

# Election existence check decorator
def election_exists(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        blockchain = load_blockchain()
        election_id = kwargs.get('election_id') or request.json.get('electionId')
        
        if not election_id or str(election_id) not in blockchain["elections"]:
            return jsonify({"error": "Election does not exist"}), 404
        return f(*args, **kwargs)
    return decorated_function

# Voting period active check decorator
def voting_period_active(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        blockchain = load_blockchain()
        election_id = kwargs.get('election_id') or request.json.get('electionId')
        election = blockchain["elections"][str(election_id)]
        current_time = int(time.time())
        
        if current_time < election["startTime"]:
            return jsonify({"error": "Voting has not started yet"}), 400
        if current_time > election["endTime"]:
            return jsonify({"error": "Voting has ended"}), 400
        if not election["isActive"]:
            return jsonify({"error": "Election is closed"}), 400
        return f(*args, **kwargs)
    return decorated_function

# Initialize blockchain on startup
initialize_blockchain()

# Routes corresponding to smart contract functions
@app.route('/api/createElection', methods=['POST'])
@admin_required
def create_election():
    data = request.json
    blockchain = load_blockchain()
    current_time = int(time.time())
    
    # Validate inputs
    if not all(k in data for k in ["name", "startTime", "endTime"]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if data["startTime"] < current_time:
        return jsonify({"error": "Start time must be in the future"}), 400
    
    if data["endTime"] <= data["startTime"]:
        return jsonify({"error": "End time must be after start time"}), 400
    
    # Create new election
    election_id = blockchain["electionCount"]
    blockchain["elections"][str(election_id)] = {
        "name": data["name"],
        "startTime": data["startTime"],
        "endTime": data["endTime"],
        "isActive": True,
        "candidates": [],
        "hasVoted": {}
    }
    
    # Increment election count
    blockchain["electionCount"] = election_id + 1
    save_blockchain(blockchain)
    
    # Emit event (log it)
    print(f"Event: ElectionCreated({election_id}, {data['name']}, {data['startTime']}, {data['endTime']})")
    
    return jsonify({
        "success": True,
        "electionId": election_id,
        "name": data["name"],
        "startTime": data["startTime"],
        "endTime": data["endTime"]
    }), 201

@app.route('/api/addCandidate', methods=['POST'])
@admin_required
@election_exists
def add_candidate():
    data = request.json
    blockchain = load_blockchain()
    election_id = data["electionId"]
    current_time = int(time.time())
    
    # Validate inputs
    if not all(k in data for k in ["electionId", "name", "party", "abbreviation", "slogan"]):
        return jsonify({"error": "Missing required fields"}), 400
    
    election = blockchain["elections"][str(election_id)]
    
    # Check if voting has started
    if current_time >= election["startTime"]:
        return jsonify({"error": "Cannot add candidates after voting starts"}), 400
    
    # Add candidate
    new_candidate = {
        "name": data["name"],
        "party": data["party"],
        "abbreviation": data["abbreviation"],
        "slogan": data["slogan"],
        "voteCount": 0
    }
    
    election["candidates"].append(new_candidate)
    save_blockchain(blockchain)
    
    # Emit event
    print(f"Event: CandidateAdded({election_id}, {data['name']}, {data['party']}, {data['abbreviation']}, {data['slogan']})")
    
    return jsonify({
        "success": True,
        "electionId": election_id,
        "candidate": new_candidate
    }), 201

@app.route('/api/vote', methods=['POST'])
@election_exists
@voting_period_active
def vote():
    data = request.json
    blockchain = load_blockchain()
    election_id = data["electionId"]
    nin_hash = data["ninHash"]
    candidate_index = data["candidateIndex"]
    
    # Validate inputs
    if not all(k in data for k in ["electionId", "ninHash", "candidateIndex"]):
        return jsonify({"error": "Missing required fields"}), 400
    
    election = blockchain["elections"][str(election_id)]
    
    # Check if user has already voted
    if str(nin_hash) in election["hasVoted"]:
        return jsonify({"error": "You have already voted"}), 400
    
    # Check if candidate exists
    if candidate_index >= len(election["candidates"]):
        return jsonify({"error": "Invalid candidate"}), 400
    
    # Record vote
    election["hasVoted"][str(nin_hash)] = True
    election["candidates"][candidate_index]["voteCount"] += 1
    save_blockchain(blockchain)
    
    # Emit event
    print(f"Event: VoteCast({election_id}, {nin_hash}, {candidate_index})")
    
    return jsonify({
        "success": True,
        "electionId": election_id,
        "ninHash": nin_hash,
        "candidateIndex": candidate_index
    }), 200

@app.route('/api/getCandidates/<int:election_id>', methods=['GET'])
@election_exists
def get_candidates(election_id):
    blockchain = load_blockchain()
    election = blockchain["elections"][str(election_id)]
    
    return jsonify({
        "success": True,
        "candidates": election["candidates"]
    }), 200

@app.route('/api/getTotalVotes/<int:election_id>/<int:candidate_index>', methods=['GET'])
@election_exists
def get_total_votes(election_id, candidate_index):
    blockchain = load_blockchain()
    election = blockchain["elections"][str(election_id)]
    
    # Validate candidate index
    if candidate_index >= len(election["candidates"]):
        return jsonify({"error": "Invalid candidate"}), 400
    
    return jsonify({
        "success": True,
        "voteCount": election["candidates"][candidate_index]["voteCount"]
    }), 200

@app.route('/api/hasUserVoted/<int:election_id>/<int:nin_hash>', methods=['GET'])
@election_exists
def has_user_voted(election_id, nin_hash):
    blockchain = load_blockchain()
    election = blockchain["elections"][str(election_id)]
    
    has_voted = str(nin_hash) in election["hasVoted"]
    
    return jsonify({
        "success": True,
        "hasVoted": has_voted
    }), 200

@app.route('/api/closeElection/<int:election_id>', methods=['POST'])
@election_exists
def close_election(election_id):
    blockchain = load_blockchain()
    election = blockchain["elections"][str(election_id)]
    current_time = int(time.time())
    
    # Check if election time has ended
    if current_time <= election["endTime"]:
        return jsonify({"error": "Election is still active"}), 400
    
    # Check if election is already closed
    if not election["isActive"]:
        return jsonify({"error": "Election already closed"}), 400
    
    # Close election
    election["isActive"] = False
    save_blockchain(blockchain)
    
    # Emit event
    print(f"Event: ElectionEnded({election_id})")
    
    return jsonify({
        "success": True,
        "electionId": election_id
    }), 200

@app.route('/api/changeAdmin', methods=['POST'])
@admin_required
def change_admin():
    data = request.json
    blockchain = load_blockchain()
    
    # Validate inputs
    if "newAdminKey" not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Generate new admin hash
    new_admin_hash = hashlib.sha256(data["newAdminKey"].encode()).hexdigest()
    blockchain["admin"] = new_admin_hash
    save_blockchain(blockchain)
    
    return jsonify({
        "success": True
    }), 200

@app.route('/api/getAllElections', methods=['GET'])
def get_all_elections():
    blockchain = load_blockchain()
    elections = {}
    
    for election_id, election in blockchain["elections"].items():
        elections[election_id] = {
            "name": election["name"],
            "startTime": election["startTime"],
            "endTime": election["endTime"],
            "isActive": election["isActive"],
            "candidateCount": len(election["candidates"])
        }
    
    return jsonify({
        "success": True,
        "elections": elections,
        "electionCount": blockchain["electionCount"]
    }), 200

@app.route('/api/getElectionDetails/<int:election_id>', methods=['GET'])
@election_exists
def get_election_details(election_id):
    blockchain = load_blockchain()
    election = blockchain["elections"][str(election_id)]
    
    return jsonify({
        "success": True,
        "name": election["name"],
        "startTime": election["startTime"],
        "endTime": election["endTime"],
        "isActive": election["isActive"],
        "candidates": election["candidates"],
        "voteCount": sum(c["voteCount"] for c in election["candidates"])
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
