
import json
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from matplotlib.patches import Ellipse
import os

class GeoAnalyzer:
    CACHE_FILE = 'cache.json'

    def __init__(self):
        self.cache = self.load_cache()
        self.failed_places = 0
        self.locations = self.load_locations()
        self.places = [loc['searchString'] for loc in self.locations if loc['type'] == 'place']
        self.boundary_points = {
            "British Museum": "British Museum, London",
            "Hyde Park": "Hyde Park, London",
            "Tower Bridge": "Tower Bridge, London",
            "Lambeth": "Lambeth, London"
        }
        self.place_coords = {}
        self.boundary_coords = {}

    def load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(self):
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(self.cache, f)

    def load_locations(self):
        with open('locations.json', 'r') as f:
            return json.load(f)

    def get_coordinates(self, place, delay=1):
        if place in self.cache:
            return self.cache[place]

        time.sleep(delay)

        try:
            url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json&limit=1"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            if data:
                location = data[0]
                coords = (float(location['lat']), float(location['lon']))
                self.cache[place] = coords
                self.save_cache()
                return coords
            else:
                print(f"Warnung: Konnte keine Koordinaten für '{place}' finden.")
                self.cache[place] = None
                self.failed_places += 1
                return None
        except Exception as e:
            print(f"Fehler bei der Geocodierung von '{place}': {e}")
            self.failed_places += 1
            return None

    def compute_ellipse_and_plot(self):
        self.place_coords = {place: self.get_coordinates(place) for place in self.places}
        self.place_coords = {place: coords for place, coords in self.place_coords.items() if coords is not None}
        self.boundary_coords = {key: self.get_coordinates(value) for key, value in self.boundary_points.items()}
        self.boundary_coords = {key: coords for key, coords in self.boundary_coords.items() if coords is not None}

        if len(self.boundary_coords) < 4:
            raise ValueError("Nicht alle Grenzpunkte konnten gefunden werden. Bitte überprüfen Sie die Eingaben.")

        ellipse_center = np.mean([coords for coords in self.boundary_coords.values()], axis=0)
        boundary_latitudes = [coords[0] for coords in self.boundary_coords.values()]
        boundary_longitudes = [coords[1] for coords in self.boundary_coords.values()]
        boundary_radius_lat = (max(boundary_latitudes) - min(boundary_latitudes)) / 2
        boundary_radius_lon = (max(boundary_longitudes) - min(boundary_longitudes)) / 2

        ellipse = Ellipse(xy=(ellipse_center[1], ellipse_center[0]), width=2*boundary_radius_lon, height=2*boundary_radius_lat, edgecolor='r', facecolor='none', linestyle='--')

        fig, ax = plt.subplots()
        ax.set_aspect('equal')
        ax.add_patch(ellipse)

        for place, coords in self.place_coords.items():
            ax.plot(coords[1], coords[0], 'bo')
            ax.text(coords[1], coords[0], place, fontsize=9)

        for key, coords in self.boundary_coords.items():
            ax.plot(coords[1], coords[0], 'go')
            ax.text(coords[1], coords[0], key, fontsize=9)

        min_latitude = min(boundary_latitudes) - 0.01
        max_latitude = max(boundary_latitudes) + 0.01
        min_longitude = min(boundary_longitudes) - 0.01
        max_longitude = max(boundary_longitudes) + 0.01

        ax.set_xlim([min_longitude, max_longitude])
        ax.set_ylim([min_latitude, max_latitude])

        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('Orte und ovales Gebiet in London')

        polygon_points = [
            (ellipse_center[0] + boundary_radius_lat * np.cos(theta), ellipse_center[1] + boundary_radius_lon * np.sin(theta))
            for theta in np.linspace(0, 2 * np.pi, 100)
        ]
        polygon = Polygon(polygon_points)

        found_places = 0

        print("Orte, die nicht gefunden wurden:")
        for place, coords in self.place_coords.items():
            if coords is None:
                print(f"{place}")
            else:
                point = Point(coords[0], coords[1])
                if polygon.contains(point):
                    print(f"{place} liegt innerhalb des Gebiets.")
                    found_places += 1
                else:
                    print(f"{place} liegt außerhalb des Gebiets.")

        print(f"Resultat: \n Total Orte: {len(self.places)} \n Innerhalb des Gebiet: {found_places}\n Ausserhalb des Gebiet: {len(self.place_coords) - found_places} \n Orte insgesammt: {len(self.place_coords)} \n Konnten nicht gefunden werden: {self.failed_places} ")

        # plt.show()
