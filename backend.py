from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests

from generate_input_file import *
import os

app = Flask(__name__)
# Configure CORS to allow requests from your frontend origin
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Constants
ITEMS_PER_PAGE = 50

def query_local_data(reactants, products, surfaces, facets):
  data = []
  filterCondition = {'reactants': reactants if reactants != "~" else "", 
                     'facet': facets, 
                     'surface_composition': surfaces if surfaces != "~" else "",
                     'products': products if products != "~" else ""}

  filterCondition = {
    'reactants': "", 
    'facet': "", 
    'surfaceComposition': "",
    'products': ""
  }

  print("filterCondition: ",filterCondition)
  
  print("Right before call---------------")
  
  response = requests.post('http://10.161.209.65:5000/get_data', json=filterCondition)

  print("response:", response)
  if response.status_code == 200:
    data = [item['node'] for item in response.json()]
    #Add data source key value pair to each reaction data 
    for item in data: 
      item['dataSource'] = 'AiScia'
      item['activationEnergy'] = float(item['activationEnergy'])
      item['reactionEnergy'] = float(item['reactionEnergy'])
    print("data:", data)
    return data
  else:
    print("Responce Error")
    return []


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
    formattedData = [edge['node'] for edge in data['edges']]
    #Add data source key value pair to each reaction data 
    for item in formattedData:
      item['dataSource'] = 'CatalysisHub'
      ## TO DO - what should the default values be 
      ## is there a way to calculate the nessary data???
      item['molecularData'] = '{"defualt": {"molecularWeight": 1,"symmetrySigma": 1, "rotationalConstant": 1}}'
    return formattedData, data['pageInfo']['endCursor'], data['pageInfo']['hasNextPage']
  else:
    return [], None, False
    
def query_total_count(reactants, products, surfaces, facets):
  query = f'''
  query {{
    reactions(first: 1, surfaceComposition:"{surfaces}", facet:"~{facets}", reactants: "{reactants}", products: "{products}") {{
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

  #Local data
  ### NEED TO FIX LOGIC 
  """Need to take into consideration how much there is in total, 
  section that into table pages, have this taken into consideration 
  when making requests from catalysisHub
  For exmple: if we have 5 local data then we need 45 cataylsisHub data for the first page"""
  if page == 1: 
    localData = query_local_data(reactants, products, surfaces, facets)
  else: 
    localData = []


  # Fetch data from Catalysis Hub API
  after_cursor = None
  if page > 1:
    for _ in range(page - 1):
      _, after_cursor, has_next_page = query_catalysisHub_data(reactants, products, surfaces, facets, after_cursor)
      if not has_next_page:
        return jsonify([])  # No more data

  catalysisHubData, _, _ = query_catalysisHub_data(reactants, products, surfaces, facets, after_cursor)

  data = localData + catalysisHubData
  return jsonify(data)
    

@app.route('/total-count', methods=['GET'])
def get_total_count():
  # Extract parameters
  reactants = request.args.get('reactants') or "~"
  products = request.args.get('products') or "~"
  surfaces = request.args.get('surfaces') or "~"
  facets = request.args.get('facets') or ""

  # Query the total count from Catalysis Hub API
  catalysisHub_count = query_total_count(reactants, products, surfaces, facets)

  #Local data
  localData = query_local_data(reactants, products, surfaces, facets)
  local_data_count = len(localData)

  total_count = catalysisHub_count + local_data_count

  return jsonify({'totalCount': total_count})


@app.route('/generate-input-file', methods=['POST'])
def generate_input_file_route():
  user_inputs = request.json  # Assuming user inputs are sent as JSON
  # Generate the input file content as a string
  input_file_content = generate_input_file(user_inputs)
  # Create a temporary file to store the input file content
  file_path = './Input_SAC.mkm'
  with open(file_path, 'w') as file:
      file.write(input_file_content)
  # Send the file as a response
  return send_file(file_path, as_attachment=True, download_name='Input_SAC.mkm')


if __name__ == '__main__':
  app.run(debug=False)
