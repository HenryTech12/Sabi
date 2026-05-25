
from datasets import load_dataset

candidates = [
    'sentence-transformers/movielens-100k',
    'DukeNLPGroup/movielens-100k',
    'harisarang/movielens-100k',
    'includeno/movielens-100k',
    'MovieLens'
]

for ds_id in candidates:
    print(f"Testing {ds_id}...")
    try:
        # Some datasets require trust_remote_code
        ds = load_dataset(ds_id, streaming=True, trust_remote_code=True)
        split = next(iter(ds))
        item = next(iter(ds[split]))
        print(f"SUCCESS: {ds_id}")
        # print first item keys
        print(f"Keys: {list(item.keys())}")
        break
    except Exception as e:
        print(f"FAILED: {ds_id} - {str(e)[:200]}")
