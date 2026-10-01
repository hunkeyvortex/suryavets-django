#!/usr/bin/env python3
"""
Script to import all categories and subcategories from suryavets.com
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'suryavets.settings')
django.setup()

from shop.models import Category, Subcategory

# Exact categories and subcategories from suryavets.com
categories_data = {
    "Cat": {
        "Medicine For Cats": [
            "Allergy Relief For Cats", "Anti Biotic For Cats", "Anxiety Care For Cats",
            "Cancer Care For Cats", "Cardiac Care For Cats", "Dewormers For Cats",
            "Diabetes For Cats", "Eye & Ear Care For Cats", "Fleas & Ticks For Cats",
            "Gastro Intestinal & Digestive Care For Cats", "Hip & Joint Care For Cats",
            "Injectable For Cats", "Liver Care For Cats", "Neural Care For Cats",
            "Post Natal Care For Cats", "Pre Natal Care For Cats", "Respiratory Care For Cats",
            "Skin & Coat Care For Cats", "Thyroid For Cats", "Urinary Tract & Renal Care For Cats",
            "Vaccine For Cats", "Wound & Pain Relief For Cats"
        ],
        "Cat Supplements": [
            "Calcium supplements For Cats", "Liver supplements For Cats",
            "Renal & Urinary supplements For Cats", "Hip & Joint supplements For Cats",
            "Immunity supplements For Cats", "Skin & Coat supplements For Cats",
            "Intestinal & Digestive supplements For Cats", "Multi Vitamin For Cats",
            "Dental Care/Mouth Hygine For Cats"
        ],
        "Cat Food": [
            "Dry Food For Cats", "Infant Food For Cats", "Premium Food For Cats",
            "Veterinary Diets For Cats", "Wet Food For Cats"
        ],
        "Treats For Cats": [
            "Biscuits & Crunchy Treats For Cats", "Soft Treat For Cats"
        ],
        "Cat Supplies": [
            "Beds For Cats", "Cleaning Product For Cats", "Crates/Carriers/Penns For Cats",
            "Deos/Fragrance For Cats", "Grooming For Cats", "Leash/Collars & Harnesses For Cats",
            "Medical Accessory For Cats", "Medicated Shampoo For Cats", "Potty Articals For Cats",
            "Surgical Accessory For Cats", "Toys For Cats", "Bowls & Feeders For Cats"
        ]
    },
    "Dog": {
        "Medicine For Dogs": [
            "Allergy Relief For Dogs", "Anti Biotic For Dogs", "Anxiety Care For Dogs",
            "Cancer Care For Dogs", "Cardiac Care For Dogs", "Dewormers For Dogs",
            "Diabetes For Dogs", "Eye & Ear Care For Dogs", "Fleas & Ticks For Dogs",
            "Gastro Intestinal & Digestive Care For Dogs", "Hip & Joint Care For Dogs",
            "Injectable For Dogs", "Liver Care For Dogs", "Neural Care For Dogs",
            "Post Natal Care For Dogs", "Pre Natal Care For Dogs", "Respiratory Care For Dogs",
            "Skin & Coat Care For Dogs", "Thyroid For Dogs", "Urinary Tract & Renal Care For Dogs",
            "Vaccine For Dogs", "Wound & Pain Relief For Dogs"
        ],
        "Dog Supplements": [
            "Anxiety supplements For Dogs", "Calcium Supplements For Dogs",
            "Dental Care/Mouth Hygine For Dogs", "Immunity supplements For Dogs",
            "Intestinal & Digestive supplements For Dogs", "Liver supplements For Dogs",
            "Multi Vitamin For Dogs", "Renal & Urinary supplements For Dogs",
            "Skin & Coat supplements For Dogs", "Hip & Joint supplements For Dogs"
        ],
        "Dog Food": [
            "Dry Food For Dogs", "Infant Food For Dogs", "Premium Food For Dogs",
            "Veterinary Diets For Dogs", "Wet Food For Dogs"
        ],
        "Treats For Dogs": [
            "Biscuits & Crunchy Treats For Dogs", "Bones & Natural Chew For Dogs",
            "Dental Treat For Dogs", "Soft Treat For Dogs"
        ],
        "Dog Supplies": [
            "Beds For Dogs", "Cleaning Product For Dogs", "Clothing For Dogs",
            "Crates/Carriers/Penns For Dogs", "Deos/Fragrance For Dogs", "Gifting For Dogs",
            "Grooming For Dogs", "Leash/Collars & Harnesses For Dogs", "Medical Accessory For Dogs",
            "Medicated Shampoo For Dogs", "Potty Articals For Dogs", "Surgical Accessory For Dogs",
            "Toys For Dogs", "Training & Behaviour For Dogs", "Bowls & Feeders For Dogs"
        ]
    },
    "Farm Animals": {
        "Medicine For Farm Animals": [
            "Allergy Relief For Farm Animals", "Antibiotic For Farm Animals",
            "Cancer Care For Farm Animals", "Cardiac Care For Farm Animals",
            "Dewormers For Farm Animals", "Eye & Ear Care For Farm Animals",
            "Fleas & Ticks For Farm Animals", "Gastro Intestinal & Digestive Care For Farm Animals",
            "Hip & Joint Care For Farm Animals", "Injectable For Farm Animals",
            "Liver Care For Farm Animals", "Neural Care For Farm Animals",
            "Post Natal Care For Farm Animals", "Pre Natal Care For Farm Animals",
            "Respiratory Care For Farm Animals", "Skin & Coat Care For Farm Animals",
            "Thyroid For Farm Animals", "Urinary Tract & Renal Care For Farm Animals",
            "Vaccine For Farm Animals", "Wound & Pain Relief For Farm Animals"
        ],
        "Supplements For Farm Animals": [
            "Calcium supplements For Farm Animals", "Dental Care/Mouth Hygine For Farm Animals",
            "Hip & Joint supplements For Farm Animals", "Immunity supplements For Farm Animals",
            "Intestinal & Digestive supplements For Farm Animals", "Liver supplements For Farm Animals",
            "Multi Vitamin For Farm Animals", "Skin & Coat supplements For Farm Animals"
        ],
        "Supplies For Farm Animals": [
            "Cleaning Product For Farm Animals", "Feeders & Bowls For Farm Animals",
            "Grooming For Farm Animals", "Leash/Collars & Harnesses For Farm Animals",
            "Medical Accessory For Farm Animals", "Medicated Shampoo For Farm Animals",
            "Surgical Accessory For Farm Animals"
        ]
    },
    "Fish & Reptiles": {
        "Supplements For Fish & Reptiles": [
            "Calcium supplements For Fish/Reptiles", "Immunity supplements For Fish/Reptiles",
            "Multi Vitamin For Fish/Reptiles"
        ],
        "Food For Fish & Reptiles": [
            "Dry Food For Fish/Reptiles"
        ]
    },
    "Vaccination": {
        "Vaccination Services": [
            "Vaccination For Dogs", "Vaccination For Cats", "Vaccination For Farm Animals"
        ]
    }
}

def import_categories():
    """Import all categories and subcategories"""
    order = 0
    
    for category_name, subcategories_dict in categories_data.items():
        # Create or get category - replace & with 'and' for cleaner URLs
        category_slug = category_name.lower().replace(' ', '-').replace('&', 'and')
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={
                'slug': category_slug,
                'order': order,
                'is_active': True
            }
        )
        
        if created:
            print(f"Created category: {category_name} (slug: {category_slug})")
        else:
            print(f"Category already exists: {category_name}")
        
        # Import subcategories
        sub_order = 0
        for subcategory_name, sub_subcategories in subcategories_dict.items():
            # Replace & with 'and' and other special characters for cleaner URLs
            subcategory_slug = f"{category.slug}-{subcategory_name.lower().replace(' ', '-').replace('&', 'and').replace('/', '-')}"
            subcategory, created = Subcategory.objects.get_or_create(
                category=category,
                name=subcategory_name,
                defaults={
                    'slug': subcategory_slug,
                    'order': sub_order,
                    'is_active': True
                }
            )
            
            if created:
                print(f"  Created subcategory: {subcategory_name} (slug: {subcategory_slug})")
            else:
                print(f"  Subcategory already exists: {subcategory_name}")
            
            sub_order += 1
        
        order += 1
    
    print("\nAll categories and subcategories imported successfully!")

if __name__ == "__main__":
    import_categories()