from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import requests

from generate_input_file import *
import os
from io import BytesIO

app = Flask(__name__)
CORS(app)

# Constants
ITEMS_PER_PAGE = 50

# Function to connect to the SQLite database
def connect_db():
    conn = sqlite3.connect('./reactionDB.db')
    return conn

def query_catalysisHub_data(reactants, products, surfaces, facets, after_cursor=None):
    after_clause = f', after: "{after_cursor}"' if after_cursor else ''
    query = f'''
    query {{
      reactions(first: 50, surfaceComposition:"{surfaces}", facet:"~{facets}", reactants: "{reactants}", products: "{products}"{after_clause}) {{
        totalCount
        pageInfo {{
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }}
        edges {{
          node {{
            Equation
            sites
            id
            pubId
            dftCode
            dftFunctional
            reactants
            products
            facet
            chemicalComposition
            reactionEnergy
            activationEnergy
            surfaceComposition
            reactionSystems {{
              name
              energyCorrection
              aseId
            }}
          }}
        }}
      }}
    }}
    '''

    response = requests.post('https://api.catalysis-hub.org/graphql', json={'query': query})
    if response.status_code == 200:
        # Extract the dictionaries inside each "node" object
        data = response.json()['data']['reactions']
        return [edge['node'] for edge in data['edges']], data['pageInfo']['endCursor'], data['pageInfo']['hasNextPage']
    else:
        return [], None, False
    
def query_total_count(reactants, products, surfaces, facets):
    query = f'''
    query {{
      reactions(first: 100, surfaceComposition:"{surfaces}", facet:"~{facets}", reactants: "{reactants}", products: "{products}") {{
        totalCount
        pageInfo {{
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }}
        edges {{
          node {{
            Equation
            sites
            id
            pubId
            dftCode
            dftFunctional
            reactants
            products
            facet
            chemicalComposition
            reactionEnergy
            activationEnergy
            surfaceComposition
            reactionSystems {{
              name
              energyCorrection
              aseId
            }}
          }}
        }}
      }}
    }}
    '''
    
    response = requests.post('https://api.catalysis-hub.org/graphql', json={'query': query})
    if response.status_code == 200:
        return response.json()['data']['reactions']['totalCount']
    else:
        return 0


# API endpoint to query data from the database
@app.route('/query', methods=['GET'])
def query_data():
    #Extract parameters
    reactants = request.args.get('reactants') or "~"
    products = request.args.get('products') or "~"
    surfaces = request.args.get('surfaces') or "~"
    facets = request.args.get('facets') or ""
    page = int(request.args.get('page', 1))


    # Fetch data from Catalysis Hub API
    after_cursor = None
    if page > 1:
        for _ in range(page - 1):
            _, after_cursor, has_next_page = query_catalysisHub_data(reactants, products, surfaces, facets, after_cursor)
            if not has_next_page:
                return jsonify([])  # No more data

    data, _, _ = query_catalysisHub_data(reactants, products, surfaces, facets, after_cursor)

    return jsonify(data)
    


@app.route('/total-count', methods=['GET'])
def get_total_count():
    # Extract parameters
    reactants = request.args.get('reactants') or "~"
    products = request.args.get('products') or "~"
    surfaces = request.args.get('surfaces') or "~"
    facets = request.args.get('facets') or ""

    # Query the total count from Catalysis Hub API
    total_count = query_total_count(reactants, products, surfaces, facets)
    
    return jsonify({'totalCount': total_count})

@app.route('/generate-input-file', methods=['POST'])
def generate_input_file_route():
    user_inputs = request.json  # Assuming user inputs are sent as JSON
    try:
        # Generate the input file content
        file_content = generate_input_file(user_inputs)
        
        # Create a BytesIO object to hold the file content
        file_stream = BytesIO()
        file_stream.write(file_content.encode())
        file_stream.seek(0)
        
        # Send the file to the frontend
        return send_file(file_stream, as_attachment=True, download_name='Input_SAC.mkm', mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
