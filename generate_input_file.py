import re
import math 
import json

"""Constants used for calculations"""
# Constants from Taha
_Nav = 6.02214076e23 # Avogardos number
h = 6.62607015e-34 # J/s  - Planks constant
kb = 1.380649e-23 # J/K  - Boltzmann's constant
_R = 8.3145 # J/mol.K - gas constant
evtj = 1.602176565e-19 # J/eV  - conversion from electronic volts to Joules
kb_eV = 8.1673303e-5 # eV/K - Boltzmann's constant in eV 

# Other constants
ev_kj = 1.602176565e-22 # kJ/eV  - conversion from electronic volts to kilo Joules
mole = 6.0223e23 # 1 mole used to convert eV to kJ/mole

"""Default Standard format for the file to be generated.
The {} are placeholders where the data will be inserted based on user input & reactions"""
def default_file_format():
	input_file_string = """# =========================== #
#     MKMCXX: Begin input     #
# =========================== #

&compounds
# Gas phase compounds
# name ; surface ; initial concentration
{}
# Surface compounds (denote with a star)
{}



# free sites on the surface
# surface "*" : {}
{}

&reactions
# Adsorption;                            m^2;      amu;       ThetaRot(K); Sigma;    sticking;  J/mol
{}

# reaction;                              vf;       vb;         EafJ/mol;     Eab J/mol
{}


&settings
TYPE = SEQUENCERUN
# pressure in bar
PRESSURE = {}
#REAGENTS = {}
#KEYCOMPONENTS = {}
EACT=0
ORDERS=0
DRC=0

&runs
#temperature; simulation time; atol   ; rtol
{} 

# =========================== #
#      MKMCXX: End input      #
# =========================== #"""
   
	return(input_file_string)


def sort_concentrations(input_concentrations):
	gas_compounds = []
	surface_compounds = []
	free_site_surface = []

	for i in input_concentrations:
		if "*" in i: 
			if i == "*":
					value = "1"
					temp = f"{i:<6} ; {value:<7} ; {input_concentrations[i]:<8}"
					free_site_surface.append(temp)
			else: 
					value = "1"
					temp = f"{i:<6} ; {value:<7} ; {input_concentrations[i]:<8}"
					surface_compounds.append(temp)
		else: 
			value = "0"
			temp = f"{i:<6} ; {value:<7} ; {input_concentrations[i]:<8}"
			gas_compounds.append(temp)
	
	return(gas_compounds, surface_compounds, free_site_surface)

""" Return surfce based on first reaction data"""
def fetch_surface_composition(input_reactions):
	#### CHECK  - TO DO ####UPDATE remove node
	""" print("first_reactions:", first_reactions)
	surface = first_reactions[0]["node"]["surfaceComposition"]
	return surface """
	results = fetch_reaction_data(input_reactions[0])
	surface_composition = results[0]["node"]["surfaceComposition"]
	return surface_composition


## TO DO 
## Change from reaction ids and fetching to dealing with list of reaction data directly
""" Functions that seperates the reactions into HK reactions and AR reactions
This is based on first the reaction includes the surface, 
    which is indicated by * in the reaction equation"""
def seperate_reactions(input_reactions): 
	hk_reactions = []
	ar_reactions = []
	for i in input_reactions:
		#fetch equation of reaction 
		results = fetch_reaction_data(str(i))
		equation = results[0]["node"]["Equation"]
		# Split the input string into reactants and products
		reactants, products = map(str.strip, equation.split("->"))
		# Regular expression to match an integer followed by '*'
		pattern = re.compile(r' \d+\*')
		#check if its absorbant reaction 
		if ((" *" in reactants) or pattern.search(reactants)) and not (" 0*" in reactants): 
			hk_reactions.append(i)
		else: 
			ar_reactions.append(i)

	return hk_reactions, ar_reactions

### -------------------------------TEMPORARY FOR TESTING-------------------------------------###
###### DELETE THIS SECTIONS ######
import sqlite3

def fetch_reaction_data(id):
	#query  = {"id": id}

	# Connect to the database
	conn = sqlite3.connect('TayebTu2024_v2.db')
	cursor = conn.cursor()

	# Query the database
	#request_dict = {'reactants': "COgas", 'facet': 110}  # Example1
	request_dict = {'id': id}

	# Building the SQL query dynamically
	query_parts = []
	for key, value in request_dict.items():
		if isinstance(value, str):  # Handle strings with LIKE
				query_parts.append(f"{key} LIKE '%{value}%'")
		else:  # Handle other data types with direct comparison
				query_parts.append(f"{key} = {value}")

	where_clause = " AND ".join(query_parts)
	query = f"SELECT * FROM reaction WHERE {where_clause}"

	# To see all enteries, uncomment the following command
	#query = f"SELECT * FROM reaction"

	# Execute the dynamic query
	cursor.execute(query)

	# Retrieve table names
	column_names = [description[0] for description in cursor.description]

	req_data = []
	for row in cursor.fetchall():
		temp_dict = {}
		for i in range(len(column_names)):
				temp_dict[column_names[i]] = str(row[i])
		req_data.append({'node':temp_dict})

	conn.close()

	return req_data

