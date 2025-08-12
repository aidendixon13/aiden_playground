#!/usr/bin/env python3
"""
Simple scratch file to test the MockExpansionCountService
"""
import asyncio
from wernicke.tests.mocks.onestream_metadata.expansion_count.expansion_count import MockExpansionCountService
from wernicke.tests.shared_utils.test_session import create_test_user_session


def test_mock_expansion_service():
    """Test the MockExpansionCountService with known data."""
    print("🧪 Testing MockExpansionCountService")
    
    # Create test user session
    user_session_info = create_test_user_session()
    
    # Create mock service
    mock_service = MockExpansionCountService(user_session_info=user_session_info)
    
    print(f"📄 Loaded expansion data with {len(mock_service.expansion_data)} keys")
    print(f"🔑 Available keys: {list(mock_service.expansion_data.keys())[:10]}...")  # Show first 10 keys
    
    # Test cases - these should exist in your JSON file
    test_cases = [
        {
            "member_expansion": "A#40000.Base",
            "potential_dim_names": ["Equipment Accounts Actuals"]
        },
        {
            "member_expansion": "A#40000.Tree", 
            "potential_dim_names": ["Equipment Accounts Actuals"]
        },
        {
            "member_expansion": "A#40000.Children",
            "potential_dim_names": ["Equipment Accounts Actuals"]
        },
        {
            "member_expansion": "A#40000.ChildrenInclusive",
            "potential_dim_names": ["Equipment Accounts Actuals"]
        },
        {
            "member_expansion": "A#60999.Base",
            "potential_dim_names": ["Some Account"]
        },
        {
            "member_expansion": "A#NonExistent.Tree",
            "potential_dim_names": ["Some Account"]
        }
    ]
    
    print("\n📊 Testing expansion count lookups:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        member_expansion = test_case["member_expansion"]
        potential_dim_names = test_case["potential_dim_names"]
        
        try:
            count = mock_service.get_member_expansion_count(
                member_expansion=member_expansion,
                potential_dim_names=potential_dim_names
            )
            print(f"✅ Test {i}: {member_expansion} = {count}")
            
        except ValueError as e:
            print(f"❌ Test {i}: {member_expansion} - {str(e)[:100]}...")
        except Exception as e:
            print(f"💥 Test {i}: {member_expansion} - Unexpected error: {str(e)[:100]}...")
    
    print("\n" + "="*50)
    print("🎯 Test Summary:")
    print(f"   - Mock service loaded {len(mock_service.expansion_data)} entries")
    print(f"   - JSON file path: source/wernicke/tests/mocks/onestream_metadata/expansion_count/expansion_count.json")
    print("   - Test completed!")


if __name__ == "__main__":
    test_mock_expansion_service()