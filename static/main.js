// Configuration
// Change this to your Render deployed API URL
const API_BASE_URL = 'https://simulation-knyz.onrender.com/api';
let adminKey = '';
let currentElectionId = null;
let resultsChart = null;

// On document ready
$(document).ready(function() {
    // Admin authentication
    $('#adminAuth').click(authenticateAdmin);
    
    // Form submissions
    $('#electionForm').submit(createElection);
    $('#candidateForm').submit(addCandidate);
    $('#changeAdminForm').submit(changeAdmin);
    
    // Buttons
    $('#closeElectionBtn').click(closeElection);
    $('#castVoteBtn').click(castVote);
    
    // Check for stored admin key in session storage
    const storedKey = sessionStorage.getItem('adminKey');
    if (storedKey) {
        $('#adminKey').val(storedKey);
        authenticateAdmin();
    }
});

// Admin Authentication
function authenticateAdmin() {
    adminKey = $('#adminKey').val().trim();
    
    if (adminKey === '') {
        showAlert('#adminStatus', 'Please enter an admin key', 'danger');
        return;
    }
    
    // Store in session storage
    sessionStorage.setItem('adminKey', adminKey);
    
    // Test authentication by fetching elections
    fetchAllElections()
        .then(() => {
            $('#adminStatus').removeClass('alert-warning alert-danger').addClass('alert-success')
                .text('Authenticated as admin');
            $('#adminPanel').removeClass('d-none').addClass('fade-in');
        })
        .catch(error => {
            console.error('Authentication failed:', error);
            sessionStorage.removeItem('adminKey');
            showAlert('#adminStatus', 'Authentication failed. Check your admin key.', 'danger');
            $('#adminPanel').addClass('d-none');
        });
}

// Fetch all elections
function fetchAllElections() {
    return fetch(`${API_BASE_URL}/getAllElections`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch elections');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                displayElections(data.elections);
                return data;
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
        });
}

// Display elections in the admin panel
function displayElections(elections) {
    const electionsContainer = $('#electionsList');
    electionsContainer.empty();
    
    const electionsCount = Object.keys(elections).length;
    
