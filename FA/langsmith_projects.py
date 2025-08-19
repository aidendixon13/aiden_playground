from langsmith import Client

client = Client()

# List all projects
print("Listing all LangSmith projects...")
try:
    projects = list(client.list_projects())
    
    if not projects:
        print("No projects found.")
    else:
        print(f"Found {len(projects)} projects:\n")
        
        for i, project in enumerate(projects, 1):
            print(f"{i}. Project: {project.name}")
            print(f"   ID: {project.id}")
            if hasattr(project, 'description') and project.description:
                print(f"   Description: {project.description}")
            if hasattr(project, 'created_at'):
                print(f"   Created: {project.created_at}")
            print()
            
        # Interactive search
        search_term = input("Enter project name to search for (or press Enter to skip): ").strip()
        if search_term:
            matching_projects = [p for p in projects if search_term.lower() in p.name.lower()]
            
            if matching_projects:
                print(f"\nFound {len(matching_projects)} matching projects:")
                for project in matching_projects:
                    print(f"- {project.name} (ID: {project.id})")
            else:
                print(f"\nNo projects found matching '{search_term}'")

except Exception as e:
    print(f"Error listing projects: {e}")
    print("Make sure you have proper LangSmith credentials configured.")