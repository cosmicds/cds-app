import pandas as pd
from pathlib import Path
hubble_data = pd.read_csv(Path(__file__).parent / "Hubble 1929-Table 1.csv")
hst_data = pd.read_csv(Path(__file__).parent / "HSTkey2001.csv")
