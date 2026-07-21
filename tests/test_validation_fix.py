import os
import sys

# Add project root to path
sys.path.append("/home/ubuntu/chem-agent")

from src.tools.schema_cache import SchemaCache

def test_validation_logic():
    print("Testing flexible column validation...")
    
    # Mock data
    file_path = "test.csv"
    columns = [
        {"name": "Machine ID", "sql_reference": '"Machine ID"'},
        {"name": "Temperature", "sql_reference": "Temperature"}
    ]
    
    # Register in cache
    SchemaCache.register(file_path, columns)
    
    # Test cases: (input_column, expected_valid)
    test_cases = [
        ("Machine ID", True),       # Exact match
        ('"Machine ID"', True),     # Quoted match (should be valid now)
        ("Temperature", True),      # Exact match
        ('"Temperature"', True),    # Quoted match (should be valid now)
        ("Invalid Col", False),     # Truly invalid
    ]
    
    all_passed = True
    for col, expected in test_cases:
        res = SchemaCache.validate_columns(file_path, [col])
        is_valid = res["valid"]
        status = "PASS" if is_valid == expected else "FAIL"
        print(f"Column: {col:15} | Expected: {expected} | Actual: {is_valid} | {status}")
        if is_valid != expected:
            all_passed = False
            
    if all_passed:
        print("\n✅ All validation tests passed!")
    else:
        print("\n❌ Some tests failed.")

if __name__ == "__main__":
    test_validation_logic()
