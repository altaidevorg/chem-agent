# src/database/fetchers.py
import os
import pandas as pd
import requests
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from io import StringIO, BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        pass

class DGSanteFetcher(BaseFetcher):
    """
    Fetches the EU Union List of Flavourings.
    Uses the FSA standardized CSV which mirrors the EC 1334/2008 Annex I structure.
    """
    FSA_URL = "https://data.food.gov.uk/regulated-products/id/flavourings/flavouring.csv"

    def fetch(self, **kwargs) -> pd.DataFrame:
        logger.info("Attempting to fetch flavouring data from FSA (Union List Proxy)...")
        
        try:
            response = requests.get(self.FSA_URL, timeout=60)
            response.raise_for_status()
            df = pd.read_csv(BytesIO(response.content))
            
            # FSA API CSV Columns (verified):
            # 'flavisNo.code', 'prefLabel', 'casNo.code', 'notation', 'status', etc.
            
            mapping = {
                'flavisNo.code': 'fl_no',
                'prefLabel': 'chemical_name',
                'casNo.code': 'cas_no',
                'description': 'restrictions',
                'comment': 'conditions_of_use'
            }
            
            df = df.rename(columns=mapping)
            df['source'] = "DG SANTE / FSA Union List (API)"
            
            # Ensure required columns exist even if mapping failed
            for col in ['fl_no', 'chemical_name', 'cas_no']:
                if col not in df.columns:
                    df[col] = None
            
            return df
        except Exception as e:
            logger.error(f"Failed to fetch flavorings: {str(e)}")
            return pd.DataFrame()

class IFRAFetcher(BaseFetcher):
    """
    Fetches and transforms IFRA Standards (51st Amendment).
    Supports local file processing and handles the 'Wide to Long' conversion.
    """
    
    def fetch(self, file_path: Optional[str] = None, **kwargs) -> pd.DataFrame:
        if file_path and os.path.exists(file_path):
            return self._process_local_file(file_path)
        
        logger.warning("No local IFRA file provided. Returning mock data.")
        return self._get_mock_data()

    def _process_local_file(self, file_path: str) -> pd.DataFrame:
        """
        Parses IFRA Excel/CSV and transforms it into 'Long Format'.
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Standard IFRA columns: 'Substance Name', 'CAS', 'SMILES', 'Cat 1', 'Cat 2', ...
            # We need to unpivot these.
            id_vars = ['Substance Name', 'CAS', 'SMILES', 'Restriction Type']
            cat_columns = [col for col in df.columns if col.startswith('Cat') or col.isdigit()]
            
            long_df = pd.melt(
                df, 
                id_vars=id_vars, 
                value_vars=cat_columns,
                var_name='category_code', 
                value_name='max_concentration_pct'
            )
            
            # Clean up category codes (e.g., 'Cat 1' -> '1')
            long_df['category_code'] = long_df['category_code'].str.replace('Cat ', '').str.replace('Category ', '')
            
            # Rename for tool consumption
            long_df = long_df.rename(columns={
                'Substance Name': 'substance_name',
                'CAS': 'cas_no',
                'SMILES': 'smiles',
                'Restriction Type': 'restriction_type'
            })
            
            return long_df
        except Exception as e:
            logger.error(f"IFRA Parsing Error: {str(e)}")
            return pd.DataFrame()

    def _get_mock_data(self) -> pd.DataFrame:
        data = [
            {"cas_no": "122-78-1", "category_code": "1", "max_concentration_pct": 0.01, "restriction_type": "Restricted", "substance_name": "Phenylacetaldehyde", "smiles": "c1ccc(CC=O)cc1"},
            {"cas_no": "122-78-1", "category_code": "4", "max_concentration_pct": 0.5, "restriction_type": "Restricted", "substance_name": "Phenylacetaldehyde", "smiles": "c1ccc(CC=O)cc1"},
            {"cas_no": "101-86-0", "category_code": "1", "max_concentration_pct": 0.0, "restriction_type": "Prohibited", "substance_name": "Hexyl Cinnamic Aldehyde", "smiles": "CCCCCCC=C(C=O)c1ccccc1"},
        ]
        return pd.DataFrame(data)
