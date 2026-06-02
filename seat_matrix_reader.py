from collections import Counter, defaultdict
from pathlib import Path
import re
import sqlite3
import pandas as pd
import pypdf


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
    'Computer Science and Engineering': '4110',
    'Electrical Engineering': '4111',
    'Electrical Engineering (Power and Automation)': '4112',
    'Electronics Engineering': '4113',
    'Electronics and Communication Engineering': '4114',
    'Electronics and Electrical Communication Engineering': '4115',
    'Electronics and Electrical Engineering': '4116',
    'Engineering Physics': '4117',
    'Engineering Science': '4118',
    'Environmental Engineering': '4119',
    'B.Tech in Materials Science and Engineering': '411D',
    'B.Tech in Microelectronics & VLSI': '411E',
    'B.Tech in Mathematics and Computing': '411F',
    'Artificial Intelligence and Data Engineering': '411G',
    'Biological Engineering': '411N',
    'Instrumentation Engineering': '4121',
    'Manufacturing Science and Engineering': '4122',
    'Materials Science and Engineering': '4123',
    'Mathematics and Computing': '4124',
    'Mechanical Engineering': '4125',
    'Metallurgical Engineering': '4126',
    'Metallurgical and Materials Engineering': '4127',
    'Metallurgical Engineering and Materials Science': '4128',
    'Industrial Engineering and Operations Research': '412I',
    'Integrated Circuit Design & Technology': '412J',
    'Artificial Intelligence and Data Analytics': '412L',
    'Biochemical Engineering': '412M',
    'Bioengineering': '412N',
    'Materials Science and Technology': '412O',
    'Design': '412T',
    'ComputationalEngineeringandMechanics': '412U',
    'InstrumentationandBiomedicalEngineering': '412V',
    'DigitalAgriculture': '412W',
    'AbuDhabiCampus-ComputerScienceandEngineering': '412Z',
    'AbuDhabiCampus-EnergyEngineering': '412[', 
    'MiningEngineering': '4130',
    'MiningMachineryEngineering':'4131',
    'NavalArchitectureandOceanEngineering':'4132',
    'OceanEngineeringandNavalArchitecture': '4133',
    'PetroleumEngineering': '4134',
    'ProductionandIndustrialEngineering': '4136',
    'TextileTechnology': '4139',
    'AbuDhabiCampus-ChemicalEngineering':'413A',
    'ElectricalEngineering(IntegratedCircuitDesignandTechnology)':'413B',
    'SpaceScienceandEngineering':'413I',
    'CivilandInfrastructureEngineering':'4141',
    'BioEngineering':'4143',
    'ElectricalandElectronicsEngineering':'4144',
    'MaterialsScienceandMetallurgicalEngineering':'4161',
    'IndustrialandSystemsEngineering':'4170',
    'PharmaceuticalEngineering&Technology':'4173',
    'MechatronicsEngineering':'4178',
    'DataScienceandArtificialIntelligence':'4181',
    'ArtificialIntelligence':'4185',
    'DataScienceandEngineering':'4187',
    'ArtificialIntelligenceandDataScience':'4188',
    'MineralandMetallurgicalEngineering':'4189',
    'BiomedicalEngineering':'4191',
    'EngineeringandComputationalMechanics':'4192',
    'MaterialsEngineering':'4193',
    'BiosciencesandBioengineering':'4194',
    'EnergyEngineering':'4198',
    'BiotechnologyandBioinformatics':'4199',
    'Chemistry':'4201',
    'Economics': '4202',
    'MathematicsandScientificComputing': '4203',
    'Physics': '4204',
    'EarthSciences': '4205',
    'BSinMathematics': '4206',
    'StatisticsandDataScience':'4207',
    'MathematicsandComputing': '4208',
    'AppliedGeology': '4209',
    'ExplorationGeophysics': '4210',
    'PhysicswithSpecialization': '4211',
    'ChemistrywithSpecialization': '4212',
    'BSinChemicalSciences': "4213",
    'BiologicalScience': '4214',
    'AppliedGeophysics': '4215'

}

DEFAULT_PDF_PATH = 'JICReport2025.pdf'
DEFAULT_CACHE_DB = 'iit_branch_seats.db'



