from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests

app = Flask(__name__)
CORS(app)

# Function to connect to the SQLite database
def connect_db():
    conn = sqlite3.connect('./reactionDB.db')
    return conn

def query_catalysisHub_data(reactants, products, surfaces, facets):
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
    print("response: ",response)
    if response.status_code == 200:
        # Extract the dictionaries inside each "node" object
        return [edge['node'] for edge in response.json()['data']['reactions']['edges']]
    else:
        return []
    
def query_total_count(reactants, products, surfaces, facets):
    print("reactants", reactants)
    print("products", products)
    print("surfaces", surfaces)
    print("facets", facets)

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


# API endpoint to fetch data from the database
@app.route('/data', methods=['GET'])
def get_data():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reaction')
    rows = cursor.fetchall()


    # Get column names
    cursor.execute(f'PRAGMA table_info(reaction)')
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    # Convert rows to list of dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(columns, row)))

    #return jsonify(data)
    return jsonify(data)


# API endpoint to query data from the database
@app.route('/query', methods=['GET'])
def query_data():
    #Extract parameters
    reactants = request.args.get('reactants') or "~"
    products = request.args.get('products') or "~"
    surfaces = request.args.get('surfaces') or "~"
    facets = request.args.get('facets') or ""

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reaction WHERE reactants = ? AND products = ? AND surfaceComposition = ? AND facet = ?', (reactants, products, surfaces, facets))
    rows = cursor.fetchall()


    # Get column names
    cursor.execute(f'PRAGMA table_info(reaction)')
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    # Convert rows to list of dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(columns, row)))

    print(reactants, products, surfaces, facets)
    # Fetch data from Catalysis Hub API
    catalysis_hub_data = query_catalysisHub_data(reactants, products, surfaces, facets)
    
    #print("fetched data: ", data)
    #print("catalysisHub Data", catalysis_hub_data)
    #return jsonify(data)
    return jsonify(catalysis_hub_data)

    ##print("fetched data: ", data)
    ##return jsonify(data)

@app.route('/total-count', methods=['GET'])
def get_total_count():
    # Extract parameters
    reactants = request.args.get('reactants') or "~"
    products = request.args.get('products') or "~"
    surfaces = request.args.get('surfaces') or "~"
    facets = request.args.get('facets') or ""

    # Query the total count from Catalysis Hub API
    total_count = query_total_count(reactants, products, surfaces, facets)
    print("TOTAL COUNT: ", total_count)
    
    return jsonify({'totalCount': total_count})

if __name__ == '__main__':
    app.run(debug=False)
