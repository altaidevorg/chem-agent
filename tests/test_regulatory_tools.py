# tests/test_regulatory_tools.py
import pytest
import os
from src.tools.regulatory_tools import CheckRegulatoryComplianceTool

def test_check_regulatory_compliance_seed_data():
    tool = CheckRegulatoryComplianceTool()
    # Coumarin is in our seed data
    result = tool.execute(molecule_names=["Coumarin"])
    
    assert result["status"] == "success"
    report = result["compliance_report"][0]
    assert report["molecule"] == "Coumarin"
    # In seed data, we used 'Active' as status for some entries, let's check details
    assert any("Coumarin" in d.get("restrictions", "") or d.get("status") == "Restricted" or d.get("source") == "EU 1334/2008" for d in report["details"])

def test_check_regulatory_compliance_banned():
    tool = CheckRegulatoryComplianceTool()
    # Safrole is in our seed data
    result = tool.execute(molecule_names=["Safrole"])
    
    assert result["status"] == "success"
    report = result["compliance_report"][0]
    # Check if Safrole was found
    assert len(report["details"]) > 0

def test_check_regulatory_compliance_learned_data():
    tool = CheckRegulatoryComplianceTool()
    # Cinnamaldehyde was learned by update script
    result = tool.execute(molecule_names=["Cinnamaldehyde"])
    
    assert result["status"] == "success"
    report = result["compliance_report"][0]
    # Should be found since we ran the update script
    assert report["ifra_status"] != "Not Found / GRAS"

def test_check_regulatory_compliance_not_found():
    tool = CheckRegulatoryComplianceTool()
    # Something unlikely to be in a regulatory DB
    result = tool.execute(molecule_names=["Methane"])
    
    assert result["status"] == "success"
    report = result["compliance_report"][0]
    assert report["ifra_status"] == "Not Found / GRAS"
    assert report["eu_status"] == "Not Found / GRAS"
