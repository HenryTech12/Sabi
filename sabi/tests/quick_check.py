import asyncio
from sabi.utils.cloud_data import fetch_full_catalog, fetch_movielens_user_profiles

async def main():
    print("--- SABI Cloud Integration Check ---")
    try:
        print("1. Testing Catalog (TMDB/Local)...")
        cat = await fetch_full_catalog(limit=2)
        print(f"   SUCCESS: Loaded {len(cat)} items.")
        if cat:
            print(f"   Sample Item: {cat[0].get('title', 'Unknown')}")
            
        print("\n2. Testing MovieLens (HuggingFace)...")
        # Use a small number to avoid long downloads in tests
        # Correcting the argument name from n_users to num_users
        prof = await fetch_movielens_user_profiles(num_users=1)
        print(f"   SUCCESS: Loaded {len(prof)} profiles.")
        if prof:
            profile = prof[0]  # Response is a list of profiles
            uid = profile.get('user_id', 'Unknown')
            print(f"   Sample Profile: User {uid} from {profile.get('detected_region', 'Unknown')} with {len(profile['reviewed_items'])} reviews.")
            
        print("\n--- All Cloud Systems Operational ---")
    except Exception as e:
        print(f"\n❌ CHECK FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