### -----------------------------HK METHOD SECTION---------------------------------- ###
"""Formats the reaction equations into the required format. 
For example: 
Original Equation: CO* + O* - 0* -> CO2(g) + 2*
Formatted Equation: {CO*} + {O*} => {CO2} + 2{*} 
AND
Original Equation: 12CO2 + * -> 12CO2*
Formatted Equation: 12{CO2} + {*}  => 12{CO2*} """
def format_equation(eq):
	# remove substring (g) which means gas from the equation
	eq = eq.replace("(g)", "")

	# Split the input string into reactants and products
	reactants, products = map(str.strip, eq.split("->"))

	# Process reactants
	reactants, reactant_separators = process_side(reactants)

	# Process products
	products, product_separators = process_side(products)

	# Join the parts to form the converted reaction
	converted_reaction = ""
	for i in range(len(reactants)): 
		converted_reaction = converted_reaction + reactants[i] + " "
		if i < len(reactant_separators): 
			converted_reaction = converted_reaction + reactant_separators[i] + " "
	
	converted_reaction = converted_reaction + " => "

	for i in range(len(products)): 
		converted_reaction = converted_reaction + products[i] + " "
		if i < len(product_separators): 
			converted_reaction = converted_reaction + product_separators[i] + " "

	# removing surface with 0 coefficients 
	converted_reaction = converted_reaction.replace(" + 0{*} ","")
	converted_reaction = converted_reaction.replace(" - 0{*} ","")

	return converted_reaction


"""Helper function for "format_equation" function"""
def process_side(side):
	# Split the side using both '+' and '-'
	species_list = re.split(r'\s*[\+-]\s*', side)

	# Determine the separators used
	separators = re.findall(r'[\+-]', side)

	# Process each species
	processed_species = [process_species(species) for species in species_list]

	return processed_species, separators


"""Helper function for "process_side" function"""
def process_species(species):
	# Extract the coefficient and species
	match = re.match(r'([-+]?\d*)(.*)', species.strip())
	coefficient, molecule = match.groups()

	# Format the species with curly braces
	formatted_species = f"{coefficient}{{{molecule.strip()}}}" if coefficient else f"{{{molecule.strip()}}}"

	return formatted_species


"""Helper function for "" function"""
def round_to_sf(number, sf):
	# Convert to scientific notation to handle both integer and fractional parts
	formatted_number = "{:.{}e}".format(number, sf - 1)
	
	# Convert back to a floating-point number
	rounded_number = float(formatted_number)
	
	return rounded_number


"""Helper function for "" function"""
def get_coverage(results): 
	try: 
		coverage = results[0]["node"]["coverages"]
		# extracting only the value from the string 
		coverage = coverage.split(":")[1]
		coverage = coverage.strip()[:-1]
		coverage = int(coverage)
	except: 
		coverage = 1 
	return coverage

### --- HK calculations --- ###
## TO DO - change reaction id to reaction data 
## TO DO - what should happen when using reactions from catalysisHub with no molecularData
"""fetches molecular weight value from molecular data"""
def reaction_equation(i):
	results = fetch_reaction_data(i)
	equation = results[0]["node"]["Equation"]
	processed_equation = format_equation(equation)
	return processed_equation


"""returns constant value for m2 currently used for all reactions"""
def fetch_m2():
	return str("1e-20")


## TO DO - change reaction id to reaction data 
## TO DO - what should happen when using reactions from catalysisHub with no molecularData
"""fetches molecular weight value from molecular data"""
def fetch_amu(i):
	results = fetch_reaction_data(i)
	try: 
		molecularData = results[0]["node"]["molecularData"]
		molecularData_dict = json.loads(molecularData)
		molecularData_list = list(molecularData_dict.values())
		amu = molecularData_list[0]["molecularWeight"]
	except: 
		amu = 0

	amu = round(amu,2)
	return str(amu)


## TO DO - change reaction id to reaction data 
## TO DO - what should happen when using reactions from catalysisHub with no molecularData
"""fetches rotational constant value from molecular data"""
def fetch_theta(i):
	results = fetch_reaction_data(i)
	try: 
		molecularData = results[0]["node"]["molecularData"]
		molecularData_dict = json.loads(molecularData)
		molecularData_list = list(molecularData_dict.values())
		theta = molecularData_list[0]["rotationalConstant"]
	except: 
		theta = 0

	theta = round(theta, 2)
	return str(theta)


