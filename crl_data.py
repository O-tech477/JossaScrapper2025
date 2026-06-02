import numpy as np
import pandas as pd
import csv
import sqlite3
from tabula.io import read_pdf

IIT_MAPPING = {
    '101': 'IIT Bhubaneswar', 
    '102': 'IIT Bombay', 
    '103': 'IIT Mandi',
    '104': 'IIT Delhi', 
    '105': 'IIT Indore', 
    '106': 'IIT Kharagpur',
    '107': 'IIT Hyderabad', 
    '108': 'IIT Jodhpur', 
    '109': 'IIT Kanpur',
    '110': 'IIT Madras', 
    '111': 'IIT Gandhinagar', 
    '112': 'IIT Patna',
    '113': 'IIT Roorkee', 
    '114': 'IIT (ISM) Dhanbad', 
    '115': 'IIT Ropar',
    '116': 'IIT (BHU) Varanasi', 
    '117': 'IIT Guwahati', 
    '118': 'IIT Bhilai',
    '119': 'IIT Goa', 
    '120': 'IIT Palakkad', 
    '121': 'IIT Tirupati',
    '122': 'IIT Jammu', 
    '123': 'IIT Dharwad'
}

BRANCH_CODE_MAP = {
    '4101':'AerospaceEngineering',
    '4102':'AgriculturalandFoodEngineering',
    '4103':'BiologicalSciencesandBioengineering',
    '4105':'BiotechnologyandBiochemicalEngineering',
    '4106':'CeramicEngineering',
    '4107' : 'ChemicalEngineering',
    '4108' : 'ChemicalScienceandTechnology',
    '4109':'CivilEngineering',
    '410A' : 'ComputationalEngineering',
    '410B' : 'IndustrialChemistry',
    '410D' : 'ChemicalandBiochemicalEngineering',
    '410T' : 'ElectricalEngineering(ICDesignandTechnology)',
    '410U' : 'EnvironmentalScienceandEngineering',
    '410Y': 'B.TechinGeneralEngineering',
    '4110': 'Computer Science and Engineering',
    '4111': 'Electrical Engineering',
    '4112': 'Electrical Engineering (Power and Automation)',
    '4113': 'Electronics Engineering',
    '4114': 'Electronics and Communication Engineering',
    '4115': 'Electronics and Electrical Communication Engineering',
    '4116': 'Electronics and Electrical Engineering',
    '4117': 'Engineering Physics',
    '4118': 'Engineering Science',
    '4119': 'Environmental Engineering',
    '411D': 'B.Tech in Materials Science and Engineering',
    '411E': 'B.Tech in Microelectronics & VLSI',
    '411F': 'B.Tech in Mathematics and Computing',
    '411G': 'Artificial Intelligence and Data Engineering',
    '411N': 'Biological Engineering',
    '4121': 'Instrumentation Engineering',
    '4122': 'Manufacturing Science and Engineering',
    '4123': 'Materials Science and Engineering',
    '4124': 'Mathematics and Computing',
    '4125': 'Mechanical Engineering',
    '4126': 'Metallurgical Engineering',
    '4127': 'Metallurgical and Materials Engineering',
    '4128': 'Metallurgical Engineering and Materials Science',
    '412I': 'Industrial Engineering and Operations Research',
    '412J': 'Integrated Circuit Design & Technology',
    '412L': 'Artificial Intelligence and Data Analytics',
    '412M': 'Biochemical Engineering',
    '412N': 'Bioengineering',
    '412O': 'Materials Science and Technology',
    '412T': 'Design',
    '412U': 'ComputationalEngineeringandMechanics',
    '412V': 'InstrumentationandBiomedicalEngineering',
    '412W': 'DigitalAgriculture',
    '412Z': 'AbuDhabiCampus-ComputerScienceandEngineering',
    '412[': 'AbuDhabiCampus-EnergyEngineering',
    '4130': 'MiningEngineering',
    '4131': 'MiningMachineryEngineering',
    '4132': 'NavalArchitectureandOceanEngineering',
    '4133': 'OceanEngineeringandNavalArchitecture',
    '4134': 'PetroleumEngineering',
    '4136': 'ProductionandIndustrialEngineering',
    '4139': 'TextileTechnology',
    '413A': 'AbuDhabiCampus-ChemicalEngineering',
    '413B': 'ElectricalEngineering(IntegratedCircuitDesignandTechnology)',
    '413I': 'SpaceScienceandEngineering',
    '4141': 'CivilandInfrastructureEngineering',
    '4143': 'BioEngineering',
    '4144': 'ElectricalandElectronicsEngineering',
    '4161': 'MaterialsScienceandMetallurgicalEngineering',
    '4170': 'IndustrialandSystemsEngineering',
    '4173': 'PharmaceuticalEngineering&Technology',
    '4178': 'MechatronicsEngineering',
    '4181': 'DataScienceandArtificialIntelligence',
    '4185': 'ArtificialIntelligence',
    '4187': 'DataScienceandEngineering',
    '4188': 'ArtificialIntelligenceandDataScience',
    '4189': 'MineralandMetallurgicalEngineering',
    '4191': 'BiomedicalEngineering',
    '4192': 'EngineeringandComputationalMechanics',
    '4193': 'MaterialsEngineering',
    '4194': 'BiosciencesandBioengineering',
    '4198': 'EnergyEngineering',
    '4199': 'BiotechnologyandBioinformatics',
    '4201': 'Chemistry',
    '4202': 'Economics',
    '4203': 'MathematicsandScientificComputing',
    '4204': 'Physics',
    '4205': 'EarthSciences',
    '4206': 'BSinMathematics',
    '4207': 'StatisticsandDataScience',
    '4208': 'MathematicsandComputing',
    '4209': 'AppliedGeology',
    '4210': 'ExplorationGeophysics',
    '4211': 'PhysicswithSpecialization',
    '4212': 'ChemistrywithSpecialization',
    '4213': 'BSinChemicalSciences',
    '4214': 'BiologicalScience',
    '4215': 'AppliedGeophysics',
    '5101': 'Architecture(5years)',
    '5201':'AerospaceEngineering(5years)',
    '5210': 'ChemicalEngineering(5years)',
    '5216': 'ComputerScienceandEngineering(5years)',
    '5217' : 'ElectricalEngineering(5years)',
    '521Q' : 'B.TechinElectronicsandCommunicationEngineeringandMTechinCommunicationSystems',
    '5227' : 'EngineeringDesign(5years)',
    '5254' : 'MathematicsandComputing(5years)',
    '5302' : 'GeologicalTechnology(5years)',
    '5303' : 'GeophysicalTechnology(5years)',
    '5306' : 'AppliedGeology(5years)',
    '5307' : 'AppliedGeophysics(5years)',
    '5406' : 'B.Tech(ChemicalScienceandTechnology)-MBAinHospitalandHealthCareManagement(IIMBodhGaya)',
    '5407' : 'B.Tech(CivilEngineering)-MBA(IIMBodhGaya)',
    '5408' : 'B.Tech(ComputerScienceandEngineering)-MBAinDigitalBusinessManagement(IIMBodhGaya)',
    '5409' : 'B.Tech(ElectronicsandCommunicationEngineering)-MBAinHospitalandHealthcareManagement(IIMBodhGaya)',
    '5410' : 'B.Tech(EngineeringPhysics)-MBA(IIMBodhGaya)',
    '5411' : 'B.Tech(MathematicsandComputing)-MBAinDigitalBusinessManagement(IIMBodhGaya)',
    '5412' : 'B.Tech(MetallurgicalandMaterialsEngineering)-MBA(IIMBodhGaya)',
    '5413' : 'B.Tech(ElectricalandElectronicsEngineering)-MBA(IIMBodhGaya)',
    '5414' : 'B.Tech(ArtificialIntelligenceandDataScience)-MBAinDigitalBusinessManagement(IIMBodhGaya)',
    '5415' : 'B.Tech(ChemicalEngineering)-MBAinHospitalandHealthCareManagement(IIMBodhGaya)',
    '5416' : 'B.Tech(MechanicalEngineering)-MBA(IIMMumbai)',
    '5602' : 'Physics(5years)',
    '5606' : 'Mathematics&Computing(5years)',
    '5607' : 'ChemicalSciences(5years)',
    '5608' : 'Economics(5years)',
    '5609' : 'InterdisciplinarySciences(5years)',
    '5A03' : 'B.TechinCE.-M.Tech.inGeotechnicalEngineering(5years)',
    '5A04' : 'B.TechinCE.-M.Tech.inStructuralEngineering(5years)',
    '5A05'  : 'B.Tech.(CSE)andM.TechinCSE',
    '5A06' : 'B.Tech.(ECE)-M.Tech. inVLSI',
    '5A07' : 'B.Tech.(EEE)-M.Tech. in(Power&.Control)',
    '5A09' : 'B.Tech.(Mathematics&Computing)M.Tech.in(Mathematics&Computing)',
    '5A10' : 'B.Tech. (ME)-M.Tech. inMechatronics',
    '5C02': 'BTechMiningEngineeringandMBAinLogisticandSupplyChainManagement(IIMMumbai)',
    '5F0A' : 'BSinEconomicswithMBA(IIMBodhGaya)',
    '5H0A': 'PhysicalScience(5years)',
    '5H2B': 'ChemicalScience(5years)'
}

