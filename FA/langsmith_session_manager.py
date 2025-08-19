from datetime import datetime, timezone

from langsmith import Client

client = Client()

# Specific session ID to search for
target_session_id = "3194c585-075a-472b-91dc-05a1fdd5f9f5"

print(f"Searching for session ID: {target_session_id}")

# Try searching for runs within this session (session parameter expects a list)
try:
    print(f"Searching for runs in session {target_session_id}...")
    runs = list(client.list_runs(session=[target_session_id], limit=50))
    
    if runs:
        print(f"Found {len(runs)} runs in this session:")
        for run in runs:
            print(f"- Run: {run.name}, ID: {run.id}")
            print(f"  Start: {run.start_time}")
            print(f"  End: {run.end_time}")
            print(f"  Status: {run.status}")
            if not run.end_time:
                print(f"  -> This run is still active")
            print()
    else:
        print("No runs found in this session")
        
except Exception as run_error:
    print(f"Could not search for runs in session: {run_error}")
    
    # Alternative approach: try to find the session by listing all sessions
    try:
        print("Trying to find session by listing all sessions...")
        sessions = list(client.list_sessions())
        
        target_session = None
        for session in sessions:
            if session.id == target_session_id:
                target_session = session
                break
                
        if target_session:
            print(f"Found session: {target_session.name}")
            print(f"ID: {target_session.id}")
            if hasattr(target_session, 'start_time'):
                print(f"Start: {target_session.start_time}")
            if hasattr(target_session, 'end_time'):
                print(f"End: {target_session.end_time}")
                if not target_session.end_time:
                    print("-> This session is still open")
        else:
            print(f"Session {target_session_id} not found in session list")
            
    except Exception as list_error:
        print(f"Could not list sessions: {list_error}")
        print("The session ID may not exist or you may not have access to it.")
