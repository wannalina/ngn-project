from flask import Flask, jsonify
import json

app = Flask(__name__)

attractions_list = [
    {
        "city": "Washington, D.C.",
        "attraction": "Smithsonian Museums",
        "description": "A collection of world-class museums, including the Air and Space Museum and the National Museum of Natural History."
    },
    {
        "city": "Bolzano",
        "attraction": "Runkelstein Castle",
        "description": "A medieval castle with well-preserved frescoes and panoramic views."
    },
    {
        "city": "Trento",
        "attraction": "Piazza Duomo",
        "description": "The heart of Trento, featuring the beautiful Neptune Fountain and the Trento Cathedral."
    },
    {
        "city": "Helsinki",
        "attraction": "Suomenlinna Fortress",
        "description": "A UNESCO World Heritage site on an island, rich in history and scenic walks."
    },
    {
        "city": "Barcelona",
        "attraction": "Park Güell",
        "description": "A colorful, artistic park designed by Gaudí, offering great city views."
    },
    {
        "city": "Washington, D.C.",
        "attraction": "National Mall & Monuments",
        "description": "Home to the Lincoln Memorial, Washington Monument, and more."
    },
    {
        "city": "Bolzano",
        "attraction": "South Tyrol Museum of Archaeology",
        "description": "Home to Ötzi the Iceman, a 5,300-year-old mummy."
    },
    {
        "city": "Trento",
        "attraction": "MUSE – Museo delle Scienze",
        "description": "A modern science museum designed by architect Renzo Piano."
    },
    {
        "city": "Helsinki",
        "attraction": "Helsinki Cathedral",
        "description": "A stunning neoclassical landmark in Senate Square."
    },
    {
        "city": "Barcelona",
        "attraction": "Sagrada Família",
        "description": "Gaudí’s masterpiece and one of the most famous basilicas in the world."
    },
    {
        "city": "Washington, D.C.",
        "attraction": "The White House",
        "description": "The official residence of the U.S. president, open for tours with advance booking."
    },
    {
        "city": "Bolzano",
        "attraction": "Walther Square (Piazza Walther)",
        "description": "A lively city square surrounded by historic buildings and cafes."
    },
    {
        "city": "Trento",
        "attraction": "Buonconsiglio Castle",
        "description": "A historic castle with medieval frescoes and stunning views."
    },
    {
        "city": "Helsinki",
        "attraction": "Temppeliaukio Church (Rock Church)",
        "description": "A unique church built directly into solid rock."
    },
    {
        "city": "Barcelona",
        "attraction": "La Rambla",
        "description": "A lively street with restaurants, street performers, and markets like La Boqueria."
    }
]

@app.route('/attractions', methods=['GET'])
def get_attractions():
    return attractions_list

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