## TO DO - change reaction id to reaction data 
## TO DO - what should happen when using reactions from catalysisHub with no molecularData
"""fetches sigma value from molecular data"""
def fetch_sigma(i):
	results = fetch_reaction_data(i)
	try: 
		molecularData = results[0]["node"]["molecularData"]
		molecularData_dict = json.loads(molecularData)
		molecularData_list = list(molecularData_dict.values())
		sigma = molecularData_list[0]["symmetrySigma"]
	except: 
		sigma = 0

	return str(sigma)


## TO DO - change reaction id to reaction data 
"""Calculates the sticking value SUM for all reactions used to calculate the 
    final sticking value for each reaction"""
def calculating_sticking_sum(absoptions_reactions): 
	sumation_of_sticking_values = 0

	for i in absoptions_reactions:
		results = fetch_reaction_data(i)
		activationEngery = results[0]["node"]["activationEnergy"]
		try:
			activationEngery  = float(activationEngery)
		except ValueError:
			activationEngery  =  1.0
		
		# Convert from eV to kj/mole
		activationEngery = activationEngery*evtj*mole

		#  calculating activation energy for a coverage of 1
		coverage = get_coverage(results)
		single_activation_energy = activationEngery/coverage

		# Tempreture value is taken as 520 for all sticking value calculations
		indiviual_sticking_value = math.exp(-single_activation_energy/(kb_eV*520))
		sumation_of_sticking_values = sumation_of_sticking_values + indiviual_sticking_value

	return sumation_of_sticking_values

## TO DO - change reaction id to reaction data 
## pass hk_reactions to function 
"""Calculates the sticking value"""
def fetch_sticking(i,hk_reactions):
	results = fetch_reaction_data(i)
	activationEngery = results[0]["node"]["activationEnergy"]
	try:
		activationEngery  = float(activationEngery)
	except ValueError:
		activationEngery  =  1.0

	# Convert from eV to kj/mole
	activationEngery = activationEngery*evtj*mole

	#  calculating activation energy for a coverage of 1
	coverage = get_coverage(results)
	single_activation_energy = activationEngery/coverage

	#indiviual_sticking_value = math.exp(division_higher_percision)
	indiviual_sticking_value = math.exp(-single_activation_energy/(kb_eV*520)) 
	sumation_of_sticking_values = calculating_sticking_sum(hk_reactions)
	try: 
		sticking = indiviual_sticking_value / sumation_of_sticking_values
	except: 
		sticking = 1

	sticking  = round_to_sf(sticking,3)

	return str(sticking)

## TO DO - change reaction id to reaction data 
"""Calculates the DES energy value"""
def fetch_energyDES(i):
	results = fetch_reaction_data(i)
	reactionEngery = results[0]["node"]["reactionEnergy"]
	try:
		reactionEngery = float(reactionEngery)
	except ValueError:
		return 0.0
  
	# calculating activation energy for a coverage of 1
	coverage = get_coverage(results)
	single_reaction_energy = reactionEngery/coverage

	desorptionEnergy = - single_reaction_energy
	# Convert from eV to j/mole
	desorptionEnergy = desorptionEnergy * evtj * _Nav
	desorptionEnergy = "{:.2e}".format(desorptionEnergy).replace('e+', 'e')
	return str(desorptionEnergy)

"""Current adsorption is constantly 1"""
def fetch_adsorption():
	return "1"


def format_hk_section(hk_reactions):
	reactions_with_values = []

	for i in (hk_reactions):
		temp = "HK; " + f"{reaction_equation(i):<35} ; {fetch_m2():<8} ; {fetch_amu(i):<8} ; {fetch_theta(i):<8} ; {fetch_sigma(i):<8} ; {fetch_sticking(i,hk_reactions):<8} ; {fetch_energyDES(i):<10} ; {fetch_adsorption():<3}"
		reactions_with_values.append(temp)

	return reactions_with_values

### -----------------------------AR METHOD SECTION---------------------------------- ###
"""For the values vf (forward rate constant) and vb (backward rate constant), the calculation is very expensive and the value difference is negligible. 
Therefore, we use 6.2e12 for both values no matter the reaction or molecules. """

"""calculated fv (forward rate constant). 
Constant value used for all"""
def fetch_vf():
	# use this value for all 
	return "6.2e12"

"""calculated fv (backward rate constant). 
Constant value used for all"""
def fetch_vb():
	# use this value for all 
	return "6.2e12"

## TO DO - change reaction id to reaction data 
"""Calculates the forward activation energy value"""
def fetch_EafJ(i):
	# forward activation energy = activation energy
	results = fetch_reaction_data(i)
	activationEngery = results[0]["node"]["activationEnergy"]
	try: 
		activationEngery = float(activationEngery)
	except: 
		activationEngery = 1.0

	# Convert from eV to kj/mole
	activationEngery = activationEngery*evtj*mole

	coverage = get_coverage(results)
	single_activation_energy = activationEngery/coverage

	single_activation_energy = round(single_activation_energy,2)
	return str(single_activation_energy)

