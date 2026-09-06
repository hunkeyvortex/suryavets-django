"""Match exported collection tags exactly; never infer medical use from descriptions."""
from collections import defaultdict
from django.utils.text import slugify
from shop.models import Category


def collection_tag_index():
    index = defaultdict(set)
    for node in Category.objects.exclude(reference_path=''):
        keys = {node.slug, slugify(node.name), node.reference_path.rstrip('/').rsplit('/', 1)[-1]}
        # Shopify uses both "Cat Food" menu labels and "food-for-cats" tags.
        for pet, plural in [('Cat', 'Cats'), ('Dog', 'Dogs')]:
            for group in ['Food', 'Supplements', 'Supplies']:
                if node.name == f'{pet} {group}':
                    keys.add(slugify(f'{group} For {plural}'))
        for key in keys:
            index[key].add(node.pk)
    return index


def matching_collections(tags, index):
    return set().union(*(index.get(slugify(tag), set()) for tag in tags)) if tags else set()
