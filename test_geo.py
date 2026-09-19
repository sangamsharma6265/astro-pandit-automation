from geopy.geocoders import Nominatim

def get_lat_lng_from_city(city_name):
    geolocator = Nominatim(user_agent="astro_pandit_factory")
    try:
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"City '{city_name}' nahi mili, default Delhi set kar rahe hain.")
            return 28.6139, 77.2090
    except Exception as e:
        print(f"Error: {e}")
        return 28.6139, 77.2090

# Test karke dekhte hain:
lat, lng = get_lat_lng_from_city("Jaipur")
print(f"Jaipur Lat: {lat}, Lng: {lng}")