## TO DO - change reaction id to reaction data 
"""Calculates the backwards activation energy value"""
def fetch_Eab(i):
	# backward activation energy = activation energy - reaction energy
	results = fetch_reaction_data(i)
	activationEngery = results[0]["node"]["activationEnergy"]
	reactionEngery = results[0]["node"]["reactionEnergy"]
	try: 
		activationEngery = float(activationEngery)
	except: 
		activationEngery = 1.0
	try: 
		reactionEngery = float(reactionEngery)
	except: 
		reactionEngery = 1.0

	# Convert from eV to kj/mole
	activationEngery = activationEngery*evtj*mole
	reactionEngery = reactionEngery*evtj*mole

	coverage = get_coverage(results)
	single_activation_energy = activationEngery/coverage
	single_reaction_energy = reactionEngery/coverage

	backward_activation_energy = single_activation_energy - single_reaction_energy
	backward_activation_energy = round(backward_activation_energy,2)
	return str(backward_activation_energy)

def format_ar_section(ar_reactions):
	reactions2_with_values = []

	for i in (ar_reactions):
		temp = "AR; " + f"{reaction_equation(i):<35} ; {fetch_vf():<8} ; {fetch_vb():<8} ; {fetch_EafJ(i):<10} ; {fetch_Eab(i):<10}"
		reactions2_with_values.append(temp)

	return reactions2_with_values


### -----------------------------Simulation Conditions SECTION---------------------------------- ###
def fetch_temperature(i):
	return str(i)

def fetch_time(input_conditions):
	return input_conditions["time"]

def fetch_atol(input_conditions):
	return input_conditions["atol"]

def fetch_rtol(input_conditions):
	return input_conditions["rtol"]

def format_conditions_section(input_conditions):
	simulation_conditions = []

	i = input_conditions["min_temperature"]
	while i <= input_conditions["max_temperature"]:
		temp = f"{fetch_temperature(i):<11} ; {fetch_time(input_conditions):<14} ; {fetch_atol(input_conditions):<6} ; {fetch_rtol(input_conditions):<6}"
		simulation_conditions.append(temp)
		i = i + 100

	return simulation_conditions

def fetch_pressure(user_inputs):
	return user_inputs["pressure"]

### -----------------------------MAIN FUCTION SECTION---------------------------------- ###
def list_to_string(input_list):
   return "\n".join(input_list)

# Main function 
def generate_input_file(user_inputs):
	# get the initial concertations from user interface 
	input_concentrations = user_inputs["initial_concentrations"]
	#generate concentation strings for file
	gas_compounds, surface_compounds, free_site_surface = sort_concentrations(input_concentrations)

	##### CHANGE so list of reaction data and NOT reaction ids - TO DO 
	# get the unique ids for each reaction from the user interface
	input_reactions = user_inputs["reaction_ids"]
	# get surface string for file 
	####TO DO - TO FIX 
	#surface = fetch_surface_composition(input_reactions[0])
	surface = fetch_surface_composition(input_reactions)

	# seperate the reactions into the 2 different types
	hk_reactions, ar_reactions = seperate_reactions(input_reactions)

	formatted_hk_section = format_hk_section(hk_reactions)
	formatted_ar_section = format_ar_section(ar_reactions)

	# get the simulation conditions from user interface 
	input_conditions = user_inputs["initial_conditions"]
	formatted_conditions_section = format_conditions_section(input_conditions)

	# File Formatting with data 
	input_file_string = default_file_format()
	formatted_input_file_string = input_file_string.format(
		list_to_string(gas_compounds),
		list_to_string(surface_compounds),
		surface,
		list_to_string(free_site_surface),
		list_to_string(formatted_hk_section),
		list_to_string(formatted_ar_section),
		fetch_pressure(user_inputs),
		"{}","{}",
		list_to_string(formatted_conditions_section))
	
	print(formatted_input_file_string)
	
	return formatted_input_file_string


if __name__ == '__main__':
	##### CHANGE so list of reaction data and NOT reaction ids - TO DO 
	user_inputs = {"initial_concentrations":{"CO2":"0.4", "H20":"0.6", "H":"0", "H2":"0", "CO":"0", "HCOOH":"0", "COOH*":"0", "*":"1", "CO*":"0", "CO2*":"0", "OCHO*":"0"},
				"reaction_ids":["1","2","3","4","5"],
				"initial_conditions":{"min_temperature": 300, "max_temperature": 900, "time": "10e5", "atol": "1e-8", "rtol": "1e-8"},
				"pressure": "1"}
	
	generate_input_file(user_inputs)