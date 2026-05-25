# import pytest  <- Removed to allow running without pytest installed
import os
import asyncio
from sabi.utils.cloud_data import (
    fetch_full_catalog, 
    fetch_movielens_user_profiles,
    fetch_regional_priors
)

# Replace pytest marker logic with simple async functions for manual verification
async def test_cloud_catalog_fetching():
    """
    Ensures that the catalog can be fetched either from cloud or local.
    We check for schema consistency.
    """
    catalog = await fetch_full_catalog(limit=5)
    
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    
    # Check schema consistency for the first item
    item = catalog[0]
    required_fields = ["item_id", "title", "category", "year"]
    for field in required_fields:
        assert field in item, f"Missing required field {field} in fetched item"

@pytest.mark.asyncio
async def test_movielens_profile_loading():
    """
    Ensures that MovieLens data can be streamed and processed.
    """
    profiles = await fetch_movielens_user_profiles(n_users=3)
    
    assert isinstance(profiles, dict)
    assert len(profiles) > 0
    
    # Check structure of a profile
    user_id = list(profiles.keys())[0]
    profile = profiles[user_id]
    
    assert "user_id" in profile
    assert "reviewed_items" in profile
    assert isinstance(profile["reviewed_items"], list)
    assert len(profile["reviewed_items"]) > 0

@pytest.mark.asyncio
async def test_regional_priors_loading():
    """
    Ensures regional priors (Nigerian behavior distributions) are loaded.
    """
    priors = await fetch_regional_priors()
    
    assert isinstance(priors, dict)
    assert "regions" in priors or "lagos" in str(priors).lower()
    
    # Verify we have at least some regional logic
    assert len(priors) > 0

if __name__ == "__main__":
    # Quick manual run script
    async def run_checks():
        print("🔍 Checking Cloud Catalog...")
        cat = await fetch_full_catalog(limit=2)
        print(f"✅ Loaded {len(cat)} items. Sample: {cat[0]['title']}")
        
        print("\n🔍 Checking MovieLens Streaming...")
        prof = await fetch_movielens_user_profiles(n_users=1)
        uid = list(prof.keys())[0]
        print(f"✅ Loaded profile for {uid} with {len(prof[uid]['reviewed_items'])} reviews")
        
    asyncio.run(run_checks())
