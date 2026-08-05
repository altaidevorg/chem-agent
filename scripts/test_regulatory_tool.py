import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.tools.regulatory_tools import CheckRegulatoryComplianceTool

def test_regulatory():
    tool = CheckRegulatoryComplianceTool()
    
    # Test 1: Check by Name (Lilial)
    res_name = tool.execute(["Lilial", "Pulegone"])
    print(f"\nTest 1 (Check by Name) Result:")
    for item in res_name["compliance_report"]:
        print(f"Molecule: {item['query']}")
        print(f"  IFRA Status: {item['ifra_status']}")
        print(f"  EU Status:   {item['eu_status']}")
        for detail in item["details"]:
            print(f"    - [{detail['source']}] {detail['substance']} ({detail['cas']}): {detail.get('limit', detail.get('restrictions'))}")
    
    # Test 2: Check by CAS (Lyral: 31906-04-4)
    res_cas = tool.execute(["31906-04-4"])
    print(f"\nTest 2 (Check by CAS - Lyral) Result:")
    for item in res_cas["compliance_report"]:
        print(f"CAS Query: {item['query']}")
        for detail in item["details"]:
            print(f"    - [{detail['source']}] {detail['substance']}: {detail['status']} / {detail['limit']}")

if __name__ == "__main__":
    test_regulatory()
