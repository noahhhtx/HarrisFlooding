import json
from flask import Flask, request, render_template, jsonify
import requests
import shapely
import os
from geopy.geocoders import ArcGIS
import geopandas as gpd

api_key = os.environ.get("api_key")

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("harris_flood.html")

@app.route("/geocode", methods=['POST'])
def geocode():
    #gis = GIS("https://www.arcgis.com", api_key=api_key)
    geolocator = ArcGIS(user_agent="Noah's Geocoder")
    data = request.get_json()
    addr = data.get("address").get("address")
    print(addr)
    try:
        location = geolocator.geocode(addr, timeout=10)
        print("found")
        print(location)
        print("uhhhhh")
        return jsonify({"long": location.longitude, "lat": location.latitude, "address": location.address})
    except Exception as e:
        print("there was an error!")
        print(e)
        return jsonify({})

@app.route("/floodquery", methods=["POST"])
def floodquery():
    data = request.get_json()

    point = shapely.Point(data["x"], data["y"])
    buffer_distance = 30 / 3.28084

    point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs="epsg:4326")
    gdf_utm = point_gdf.to_crs(epsg=32618)
    buffered_point_utm = gdf_utm.buffer(buffer_distance, cap_style=3)
    buffered_point_wgs84 = buffered_point_utm.to_crs(epsg=4326)
    buffered_polygon = buffered_point_wgs84.geometry[0]

    url = "https://services1.arcgis.com/KtqvyF87KwiZmuTC/arcgis/rest/services/Harvey_Damage/FeatureServer/0/query"

    print("well we got this far")

    point_geojson = shapely.to_geojson(buffered_polygon)
    rings_str = point_geojson[point_geojson.find("["):-1]
    print(rings_str)
    pointstr = "{" + f'"rings": {rings_str}, "spatialReference": ' + "{" + '"wkid": 4326' + "}" + "}"
    print(pointstr)

    params = {

        "token": api_key,
        "f": "json",
        "geometry": pointstr,
        "geometryType": "esriGeometryPolygon",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "MAX_IN_DEP",

    }

    response = requests.get(url, params=params)

    print("okay...")

    flood_depth = 0

    if response.status_code == 200:
        data = response.json()
        print(data)
        if "features" in data:
            for feature in data["features"]:
                if feature['attributes']['MAX_IN_DEP'] > flood_depth:
                    flood_depth = feature['attributes']['MAX_IN_DEP']
        else:
            print("No intersecting features found.")
    else:
        print(f"Error querying feature layer: {response.status_code} - {response.text}")

    print("Est. Flood Depth:", flood_depth)
    return jsonify({"flood_depth": flood_depth})
