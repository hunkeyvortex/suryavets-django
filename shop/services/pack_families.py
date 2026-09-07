"""Conservative grouping of existing source-backed packs, never product-name fuzzy matching."""
import re
from collections import defaultdict
from decimal import Decimal

SIZE_SUFFIX=re.compile(r'\s*\((?:XXS|XS|S|M|L|XL|XXL|XXXL)\)\s*$',re.I)
PACK=re.compile(r'^\s*(\d+(?:\.\d+)?)\s*(KG|GM|G|ML|LTR|L)\s*$',re.I)
SLUG_PACK=re.compile(r'-\d+(?:-\d+)?(?:kg|gm|g|ml|ltr|l)$',re.I)


def pack_quantity(name):
    match=PACK.fullmatch(name)
    if not match or Decimal(match[1])<=0: return None
    unit={'GM':'g','G':'g','KG':'kg','ML':'ml','LTR':'L','L':'L'}[match[2].upper()]
    return Decimal(match[1]),unit


def slug_stem(slug):
    stripped=SLUG_PACK.sub('',slug)
    if stripped==slug: return None
    return re.sub(r'-(?:xxs|xs|s|m|l|xl|xxl|xxxl)$','',stripped,flags=re.I)


def candidates(products):
    buckets=defaultdict(list)
    for product in products:
        name=SIZE_SUFFIX.sub('',product.name).strip()
        buckets[(name.casefold(),product.brand_id,product.category_id,product.product_type_id,product.requires_prescription)].append(product)
    for key, members in buckets.items():
        if len(members)<2: continue
        reason=''; packs=[]; stems={slug_stem(p.slug) for p in members}
        for p in members:
            variants=list(p.variants.all())
            if len(variants)!=1 or not variants[0].is_active or not p.is_active:
                reason='Requires exactly one active pack per active source product'; break
            pack=variants[0]; parsed=pack_quantity(pack.name)
            if not parsed:
                reason='Pack quantity/unit needs manual verification'; break
            suffix=re.search(r'-(\d+(?:-\d+)?)(kg|gm|g|ml|ltr|l)$',p.slug,re.I)
            slug_pack=pack_quantity(suffix[1].replace('-','.')+suffix[2]) if suffix else None
            def normalized(value):
                q,u=value
                return ('mass' if u in ('g','kg') else 'volume',q/(1000 if u in ('g','ml') else 1))
            if not slug_pack or normalized(slug_pack)!=normalized(parsed):
                reason='Source handle quantity conflicts with pack option or is missing'; break
            if pack.current_price<=0:
                reason='Missing or zero selling price needs review'; break
            if pack.attributes and any(k.lower() not in ('pack','size','weight','option 1') for k in pack.attributes):
                reason='Additional option attributes need review'; break
            packs.append((p,pack,parsed))
        if not reason and (None in stems or len(stems)!=1): reason='Source handle stems do not match exactly'
        if not reason:
            dimensions={('mass' if unit in ('g','kg') else 'volume') for _,_,(_,unit) in packs}
            amounts=[q*(Decimal('0.001') if unit in ('g','ml') else 1) for _,_,(q,unit) in packs]
            if len(dimensions)>1 or len(set(amounts))!=len(amounts): reason='Duplicate or incomparable pack sizes need review'
        yield SIZE_SUFFIX.sub('',members[0].name).strip(),members,packs,reason


def family_products(product):
    root=product.variant_family if product.variant_family_id else product
    return [root,*[p for p in root.family_members.all() if p.is_active]]


def buying_variants(product):
    members=family_products(product)
    return [v for p in members if p.is_active for v in p.variants.all() if v.is_active]
