import osmnx as ox
import networkx as nx
import folium
import numpy as np
from math import radians, cos, sin, asin, sqrt
import time
from typing import Dict, Tuple, List
import sys

# Define the hospitals with coordinates
hospital_locations = {
    'Apollo Speciality Hospitals': (9.92845107063264, 78.1490877660568),
    'Meenakshi Mission Hospital': (9.94802716543532, 78.1629092749301),
    'Velammal Medical College Hospital': (9.886849012033327, 78.15014381533766),
    'AVSS Hospital': (9.91758806933076, 78.13921992029667),
    'Madurai Medical College': (9.929116498156905, 78.1370005945043),
    'Booma Nursing Home': (9.935864108998347, 78.13466017122525),
    'Venkateswara Hospital': (9.925768390898137, 78.13276213497977),
}

# Current location
current_location = (9.918335304387874, 78.1134397514805)

def display_loading_animation(duration: int = 3):
    """Display a simple loading animation in the terminal"""
    animation = "|/-\\"
    for _ in range(duration * 10):
        for char in animation:
            sys.stdout.write(f'\rLoading... {char}')
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 20 + '\r')

def display_hospitals():
    """Display available hospitals with numbered options"""
    print("\n=== Available Hospitals ===")
    print("-" * 50)
    for idx, (name, coords) in enumerate(hospital_locations.items(), 1):
        print(f"{idx}. {name}")
        print(f"   Coordinates: {coords}")
        print("-" * 50)

def get_user_selection() -> str:
    """Get and validate user's hospital selection"""
    while True:
        try:
            print("\nSelect a hospital by entering its number:")
            choice = int(input("Your choice (1-7): "))
            if 1 <= choice <= len(hospital_locations):
                return list(hospital_locations.keys())[choice - 1]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def calculate_alternative_routes(G, start_node: int, end_node: int, 
                              num_routes: int = 3) -> List[Tuple[List[int], float]]:
    """Calculate multiple routes between two points"""
    routes = []
    for i in range(num_routes):
        try:
            if i == 0:
                # First route - shortest path
                route = nx.astar_path(G, start_node, end_node, weight='length')
                distance = nx.astar_path_length(G, start_node, end_node, weight='length')
            else:
                # Alternative routes by temporarily removing some nodes from shortest path
                temp_G = G.copy()
                for prev_route, _ in routes:
                    # Remove some random nodes from previous routes
                    nodes_to_remove = np.random.choice(prev_route[1:-1], 
                                                     size=min(3, len(prev_route)-2), 
                                                     replace=False)
                    temp_G.remove_nodes_from(nodes_to_remove)
                route = nx.astar_path(temp_G, start_node, end_node, weight='length')
                distance = nx.astar_path_length(temp_G, start_node, end_node, weight='length')
            routes.append((route, distance))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    return routes

def create_map_with_alternatives(G, current_loc: Tuple[float, float], 
                               hospital_name: str, routes: List[Tuple[List[int], float]]):
    """Create an interactive map with alternative routes"""
    m = folium.Map(location=current_loc, zoom_start=13)

    # Add marker for current location
    folium.Marker(
        current_loc,
        popup='Your Location',
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)

    # Add hospital marker
    hospital_loc = hospital_locations[hospital_name]
    
    # Calculate average time for all routes
    distances_km = [dist/1000 for _, dist in routes]
    times_min = [d/40*60 for d in distances_km]  # Assuming 40 km/h average speed
    
    popup_text = f"""
    <div style="min-width: 200px">
        <h4>{hospital_name}</h4>
        <p>Shortest route: {min(distances_km):.2f} km</p>
        <p>Est. time: {min(times_min):.1f} min</p>
        <p>Alternative routes available</p>
    </div>
    """

    folium.Marker(
        hospital_loc,
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color='red', icon='plus', prefix='fa'),
        tooltip=hospital_name
    ).add_to(m)

    # Sort routes by distance
    routes.sort(key=lambda x: x[1])
    
    # Color scheme for routes
    colors = ['green', 'darkblue', 'red']
    labels = ['Shortest Route', 'Alternative Route', 'Longest Route']

    # Add routes
    for i, (route, distance) in enumerate(routes):
        path = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
        
        folium.PolyLine(
            locations=path,
            weight=4 if i == 0 else 3,  # Make shortest route slightly thicker
            color=colors[min(i, len(colors)-1)],
            opacity=0.8,
            popup=f"Distance: {distance/1000:.2f} km",
            tooltip=labels[min(i, len(labels)-1)]
        ).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; background-color: white;
         padding: 10px; border: 2px solid grey; border-radius: 5px; z-index:9999;">
        <h4>Route Legend</h4>
        <p><span style='color: green'>━━</span> Shortest Route</p>
        <p><span style='color: darkblue'>━━</span> Alternative Route</p>
        <p><span style='color: red'>━━</span> Longest Route</p>
        <p>🏥 Hospital</p>
        <p>📍 Your Location</p>
        <small>Times based on 40 km/h average speed</small>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

def main():
    # Display welcome message
    print("\n=== Welcome to Hospital Route Finder ===")
    print("Finding nearby hospitals and calculating routes...")
    
    # Show loading animation while getting road network
    display_loading_animation(2)
    
    # Get road network
    G = ox.graph_from_point(current_location, dist=5000, network_type='drive')
    
    # Display available hospitals
    display_hospitals()
    
    # Get user selection
    selected_hospital = get_user_selection()
    
    print(f"\nCalculating routes to {selected_hospital}...")
    display_loading_animation(1)
    
    # Calculate routes
    current_node = ox.distance.nearest_nodes(G, current_location[1], current_location[0])
    hospital_node = ox.distance.nearest_nodes(G, 
                                            hospital_locations[selected_hospital][1],
                                            hospital_locations[selected_hospital][0])
    
    # Get multiple routes
    routes = calculate_alternative_routes(G, current_node, hospital_node)
    
    if not routes:
        print("Error: No route found to the selected hospital.")
        return
    
    # Create and save map
    print("\nGenerating interactive map...")
    display_loading_animation(1)
    
    m = create_map_with_alternatives(G, current_location, selected_hospital, routes)
    output_file = 'hospital_route.html'
    m.save(output_file)
    
    # Display results
    print("\n=== Route Summary ===")
    print(f"Routes to {selected_hospital}:")
    for i, (_, distance) in enumerate(routes):
        distance_km = distance / 1000
        time_min = distance_km / 40 * 60
        route_type = "Shortest" if i == 0 else "Alternative" if i == 1 else "Longest"
        print(f"{route_type} route: {distance_km:.2f} km ({time_min:.1f} min)")
    
    print(f"\nMap has been saved to '{output_file}'")
    print("Open the file in your web browser to view the routes.")

if __name__ == "__main__":
    main()