def create_table():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    #cursor.execute("CREATE TABLE crl_vs_alloted (rank INTEGER, insti_name VARCHAR, branch VARCHAR)")
    
    with open("trial.csv", "r") as f:
        reader = csv.reader(f)
        for i in reader:
            if len(i) != 0:
                row1 = i[0:4]
                row2 = i[4:]
                print("Row1:", row1)
                print("Row2:", row2)

                cursor.executemany(
                    "INSERT INTO crl_vs_alloted (rank, insti_name, branch) VALUES (?, ?, ?)",
                    [
                        (int(row1[0]), IIT_MAPPING[row1[2]], BRANCH_CODE_MAP[row1[3]]),
                        (int(row2[0]), IIT_MAPPING[row2[2]], BRANCH_CODE_MAP[row2[3]]),
                    ],
                )
    conn.commit()

def create_csv():
    pages = [i for i in range(307, 385)]
    print(pages)
    allotted_crl_table = read_pdf("JICReport2025.pdf", pages = pages)

    combined_tables = pd.concat(allotted_crl_table, ignore_index=True)
    combined_tables = combined_tables.to_numpy()

    with open("trial.csv", "w") as f:
        writer = csv.writer(f)
        for i in combined_tables:
            writer.writerow(i)

def get_btw_ranks(lower, upper):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT rank, insti_name, branch FROM crl_vs_alloted WHERE rank >= ? AND rank <= ? ORDER BY rank ASC",
        (lower, upper),
    )
    result = cursor.fetchall()
    conn.close()

    return result

