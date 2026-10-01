#!/usr/bin/env python3
"""
Script to update category and subcategory slugs to remove special characters
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'suryavets.settings')
django.setup()

from shop.models import Category, Subcategory

def update_category_slugs():
    """Update all category slugs to replace & with 'and'"""
    for category in Category.objects.all():
        old_slug = category.slug
        new_slug = category.name.lower().replace(' ', '-').replace('&', 'and')
        if old_slug != new_slug:
            category.slug = new_slug
            category.save()
            print(f"Updated category slug: {old_slug} -> {new_slug}")
        else:
            print(f"Category slug already correct: {old_slug}")

def update_subcategory_slugs():
    """Update all subcategory slugs to replace special characters"""
    for subcategory in Subcategory.objects.all():
        old_slug = subcategory.slug
        new_slug = f"{subcategory.category.slug}-{subcategory.name.lower().replace(' ', '-').replace('&', 'and').replace('/', '-')}"
        if old_slug != new_slug:
            subcategory.slug = new_slug
            subcategory.save()
            print(f"Updated subcategory slug: {old_slug} -> {new_slug}")
        else:
            print(f"Subcategory slug already correct: {old_slug}")

if __name__ == "__main__":
    print("Updating category slugs...")
    update_category_slugs()
    print("\nUpdating subcategory slugs...")
    update_subcategory_slugs()
    print("\nAll slugs updated successfully!")
