import json
from flask import Flask, request, render_template, jsonify
import requests
from arcgis.gis import GIS
from arcgis import geocoding
from arcgis.geometry import LengthUnits, Point, project, Polygon
from arcgis.geometry.functions import buffer
import os

api_key = os.environ.get("api_key")

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("harris_flood.html")

@app.route("/geocode", methods=['POST'])
def geocode():
    gis = GIS("https://www.arcgis.com", api_key=api_key)
    data = request.get_json()
    addr = data.get("address")
    coder = geocoding.Geocoder("https://geocode-api.arcgis.com/arcgis/rest/services/World/GeocodeServer", gis)
    result = coder.geocode(addr)
    print(len(result))
    if len(result) > 0:
        for r in result:
            print(r["location"])
        return jsonify({"long": result[0]["location"]["x"], "lat": result[0]["location"]["y"], "address": result[0]["address"]})
    else:
        return jsonify({})

@app.route("/floodquery", methods=["POST"])
def floodquery():
    gis = GIS("https://www.arcgis.com", api_key=api_key)
    data = request.get_json()

    point = Point({
        "x": data["x"],
        "y": data["y"],
        "spatialReference": {"wkid": 4326}
    })
    buffer_distance = 40

    url = "https://services1.arcgis.com/KtqvyF87KwiZmuTC/arcgis/rest/services/Harvey_Damage/FeatureServer/0/query"

    projected_point = project([point], in_sr=4326, out_sr=3857)[0]
    buffered_geometry = buffer([projected_point], distances=[buffer_distance], in_sr={"wkid": 3857}, unit = LengthUnits.METER)[0]
    buffered_geometry = project([buffered_geometry], in_sr=3857, out_sr=4326)[0]
    extent = buffered_geometry.extent
    square = Polygon({"rings": [[
        [extent[0], extent[1]],
        [extent[2], extent[1]],
        [extent[2], extent[3]],
        [extent[0], extent[3]],
        [extent[0], extent[1]]
    ]], "spatialReference": {"wkid": 4326}})

    print("well we got this far")

    params = {

        "token": api_key,
        "f": "json",
        "geometry": json.dumps(square),
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