DEFAULT_PAGE_START_SEAT_MATRIX = 299
DEFAULT_PAGE_END_SEAT_MATRIX = 499

def get_available_branches():
    return sorted(BRANCH_CODE_MAP.keys())

def _resolve_branch_code(branch_name):
    if branch_name not in BRANCH_CODE_MAP:
        raise ValueError(f"Unknown branch: {branch_name}")
    return BRANCH_CODE_MAP[branch_name]

def _parse_all_branch_seat_counts(pdf_path=DEFAULT_PDF_PATH, page_start=DEFAULT_PAGE_START_SEAT_MATRIX, page_end=DEFAULT_PAGE_END_SEAT_MATRIX):
    pdf_file = Path(pdf_path)
    reader = pypdf.PdfReader(str(pdf_file))
    branch_codes = sorted(set(BRANCH_CODE_MAP.values()), key=len, reverse=True)
    code_to_branch = {code: name for name, code in BRANCH_CODE_MAP.items()}
    branch_counts = defaultdict(Counter)
    pattern = re.compile(rf"\b\d{{9}}\s+(\d{{3}})\s+({'|'.join(map(re.escape, branch_codes))})\b")

    last_page = min(page_end, len(reader.pages))
    for page_num in range(page_start, last_page):
        page_text = reader.pages[page_num].extract_text() or ""
        for institute_code, branch_code in pattern.findall(page_text):
            branch_name = code_to_branch.get(branch_code)
            if branch_name:
                branch_counts[branch_name][institute_code] += 1

    rows = []
    for branch_name, counts in branch_counts.items():
        branch_code = _resolve_branch_code(branch_name)
        for institute_code, seat_count in counts.items():
            institute_name = IIT_MAPPING.get(institute_code)
            if institute_name:
                rows.append(
                    {
                        'branch_name': branch_name,
                        'branch_code': branch_code,
                        'institute_code': institute_code,
                        'institute_name': institute_name,
                        'seats_taken': int(seat_count),
                    }
                )

    return rows

def initialize_branch_cache_db(db_path=DEFAULT_CACHE_DB, pdf_path=DEFAULT_PDF_PATH, force_rebuild=False):
    """Build or refresh the branch seat cache database from the PDF report."""

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF report not found: {pdf_path}")

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS branch_seat_counts (
            branch_name TEXT NOT NULL,
            branch_code TEXT NOT NULL,
            institute_code TEXT NOT NULL,
            institute_name TEXT NOT NULL,
            seats_taken INTEGER NOT NULL,
            PRIMARY KEY (branch_name, institute_code)
        );

        CREATE INDEX IF NOT EXISTS idx_branch_seat_counts_branch
        ON branch_seat_counts (branch_name, seats_taken DESC, institute_code ASC);
        """
    )

    if force_rebuild:
        cursor.execute("DELETE FROM branch_seat_counts")

    existing_count = cursor.execute("SELECT COUNT(*) FROM branch_seat_counts").fetchone()[0]
    if existing_count == 0 or force_rebuild:
        rows = _parse_all_branch_seat_counts(pdf_path=pdf_path)

        cursor.executemany(
            """
            INSERT OR REPLACE INTO branch_seat_counts
            (branch_name, branch_code, institute_code, institute_name, seats_taken)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row['branch_name'],
                    row['branch_code'],
                    row['institute_code'],
                    row['institute_name'],
                    row['seats_taken'],
                )
                for row in rows
            ],
        )

    connection.commit()
    connection.close()


def get_iit_branch_seat_counts(branch_name, db_path=DEFAULT_CACHE_DB):
    """Read precomputed branch seat counts from the cache database."""

    connection = sqlite3.connect(db_path)
    query = """
        SELECT institute_code AS [Institute Code],
               institute_name AS [Institute Name],
               seats_taken AS [Seats Taken]
        FROM branch_seat_counts
        WHERE branch_name = ?
        ORDER BY seats_taken DESC, institute_code ASC
    """
    result_df = pd.read_sql(query, connection, params=(branch_name,))
    connection.close()
    return result_df


if __name__ == '__main__':
    initialize_branch_cache_db(force_rebuild=True)