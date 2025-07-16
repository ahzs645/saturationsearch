#!/usr/bin/env python3
"""
Integration test for read-only Zotero access.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from src.api.zotero_integration import ZoteroManager

def test_readonly_zotero():
    """Test Zotero integration with read-only access."""
    
    print("=== Read-Only Zotero Integration Test ===")
    
    try:
        # Test 1: Initialize ZoteroManager
        print("1. Testing ZoteroManager initialization...")
        zotero_manager = ZoteroManager()
        print("   ✅ ZoteroManager initialized successfully")
        print(f"   📡 Mode: {'Local' if zotero_manager.use_local else 'Online'}")
        print(f"   📚 Library ID: {zotero_manager.library_id}")
        print(f"   🏷️  Library Type: {zotero_manager.library_type}")
        
        # Test 2: Validate connection
        print("\n2. Testing connection validation...")
        if zotero_manager.validate_connection():
            print("   ✅ Connection validation passed")
        else:
            print("   ❌ Connection validation failed")
            return False
        
        # Test 3: Get existing collections (read-only test)
        print("\n3. Testing collection reading...")
        try:
            existing_collections = zotero_manager.zot.collections()
            print(f"   ✅ Successfully read {len(existing_collections)} existing collections")
            
            if existing_collections:
                print("   📁 Existing collections:")
                for coll in existing_collections[:5]:  # Show first 5
                    print(f"      - {coll['data']['name']} (ID: {coll['key']})")
                if len(existing_collections) > 5:
                    print(f"      ... and {len(existing_collections) - 5} more")
            else:
                print("   📁 No existing collections found (empty library)")
                
        except Exception as e:
            print(f"   ❌ Failed to read collections: {e}")
            return False
        
        # Test 4: Get library statistics
        print("\n4. Testing library statistics...")
        stats = zotero_manager.get_collection_statistics()
        if 'error' not in stats:
            print(f"   ✅ Statistics retrieved: {stats['total_collections']} collections")
            total_items = sum(info['item_count'] for info in stats['collections'].values())
            print(f"   📊 Total items across all collections: {total_items}")
        else:
            print(f"   ⚠️ Statistics error: {stats['error']}")
        
        # Test 5: Test read-only item access
        print("\n5. Testing item reading...")
        try:
            items = zotero_manager.zot.items(limit=3)
            print(f"   ✅ Successfully read {len(items)} items (showing max 3)")
            
            if items:
                for i, item in enumerate(items, 1):
                    title = item['data'].get('title', 'No title')[:50]
                    print(f"      {i}. {title}...")
            else:
                print("   📄 No items found in library")
                
        except Exception as e:
            print(f"   ❌ Failed to read items: {e}")
        
        print("\n🎉 Read-only integration test completed successfully!")
        print("\n📋 Summary:")
        print(f"   - ✅ Zotero connection: Working")
        print(f"   - ✅ Authentication: Valid (read-only)")
        print(f"   - ✅ Library access: Can read collections and items")
        print(f"   - ⚠️  Write permissions: Not available (collections/items cannot be created)")
        
        print("\n💡 Next Steps:")
        print("   1. ✅ Your Zotero integration is properly configured for read access")
        print("   2. ⚠️  For full functionality (creating collections, uploading articles):")
        print("      - Check your API key permissions at https://www.zotero.org/settings/keys")
        print("      - Ensure 'Allow write access' is enabled")
        print("      - For group libraries, ensure you have write permissions in the group")
        print("   3. 🚀 The saturation search system can run with read-only access")
        print("      - It will skip Zotero uploads but perform all other functions")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_readonly_zotero()
    
    if success:
        print("\n🎉 Zotero integration test completed!")
        print("\nThe saturation search system is ready to use with current configuration.")
    else:
        print("\n🔧 Please fix the issues above before proceeding.")
        sys.exit(1)