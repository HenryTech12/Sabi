
from datasets import load_dataset

datasets_to_try = [
    'includeno/movielens-100k',
    'HsSIn/MovieLens-100k',
    'AgustinPiaz/movielens-100k',
    'movie_lens',
    'movielens'
]

for ds_id in datasets_to_try:
    print(f"Trying {ds_id}...")
    try:
        ds = load_dataset(ds_id, streaming=True)
        # Try to get the first item to verify it's really working
        # Usually MovieLens has 'train' split
        split = 'train'
        if 'train' not in ds:
             # Just pick the first available split
             split = next(iter(ds.keys()))
        
        it = iter(ds[split])
        first_item = next(it)
        print(f"SUCCESS: {ds_id}")
        break
    except Exception as e:
        print(f"FAILED: {ds_id} - {str(e)[:100]}")
